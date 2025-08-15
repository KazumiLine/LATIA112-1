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

from .tools import ToolsBuilder

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
你是一個禮貌且簡潔的助理，可以回答問題、查詢產品資訊、存取文件內容，以及協助下單。
請嚴格遵守以下規則：

1. **只有在必要時才使用工具**
   - `product_sql_tool`：僅用於從資料庫取得產品描述或規格。
   - `order_sql_tool`：用於查詢訂單資訊。
   - `docs_tool`：用於回答文件中的問題。
   - `place_order_tool`：在所有必要資訊齊全後才用於下單。
   - `request_more_info_tool`：用於向使用者詢問缺少的必要資訊。

2. **保持禮貌與簡潔**
   - 如果可以辨識使用者的語言，則用相同語言回覆。
   - 避免重複同一個問題超過兩次。

3. **謹慎詢問缺失的資訊**
   - 只詢問完成任務所必須的欄位。
   - 提供清楚的例子，例如產品名稱格式或電子郵件格式。

4. **逐步推理**
   - 思考使用者的需求。
   - 決定要用哪個工具。
   - 如果要使用 `sql_tool`，先推敲正確的 WHERE 條件再寫 SQL。
   - 展示推理過程後再呼叫工具。
   - 觀察工具輸出，然後回覆使用者。

5. **避免工具連續呼叫**
   - 每個問題只能呼叫**一個工具**。
   - 觀察工具輸出後，必須先更新推理，再決定是否呼叫下一個工具。

6. **使用者資訊**
    - 使用者 ID 或電子郵件將用於記憶範圍。
    - 每個使用者的記憶是獨立的。
"""

class AgentBuilder:

    def __init__(self, store_id: int, user_id: str):
        os.makedirs(os.path.join(os.getcwd(), "storage"), exist_ok=True)

        # Configure global settings
        Settings.llm = get_llm()
        Settings.embed_model = HuggingFaceEmbedding(model_name="BAAI/bge-small-en-v1.5")

        self.chat_store = SimpleChatStore()
        chat_store_path = os.path.join(os.getcwd(), "storage", "chat_store.json")
        # self.chat_store.from_persist_path(chat_store_path)
        self.memory = ChatMemoryBuffer.from_defaults(chat_store=self.chat_store, chat_store_key=user_id, token_limit=4000)

        tools_builder = ToolsBuilder(store_id, user_id)

        self.agent = ReActAgent(system_prompt=PROMPT, tools=tools_builder.build_tools(), memory=self.memory, llm=Settings.llm, verbose=True, max_iterations=3)
        self.ctx = Context(self.agent)
        self.ctx.set("store_id", store_id)
        self.ctx.set("user_id", user_id)

    async def chat(self, user_input: str) -> str:
        handler = self.agent.run(user_input, context=self.ctx, memory=self.memory)
        async for ev in handler.stream_events():
            if isinstance(ev, ToolCallResult):
                print(f"\nCall {ev.tool_name} with {ev.tool_kwargs}\nReturned: {ev.tool_output}")
                if ev.tool_name == "request_more_info_tool":
                    handler.cancel_run()
                    return ev.tool_output
            if isinstance(ev, AgentStream):
                print(f"{ev.delta}", end="", flush=True)

        response = await handler
        return str(response)
    
    def save(self):
        chat_store_path = os.path.join(os.getcwd(), "storage", "chat_store.json")
        self.chat_store.persist(chat_store_path)