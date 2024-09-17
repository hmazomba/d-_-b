import getpass
import os

os.environ["GROQ_API_KEY"] = getpass.getpass()

from langchain_groq import ChatGroq

llm = ChatGroq(model="llama3-8b-8192")

llm_with_tools = llm.bind_tools(tools)

query = "What is 3 * 12?"

llm_with_tools.invoke(query)