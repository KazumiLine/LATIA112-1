import os
from typing import List, Dict, Any, Optional

from llama_index.core.tools import QueryEngineTool, ToolMetadata, FunctionTool
from llama_index.core.indices.vector_store import VectorStoreIndex
from llama_index.core import SimpleDirectoryReader
from llama_index.experimental.query_engine import NLSQLTableQueryEngine

from .db import get_sql_database, place_order_in_db, OrderItemInput


def build_product_sql_tool() -> QueryEngineTool:
    sql_db = get_sql_database()
    qe = NLSQLTableQueryEngine(sql_database=sql_db, tables=["products"])
    return QueryEngineTool(
        query_engine=qe,
        metadata=ToolMetadata(
            name="product_sql_tool",
            description=(
                "Use this tool to answer questions about product catalog, product names, prices, stock, or descriptions. "
                "It converts natural language to SQL over the 'products' table."
            ),
        ),
    )


def build_order_sql_tool() -> QueryEngineTool:
    sql_db = get_sql_database()
    qe = NLSQLTableQueryEngine(sql_database=sql_db, tables=["orders", "order_items", "customers", "products"])
    return QueryEngineTool(
        query_engine=qe,
        metadata=ToolMetadata(
            name="order_sql_tool",
            description=(
                "Use this tool to answer questions about orders, order status, order items, customers, and related details. "
                "It converts natural language to SQL over orders, order_items, customers, and products tables."
            ),
        ),
    )


DOCS_DIR = os.environ.get("APP_DOCS_DIR", os.path.join(os.getcwd(), "docs"))


def build_docs_tool() -> QueryEngineTool:
    documents = SimpleDirectoryReader(DOCS_DIR, required_exts=[".md", ".txt"]).load_data()
    index = VectorStoreIndex.from_documents(documents)
    qe = index.as_query_engine(similarity_top_k=3)
    return QueryEngineTool(
        query_engine=qe,
        metadata=ToolMetadata(
            name="policy_docs_tool",
            description=(
                "Use this tool to answer questions about purchasing process, returns, warranty, or after-sales service based on local policy documents."
            ),
        ),
    )


# FunctionTool: place order

def _place_order(customer_email: str, items: List[Dict[str, Any]]) -> Dict[str, Any]:
    parsed_items = [OrderItemInput(sku=str(i["sku"]), quantity=int(i["quantity"])) for i in items]
    return place_order_in_db(customer_email=customer_email, items=parsed_items)


place_order_tool = FunctionTool.from_defaults(
    fn=_place_order,
    name="place_order",
    description=(
        "Place an order. Use this tool when the user wants to buy products. "
        "Arguments: customer_email (str), items (list of {sku: str, quantity: int})."
    ),
)


# FunctionTool: request more info when user query lacks details

def _request_more_info(missing_fields: List[str], context: Optional[str] = None) -> str:
    fields = ", ".join(missing_fields)
    prefix = "To proceed, please provide the following details" if not context else f"{context}\n\nTo proceed, please provide the following details"
    return f"{prefix}: {fields}."


request_more_info_tool = FunctionTool.from_defaults(
    fn=_request_more_info,
    name="request_more_info",
    description=(
        "Ask the user to supply missing details required to answer their question or fulfill a request. "
        "Use when the user's query is ambiguous or missing required fields (e.g., missing SKU, order id, email)."
    ),
)