
from typing import Any, Dict, Union
import yaml
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.prebuilt import create_react_agent
from langchain_community.agent_toolkits.openapi.toolkit import RequestsToolkit
from langchain_community.utilities.requests import TextRequestsWrapper
from langchain_google_genai import ChatGoogleGenerativeAI

from dotenv import load_dotenv
import os

def _get_schema(response_json: Union[dict, list]) -> dict:
    if isinstance(response_json, list):
        response_json = response_json[0] if response_json else {}
    return {key: type(value).__name__ for key, value in response_json.items()}

def _get_api_spec() -> str:
    base_url = "https://example.com"
    endpoints = [
        "/fetch",
    ]
    common_query_parameters = [
        {
            "name": "url",
            "in": "query",
            "required": True,
            "schema": {"type": "string", "example": "https://example.com"},
            "description": "URL to fetch",
        },
        {
            "name": "num_pages",
            "in": "query",
            "required": True,
            "schema": {"type": "integer", "example": 10},
            "description": "Number of pages to crawl",
        },
        {
            "name": "num_links",
            "in": "query",
            "required": True,
            "schema": {"type": "integer", "example": 3},
            "description": "Number of child links to follow",
        },
    ]
    openapi_spec: Dict[str, Any] = {
        "openapi": "3.0.0",
        "info": {"title": "Webpage Fetcher API", "version": "1.0.0"},
        "servers": [{"url": base_url}],
        "paths": {},
    }
    # Iterate over the endpoints to construct the paths
    for endpoint in endpoints:
        openapi_spec["paths"][endpoint] = {
            "get": {
                "summary": f"Fetch webpage content",
                "parameters": common_query_parameters,
                "responses": {
                    "200": {
                        "description": "Successful response",
                        "content": {
                            "text/plain": {
                                "schema": {"type": "string"}
                            }
                        },
                    }
                },
            }
        }
    return yaml.dump(openapi_spec, sort_keys=False)

api_spec = _get_api_spec()

toolkit = RequestsToolkit(
    requests_wrapper=TextRequestsWrapper(headers={}),
    allow_dangerous_requests=True,
)
tools = toolkit.get_tools()

# Load environment variables from .env file
load_dotenv()
google_api_key = os.getenv('GOOGLE_API_KEY')
llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash")

system_message = """
You have access to an API to help answer user queries.
Here is documentation on the API:
{api_spec}
""".format(api_spec=api_spec)

agent_executor = create_react_agent(llm, tools, state_modifier=system_message)
example_query = "Fetch webpage content from https://python.langchain.com/docs/integrations/tools/requests and tell me what is the main purpose of this website."

events = agent_executor.stream(
    {"messages": [("user", example_query)]},
    stream_mode="values",
)
for event in events:
    event["messages"][-1].pretty_print()


