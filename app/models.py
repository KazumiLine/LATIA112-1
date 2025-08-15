# -*- coding: utf-8 -*-
import os
import json
import random
import enum
from sqlalchemy import (
    create_engine, Column, Integer, String, Float, ForeignKey, Text,
    DateTime, Boolean, Enum, Date
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker, scoped_session
from sqlalchemy.engine import Engine
from sqlalchemy.sql import func
from datetime import date
from llama_index.core import SQLDatabase
from sqlalchemy import event, DDL, text
from werkzeug.security import generate_password_hash
# =========================
# SQLAlchemy Base
# =========================
Base = declarative_base()

DB_PATH = os.environ.get("APP_DB_PATH", os.path.join(os.getcwd(), "storage", "app.db"))
DB_URI = f"sqlite:///{DB_PATH}"

SessionLocal = None  # will be initialized in get_engine

def get_engine(echo: bool = False) -> Engine:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    engine = create_engine(DB_URI, echo=echo, future=True)
    global SessionLocal
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    return engine

Session = scoped_session(sessionmaker(bind=get_engine()))
Base.query = Session.query_property()
# =========================
# Enums（保留原列舉）
# =========================
class PageType(str, enum.Enum):
    ABOUT_US = "關於我們"
    TERM_SERVICE = "服務條款"
    COOPERATE_MEETING = "合作洽談"
    AGENT_RECRUITMENT = "代理招募"

class AdminLevel(int, enum.Enum):
    STAFF = 1      # Staff can only view and manage orders
    MANAGER = 2    # Manager can view and manage orders, products, and coupons
    OWNER = 3      # Owner can view and manage all data

class CouponType(int, enum.Enum):
    DISCOUNT_PERCENT = 1  # 打折
    DISCOUNT_CONST = 2    # 定額折扣

class DeliveryStatus(int, enum.Enum):
    PENDING = 1    # 待發貨
    SHIPPED = 2    # 已發貨
    DELIVERED = 3  # 已送達
    REFUND = 4     # 退貨

class ProductStatus(int, enum.Enum):
    NORMAL = 1     # 正常
    HIDE = 2       # 隱藏

class OrderStatus(int, enum.Enum):
    PENDING = 1    # 待付款
    PAID = 2       # 已付款
    SHIPPED = 3    # 已發貨
    REFUND = 4     # 退款

class PaymentStatus(int, enum.Enum):
    PENDING = 1    # 待付款
    PAID = 2       # 已付款
    FAILED = 3     # 付款失敗
    REFUNDED = 4   # 已退款

class UserLevel(int, enum.Enum):
    FIRST = 1      # 一般會員
    SECOND = 2     # 銀卡會員
    THIRD = 3      # 金卡會員

class WalletType(int, enum.Enum):
    RECHARGE = 1   # 充值
    PAY = 2        # 支付
    WITHDRAW = 3   # 提現
    AWARD = 4      # 獎勵

class DeliveryMethod(str, enum.Enum):
    HOME_DELIVERY = "宅配"
    PICKUP = "自取"
    COURIER = "快遞"
    POSTAL = "郵寄"
    ONLINE = "線上配送"

# =========================
# 共用時間欄位
# =========================
class TimestampMixin:
    created_at = Column(
        DateTime, server_default=func.now(), nullable=False,
        comment="建立時間（自動）", key="created_at"
    )
    updated_at = Column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False,
        comment="更新時間（自動）", key="updated_at"
    )
    deleted_at = Column(
        DateTime, nullable=True, comment="刪除時間（軟刪除用）", key="deleted_at"
    )

# =========================
# 資料表定義（保留原表）
# =========================
class Store(Base, TimestampMixin):
    __tablename__ = "stores"

    id = Column(Integer, primary_key=True, comment="商店唯一 ID", key="id")
    prefix = Column(String(50), nullable=False, comment="商店前綴", key="prefix")
    store_name = Column(String(255), unique=True, nullable=False, comment="商店名稱", key="store_name")
    store_picture = Column(String(500), nullable=True, comment="商店圖片 URL", key="store_picture")
    store_info = Column(Text, nullable=True, comment="商店資訊", key="store_info")
    email = Column(String(255), nullable=False, comment="商店電子郵件", key="email")
    address = Column(String(500), nullable=True, comment="商店地址", key="address")
    phone = Column(String(50), nullable=True, comment="商店電話", key="phone")
    business_hours = Column(String(200), nullable=True, comment="商店營業時間", key="business_hours")
    payment_api = Column(String(500), nullable=True, comment="商店付款 API 設定", key="payment_api")
    marquee = Column(Text, nullable=True, comment="商店跑馬燈", key="marquee")

    raw_pages = relationship("RawPage", back_populates="store", cascade="all, delete-orphan")
    admins = relationship("Admin", back_populates="store", cascade="all, delete-orphan")
    coupons = relationship("Coupon", back_populates="store", cascade="all, delete-orphan")
    interrogations = relationship("Interrogation", back_populates="store", cascade="all, delete-orphan")
    products = relationship("Product", back_populates="store", cascade="all, delete-orphan")
    orders = relationship("Order", back_populates="store", cascade="all, delete-orphan")

class RawPage(Base, TimestampMixin):
    __tablename__ = "raw_pages"

    id = Column(Integer, primary_key=True, comment="頁面唯一 ID", key="id")
    store_id = Column(Integer, ForeignKey("stores.id"), nullable=False, comment="商店 ID", key="store_id")
    type = Column(Enum(PageType), nullable=False, comment="頁面類型", key="type")
    title = Column(String(255), nullable=False, comment="標題", key="title")
    image = Column(String(500), nullable=True, comment="頁面圖片 URL", key="image")
    content = Column(Text, nullable=True, comment="頁面內容", key="content")

    store = relationship("Store", back_populates="raw_pages")

class Admin(Base, TimestampMixin):
    __tablename__ = "admins"

    id = Column(Integer, primary_key=True, comment="管理員唯一 ID", key="id")
    store_id = Column(Integer, ForeignKey("stores.id"), nullable=False, comment="商店 ID", key="store_id")
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, comment="使用者 ID", key="user_id")
    notify_token = Column(String(500), nullable=True, comment="通知 Token", key="notify_token")
    level = Column(Enum(AdminLevel), nullable=False, default=AdminLevel.STAFF, comment="管理員等級", key="level")

    store = relationship("Store", back_populates="admins")
    user = relationship("User", back_populates="admin_roles")

class Coupon(Base, TimestampMixin):
    __tablename__ = "coupons"

    id = Column(Integer, primary_key=True, comment="優惠券唯一 ID", key="id")
    store_id = Column(Integer, ForeignKey("stores.id"), nullable=False, comment="商店 ID", key="store_id")
    type = Column(Enum(CouponType), nullable=False, comment="優惠券類型", key="type")
    discount = Column(Integer, nullable=False, comment="優惠金額或折扣百分比", key="discount")
    min_price = Column(Integer, nullable=False, comment="最低消費金額", key="min_price")
    remain_count = Column(Integer, nullable=False, comment="剩餘數量", key="remain_count")

    store = relationship("Store", back_populates="coupons")

class User(Base, TimestampMixin):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, comment="使用者唯一 ID", key="id")
    account = Column(String(100), unique=True, nullable=False, comment="帳號（唯一）", key="account")
    password = Column(String(255), nullable=False, comment="雜湊後密碼", key="password")
    name = Column(String(100), nullable=False, comment="姓名", key="name")
    email = Column(String(255), unique=True, nullable=False, comment="電子郵件", key="email")
    phone = Column(String(50), nullable=True, comment="電話", key="phone")
    address = Column(String(500), nullable=True, comment="地址", key="address")
    birthday = Column(Date, nullable=True, comment="生日", key="birthday")
    register_ip = Column(String(50), nullable=True, comment="註冊 IP", key="register_ip")
    wallet = Column(Integer, nullable=False, default=0, comment="錢包餘額", key="wallet")
    award = Column(Integer, nullable=False, default=0, comment="獎金餘額", key="award")
    referee_id = Column(Integer, ForeignKey("users.id"), nullable=True, comment="推薦人使用者 ID", key="referee_id")
    level = Column(Enum(UserLevel), nullable=False, default=UserLevel.FIRST, comment="會員等級", key="level")
    real_name_id = Column(Integer, ForeignKey("real_names.id"), nullable=True, comment="實名資料 ID", key="real_name_id")

    admin_roles = relationship("Admin", back_populates="user")
    referee = relationship("User", remote_side=[id], backref="referrals")
    real_name = relationship("RealName", back_populates="user", uselist=False)
    orders = relationship("Order", back_populates="user", cascade="all, delete-orphan")
    wallet_records = relationship("WalletRecord", back_populates="user", cascade="all, delete-orphan", foreign_keys="WalletRecord.user_id")

class RealName(Base, TimestampMixin):
    __tablename__ = "real_names"

    id = Column(Integer, primary_key=True, comment="實名資料唯一 ID", key="id")
    name = Column(String(100), nullable=False, comment="姓名", key="name")
    identity_card_front = Column(String(500), nullable=True, comment="身分證正面 URL", key="identity_card_front")
    identity_card_back = Column(String(500), nullable=True, comment="身分證反面 URL", key="identity_card_back")
    identity_card_id = Column(String(50), nullable=True, comment="身分證字號", key="identity_card_id")
    deposit_book_front = Column(String(500), nullable=True, comment="存摺正面 URL", key="deposit_book_front")
    deposit_book_back = Column(String(500), nullable=True, comment="存摺反面 URL", key="deposit_book_back")
    bank_code = Column(String(20), nullable=True, comment="銀行代碼", key="bank_code")
    bank_ch_code = Column(String(20), nullable=True, comment="銀行分行代碼", key="bank_ch_code")
    bank_id = Column(String(50), nullable=True, comment="銀行帳號", key="bank_id")
    verified = Column(Boolean, nullable=False, default=False, comment="審核通過", key="verified")
    user = relationship("User", back_populates="real_name", uselist=False)

class Product(Base, TimestampMixin):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, comment="商品唯一 ID", key="id")
    store_id = Column(Integer, ForeignKey("stores.id"), nullable=False, comment="商店 ID", key="store_id")
    catalog = Column(String(100), nullable=False, comment="商品分類", key="catalog")
    name = Column(String(255), nullable=False, comment="商品名稱", key="name")
    descriptions = Column(Text, nullable=True, comment="商品簡介", key="descriptions")
    detail = Column(Text, nullable=True, comment="商品詳情", key="detail")
    picture = Column(String(500), nullable=True, comment="商品主圖", key="picture")
    carousel = Column(Text, nullable=True, comment="商品輪播圖", key="carousel")
    status = Column(Enum(ProductStatus), nullable=False, default=ProductStatus.NORMAL, comment="商品狀態", key="status")

    store = relationship("Store", back_populates="products")
    product_items = relationship("ProductItem", back_populates="product", cascade="all, delete-orphan")

class ProductItem(Base, TimestampMixin):
    __tablename__ = "product_items"

    id = Column(Integer, primary_key=True, comment="商品細項唯一 ID", key="id")
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, comment="商品 ID", key="product_id")
    name = Column(String(255), nullable=False, comment="商品細項名稱", key="name")
    price = Column(Integer, nullable=False, comment="商品細項價格", key="price")
    stock = Column(Integer, nullable=False, comment="商品細項庫存數量", key="stock")
    discount = Column(String(200), nullable=True, comment="商品細項折扣描述", key="discount")
    status = Column(Enum(ProductStatus), nullable=False, default=ProductStatus.NORMAL, comment="商品狀態", key="status")

    product = relationship("Product", back_populates="product_items")
    order_items = relationship("OrderItem", back_populates="product_item")

class Order(Base, TimestampMixin):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, comment="訂單唯一 ID", key="id")
    store_id = Column(Integer, ForeignKey("stores.id"), nullable=False, comment="商店 ID", key="store_id")
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, comment="使用者 ID", key="user_id")
    total = Column(Integer, nullable=False, comment="訂單總金額", key="total")
    status = Column(Enum(OrderStatus), nullable=False, default=OrderStatus.PENDING, comment="訂單狀態", key="status")
    remark = Column(Text, nullable=True, comment="訂單備註", key="remark")
    coupon = Column(String(100), nullable=True, comment="訂單優惠券代碼", key="coupon")
    delivery_id = Column(Integer, ForeignKey("deliveries.id"), nullable=True, comment="訂單發貨資料 ID", key="delivery_id")
    payment_id = Column(Integer, ForeignKey("payments.id"), nullable=True, comment="訂單付款資料 ID", key="payment_id")

    store = relationship("Store", back_populates="orders")
    user = relationship("User", back_populates="orders")
    order_items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    delivery = relationship("Delivery", back_populates="order", uselist=False)
    payment = relationship("Payment", back_populates="order", uselist=False)
    logs = relationship("OrderLog", back_populates="order", cascade="all, delete-orphan")

class OrderItem(Base, TimestampMixin):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, comment="訂單項目唯一 ID", key="id")
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False, comment="訂單 ID", key="order_id")
    product_item_id = Column(Integer, ForeignKey("product_items.id"), nullable=False, comment="訂單細項 ID", key="product_item_id")
    quantity = Column(Integer, nullable=False, comment="商品購買數量", key="quantity")

    order = relationship("Order", back_populates="order_items")
    product_item = relationship("ProductItem", back_populates="order_items")

class Delivery(Base, TimestampMixin):
    __tablename__ = "deliveries"

    id = Column(Integer, primary_key=True, comment="發貨資料唯一 ID", key="id")
    destination = Column(String(500), nullable=True, comment="收貨地址", key="destination")
    method = Column(Enum(DeliveryMethod), nullable=False, default=DeliveryMethod.HOME_DELIVERY, comment="配送方式", key="method")
    status = Column(Enum(DeliveryStatus), nullable=False, default=DeliveryStatus.PENDING, comment="發貨狀態", key="status")
    freight = Column(Integer, nullable=False, default=0, comment="運費", key="freight")
    remark = Column(Text, nullable=True, comment="備註", key="remark")

    order = relationship("Order", back_populates="delivery", uselist=False)

class Payment(Base, TimestampMixin):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, comment="付款資料唯一 ID", key="id")
    amount = Column(Integer, nullable=False, comment="付款金額", key="amount")
    status = Column(Enum(PaymentStatus), nullable=False, default=PaymentStatus.PENDING, comment="付款狀態", key="status")
    payment_method = Column(String(100), nullable=True, comment="付款方式", key="payment_method")
    details = Column(Text, nullable=True, comment="付款詳情", key="details")

    order = relationship("Order", back_populates="payment")

class WalletRecord(Base, TimestampMixin):
    __tablename__ = "wallet_records"

    id = Column(Integer, primary_key=True, comment="錢包紀錄唯一 ID", key="id")
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, comment="使用者 ID", key="user_id")
    from_id = Column(Integer, ForeignKey("users.id"), nullable=True, comment="推薦人 ID", key="from_id")
    amount = Column(Float, nullable=False, comment="金額", key="amount")
    type = Column(Enum(WalletType), nullable=False, comment="類型", key="type")
    comment = Column(Text, nullable=True, comment="備註", key="comment")

    user = relationship("User", back_populates="wallet_records", foreign_keys=[user_id])
    from_user = relationship("User", foreign_keys=[from_id])

class Interrogation(Base, TimestampMixin):
    __tablename__ = "interrogations"

    id = Column(Integer, primary_key=True, comment="常見問題唯一 ID", key="id")
    store_id = Column(Integer, ForeignKey("stores.id"), nullable=False, comment="商店 ID", key="store_id")
    question = Column(Text, nullable=False, comment="問題", key="question")
    answer = Column(Text, nullable=True, comment="回答", key="answer")

    store = relationship("Store", back_populates="interrogations")

class OrderLog(Base, TimestampMixin):
    __tablename__ = "order_logs"

    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    action = Column(String(100), nullable=False)
    from_status = Column(String(50), nullable=True)
    to_status = Column(String(50), nullable=True)
    note = Column(Text, nullable=True)

    order = relationship("Order", back_populates="logs")

class ProductFullView(Base):
    __tablename__ = "product_full_view"
    full_name = Column(String)
    product_id = Column(Integer, primary_key=True)
    product_item_id = Column(Integer, primary_key=True)
    store_id = Column(Integer)
    catalog = Column(String(100))
    descriptions = Column(Text)
    detail = Column(Text)
    picture = Column(String(500))
    carousel = Column(Text)
    price = Column(Integer)
    stock = Column(Integer)
    discount = Column(String(200))

# =========================
# 初始化與種子資料
# =========================
FIRST_NAMES = ["Alice", "Bob", "Carol", "David", "Eve", "Frank", "Grace", "Hank", "Ivy", "Jack"]
LAST_NAMES = ["Lin", "Chen", "Wang", "Huang", "Li", "Liu", "Tsai", "Wu", "Chang", "Hsiao"]
CATEGORIES = ["電子產品", "配件", "居家", "戶外", "美食", "美妝"]
PAY_METHODS = ["credit_card", "apple_pay", "line_pay", "bank_transfer", "cod"]

def _rand_name(i: int) -> str:
    return f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"

def _email_from_name(name: str, i: int) -> str:
    return f"{name.lower().replace(' ', '.')}+{i}@example.com"

def _json_list(lst) -> str:
    return json.dumps(lst, ensure_ascii=False)

def init_db(seed: bool = True, echo: bool = False) -> None:
    """建立資料庫並（可選）填充 20-50 筆跨表範例資料。"""
    engine = get_engine(echo=echo)
    # 安全刪除舊的 VIEW（如果存在）
    with engine.connect() as conn:
        try:
            conn.execute(text(f"DROP VIEW IF EXISTS {ProductFullView.__tablename__};"))
        except Exception:
            pass
    Base.metadata.create_all(engine)

    if not seed:
        return

    with SessionLocal() as session:
        result = session.execute(
            text("SELECT name FROM sqlite_master WHERE type='view' AND name=:view_name"),
            {"view_name": ProductFullView.__tablename__}
        ).fetchone()
        if not result:
            session.execute(text("""
                CREATE VIEW product_full_view AS
                SELECT
                    p.name || ' - ' || pi.name AS full_name,
                    p.id AS product_id,
                    pi.id AS product_item_id,
                    p.store_id,
                    p.catalog,
                    p.descriptions,
                    p.detail,
                    p.picture,
                    p.carousel,
                    pi.price,
                    pi.stock,
                    pi.discount
                FROM products p
                JOIN product_items pi ON pi.product_id = p.id
                WHERE p.status = 'NORMAL';
            """))
            session.commit()
        # 若已存在資料就不重複填充
        if session.query(Store).count() > 0:
            session.commit()
            return

        random.seed(42)

        # --- Stores (3)
        stores = [
            Store(
                prefix="MAIN",
                store_name="主力商城",
                store_picture="https://img.example.com/store/main.png",
                store_info="精選 3C 與生活用品",
                email="service@main.example.com",
                address="台北市中正區仁愛路一段 1 號",
                phone="02-1234-5678",
                business_hours="Mon-Sun 10:00-20:00",
                payment_api="https://pay.example.com/api",
                marquee=_json_list(["夏日特賣 7 折起", "滿千折百", "新會員再送 100 元"])
            ),
            Store(
                prefix="OUT",
                store_name="戶外館",
                store_picture="https://img.example.com/store/outdoor.png",
                store_info="露營、登山專區",
                email="service@outdoor.example.com",
                address="新北市板橋區文化路 100 號",
                phone="02-2222-3333",
                business_hours="Tue-Sun 11:00-21:00",
                payment_api="https://pay.example.com/api2",
                marquee=_json_list(["野營補給站開張", "買帳篷送營燈"])
            ),
            Store(
                prefix="BEAUTY",
                store_name="美妝小舖",
                store_picture="https://img.example.com/store/beauty.png",
                store_info="護膚彩妝與保養",
                email="hi@beauty.example.com",
                address="桃園市桃園區中山路 88 號",
                phone="03-567-1234",
                business_hours="Mon-Fri 12:00-20:00",
                payment_api="",
                marquee=_json_list(["新品上架", "指定品第二件 5 折"])
            ),
        ]
        session.add_all(stores)
        session.flush()  # 取得 store.id

        # --- Admin user (seed one)
        admin_user = User(
            account="admin",
            password=generate_password_hash("admin123"),
            name="Administrator",
            email="admin@example.com",
            phone="0900000000",
            address="Taipei",
            birthday=date(1990,1,1),
            register_ip="127.0.0.1",
            wallet=0,
            award=0,
            referee_id=None,
            level=UserLevel.THIRD,
        )
        session.add(admin_user)
        session.flush()

        # --- Users (10) + RealNames(6) + WalletRecords(20)
        users = []
        for i in range(10):
            nm = _rand_name(i)
            u = User(
                account=f"user{i+1}",
                password=generate_password_hash(f"user{i+1}pass"),
                name=nm,
                email=_email_from_name(nm, i+1),
                phone=f"09{random.randint(10000000, 99999999)}",
                address=f"台灣某市某區{random.randint(1,300)}號",
                birthday=date(1990 + (i % 10), random.randint(1, 12), random.randint(1, 28)),
                register_ip=f"192.168.0.{i+10}",
                wallet=random.randint(0, 5000),
                award=random.randint(0, 1000),
                referee_id=None if i < 2 else random.randint(1, i),  # 某些有推薦人
                level=random.choice([UserLevel.FIRST, UserLevel.SECOND, UserLevel.THIRD]),
            )
            users.append(u)
        session.add_all(users)
        session.flush()

        # RealName 綁定 6 位
        real_names = []
        for i in range(6):
            rn = RealName(
                name=users[i].name,
                identity_card_front=f"https://img.example.com/id/front_{users[i].id}.png",
                identity_card_back=f"https://img.example.com/id/back_{users[i].id}.png",
                identity_card_id=f"A{random.randint(100000000, 999999999)}",
                deposit_book_front=f"https://img.example.com/bank/front_{users[i].id}.png",
                deposit_book_back=f"https://img.example.com/bank/back_{users[i].id}.png",
                bank_code="004",
                bank_ch_code="001",
                bank_id=f"00012345{users[i].id:03d}",
                verified=(i % 2 == 0),
            )
            real_names.append(rn)
        session.add_all(real_names)
        session.flush()

        # 回填 user.real_name_id
        for i in range(6):
            users[i].real_name_id = real_names[i].id

        # --- Admins: bind admin_user as OWNER to first store
        admins = [
            Admin(store_id=stores[0].id, user_id=admin_user.id, level=AdminLevel.OWNER, notify_token=None),
            Admin(store_id=stores[0].id, user_id=users[0].id, level=AdminLevel.MANAGER, notify_token=None),
            Admin(store_id=stores[1].id, user_id=users[1].id, level=AdminLevel.MANAGER, notify_token=None),
            Admin(store_id=stores[2].id, user_id=users[2].id, level=AdminLevel.STAFF, notify_token=None),
        ]
        session.add_all(admins)

        # --- RawPages (6)
        raw_pages = [
            RawPage(store_id=stores[0].id, type=PageType.ABOUT_US, title="關於主力商城", image=None, content="我們致力於提供最優質商品"),
            RawPage(store_id=stores[0].id, type=PageType.TERM_SERVICE, title="服務條款", image=None, content="使用前請詳閱服務條款"),
            RawPage(store_id=stores[1].id, type=PageType.COOPERATE_MEETING, title="合作洽談", image=None, content="歡迎品牌合作"),
            RawPage(store_id=stores[1].id, type=PageType.AGENT_RECRUITMENT, title="代理招募", image=None, content="尋找區域代理"),
            RawPage(store_id=stores[2].id, type=PageType.ABOUT_US, title="關於美妝小舖", image=None, content="美麗從這裡開始"),
            RawPage(store_id=stores[2].id, type=PageType.TERM_SERVICE, title="服務條款", image=None, content="退換貨與保固說明"),
        ]
        session.add_all(raw_pages)

        # --- Coupons (6)
        coupons = [
            Coupon(store_id=stores[0].id, type=CouponType.DISCOUNT_PERCENT, discount=10, min_price=1000, remain_count=100),
            Coupon(store_id=stores[0].id, type=CouponType.DISCOUNT_CONST, discount=150, min_price=1200, remain_count=80),
            Coupon(store_id=stores[1].id, type=CouponType.DISCOUNT_PERCENT, discount=15, min_price=2000, remain_count=60),
            Coupon(store_id=stores[1].id, type=CouponType.DISCOUNT_CONST, discount=200, min_price=1800, remain_count=50),
            Coupon(store_id=stores[2].id, type=CouponType.DISCOUNT_PERCENT, discount=5, min_price=800, remain_count=120),
            Coupon(store_id=stores[2].id, type=CouponType.DISCOUNT_CONST, discount=100, min_price=900, remain_count=90),
        ]
        session.add_all(coupons)

        # --- Products (12) 與 ProductItems (24)
        products = []
        product_items = []
        for s in stores:
            for i in range(4):  # 每店 4 個商品
                p = Product(
                    store_id=s.id,
                    catalog=random.choice(CATEGORIES),
                    name=f"{s.prefix} 商品 {i+1}",
                    descriptions="精選商品，物超所值",
                    detail="這是一段詳情描述，包含規格、材質與保固。",
                    picture=f"https://img.example.com/product/{s.prefix.lower()}_{i+1}.png",
                    carousel=_json_list([
                        f"https://img.example.com/product/{s.prefix.lower()}_{i+1}_1.png",
                        f"https://img.example.com/product/{s.prefix.lower()}_{i+1}_2.png"
                    ]),
                    status=random.choice(list(ProductStatus))
                )
                products.append(p)
        session.add_all(products)
        session.flush()

        for p in products:
            for v in ["標準版", "加強版"]:
                pi = ProductItem(
                    product_id=p.id,
                    name=v,
                    price=random.randint(200, 5000),
                    stock=random.randint(5, 150),
                    discount=random.choice([None, "滿千折百", "第二件 5 折"])
                )
                product_items.append(pi)
        session.add_all(product_items)
        session.flush()

        # --- Interrogations (5)
        faqs = [
            Interrogation(store_id=stores[0].id, question="多久出貨？", answer="一般 1-3 個工作天"),
            Interrogation(store_id=stores[0].id, question="有提供發票嗎？", answer="提供電子發票"),
            Interrogation(store_id=stores[1].id, question="大型帳篷運費？", answer="依材積另計"),
            Interrogation(store_id=stores[2].id, question="化妝品是否可退？", answer="未拆封 7 日內可退"),
            Interrogation(store_id=stores[2].id, question="如何成為會員？", answer="註冊並完成信箱驗證"),
        ]
        session.add_all(faqs)

        # --- Orders (15) + OrderItems(~30) + Delivery(12) + Payment(15)
        orders = []
        order_items = []
        deliveries = []
        payments = []

        # 從已存在的 product_items 中隨機挑選
        all_items = session.query(ProductItem).all()

        for i in range(15):
            buyer = random.choice(users)
            store = random.choice(stores)
            chosen_items = random.sample(all_items, k=2)
            qty1, qty2 = random.randint(1, 3), random.randint(1, 3)
            total_amount = chosen_items[0].price * qty1 + chosen_items[1].price * qty2
            coupon_code = random.choice([None, "SALE10", "WELCOME100"])

            order = Order(
                store_id=store.id,
                user_id=buyer.id,
                total=total_amount,
                status=random.choice(list(OrderStatus)),
                remark="測試訂單",
                coupon=coupon_code,
            )
            if random.random() < 0.8:
                order.delivery = Delivery(
                    status=random.choice(list(DeliveryStatus)),
                    freight=random.choice([0, 60, 120]),
                    method=random.choice(list(DeliveryMethod)),
                    remark=None
                )
            order.payment = Payment(
                amount=order.total,
                status=random.choice(list(PaymentStatus)),
                payment_method=random.choice(PAY_METHODS),
                details="支付測試紀錄"
            )
            orders.append(order)

        session.add_all(orders)
        session.flush()

        for o in orders:
            chosen_items = random.sample(all_items, k=2)
            q1, q2 = random.randint(1, 2), random.randint(1, 2)
            oi1 = OrderItem(order_id=o.id, product_item_id=chosen_items[0].id, quantity=q1)
            oi2 = OrderItem(order_id=o.id, product_item_id=chosen_items[1].id, quantity=q2)
            order_items.extend([oi1, oi2])

        session.add_all(order_items + deliveries + payments)

        session.commit()

def get_sql_database():
    if SQLDatabase is None:
        raise RuntimeError("LlamaIndex is not installed")
    engine = get_engine()
    # 將所有表都包含進去
    return SQLDatabase(
        engine,
        include_tables=[
            Store.__tablename__, RawPage.__tablename__, Admin.__tablename__,
            Coupon.__tablename__, User.__tablename__, RealName.__tablename__,
            Product.__tablename__, ProductItem.__tablename__,
            Order.__tablename__, OrderItem.__tablename__,
            Delivery.__tablename__, Payment.__tablename__,
            WalletRecord.__tablename__, Interrogation.__tablename__,
        ],
    )