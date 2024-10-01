import logging
from typing import List, Dict, Any, Annotated, Optional
from pathlib import Path
from tempfile import TemporaryDirectory
from functools import partial
from dotenv import load_dotenv
import os

from langgraph.graph import StateGraph, END, START
from langchain_core.messages import HumanMessage, BaseMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_cohere import CohereEmbeddings
from langchain_community.document_loaders import WebBaseLoader, DirectoryLoader, RecursiveUrlLoader
from langchain_community.document_loaders.merge import MergedDataLoader
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_experimental.utilities import PythonREPL
from typing_extensions import TypedDict

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
COHERE_API_KEY = os.getenv('COHERE_API_KEY')

if not GOOGLE_API_KEY or not COHERE_API_KEY:
    logger.error("API keys not found. Please check your .env file.")
    raise ValueError("API keys not found. Please check your .env file.")

# Initialize LLM and Embeddings
llm = ChatGoogleGenerativeAI(model="gemini-1.5-pro-exp-0827", google_api_key=GOOGLE_API_KEY)
embeddings = CohereEmbeddings(model="embed-english-v3.0", cohere_api_key=COHERE_API_KEY)

# Set up temporary directory
_TEMP_DIRECTORY = TemporaryDirectory()
WORKING_DIRECTORY = Path(_TEMP_DIRECTORY.name)

# Tools
tavily_tool = TavilySearchResults(max_results=5)
repl = PythonREPL()

@tool
def scrape_webpages(urls: List[str]) -> str:
    """Scrape the provided web pages for detailed information."""
    try:
        loader = WebBaseLoader(urls)
        docs = loader.load()
        return "\n\n".join([f'\n{doc.page_content}\n' for doc in docs])
    except Exception as e:
        logger.error(f"Error scraping webpages: {e}")
        return f"Error scraping webpages: {str(e)}"

@tool
def create_outline(points: List[str], file_name: str) -> str:
    """Create and save an outline."""
    try:
        with (WORKING_DIRECTORY / file_name).open("w") as file:
            for i, point in enumerate(points):
                file.write(f"{i + 1}. {point}\n")
        return f"Outline saved to {file_name}"
    except Exception as e:
        logger.error(f"Error creating outline: {e}")
        return f"Error creating outline: {str(e)}"

@tool
def read_document(file_name: str, start: Optional[int] = None, end: Optional[int] = None) -> str:
    """Read the specified document."""
    try:
        with (WORKING_DIRECTORY / file_name).open("r") as file:
            lines = file.readlines()
        if start is None:
            start = 0
        return "\n".join(lines[start:end])
    except Exception as e:
        logger.error(f"Error reading document: {e}")
        return f"Error reading document: {str(e)}"

@tool
def write_document(content: str, file_name: str) -> str:
    """Create and save a text document."""
    try:
        with (WORKING_DIRECTORY / file_name).open("w") as file:
            file.write(content)
        return f"Document saved to {file_name}"
    except Exception as e:
        logger.error(f"Error writing document: {e}")
        return f"Error writing document: {str(e)}"

@tool
def edit_document(file_name: str, inserts: Dict[int, str]) -> str:
    """Edit a document by inserting text at specific line numbers."""
    try:
        with (WORKING_DIRECTORY / file_name).open("r") as file:
            lines = file.readlines()

        sorted_inserts = sorted(inserts.items())

        for line_number, text in sorted_inserts:
            if 1 <= line_number <= len(lines) + 1:
                lines.insert(line_number - 1, text + "\n")
            else:
                return f"Error: Line number {line_number} is out of range."

        with (WORKING_DIRECTORY / file_name).open("w") as file:
            file.writelines(lines)

        return f"Document edited and saved to {file_name}"
    except Exception as e:
        logger.error(f"Error editing document: {e}")
        return f"Error editing document: {str(e)}"

@tool
def python_repl(code: str):
    """Execute Python code."""
    try:
        result = repl.run(code)
        return f"Successfully executed:\n```python\n{code}\n```\nStdout: {result}"
    except Exception as e:
        logger.error(f"Error executing Python code: {e}")
        return f"Failed to execute. Error: {repr(e)}"

class SEOTeamState(TypedDict):
    messages: Annotated[List[BaseMessage], lambda x, y: x + y]
    team_members: List[str]
    next: str
    current_files: str

class SEOTeam:
    def __init__(self):
        self.team_members = ["SEO Expert", "Copywriter", "HubSpot Developer", "UI/UX Expert"]
        self.graph = self._create_graph()

    def _create_graph(self) -> StateGraph:
        def prelude(state):
            try:
                written_files = [f.relative_to(WORKING_DIRECTORY) for f in WORKING_DIRECTORY.rglob("*")]
                if not written_files:
                    return {**state, "current_files": "No files written."}
                return {
                    **state,
                    "current_files": "\nBelow are files your team has written to the directory:\n"
                    + "\n".join([f" - {f}" for f in written_files]),
                }
            except Exception as e:
                logger.error(f"Error in prelude: {e}")
                return {**state, "current_files": "Error reading current files."}

        def create_agent_node(name: str, tools: List[Any]):
            agent = self._create_react_agent(tools)
            context_aware_agent = prelude | agent
            return partial(self._agent_node, agent=context_aware_agent, name=name)

        seo_expert_node = create_agent_node("SEO Expert", [tavily_tool, scrape_webpages])
        copywriter_node = create_agent_node("Copywriter", [write_document, edit_document, read_document])
        hubspot_dev_node = create_agent_node("HubSpot Developer", [python_repl, read_document])
        uiux_expert_node = create_agent_node("UI/UX Expert", [create_outline, read_document])

        graph = StateGraph(SEOTeamState)
        graph.add_node("SEO Expert", seo_expert_node)
        graph.add_node("Copywriter", copywriter_node)
        graph.add_node("HubSpot Developer", hubspot_dev_node)
        graph.add_node("UI/UX Expert", uiux_expert_node)
        graph.add_node("supervisor", self._create_team_supervisor())

        for member in self.team_members:
            graph.add_edge(member, "supervisor")

        graph.add_conditional_edges(
            "supervisor",
            lambda x: x["next"],
            {member: member for member in self.team_members} | {"FINISH": END}
        )

        graph.add_edge(START, "supervisor")
        return graph.compile()

    def _create_react_agent(self, tools: List[Any]):
        from langchain.agents import create_react_agent
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are an AI assistant specialized in {role}. Use the following tools to assist you: {tool_names}"),
            MessagesPlaceholder(variable_name="messages"),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])
        return create_react_agent(llm, tools, prompt)

    def _agent_node(self, state, agent, name):
        try:
            result = agent.invoke(state)
            return {"messages": [HumanMessage(content=result["messages"][-1].content, name=name)]}
        except Exception as e:
            logger.error(f"Error in agent node {name}: {e}")
            return {"messages": [HumanMessage(content=f"Error in {name} node: {str(e)}", name=name)]}

    def _create_team_supervisor(self):
        options = ["FINISH"] + self.team_members
        function_def = {
            "name": "route",
            "description": "Select the next role.",
            "parameters": {
                "title": "routeSchema",
                "type": "object",
                "properties": {
                    "next": {
                        "title": "Next",
                        "anyOf": [
                            {"enum": options},
                        ],
                    },
                },
                "required": ["next"],
            },
        }
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a supervisor managing a conversation between: {team_members}. Given the user request, who should act next?"),
            MessagesPlaceholder(variable_name="messages"),
            ("system", "Select one of: {options}"),
        ]).partial(options=str(options), team_members=", ".join(self.team_members))

        from langchain.output_parsers.openai_functions import JsonOutputFunctionsParser
        return (
            prompt
            | llm.bind_functions(functions=[function_def], function_call="route")
            | JsonOutputFunctionsParser()
        )

    def run(self, query: str):
        try:
            chain = self._enter_chain | self.graph
            for s in chain.stream(query, {"recursion_limit": 100}):
                if "__end__" not in s:
                    yield s
        except Exception as e:
            logger.error(f"Error running SEO Team: {e}")
            yield {"error": f"Error running SEO Team: {str(e)}"}

    @property
    def _enter_chain(self):
        def enter_chain(message: str):
            return {
                "messages": [HumanMessage(content=message)],
                "team_members": self.team_members,
            }
        return enter_chain

# Usage example
seo_team = SEOTeam()
query = "Analyze our website's SEO performance and suggest improvements."
for step in seo_team.run(query):
    print(step)
    print("---")