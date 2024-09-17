from langchain_google_genai import ChatGoogleGenerativeAI

from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()


google_api__key = os.getenv('GOOGLE_API_KEY')



llm = ChatGoogleGenerativeAI(model="gemini-1.5-pro-exp-0827")
result = llm.invoke("What is life?")
print(result.content)