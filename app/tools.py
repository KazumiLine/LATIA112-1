from dataclasses import dataclass
import os
from typing import List, Dict, Any, Optional

from llama_index.core.tools import QueryEngineTool, ToolMetadata, FunctionTool
from llama_index.core.indices.vector_store import VectorStoreIndex
from llama_index.core import SimpleDirectoryReader, StorageContext, load_index_from_storage
from llama_index.core.query_engine import NLSQLTableQueryEngine
from llama_index.core.callbacks import CallbackManager, CBEventType, LlamaDebugHandler
from llama_index.core.prompts import PromptTemplate, PromptType
from typing import Any, Dict, List

from .models import get_sql_database
from .models import Store, Coupon, User, RealName, Product, ProductItem, Order, OrderItem, Delivery, Payment, WalletRecord, Interrogation, ProductFullView
from .models import PageType, AdminLevel, CouponType, DeliveryStatus, ProductStatus, OrderStatus, PaymentStatus, UserLevel, WalletType, DeliveryMethod

DOCS_DIR = os.environ.get("APP_DOCS_DIR", os.path.join(os.getcwd(), "docs"))

# Helper to place order imperatively
@dataclass
class OrderItemInput:
    name: str
    quantity: int

class ToolsBuilder:
    def __init__(self, store_id: int, user_id: str):
        self.store_id = store_id
        self.user_id = user_id
        self.sql_db = get_sql_database()
        self.text_to_sql_prompt = PromptTemplate("""
You are an expert SQL assistant for an online store. 
Given an input question, generate a syntactically correct {dialect} SQL query to answer it. 
Then, review the results of the query and provide the final answer.

Follow these strict rules:

1. **Fuzzy and Multilingual Search**:
   - If the question involves product names or catalogs, use a fuzzy matching approach:
     - Prefer `LOWER(column) LIKE LOWER('%%keyword%%')` for case-insensitive partial matches.
     - For multilingual support, also consider matching using transliterated or translated keywords if available in the database.
     - When matching multiple keywords, use `OR` between fuzzy matches.
   
2. **Select Only Relevant Columns**:
   - Never use `SELECT *`.
   - Choose only the columns that are directly needed to answer the question.
   - Use only columns and tables listed in the provided schema.
   - Always check that the column belongs to the table you are querying.

3. **Qualify Column Names**:
   - Prefix columns with their table name if there is any ambiguity.

4. **Apply Business Constraints**:
   - When querying the `orders` table, always add `WHERE user_id = %s`.
   - When querying the `products` table, always add `WHERE store_id = %d`.
   - If searching for products, also include the fuzzy match in the `WHERE` clause.

5. **Limit & Order**:
   - Always limit results to a reasonable number (e.g., `LIMIT 10`) unless otherwise specified.
   - Order results by the most relevant metric:
     - By `created_at` (newest first) for new products or orders
     - By `price` if explicitly requested in the question.

6. **Output Format**:
   Output exactly in the following format, each on its own line:

   Question: Question here
   SQLQuery: SQL Query to run
   SQLResult: Result of the SQLQuery
   Answer: Final answer here

---

Only use the schema provided below:
{schema}

Question: {query_str}
SQLQuery:

"""%(self.user_id, self.store_id), prompt_type=PromptType.TEXT_TO_SQL)
        self.callback_manager = CallbackManager([LlamaDebugHandler(print_trace_on_end=True)])

    def build_tools(self) -> List[QueryEngineTool]:
        return [
            self.build_product_sql_tool(),
            self.build_order_sql_tool(),
            self.build_docs_tool(),
            self.build_place_order_tool(),
            self.build_request_more_info_tool(),
        ]

    def build_product_sql_tool(self) -> QueryEngineTool:
        qe = NLSQLTableQueryEngine(sql_database=self.sql_db, tables=[ProductFullView.__table__], callback_manager=self.callback_manager, text_to_sql_prompt=self.text_to_sql_prompt)
        return QueryEngineTool(
            query_engine=qe,
            metadata=ToolMetadata(
                name="product_sql_tool",
                description=(
                    "此工具用於查詢產品相關資訊，包括產品目錄、名稱、價格、庫存及描述等。"
                    "它會將使用者的自然語言問題轉換成 SQL 語句，並在 'product_full_view' 資料表中執行查詢。"
                    "適合用於需要依條件篩選、比對或取得產品詳細資訊的情境。"
                ),
            ),
        )

    def build_order_sql_tool(self) -> QueryEngineTool:
        qe = NLSQLTableQueryEngine(sql_database=self.sql_db, tables=[Order.__table__, OrderItem.__table__, User.__table__, Product.__table__, ProductItem.__table__], callback_manager=self.callback_manager, text_to_sql_prompt=self.text_to_sql_prompt)
        return QueryEngineTool(
            query_engine=qe,
            metadata=ToolMetadata(
                name="order_sql_tool",
                description=(
                    "此工具用於查詢訂單相關資訊，包括訂單狀態、訂單項目、使用者及相關細節等。"
                    "它會將使用者的自然語言問題轉換成 SQL 語句，並在 'orders'、'order_items'、'users'、'products' 與 'product_items' 資料表中執行查詢。"
                    "適合用於需要查詢訂單歷史、狀態或特定訂單項目的情境。"
                ),
            ),
        )

    def build_docs_tool(self) -> QueryEngineTool:
        if not os.path.exists(os.path.join(os.getcwd(), "storage", "index_store.json")):  # First time, build index
            documents = SimpleDirectoryReader(DOCS_DIR, required_exts=[".md", ".txt"]).load_data()
            index = VectorStoreIndex.from_documents(documents)
            index.storage_context.persist(persist_dir=os.path.join(os.getcwd(), "storage"))
        else:
            storage_context = StorageContext.from_defaults(persist_dir=os.path.join(os.getcwd(), "storage"))
            index = load_index_from_storage(storage_context)
        qe = index.as_query_engine(similarity_top_k=3)
        return QueryEngineTool(
            query_engine=qe,
            metadata=ToolMetadata(
                name="policy_docs_tool",
                description=(
                    "此工具用於查詢購買流程、退貨、保固或售後服務等問題，並根據當地政策文件提供答案。"
                ),
            ),
        )

    def _place_order_in_db(self, items: List[OrderItemInput], destination: str) -> Dict[str, Any]:
        """在資料庫建立訂單，並扣除庫存"""
        from .models import SessionLocal
        with SessionLocal() as session:
            # 找使用者
            user = session.query(User).filter(User.id == self.user_id).one_or_none()
            if user is None:
                raise ValueError(f"Unknown user ID: {self.user_id}")
            # 建立訂單
            order = Order(store_id=self.store_id, user_id=user.id, status=OrderStatus.PENDING, delivery=Delivery(destination=destination, status=DeliveryStatus.PENDING), order_items=[], total=0)
            session.add(order)

            # 處理每一個訂單項目
            for item in items:
                product_view = session.query(ProductFullView).filter(ProductFullView.full_name == item.name).one_or_none()
                if product_view is None:
                    raise ValueError(f"Unknown name: {item.name}")
                if product_view.stock < item.quantity:
                    raise ValueError(f"Insufficient stock for name {item.name}. Available: {product_view.stock}")

                # 扣庫存
                product_item = session.query(ProductItem).filter(ProductItem.id == product_view.product_item_id).one_or_none()
                if product_item is None:
                    raise ValueError(f"Unknown product ID: {product_view.product_item_id}")
                product_item.stock -= item.quantity

                # 建立訂單明細
                order_item = OrderItem(
                    product_item_id=product_view.product_item_id,
                    quantity=item.quantity,
                )
                order.order_items.append(order_item)
                order.total += product_view.price * item.quantity

            if len(order.order_items) == 0:
                raise ValueError("No valid items to order.")
            # 提交交易
            session.commit()

            # 回傳訂單資訊
            session.refresh(order)
            result = {
                "order_id": order.id,
                "user_email": user.email,
                "status": order.status,
                "items": [
                    {
                        "name": session.get(ProductItem, oi.product_item_id).name,
                        "quantity": oi.quantity,
                        "unit_price": session.get(ProductItem, oi.product_item_id).price,
                        "line_total": round(oi.quantity * session.get(ProductItem, oi.product_item_id).price, 2),
                    }
                    for oi in order.order_items
                ],
            }
            result["order_total"] = round(sum(i["line_total"] for i in result["items"]), 2)
            return result

    def place_order(self, items: List[Dict[str, Any]], destination: str) -> Dict[str, Any]:
        parsed_items = [OrderItemInput(name=i["name"], quantity=int(i["quantity"])) for i in items]
        return self._place_order_in_db( items=parsed_items, destination=destination)


    def build_place_order_tool(self) -> FunctionTool:
        return FunctionTool.from_defaults(
            fn=self.place_order,
            name="place_order",
            description=(
                "此工具用於下訂單，當使用者想要購買產品時可以使用。"
                "參數: items (list of {name: str, quantity: int}), destination (str)."
            ),
        )

    def request_more_info(self, missing_fields: List[str], context: Optional[str] = None) -> str:
        fields = ", ".join(missing_fields)
        prefix = "To proceed, please provide the following details" if not context else f"{context}\n\nTo proceed, please provide the following details"
        return f"{prefix}: {fields}.\n----\nwaiting user to input"


    def build_request_more_info_tool(self) -> FunctionTool:
        return FunctionTool.from_defaults(
            fn=self.request_more_info,
            name="request_more_info",
            description=(
                "此工具用於請求使用者提供更多資訊，以便回答問題或滿足請求。"
                "請檢查完整的產品項目名稱。"
                "當使用者的查詢不明確或缺少必要欄位（例如：缺少名稱、數量、目的地）時，請使用此工具。"
        ),
    )