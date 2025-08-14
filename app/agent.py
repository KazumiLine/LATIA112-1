import os
from typing import List
from llama_index.core.agent import ReActAgent
from llama_index.core.workflow import Context
from llama_index.core.agent.workflow import AgentStream, ToolCallResult
from llama_index.core.memory import ChatMemoryBuffer
from llama_index.core.storage.chat_store import SimpleChatStore
from llama_index.core import Settings

from llama_index.llms.ollama import Ollama
from llama_index.llms.openai_like import OpenAILike
from llama_index.embeddings.huggingface import HuggingFaceEmbedding

from .tools import build_product_sql_tool, build_order_sql_tool, build_docs_tool, place_order_tool, request_more_info_tool

def get_llm():
    # OLLAMA_MODEL = "qwen3:8b" 
    # OLLAMA_ENDPOINT = "http://localhost:11434/api/chat"
    # return Ollama(model=OLLAMA_MODEL, endpoint=OLLAMA_ENDPOINT)
    return OpenAILike(
        model="gemini-2.5-flash",
        api_base="https://gemini.kzm.pw/openai/v1",
        api_key="sk-G@ry1203",
        context_window=128000,
        is_chat_model=True,
        is_function_calling_model=True,
    )

PROMPT = """
You are a helpful, concise assistant that can answer questions, retrieve product information, access documentation, and place orders. 
Follow these rules:

1. **Use tools only when necessary.**
   - `product_sql_tool`: to get product descriptions or specifications.
   - `order_sql_tool`: to retrieve order information.
   - `docs_tool`: to answer questions from documentation.
   - `place_order_tool`: to place an order once all required information is available.
   - `request_more_info_tool`: to ask the user for missing information needed to complete a task.

2. **Be polite and concise**.  
   - Always respond in the user's language if detectable.
   - Avoid repeating the same question more than twice.

3. **Request missing information carefully**.  
   - Only ask for fields you really need to complete the request.
   - Provide clear examples, e.g., product names or email formats.

4. **Reason step by step** (ReAct style).  
   - Think about what the user wants.
   - Decide which tool to use.
   - Show your reasoning before executing the tool.
   - Observe the tool's output, and then answer the user.

5. **Stop the loop**:
   - You may only call **one tool per question**.
   - After observing the output of a tool, you must update your reasoning before calling any next tool.

"""

class AgentBuilder:

    def __init__(self, user_id: str):
        os.makedirs(os.path.join(os.getcwd(), "storage"), exist_ok=True)

        # Configure global settings
        Settings.llm = get_llm()
        Settings.embed_model = HuggingFaceEmbedding(model_name="BAAI/bge-small-en-v1.5")

        self.chat_store = SimpleChatStore()
        chat_store_path = os.path.join(os.getcwd(), "storage", "chat_store.json")
        self.chat_store.from_persist_path(chat_store_path)
        self.memory = ChatMemoryBuffer.from_defaults(chat_store=self.chat_store, chat_store_key=user_id, token_limit=4000)

        tools = [
            build_product_sql_tool(),
            build_order_sql_tool(),
            build_docs_tool(),
            place_order_tool,
            request_more_info_tool,
        ]

        self.agent = ReActAgent(prompt=PROMPT, tools=tools, memory=self.memory, llm=Settings.llm, verbose=True, max_iterations=3)
        self.ctx = Context(self.agent)

    async def chat(self, user_input: str) -> str:
        handler = self.agent.run(user_input, context=self.ctx, memory=self.memory)
        call_tool_count = 0
        async for ev in handler.stream_events():
            if isinstance(ev, ToolCallResult):
                print(f"\nCall {ev.tool_name} with {ev.tool_kwargs}\nReturned: {ev.tool_output}")
                call_tool_count += 1
                if call_tool_count >= 2:
                    print("\nYou can only call one tool per question. Please provide the missing information or ask a new question.")
                    break
            if isinstance(ev, AgentStream):
                print(f"{ev.delta}", end="", flush=True)

        response = await handler
        return str(response)
    
    def save(self):
        chat_store_path = os.path.join(os.getcwd(), "storage", "chat_store.json")
        self.chat_store.persist(chat_store_path)