from datetime import datetime, date
from typing import List, Optional
from sqlalchemy import (
    Column, Integer, String, Float, ForeignKey, Text, DateTime, 
    Boolean, Enum, Date, JSON, ARRAY
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.dialects.postgresql import ARRAY as PG_ARRAY
import enum

Base = declarative_base()

# Enums
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

# Base model with common fields
class TimestampMixin:
    @declared_attr
    def created_at(cls):
        return Column(DateTime, default=datetime.utcnow, nullable=False)
    
    @declared_attr
    def updated_at(cls):
        return Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    @declared_attr
    def deleted_at(cls):
        return Column(DateTime, nullable=True)

# Store model
class Store(Base, TimestampMixin):
    __tablename__ = "stores"
    
    id = Column(Integer, primary_key=True, index=True)
    prefix = Column(String(50), nullable=False, comment="商店前綴")
    store_name = Column(String(255), unique=True, nullable=False, comment="商店名稱")
    store_picture = Column(String(500), nullable=True, comment="商店圖片")
    store_info = Column(Text, nullable=True, comment="商店資訊")
    email = Column(String(255), nullable=False, comment="電子郵件")
    address = Column(String(500), nullable=True, comment="地址")
    phone = Column(String(50), nullable=True, comment="電話")
    business_hours = Column(String(200), nullable=True, comment="營業時間")
    payment_api = Column(String(500), nullable=True, comment="付款API")
    marquee = Column(PG_ARRAY(String), nullable=True, comment="跑馬燈")
    
    # Relationships
    raw_pages = relationship("RawPage", back_populates="store", cascade="all, delete-orphan")
    admins = relationship("Admin", back_populates="store", cascade="all, delete-orphan")
    coupons = relationship("Coupon", back_populates="store", cascade="all, delete-orphan")
    interrogations = relationship("Interrogation", back_populates="store", cascade="all, delete-orphan")
    products = relationship("Product", back_populates="store", cascade="all, delete-orphan")
    orders = relationship("Order", back_populates="store", cascade="all, delete-orphan")

# RawPage model
class RawPage(Base, TimestampMixin):
    __tablename__ = "raw_pages"
    
    id = Column(Integer, primary_key=True, index=True)
    store_id = Column(Integer, ForeignKey("stores.id"), nullable=False, comment="商店ID")
    type = Column(Enum(PageType), nullable=False, comment="頁面類型")
    title = Column(String(255), nullable=False, comment="標題")
    image = Column(String(500), nullable=True, comment="圖片")
    content = Column(Text, nullable=True, comment="內容")
    
    # Relationships
    store = relationship("Store", back_populates="raw_pages")

# Admin model
class Admin(Base, TimestampMixin):
    __tablename__ = "admins"
    
    id = Column(Integer, primary_key=True, index=True)
    store_id = Column(Integer, ForeignKey("stores.id"), nullable=False, comment="商店ID")
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, comment="使用者ID")
    notify_token = Column(String(500), nullable=True, comment="通知Token")
    level = Column(Enum(AdminLevel), nullable=False, default=AdminLevel.STAFF, comment="管理員等級")
    
    # Relationships
    store = relationship("Store", back_populates="admins")
    user = relationship("User", back_populates="admin_roles")

# Coupon model
class Coupon(Base, TimestampMixin):
    __tablename__ = "coupons"
    
    id = Column(Integer, primary_key=True, index=True)
    store_id = Column(Integer, ForeignKey("stores.id"), nullable=False, comment="商店ID")
    type = Column(Enum(CouponType), nullable=False, comment="優惠券類型")
    discount = Column(Integer, nullable=False, comment="優惠金額")
    min_price = Column(Integer, nullable=False, comment="最低消費金額")
    remain_count = Column(Integer, nullable=False, comment="剩餘數量")
    
    # Relationships
    store = relationship("Store", back_populates="coupons")

# User model
class User(Base, TimestampMixin):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    account = Column(String(100), unique=True, nullable=False, comment="帳號")
    password = Column(String(255), nullable=False, comment="密碼")
    name = Column(String(100), nullable=False, comment="姓名")
    email = Column(String(255), unique=True, nullable=False, comment="電子郵件")
    phone = Column(String(50), nullable=True, comment="電話")
    address = Column(String(500), nullable=True, comment="地址")
    birthday = Column(Date, nullable=True, comment="生日")
    register_ip = Column(String(50), nullable=True, comment="註冊IP")
    wallet = Column(Integer, default=0, comment="錢包餘額")
    award = Column(Integer, default=0, comment="獎金餘額")
    referee_id = Column(Integer, ForeignKey("users.id"), nullable=True, comment="推薦人ID")
    level = Column(Enum(UserLevel), default=UserLevel.FIRST, comment="會員等級")
    real_name_id = Column(Integer, ForeignKey("real_names.id"), nullable=True, comment="實名資料ID")
    
    # Relationships
    admin_roles = relationship("Admin", back_populates="user")
    referee = relationship("User", remote_side=[id], backref="referrals")
    real_name = relationship("RealName", back_populates="user")
    orders = relationship("Order", back_populates="user", cascade="all, delete-orphan")
    wallet_records = relationship("WalletRecord", back_populates="user", cascade="all, delete-orphan")

# RealName model
class RealName(Base, TimestampMixin):
    __tablename__ = "real_names"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, comment="使用者ID")
    name = Column(String(100), nullable=False, comment="姓名")
    identity_card_front = Column(String(500), nullable=True, comment="身分證正面")
    identity_card_back = Column(String(500), nullable=True, comment="身分證反面")
    identity_card_id = Column(String(50), nullable=True, comment="身分證號")
    deposit_book_front = Column(String(500), nullable=True, comment="存摺正面")
    deposit_book_back = Column(String(500), nullable=True, comment="存摺反面")
    bank_code = Column(String(20), nullable=True, comment="銀行代碼")
    bank_ch_code = Column(String(20), nullable=True, comment="銀行分行代碼")
    bank_id = Column(String(50), nullable=True, comment="銀行帳號")
    verified = Column(Boolean, default=False, comment="審核通過")
    
    # Relationships
    user = relationship("User", back_populates="real_name")

# Product model
class Product(Base, TimestampMixin):
    __tablename__ = "products"
    
    id = Column(Integer, primary_key=True, index=True)
    store_id = Column(Integer, ForeignKey("stores.id"), nullable=False, comment="商店ID")
    category = Column(String(100), nullable=False, comment="分類")
    name = Column(String(255), nullable=False, comment="名稱")
    outline = Column(Text, nullable=True, comment="簡介")
    detail = Column(Text, nullable=True, comment="詳情")
    picture = Column(String(500), nullable=True, comment="圖片")
    carousel = Column(PG_ARRAY(String), nullable=True, comment="輪播圖")
    status = Column(Enum(ProductStatus), default=ProductStatus.NORMAL, comment="狀態")
    
    # Relationships
    store = relationship("Store", back_populates="products")
    product_items = relationship("ProductItem", back_populates="product", cascade="all, delete-orphan")

# ProductItem model
class ProductItem(Base, TimestampMixin):
    __tablename__ = "product_items"
    
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, comment="商品ID")
    name = Column(String(255), nullable=False, comment="細項名稱")
    price = Column(Integer, nullable=False, comment="商品價格")
    stock = Column(Integer, nullable=False, comment="庫存")
    discount = Column(String(200), nullable=True, comment="折扣描述")
    
    # Relationships
    product = relationship("Product", back_populates="product_items")
    order_items = relationship("OrderItem", back_populates="product_item")

# Order model
class Order(Base, TimestampMixin):
    __tablename__ = "orders"
    
    id = Column(Integer, primary_key=True, index=True)
    store_id = Column(Integer, ForeignKey("stores.id"), nullable=False, comment="商店ID")
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, comment="用戶ID")
    total = Column(Integer, nullable=False, comment="總金額")
    status = Column(Enum(OrderStatus), default=OrderStatus.PENDING, comment="訂單狀態")
    remark = Column(Text, nullable=True, comment="備註")
    coupon = Column(String(100), nullable=True, comment="優惠券")
    delivery_id = Column(Integer, ForeignKey("deliveries.id"), nullable=True, comment="發貨ID")
    payment_id = Column(Integer, ForeignKey("payments.id"), nullable=True, comment="付款ID")
    
    # Relationships
    store = relationship("Store", back_populates="orders")
    user = relationship("User", back_populates="orders")
    order_items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    delivery = relationship("Delivery", back_populates="order")
    payment = relationship("Payment", back_populates="order")

# OrderItem model
class OrderItem(Base, TimestampMixin):
    __tablename__ = "order_items"
    
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False, comment="訂單ID")
    product_item_id = Column(Integer, ForeignKey("product_items.id"), nullable=False, comment="商品ID")
    count = Column(Integer, nullable=False, comment="商品數量")
    
    # Relationships
    order = relationship("Order", back_populates="order_items")
    product_item = relationship("ProductItem", back_populates="order_items")

# Delivery model
class Delivery(Base, TimestampMixin):
    __tablename__ = "deliveries"
    
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False, comment="訂單ID")
    status = Column(Enum(DeliveryStatus), default=DeliveryStatus.PENDING, comment="發貨狀態")
    freight = Column(Integer, default=0, comment="運費")
    remark = Column(Text, nullable=True, comment="備註")
    
    # Relationships
    order = relationship("Order", back_populates="delivery")

# Payment model
class Payment(Base, TimestampMixin):
    __tablename__ = "payments"
    
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False, comment="訂單ID")
    amount = Column(Integer, nullable=False, comment="金額")
    status = Column(Enum(PaymentStatus), default=PaymentStatus.PENDING, comment="付款狀態")
    payment_method = Column(String(100), nullable=True, comment="付款方式")
    details = Column(Text, nullable=True, comment="付款詳情")
    
    # Relationships
    order = relationship("Order", back_populates="payment")

# WalletRecord model
class WalletRecord(Base, TimestampMixin):
    __tablename__ = "wallet_records"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, comment="用戶ID")
    from_id = Column(Integer, ForeignKey("users.id"), nullable=True, comment="來源ID")
    amount = Column(Float, nullable=False, comment="金額")
    type = Column(Enum(WalletType), nullable=False, comment="類型")
    comment = Column(Text, nullable=True, comment="備註")
    
    # Relationships
    user = relationship("User", back_populates="wallet_records")
    from_user = relationship("User", foreign_keys=[from_id])

# Interrogation model
class Interrogation(Base, TimestampMixin):
    __tablename__ = "interrogations"
    
    id = Column(Integer, primary_key=True, index=True)
    store_id = Column(Integer, ForeignKey("stores.id"), nullable=False, comment="商店ID")
    question = Column(Text, nullable=False, comment="問題")
    answer = Column(Text, nullable=True, comment="回答")
    
    # Relationships
    store = relationship("Store", back_populates="interrogations")

# For SQLite compatibility (since SQLite doesn't support ARRAY)
class SQLiteArray:
    def __init__(self, *args, **kwargs):
        pass

# Override ARRAY columns for SQLite
if 'sqlite' in str(Base.metadata.bind.url) if hasattr(Base.metadata, 'bind') and Base.metadata.bind else True:
    Store.marquee = Column(Text, nullable=True, comment="跑馬燈 (JSON array)")
    Product.carousel = Column(Text, nullable=True, comment="輪播圖 (JSON array)")