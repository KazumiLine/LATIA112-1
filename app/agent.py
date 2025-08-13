import os
from typing import List
from llama_index.core.agent import ReActAgent
from llama_index.core.memory import ChatMemoryBuffer, SimpleChatStore
from llama_index.core import Settings

from llama_index.llms.openai import OpenAI
from llama_index.llms.mock import MockLLM

from .tools import build_product_sql_tool, build_order_sql_tool, build_docs_tool, place_order_tool, request_more_info_tool


def get_llm():
    api_key = os.environ.get("OPENAI_API_KEY")
    if api_key:
        return OpenAI(model="gpt-4o-mini", temperature=0.1)
    # Fallback mock LLM for offline/dev
    return MockLLM(max_tokens=256)


def build_user_agent(user_id: str) -> ReActAgent:
    os.makedirs(os.path.join(os.getcwd(), "storage"), exist_ok=True)

    # Configure global settings
    Settings.llm = get_llm()

    chat_store_path = os.path.join("storage", "chat_store.json")
    chat_store = SimpleChatStore(persist_path=chat_store_path)
    memory = ChatMemoryBuffer.from_defaults(chat_store=chat_store, chat_store_key=user_id, token_limit=4000)

    tools = [
        build_product_sql_tool(),
        build_order_sql_tool(),
        build_docs_tool(),
        place_order_tool,
        request_more_info_tool,
    ]

    agent = ReActAgent.from_tools(tools=tools, memory=memory, llm=Settings.llm, verbose=True)
    return agent