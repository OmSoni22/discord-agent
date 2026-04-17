import asyncio
import os
from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool
from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage
from dotenv import load_dotenv

load_dotenv()

class WebSearchInput(BaseModel):
    query: str = Field(description="The search query")

class WebSearchTool(BaseTool):
    name: str = "web_search"
    description: str = "Search the web"
    args_schema: type[BaseModel] = WebSearchInput

    def _run(self, query):
        return "Not implemented"

async def main():
    from langchain_groq import ChatGroq
    llm = ChatGroq(
        model="llama-3.3-70b-versatile",
        api_key=os.getenv("API_KEY")
    )
    tools = [WebSearchTool()]
    llm_with_tools = llm.bind_tools(tools, parallel_tool_calls=False)
    
    messages = [HumanMessage(content="Search for Anthropics latest news")]
    import sys
    async for chunk in llm_with_tools.astream(messages):
        print(chunk)

if __name__ == "__main__":
    asyncio.run(main())
