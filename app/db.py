import os
from typing import List, Dict, Any
from dataclasses import dataclass
from sqlalchemy import create_engine, Column, Integer, String, Float, ForeignKey, Text, DateTime, func
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from sqlalchemy.engine import Engine

# SQLAlchemy setup
Base = declarative_base()

class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True)
    sku = Column(String(64), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    price = Column(Float, nullable=False)
    stock = Column(Integer, nullable=False, default=0)

class Customer(Base):
    __tablename__ = "customers"
    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, nullable=False)
    name = Column(String(255), nullable=False)

class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    status = Column(String(50), nullable=False, default="created")
    created_at = Column(DateTime, server_default=func.now())

    customer = relationship("Customer", backref="orders")
    items = relationship("OrderItem", backref="order", cascade="all, delete-orphan")

class OrderItem(Base):
    __tablename__ = "order_items"
    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Float, nullable=False)

    product = relationship("Product")

DB_PATH = os.environ.get("APP_DB_PATH", os.path.join(os.getcwd(), "storage", "app.db"))
DB_URI = f"sqlite:///{DB_PATH}"

SessionLocal = None  # will be initialized in get_engine


def get_engine(echo: bool = False) -> Engine:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    engine = create_engine(DB_URI, echo=echo, future=True)
    global SessionLocal
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    return engine


def init_db(seed: bool = True) -> None:
    engine = get_engine()
    Base.metadata.create_all(engine)

    if not seed:
        return

    # Seed sample data if empty
    with SessionLocal() as session:
        if session.query(Product).count() == 0:
            products = [
                Product(sku="SKU-1001", name="Wireless Mouse", description="Ergonomic wireless mouse", price=29.99, stock=120),
                Product(sku="SKU-1002", name="Mechanical Keyboard", description="RGB mechanical keyboard", price=89.50, stock=80),
                Product(sku="SKU-1003", name="USB-C Hub", description="7-in-1 USB-C hub", price=49.00, stock=150),
                Product(sku="SKU-1004", name="27-inch 4K Monitor", description="IPS 4K UHD monitor", price=329.00, stock=35),
            ]
            session.add_all(products)

        if session.query(Customer).count() == 0:
            customers = [
                Customer(email="alice@example.com", name="Alice"),
                Customer(email="bob@example.com", name="Bob"),
            ]
            session.add_all(customers)

        session.commit()


# Helper to place order imperatively
@dataclass
class OrderItemInput:
    sku: str
    quantity: int


def place_order_in_db(customer_email: str, items: List[OrderItemInput]) -> Dict[str, Any]:
    engine = get_engine()
    with SessionLocal() as session:
        customer = session.query(Customer).filter(Customer.email == customer_email).one_or_none()
        if customer is None:
            customer = Customer(email=customer_email, name=customer_email.split("@")[0])
            session.add(customer)
            session.flush()

        order = Order(customer_id=customer.id, status="created")
        session.add(order)
        session.flush()

        for item in items:
            product = session.query(Product).filter(Product.sku == item.sku).one_or_none()
            if product is None:
                raise ValueError(f"Unknown SKU: {item.sku}")
            if product.stock < item.quantity:
                raise ValueError(f"Insufficient stock for SKU {item.sku}. Available: {product.stock}")
            product.stock -= item.quantity
            order_item = OrderItem(
                order_id=order.id,
                product_id=product.id,
                quantity=item.quantity,
                unit_price=product.price,
            )
            session.add(order_item)

        session.commit()

        session.refresh(order)
        result = {
            "order_id": order.id,
            "customer_email": customer.email,
            "status": order.status,
            "items": [
                {
                    "sku": session.get(Product, oi.product_id).sku,
                    "quantity": oi.quantity,
                    "unit_price": oi.unit_price,
                    "line_total": round(oi.quantity * oi.unit_price, 2),
                }
                for oi in order.items
            ],
        }
        result["order_total"] = round(sum(i["line_total"] for i in result["items"]), 2)
        return result


# LlamaIndex SQLDatabase helper
try:
    from llama_index.core import SQLDatabase
except Exception:  # pragma: no cover
    SQLDatabase = None  # type: ignore


def get_sql_database():
    if SQLDatabase is None:
        raise RuntimeError("LlamaIndex is not installed")
    engine = get_engine()
    return SQLDatabase(engine, include_tables=["products", "customers", "orders", "order_items"])