from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session, Response, send_from_directory
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime, date
import json
import os
import csv
import io
import uuid
from typing import List, Dict, Any
from functools import wraps
from sqlalchemy import func
import concurrent.futures
import threading
import asyncio

# Import models
from .models import (
    Base, get_engine, SessionLocal, SQLDatabase,
    Store, RawPage, Product, ProductItem, Order, OrderItem, Delivery, Payment, Coupon, Admin, RealName, WalletRecord, Interrogation,
    PageType, AdminLevel, CouponType, DeliveryStatus, ProductStatus, 
    OrderStatus, PaymentStatus, UserLevel, WalletType, OrderLog,
    init_db as models_init_db,
    ChatSession, ChatMessage,
    User,
)
from .agent import AgentBuilder

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-here')
DB_PATH = os.environ.get("APP_DB_PATH", os.path.join(os.getcwd(), "storage", "app.db"))
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', f"sqlite:///{DB_PATH}")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# 圖片上傳配置
UPLOAD_FOLDER = os.path.join(os.getcwd(), "storage", "uploads")
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# 確保上傳目錄存在
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

db = SQLAlchemy(app)
CORS(app)

agent = AgentBuilder(1, 1)

# Provide an init function for run.py

def init_db(seed: bool = False) -> None:
    models_init_db(seed=seed, echo=False)

# -----------------
# Auth helpers
# -----------------

def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if 'user_id' not in session:
            # redirect users to appropriate login
            return redirect(url_for('user_login'))
        return f(*args, **kwargs)
    return wrapper

def admin_required(level: AdminLevel = AdminLevel.STAFF):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if 'user_id' not in session or session.get('user_type') != 'admin':
                return redirect(url_for('admin_login'))
            # Optional: further level checks could be added
            return f(*args, **kwargs)
        return wrapper
    return decorator

# -----------------
# Auth routes
# -----------------

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username') or request.form.get('account') or ''
        password = request.form.get('password') or ''
        
        # Find user by account
        user = User.query.filter_by(account=username).first()
        if not user:
            flash('帳號不存在', 'danger')
            return render_template('login.html')
        
        # Verify password
        if not check_password_hash(user.password, password):
            flash('密碼錯誤', 'danger')
            return render_template('login.html')
        
        # Check if user has admin role
        admin = Admin.query.filter_by(user_id=user.id).first()
        if not admin:
            flash('此帳號沒有管理員權限', 'danger')
            return render_template('login.html')
        
        # Set session with admin info
        session['user_id'] = user.id
        session['user_type'] = 'admin'
        session['username'] = user.name
        session['store_id'] = admin.store_id
        session['admin_level'] = admin.level.value
        session.permanent = True
        
        flash(f'管理員登入成功 - {user.name} (商店ID: {admin.store_id})', 'success')
        return redirect(url_for('admin_dashboard'))
    
    return render_template('login.html')

@app.route('/admin/logout')
@admin_required()
def admin_logout():
    session.clear()
    flash('已登出管理後台', 'info')
    return redirect(url_for('admin_login'))

# Legacy user /logout -> redirect to homepage
@app.route('/logout')
@login_required
def logout():
    session.clear()
    flash('已登出', 'info')
    return redirect(url_for('index'))

# -----------------
# Health and metrics
# -----------------

@app.route('/healthz')
def healthz():
    return jsonify({'status': 'ok', 'time': datetime.utcnow().isoformat()})

@app.route('/metrics')
def metrics():
    return jsonify({
        'users': User.query.count(),
        'products': Product.query.count(),
        'orders': Order.query.count(),
        'payments_paid': Payment.query.filter_by(status=PaymentStatus.PAID).count(),
    })

# -----------------
# Frontend Routes
# -----------------

@app.route('/')
def index():
    """Frontend homepage - separate from admin backend"""
    products = Product.query.filter_by(status=ProductStatus.NORMAL).limit(8).all()
    # Load basic pages for footer linking
    store_id = session.get('store_id', 1)
    about = RawPage.query.filter_by(store_id=store_id, type=PageType.ABOUT_US).first()
    contact = RawPage.query.filter_by(store_id=store_id, type=PageType.CONTACT_US).first()
    privacy = RawPage.query.filter_by(store_id=store_id, type=PageType.PRIVACY_POLICY).first()
    terms = RawPage.query.filter_by(store_id=store_id, type=PageType.TERM_SERVICE).first()
    return render_template('index.html', products=products, about=about, contact=contact, privacy=privacy, terms=terms)

# Remove duplicate /login here; keep admin /login defined earlier

@app.route('/user/login', methods=['GET', 'POST'])
def user_login():
    """Frontend user login page"""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        
        # Validate against database
        user = User.query.filter_by(account=username).first()
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['user_type'] = 'user'
            session['username'] = user.name
            flash('登入成功', 'success')
            return redirect(url_for('index'))
        else:
            flash('帳號或密碼錯誤', 'danger')
    
    return render_template('user_login.html')

@app.route('/user/dashboard')
@login_required
def user_dashboard():
    """User dashboard - separate from admin"""
    if session.get('user_type') != 'user':
        flash('權限不足', 'danger')
        return redirect(url_for('index'))
    
    user_id = session['user_id']
    orders = Order.query.filter_by(user_id=user_id).order_by(Order.created_at.desc()).all()
    chats = ChatSession.query.filter_by(user_id=user_id).order_by(ChatSession.created_at.desc()).all()
    return render_template('user/dashboard.html', orders=orders, chats=chats)

@app.route('/chat')
@login_required
def chat_page():
    """AI Chat page for users"""
    if session.get('user_type') != 'user':
        flash('權限不足', 'danger')
        return redirect(url_for('index'))
    
    return render_template('chat.html')

@app.route('/api/chat', methods=['POST'])
@login_required
def api_chat():
    """AI Chat API endpoint"""
    if session.get('user_type') != 'user':
        return jsonify({'error': '權限不足'}), 403
    
    try:
        data = request.get_json()
        message = data.get('message', '').strip()
        session_id = data.get('session_id')
        
        if not message:
            return jsonify({'error': '訊息不能為空'}), 400
        
        # Persist user message
        if session_id:
            chat_session = db.session.get(ChatSession, int(session_id))
        else:
            chat_session = None
        if not chat_session:
            chat_session = ChatSession(store_id=session.get('store_id', 1), user_id=session.get('user_id'), status='ai')
            db.session.add(chat_session)
            db.session.flush()
        db.session.add(ChatMessage(session_id=chat_session.id, sender='user', content=message))
        
        # 使用同步方式調用 AI 響應生成
        ai_response = generate_ai_response(chat_session, message)
        db.session.add(ChatMessage(session_id=chat_session.id, sender='ai', content=ai_response))
        db.session.commit()
        
        return jsonify({
            'success': True,
            'response': ai_response,
            'session_id': chat_session.id,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# 創建線程池用於處理 AI 請求
executor = concurrent.futures.ThreadPoolExecutor(max_workers=4)

async def generate_ai_response_async(chat_session, message):
    """異步版本的 AI 響應生成"""
    try:
        # 更新代理信息並生成響應
        await agent.update_info(chat_session.store_id, chat_session.user_id)
        response = await agent.chat(message)
        return response
    except Exception as e:
        # 如果 AI 代理出錯，返回一個友好的錯誤消息
        return f"抱歉，AI 服務暫時無法使用。錯誤信息：{str(e)}"

def generate_ai_response(chat_session, message):
    """在同步環境中運行異步 AI 響應生成"""
    try:
        # 創建新的事件循環或使用現有的
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        # 如果循環正在運行，使用 asyncio.create_task
        if loop.is_running():
            # 在新線程中運行異步函數
            def run_async():
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                try:
                    return new_loop.run_until_complete(generate_ai_response_async(chat_session, message))
                finally:
                    new_loop.close()
            
            future = executor.submit(run_async)
            response = future.result(timeout=30)
            return response
        else:
            # 直接運行異步函數
            response = loop.run_until_complete(generate_ai_response_async(chat_session, message))
            return response
            
    except concurrent.futures.TimeoutError:
        return "抱歉，AI 響應時間過長，請稍後再試。"
    except Exception as e:
        return f"抱歉，AI 服務出現錯誤：{str(e)}"

# -----------------
# Admin Routes (Protected)
# -----------------

@app.route('/admin')
@admin_required(AdminLevel.STAFF)
def admin_dashboard():
    store_id = session.get('store_id', 1)
    total_products = Product.query.filter_by(store_id=store_id).count()
    total_orders = Order.query.filter_by(store_id=store_id).count()
    total_users = db.session.query(User).join(Order).filter(Order.store_id == store_id).distinct().count()

    # Monthly revenue (paid orders current month)
    now = datetime.now()
    monthly_revenue = db.session.query(func.coalesce(func.sum(Order.total), 0)).filter(
        Order.store_id == store_id,
        Order.status == OrderStatus.PAID,
        func.extract('year', Order.created_at) == now.year,
        func.extract('month', Order.created_at) == now.month,
    ).scalar() or 0

    recent_orders = Order.query.filter_by(store_id=store_id).order_by(Order.created_at.desc()).limit(5).all()
    
    return render_template('admin/dashboard.html', 
                         total_products=total_products,
                         total_orders=total_orders,
                         total_users=total_users,
                         monthly_revenue=monthly_revenue,
                         recent_orders=recent_orders)

# -----------------
# Admin: Orders
# -----------------

@app.route('/admin/orders')
@admin_required(AdminLevel.STAFF)
def admin_orders():
    store_id = session.get('store_id', 1)
    orders = Order.query.filter_by(store_id=store_id).order_by(Order.created_at.desc()).all()
    return render_template('admin/orders.html', orders=orders)

@app.route('/admin/orders/<int:order_id>')
@admin_required(AdminLevel.STAFF)
def admin_order_detail(order_id):
    store_id = session.get('store_id', 1)
    order = Order.query.filter_by(id=order_id, store_id=store_id).first()
    if not order:
        flash('訂單不存在', 'danger')
        return redirect(url_for('admin_orders'))
    
    return render_template('admin/order_detail.html', order=order)

@app.route('/admin/orders/<int:order_id>/status', methods=['POST'])
@admin_required(AdminLevel.STAFF)
def admin_order_status_update(order_id):
    store_id = session.get('store_id', 1)
    order = db.session.get(Order, order_id)
    if not order or order.store_id != store_id:
        if request.headers.get('Accept') == 'application/json':
            return jsonify({'error': '訂單不存在'}), 404
        else:
            flash('訂單不存在', 'danger')
            return redirect(url_for('admin_orders'))
    
    try:
        new_status = OrderStatus(int(request.form.get('status')))
        old_status = order.status
        
        # Add order log
        log = OrderLog(
            order_id=order_id,
            action='status_update',
            from_status=old_status.name if hasattr(old_status, 'name') else str(old_status),
            to_status=new_status.name if hasattr(new_status, 'name') else str(new_status),
            note=request.form.get('note', '')
        )
        db.session.add(log)
        
        # Update status after logging
        order.status = new_status
        
        db.session.commit()
        
        # 智能響應格式
        if request.headers.get('Accept') == 'application/json':
            return jsonify({'message': '訂單狀態已更新'})
        else:
            flash('訂單狀態已更新', 'success')
            return redirect(url_for('admin_order_detail', order_id=order_id))
            
    except Exception as e:
        db.session.rollback()
        if request.headers.get('Accept') == 'application/json':
            return jsonify({'error': f'更新失敗：{str(e)}'}), 500
        else:
            flash(f'更新失敗：{str(e)}', 'danger')
            return redirect(url_for('admin_order_detail', order_id=order_id))

@app.route('/admin/orders/<int:order_id>/delivery', methods=['POST'])
@admin_required(AdminLevel.STAFF)
def admin_order_update_delivery(order_id):
    store_id = session.get('store_id', 1)
    # 使用統一的數據庫會話
    order = db.session.query(Order).filter_by(id=order_id, store_id=store_id).first()
    if not order:
        if request.headers.get('Accept') == 'application/json':
            return jsonify({'error': '訂單不存在'}), 404
        else:
            flash('訂單不存在', 'danger')
            return redirect(url_for('admin_orders'))
    
    try:
        # Create or update delivery info
        delivery = order.delivery
        if not delivery:
            delivery = Delivery()
            db.session.add(delivery)
            db.session.flush()  # To get delivery.id
            order.delivery_id = delivery.id
        
        delivery.destination = request.form.get('destination')
        delivery.method = request.form.get('method')
        delivery.freight = int(request.form.get('freight', 0))
        delivery.remark = request.form.get('remark')
        
        db.session.commit()
        
        # 智能響應格式
        if request.headers.get('Accept') == 'application/json':
            return jsonify({'message': '配送資訊已更新'})
        else:
            flash('配送資訊已更新', 'success')
            return redirect(url_for('admin_order_detail', order_id=order_id))
            
    except Exception as e:
        db.session.rollback()
        if request.headers.get('Accept') == 'application/json':
            return jsonify({'error': f'更新失敗：{str(e)}'}), 500
        else:
            flash(f'更新失敗：{str(e)}', 'danger')
            return redirect(url_for('admin_order_detail', order_id=order_id))

@app.route('/admin/orders/<int:order_id>/payment', methods=['POST'])
@admin_required(AdminLevel.STAFF)
def admin_order_update_payment(order_id):
    store_id = session.get('store_id', 1)
    # 使用統一的數據庫會話
    order = db.session.query(Order).filter_by(id=order_id, store_id=store_id).first()
    if not order:
        if request.headers.get('Accept') == 'application/json':
            return jsonify({'error': '訂單不存在'}), 404
        else:
            flash('訂單不存在', 'danger')
            return redirect(url_for('admin_orders'))
    
    try:
        # Create or update payment info
        payment = order.payment
        if not payment:
            payment = Payment(amount=order.total)  # Use order total as payment amount
            db.session.add(payment)
            db.session.flush()  # To get payment.id
            order.payment_id = payment.id
        
        payment.payment_method = request.form.get('method')
        payment.details = request.form.get('details')
        
        db.session.commit()
        
        # 智能響應格式
        if request.headers.get('Accept') == 'application/json':
            return jsonify({'message': '付款資訊已更新'})
        else:
            flash('付款資訊已更新', 'success')
            return redirect(url_for('admin_order_detail', order_id=order_id))
            
    except Exception as e:
        db.session.rollback()
        if request.headers.get('Accept') == 'application/json':
            return jsonify({'error': f'更新失敗：{str(e)}'}), 500
        else:
            flash(f'更新失敗：{str(e)}', 'danger')
            return redirect(url_for('admin_order_detail', order_id=order_id))

# -----------------
# Admin: Users
# -----------------

@app.route('/admin/users')
@admin_required(AdminLevel.MANAGER)
def admin_users():
    store_id = session.get('store_id', 1)
    # Get users who have orders in this store
    users = db.session.query(User).join(Order).filter(Order.store_id == store_id).distinct().all()
    return render_template('admin/users.html', users=users)

@app.route('/admin/users', methods=['POST'])
@admin_required(AdminLevel.MANAGER)
def admin_users_add():
    try:
        password = request.form.get('password')
        if not password:
            return jsonify({'error': '密碼不得為空'}), 400
        
        account = request.form.get('account')
        name = request.form.get('name')
        email = request.form.get('email')
        
        if not account or not name or not email:
            return jsonify({'error': '帳號、姓名和電子郵件為必填項目'}), 400
            
        user = User(
            account=account,
            password=generate_password_hash(password),
            name=name,
            email=email,
            phone=request.form.get('phone') or '',
            address=request.form.get('address') or '',
            level=UserLevel.FIRST
        )
        db.session.add(user)
        db.session.commit()
        return jsonify({'message': '用戶已新增'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'新增失敗：{str(e)}'}), 500

@app.route('/admin/users/<int:user_id>/edit', methods=['POST'])
@admin_required(AdminLevel.MANAGER)
def admin_users_edit(user_id):
    try:
        # 使用統一的數據庫會話
        user = db.session.query(User).filter_by(id=user_id).first()
        if not user:
            if request.headers.get('Accept') == 'application/json':
                return jsonify({'error': '用戶不存在'}), 404
            else:
                flash('用戶不存在', 'danger')
                return redirect(url_for('admin_users'))
        
        user.name = request.form.get('name')
        user.email = request.form.get('email')
        user.phone = request.form.get('phone')
        user.address = request.form.get('address')
        user.level = UserLevel(int(request.form.get('level', 1)))
        
        db.session.commit()
        
        # 智能響應格式
        if request.headers.get('Accept') == 'application/json':
            return jsonify({'message': '用戶已更新'})
        else:
            flash('用戶已更新', 'success')
            return redirect(url_for('admin_users'))
            
    except Exception as e:
        db.session.rollback()
        if request.headers.get('Accept') == 'application/json':
            return jsonify({'error': f'更新失敗：{str(e)}'}), 500
        else:
            flash(f'更新失敗：{str(e)}', 'danger')
            return redirect(url_for('admin_users'))

@app.route('/admin/users/<int:user_id>/details')
@admin_required(AdminLevel.MANAGER)
def admin_users_details(user_id):
    try:
        user = db.session.get(User, user_id)
        if not user:
            return jsonify({'error': '用戶不存在'}), 404
        
        # Get user's orders in current store
        store_id = session.get('store_id', 1)
        orders = Order.query.filter_by(user_id=user_id, store_id=store_id).all()
        
        user_data = {
            'id': user.id,
            'account': user.account,
            'name': user.name,
            'email': user.email,
            'phone': user.phone,
            'address': user.address,
            'level': user.level.value,
            'wallet': user.wallet,
            'award': user.award,
            'created_at': user.created_at.strftime('%Y-%m-%d %H:%M'),
            'orders_count': len(orders)
        }
        return jsonify(user_data)
    except Exception as e:
        return jsonify({'error': f'獲取失敗：{str(e)}'}), 500

# -----------------
# Admin: Product CRUD with store_id support
# -----------------

@app.route('/admin/products')
@admin_required(AdminLevel.MANAGER)
def admin_products():
    store_id = session.get('store_id', 1)
    status_filter = request.args.get('status', '')
    store_filter = request.args.get('store_id', '')
    
    query = Product.query.filter_by(store_id=store_id)
    if status_filter:
        query = query.filter_by(status=ProductStatus(int(status_filter)))
    
    products = query.order_by(Product.created_at.desc()).all()
    return render_template('admin/products.html', products=products)

@app.route('/admin/products/new', methods=['GET', 'POST'])
@admin_required(AdminLevel.MANAGER)
def admin_product_new():
    if request.method == 'POST':
        try:
            store_id = session.get('store_id', 1)
            p = Product(
                store_id=store_id,
                catalog=request.form.get('catalog'),
                name=request.form.get('name'),
                descriptions=request.form.get('descriptions'),
                detail=request.form.get('detail'),
                picture=request.form.get('picture'),
                carousel=request.form.get('carousel'),  # 添加輪播圖支持
                status=ProductStatus(int(request.form.get('status', 1)))
            )
            db.session.add(p)
            db.session.commit()
            
            # 根據請求類型返回適當響應
            # 如果明確請求 JSON 響應（API 調用），返回 JSON
            if request.headers.get('Accept') == 'application/json':
                return jsonify({'message': '商品已建立', 'product_id': p.id})
            else:
                # 普通網頁表單提交，使用 flash 和重定向
                flash('商品已建立', 'success')
                return redirect(url_for('admin_products'))
        except Exception as e:
            db.session.rollback()
            # 如果明確請求 JSON 響應（API 調用），返回 JSON 錯誤
            if request.headers.get('Accept') == 'application/json':
                return jsonify({'error': f'建立失敗：{str(e)}'}), 500
            else:
                # 普通網頁表單提交，使用 flash 和重定向
                flash(f'建立失敗：{str(e)}', 'danger')
    
    stores = Store.query.all()
    return render_template('admin/product_form.html', stores=stores)

@app.route('/admin/products/<int:pid>/edit', methods=['GET', 'POST'])
@admin_required(AdminLevel.MANAGER)
def admin_product_edit(pid):
    store_id = session.get('store_id', 1)
    p = db.session.query(Product).filter_by(id=pid, store_id=store_id).first()
    if not p:
        # 如果按 store_id 找不到，嘗試直接按 id 查找（調試用）
        p = db.session.query(Product).filter_by(id=pid).first()
        if p:
            if request.headers.get('Accept') == 'application/json':
                return jsonify({'error': f'商品存在但不屬於當前商店 (商品store_id: {p.store_id}, 會話store_id: {store_id})'}), 403
            else:
                flash(f'商品不屬於當前商店 (商品store_id: {p.store_id}, 會話store_id: {store_id})', 'danger')
                return redirect(url_for('admin_products'))
        else:
            if request.headers.get('Accept') == 'application/json':
                return jsonify({'error': '商品不存在'}), 404
            else:
                flash('商品不存在', 'danger')
                return redirect(url_for('admin_products'))
    
    if request.method == 'POST':
        try:
            old_name = p.name  # 保存舊名稱用於調試
            
            # 處理可能為 None 的字段，提供默認值
            catalog = request.form.get('catalog')
            if catalog is None or catalog.strip() == '':
                catalog = '未分類'  # 提供默認分類
            
            name = request.form.get('name')
            # 如果是圖片 API 更新（multipart/form-data 且只帶 picture 欄位），只更新圖片，不動其他欄位
            if request.content_type and request.content_type.startswith('multipart/form-data') and 'picture' in request.form and len(request.form) == 1:
                picture = request.form.get('picture') or ''
                p.picture = picture
                db.session.commit()
                if request.headers.get('Accept') == 'application/json':
                    return jsonify({'message': '圖片已更新', 'product_id': p.id, 'picture': p.picture})
                else:
                    flash('圖片已更新', 'success')
                    return redirect(url_for('admin_products'))
            # 其餘情況照常處理
            if name is None or name.strip() == '':
                name = '未命名商品'  # 提供默認名稱
            descriptions = request.form.get('descriptions') or ''
            detail = request.form.get('detail') or ''
            picture = request.form.get('picture') or ''
            carousel = request.form.get('carousel') or ''
            
            p.catalog = catalog
            p.name = name
            p.descriptions = descriptions
            p.detail = detail
            p.picture = picture
            p.carousel = carousel  # 重新添加輪播圖支持
            p.status = ProductStatus(int(request.form.get('status', 1)))
            db.session.commit()
            
            # 根據請求類型返回適當響應
            # 如果明確請求 JSON 響應（API 調用），返回 JSON
            if request.headers.get('Accept') == 'application/json':
                return jsonify({
                    'message': '商品已更新',
                    'old_name': old_name,
                    'new_name': p.name,
                    'product_id': p.id,
                    'store_id': p.store_id
                })
            else:
                # 普通網頁表單提交，使用 flash 和重定向
                flash('商品已更新', 'success')
                return redirect(url_for('admin_products'))
        except Exception as e:
            db.session.rollback()
            # 如果明確請求 JSON 響應（API 調用），返回 JSON 錯誤
            if request.headers.get('Accept') == 'application/json':
                return jsonify({'error': f'更新失敗：{str(e)}'}), 500
            else:
                # 普通網頁表單提交，使用 flash 和重定向
                flash(f'更新失敗：{str(e)}', 'danger')
    
    stores = Store.query.all()
    return render_template('admin/product_form.html', product=p, stores=stores)

@app.route('/admin/products/<int:pid>/delete', methods=['POST'])
@admin_required(AdminLevel.MANAGER)
def admin_product_delete(pid):
    store_id = session.get('store_id', 1)
    p = Product.query.filter_by(id=pid, store_id=store_id).first()
    if not p:
        flash('商品不存在', 'danger')
        return redirect(url_for('admin_products'))
    
    p.deleted_at = datetime.now()
    db.session.commit()
    flash('商品已刪除', 'success')
    return redirect(url_for('admin_products'))

@app.route('/admin/products/<int:pid>/toggle-status', methods=['POST'])
@admin_required(AdminLevel.MANAGER)
def admin_product_toggle_status(pid):
    try:
        store_id = session.get('store_id', 1)
        # 使用統一的數據庫會話
        p = db.session.query(Product).filter_by(id=pid, store_id=store_id).first()
        if not p:
            if request.headers.get('Accept') == 'application/json':
                return jsonify({'error': '商品不存在'}), 404
            else:
                flash('商品不存在', 'danger')
                return redirect(url_for('admin_products'))
        
        new_status = ProductStatus(int(request.form.get('status')))
        p.status = new_status
        db.session.commit()
        
        action = '已隱藏' if new_status == ProductStatus.HIDE else '已顯示'
        
        # 智能響應格式
        if request.headers.get('Accept') == 'application/json':
            return jsonify({'message': f'商品{action}'})
        else:
            flash(f'商品{action}', 'success')
            return redirect(url_for('admin_products'))
            
    except Exception as e:
        db.session.rollback()
        if request.headers.get('Accept') == 'application/json':
            return jsonify({'error': f'操作失敗：{str(e)}'}), 500
        else:
            flash(f'操作失敗：{str(e)}', 'danger')
            return redirect(url_for('admin_products'))

# -----------------
# Admin: Product Items
# -----------------

@app.route('/admin/products/<int:pid>/items', methods=['GET', 'POST'])
@admin_required(AdminLevel.MANAGER)
def admin_product_items(pid):
    p = db.session.get(Product, pid)
    if not p:
        flash('商品不存在', 'danger')
        return redirect(url_for('admin_products'))
    if request.method == 'POST':
        name = request.form.get('name','').strip()
        price = int(request.form.get('price','0') or 0)
        stock = int(request.form.get('stock','0') or 0)
        if not name or price <= 0:
            # 如果明確請求 JSON 響應（API 調用），返回 JSON 錯誤
            if request.headers.get('Accept') == 'application/json':
                return jsonify({'error': '名稱與價格必填'}), 400
            else:
                # 普通網頁表單提交，使用 flash
                flash('名稱與價格必填', 'warning')
        else:
            it = ProductItem(product_id=p.id, name=name, price=price, stock=stock, discount=request.form.get('discount',''))
            db.session.add(it)
            db.session.commit()
            
            # 如果明確請求 JSON 響應（API 調用），返回 JSON
            if request.headers.get('Accept') == 'application/json':
                return jsonify({'message': '細項已新增', 'item_id': it.id})
            else:
                # 普通網頁表單提交，使用 flash
                flash('細項已新增', 'success')
        
        # 普通網頁表單提交，重定向到商品細項頁面
        return redirect(url_for('admin_product_items', pid=pid))
    items = ProductItem.query.filter_by(product_id=p.id).all()
    return render_template('admin/product_items.html', product=p, items=items)

@app.route('/admin/product-items/<int:item_id>/edit', methods=['POST'])
@admin_required(AdminLevel.MANAGER)
def admin_product_item_edit(item_id):
    try:
        # 使用統一的數據庫會話
        item = db.session.query(ProductItem).filter_by(id=item_id).first()
        if not item:
            if request.headers.get('Accept') == 'application/json':
                return jsonify({'error': '商品細項不存在'}), 404
            else:
                flash('商品細項不存在', 'danger')
                return redirect(url_for('admin_products'))
        
        # Check if item belongs to current store
        store_id = session.get('store_id', 1)
        if item.product.store_id != store_id:
            if request.headers.get('Accept') == 'application/json':
                return jsonify({'error': '無權限編輯此商品'}), 403
            else:
                flash('無權限編輯此商品', 'danger')
                return redirect(url_for('admin_products'))
        
        item.price = int(request.form.get('price'))
        item.stock = int(request.form.get('stock'))
        item.discount = request.form.get('discount')
        item.status = ProductStatus(int(request.form.get('status', 1)))
        
        db.session.commit()
        
        # 智能響應格式
        if request.headers.get('Accept') == 'application/json':
            return jsonify({'message': '商品細項已更新'})
        else:
            flash('商品細項已更新', 'success')
            return redirect(url_for('admin_product_items', pid=item.product_id))
            
    except Exception as e:
        db.session.rollback()
        if request.headers.get('Accept') == 'application/json':
            return jsonify({'error': f'更新失敗：{str(e)}'}), 500
        else:
            flash(f'更新失敗：{str(e)}', 'danger')
            return redirect(url_for('admin_product_items', pid=item.product_id if 'item' in locals() else 1))

@app.route('/admin/product-items/<int:item_id>/delete', methods=['POST'])
@admin_required(AdminLevel.MANAGER)
def admin_product_item_delete(item_id):
    try:
        item = db.session.get(ProductItem, item_id)
        if not item:
            return jsonify({'error': '商品細項不存在'}), 404
        
        # Check if item belongs to current store
        store_id = session.get('store_id', 1)
        if item.product.store_id != store_id:
            return jsonify({'error': '無權限刪除此商品'}), 403
        
        db.session.delete(item)
        db.session.commit()
        return jsonify({'message': '商品細項已刪除'})
    except Exception as e:
        return jsonify({'error': f'刪除失敗：{str(e)}'}), 500

# -----------------
# Admin: Coupons
# -----------------

@app.route('/admin/coupons')
@admin_required(AdminLevel.MANAGER)
def admin_coupons():
    store_id = session.get('store_id', 1)
    coupons = Coupon.query.filter_by(store_id=store_id).order_by(Coupon.id.desc()).all()
    return render_template('admin/coupons.html', coupons=coupons)

@app.route('/admin/coupons/<int:cid>/edit', methods=['POST'])
@admin_required(AdminLevel.MANAGER)
def admin_coupon_edit(cid):
    store_id = session.get('store_id', 1)
    # 使用統一的數據庫會話
    cp = db.session.query(Coupon).filter_by(id=cid, store_id=store_id).first()
    if not cp:
        if request.headers.get('Accept') == 'application/json':
            return jsonify({'error': '優惠券不存在'}), 404
        else:
            flash('優惠券不存在', 'danger')
            return redirect(url_for('admin_coupons'))
    
    try:
        cp.type = CouponType(int(request.form.get('type')))
        cp.discount = int(request.form.get('discount'))
        cp.min_price = int(request.form.get('min_price'))
        cp.remain_count = int(request.form.get('remain_count'))
        db.session.commit()
        
        # 智能響應格式
        if request.headers.get('Accept') == 'application/json':
            return jsonify({'message': '優惠券已更新'})
        else:
            flash('優惠券已更新', 'success')
            return redirect(url_for('admin_coupons'))
            
    except Exception as e:
        db.session.rollback()
        if request.headers.get('Accept') == 'application/json':
            return jsonify({'error': f'更新失敗：{str(e)}'}), 500
        else:
            flash(f'更新失敗：{str(e)}', 'danger')
            return redirect(url_for('admin_coupons'))

@app.route('/admin/coupons/<int:cid>/delete', methods=['POST'])
@admin_required(AdminLevel.MANAGER)
def admin_coupon_delete(cid):
    store_id = session.get('store_id', 1)
    # 使用統一的數據庫會話
    cp = db.session.query(Coupon).filter_by(id=cid, store_id=store_id).first()
    if not cp:
        if request.headers.get('Accept') == 'application/json':
            return jsonify({'error': '優惠券不存在'}), 404
        else:
            flash('優惠券不存在', 'danger')
            return redirect(url_for('admin_coupons'))
    
    try:
        db.session.delete(cp)
        db.session.commit()
        
        # 智能響應格式
        if request.headers.get('Accept') == 'application/json':
            return jsonify({'message': '優惠券已刪除'})
        else:
            flash('優惠券已刪除', 'success')
            return redirect(url_for('admin_coupons'))
            
    except Exception as e:
        db.session.rollback()
        if request.headers.get('Accept') == 'application/json':
            return jsonify({'error': f'刪除失敗：{str(e)}'}), 500
        else:
            flash(f'刪除失敗：{str(e)}', 'danger')
            return redirect(url_for('admin_coupons'))

# -----------------
# Admin: RawPage management with TinyMCE
# -----------------

@app.route('/admin/raw-pages')
@admin_required(AdminLevel.MANAGER)
def admin_raw_pages():
    store_id = session.get('store_id', 1)
    raw_pages = RawPage.query.filter_by(store_id=store_id).order_by(RawPage.created_at.desc()).all()
    return render_template('admin/raw_pages.html', pages=raw_pages)

@app.route('/admin/raw-pages/new', methods=['GET','POST'])
@admin_required(AdminLevel.MANAGER)
def admin_raw_page_new():
    if request.method == 'POST':
        store_id = session.get('store_id', 1)
        rp = RawPage(
            store_id=store_id,
            type=PageType[request.form.get('type')],
            title=request.form.get('title'),
            image=request.form.get('image'),
            content=request.form.get('content')
        )
        db.session.add(rp)
        db.session.commit()
        
        # 如果明確請求 JSON 響應（API 調用），返回 JSON
        if request.headers.get('Accept') == 'application/json':
            return jsonify({'message': '頁面已建立', 'page_id': rp.id})
        else:
            # 普通網頁表單提交，使用 flash 和重定向
            flash('頁面已建立', 'success')
            return redirect(url_for('admin_raw_pages'))
    return render_template('admin/raw_page_form.html', page_types=list(PageType))

@app.route('/admin/raw-pages/<int:rid>/edit', methods=['GET', 'POST'])
@admin_required(AdminLevel.MANAGER)
def admin_raw_page_edit(rid):
    store_id = session.get('store_id', 1)
    # 使用統一的數據庫會話
    rp = db.session.query(RawPage).filter_by(id=rid, store_id=store_id).first()
    if not rp:
        if request.headers.get('Accept') == 'application/json':
            return jsonify({'error': '頁面不存在'}), 404
        else:
            flash('頁面不存在', 'danger')
            return redirect(url_for('admin_raw_pages'))
    
    if request.method == 'POST':
        try:
            rp.type = PageType[request.form.get('type')]
            rp.title = request.form.get('title')
            rp.image = request.form.get('image')
            rp.content = request.form.get('content')
            db.session.commit()
            
            # 智能響應格式
            if request.headers.get('Accept') == 'application/json':
                return jsonify({'message': '頁面已更新'})
            else:
                flash('頁面已更新', 'success')
                return redirect(url_for('admin_raw_pages'))
        except Exception as e:
            db.session.rollback()
            if request.headers.get('Accept') == 'application/json':
                return jsonify({'error': f'更新失敗：{str(e)}'}), 500
            else:
                flash(f'更新失敗：{str(e)}', 'danger')
                return redirect(url_for('admin_raw_pages'))
    
    return render_template('admin/raw_page_form.html', page=rp, page_types=list(PageType))

# -----------------
# Admin: Customer Service
# -----------------

@app.route('/admin/customer-service')
@admin_required(AdminLevel.STAFF)
def admin_customer_service():
    store_id = session.get('store_id', 1)
    status_filter = request.args.get('status')
    
    query = ChatSession.query.filter_by(store_id=store_id)
    if status_filter:
        if status_filter == 'resolved':
            query = query.filter_by(status='resolved')
        elif status_filter == 'unresolved':
            query = query.filter(ChatSession.status != 'resolved')
    sessions = query.order_by(ChatSession.created_at.desc()).all()
    
    chats = []
    for cs in sessions:
        last_msg = ChatMessage.query.filter_by(session_id=cs.id).order_by(ChatMessage.created_at.desc()).first()
        user_name = None
        if cs.user_id:
            u = db.session.get(User, cs.user_id)
            user_name = u.name if u else None
        chats.append({
            'id': cs.id,
            'user_id': cs.user_id,
            'user_name': user_name or '訪客',
            'last_message': (last_msg.content if last_msg else ''),
            'status': cs.status if cs.status != 'resolved' else 'resolved',
            'created_at': cs.created_at.strftime('%Y-%m-%d %H:%M') if cs.created_at else '',
            'last_activity': last_msg.created_at.strftime('%Y-%m-%d %H:%M') if last_msg and last_msg.created_at else ''
        })
    
    return render_template('admin/customer_service.html', chats=chats)

@app.route('/admin/customer-service/<int:chat_id>')
@admin_required(AdminLevel.STAFF)
def admin_customer_service_chat(chat_id):
    cs = db.session.get(ChatSession, chat_id)
    if not cs:
        flash('聊天不存在', 'danger')
        return redirect(url_for('admin_customer_service'))
    user_name = None
    if cs.user_id:
        u = db.session.get(User, cs.user_id)
        user_name = u.name if u else None
    messages = ChatMessage.query.filter_by(session_id=cs.id).order_by(ChatMessage.created_at.asc()).all()
    chat = {
        'id': cs.id,
        'user_id': cs.user_id,
        'user_name': user_name or '訪客',
        'messages': [
            {'id': m.id, 'sender': m.sender, 'content': m.content, 'timestamp': m.created_at.strftime('%Y-%m-%d %H:%M') if m.created_at else ''}
            for m in messages
        ],
        'status': cs.status
    }
    return render_template('admin/customer_service_chat.html', chat=chat)

@app.route('/admin/customer-service/<int:chat_id>/resolve', methods=['POST'])
@admin_required(AdminLevel.STAFF)
def admin_customer_service_resolve(chat_id):
    try:
        cs = db.session.get(ChatSession, chat_id)
        if not cs:
            flash('聊天不存在', 'danger')
        else:
            cs.status = 'resolved'
            db.session.commit()
            flash('聊天已標記為已解決', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'操作失敗：{e}', 'danger')
    return redirect(url_for('admin_customer_service_chat', chat_id=chat_id))

@app.route('/admin/customer-service/<int:chat_id>/reply', methods=['POST'])
@admin_required(AdminLevel.STAFF)
def admin_customer_service_reply(chat_id):
    try:
        message = request.form.get('message', '').strip()
        if not message:
            flash('回覆內容不能為空', 'warning')
            return redirect(url_for('admin_customer_service_chat', chat_id=chat_id))
        cs = db.session.get(ChatSession, chat_id)
        if not cs:
            flash('聊天不存在', 'danger')
            return redirect(url_for('admin_customer_service'))
        db.session.add(ChatMessage(session_id=cs.id, sender='admin', content=message))
        if cs.status == 'ai':
            cs.status = 'human'
        db.session.commit()
        flash('回覆已發送', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'發送失敗：{e}', 'danger')
    return redirect(url_for('admin_customer_service_chat', chat_id=chat_id))

# -----------------
# APIs with workflow logging and creation
# -----------------

@app.route('/api/orders', methods=['POST'])
@login_required
def api_create_order():
    """Create a new order"""
    try:
        data = request.get_json()
        if not data or 'items' not in data:
            return jsonify({'error': '缺少訂單項目'}), 400
        
        # Calculate total
        total = 0
        order_items = []
        
        for item_data in data['items']:
            product_item = db.session.get(ProductItem, item_data['product_item_id'])
            if not product_item:
                return jsonify({'error': f'商品細項 {item_data["product_item_id"]} 不存在'}), 404
            
            if product_item.stock < item_data['quantity']:
                return jsonify({'error': f'商品 {product_item.id} 庫存不足'}), 400
            
            price = product_item.price
            if product_item.discount:
                # Apply discount if available
                try:
                    discount_value = float(product_item.discount)
                    price = max(0, price - discount_value)
                except:
                    pass
            
            item_total = price * item_data['quantity']
            total += item_total
            
            # Create order item
            order_item = OrderItem(
                product_item_id=product_item.id,
                quantity=item_data['quantity']
            )
            order_items.append(order_item)
            
            # Update stock
            product_item.stock -= item_data['quantity']
        
        # Create order
        order = Order(
            user_id=session['user_id'],
            store_id=1,  # Default store for now
            total=total,
            status=OrderStatus.PENDING
        )
        db.session.add(order)
        db.session.flush()
        
        # Add order items
        for item in order_items:
            item.order_id = order.id
            db.session.add(item)
        
        db.session.commit()
        
        return jsonify({
            'message': '訂單已建立',
            'order_id': order.id,
            'total': total
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/orders/<int:order_id>/status', methods=['PUT'])
def api_update_order_status(order_id):
    """Update order status"""
    try:
        order = db.session.get(Order, order_id)
        if not order:
            return jsonify({'error': '訂單不存在'}), 404
        
        data = request.get_json()
        new_status = OrderStatus(int(data.get('status')))
        
        # Validate status transition
        if order.status == OrderStatus.PENDING and new_status not in [OrderStatus.PAID, OrderStatus.REFUND]:
            return jsonify({'error': '非法狀態轉移'}), 400
        
        if order.status == OrderStatus.PAID and new_status not in [OrderStatus.SHIPPED, OrderStatus.REFUND]:
            return jsonify({'error': '非法狀態轉移'}), 400
        
        # Update status
        order.status = new_status
        
        # Add order log
        log = OrderLog(
            order_id=order_id,
            action='status_update',
            from_status=order.status.name,
            to_status=new_status.name,
            note=data.get('note', '')
        )
        db.session.add(log)
        
        db.session.commit()
        return jsonify({'message': '訂單狀態已更新'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/orders/<int:order_id>/apply-coupon', methods=['POST'])
@login_required
def apply_coupon_to_order(order_id):
    try:
        order = db.session.get(Order, order_id)
        if not order:
            return jsonify({'error': '訂單不存在'}), 404
        
        coupon_code = request.form.get('coupon_code', '').strip()
        if not coupon_code:
            return jsonify({'error': '請輸入優惠券代碼'}), 400
        
        # Find coupon by code (assuming coupon code is the ID for now)
        if coupon_code.isdigit():
            cp = db.session.get(Coupon, int(coupon_code))
        else:
            cp = None
            
        if not cp:
            return jsonify({'error': '優惠券不存在'}), 404
        
        if cp.remain_count <= 0:
            return jsonify({'error': '優惠券已用完'}), 400
        
        if order.total < cp.min_price:
            return jsonify({'error': f'訂單金額需達 {cp.min_price} 元才能使用此優惠券'}), 400
        
        # Apply coupon discount
        if cp.type == CouponType.DISCOUNT_PERCENT:
            discount_amount = int(order.total * cp.discount / 100)
        else:
            discount_amount = cp.discount
        
        order.total = max(0, order.total - discount_amount)
        cp.remain_count -= 1
        
        db.session.commit()
        return jsonify({
            'message': '優惠券已套用',
            'discount_amount': discount_amount,
            'new_total': order.total
        })
    except Exception as e:
        return jsonify({'error': f'套用失敗：{str(e)}'}), 500

@app.route('/api/orders/<int:order_id>/confirm', methods=['POST'])
@login_required
def confirm_order(order_id):
    try:
        order = db.session.get(Order, order_id)
        if not order:
            return jsonify({'error': '訂單不存在'}), 404
        
        # Update order status to confirmed
        order.status = OrderStatus.PENDING
        
        # Add order log
        log = OrderLog(
            order_id=order_id,
            action='order_confirmed',
            note='用戶確認訂單'
        )
        db.session.add(log)
        
        db.session.commit()
        return jsonify({'message': '訂單已確認'})
    except Exception as e:
        return jsonify({'error': f'確認失敗：{str(e)}'}), 500

# -----------------
# Existing APIs (products, users, stats) remain below
# -----------------

@app.route('/api/products')
def api_products():
    """Get products with optional filtering"""
    try:
        store_id = request.args.get('store', 1, type=int)  # Changed from 'store_id' to 'store'
        category = request.args.get('category', '')
        status = request.args.get('status', '')
        
        query = db.session.query(Product).filter_by(store_id=store_id)
        
        if category:
            query = query.filter_by(catalog=category)
        if status:
            query = query.filter_by(status=ProductStatus(int(status)))
        
        products = query.all()
        
        result = []
        for p in products:
            # Get product items
            items = ProductItem.query.filter_by(product_id=p.id).all()
            product_data = {
                'id': p.id,
                'name': p.name,
                'catalog': p.catalog,
                'descriptions': p.descriptions,
                'detail': p.detail,
                'picture': p.picture,
                'carousel': p.carousel,
                'status': p.status.value,
                'items': []
            }
            
            for item in items:
                item_data = {
                    'id': item.id,
                    'price': item.price,
                    'stock': item.stock,
                    'discount': item.discount,
                    'status': item.status.value
                }
                product_data['items'].append(item_data)
            
            result.append(product_data)
        
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/products/<int:product_id>')
def api_product_detail(product_id: int):
    try:
        # 使用 Flask-SQLAlchemy 會話查詢
        p = db.session.query(Product).filter_by(id=product_id).first()
        if not p:
            return jsonify({'error': '商品不存在'}), 404
        items = ProductItem.query.filter_by(product_id=p.id).all()
        return jsonify({
            'id': p.id,
            'name': p.name,
            'catalog': p.catalog,
            'descriptions': p.descriptions,
            'detail': p.detail,
            'picture': p.picture,
            'carousel': p.carousel,
            'status': p.status.value,
            'items': [
                {
                    'id': it.id,
                    'name': it.name,
                    'price': it.price,
                    'stock': it.stock,
                    'status': it.status.value,
                    'discount': it.discount,
                } for it in items
            ]
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/orders/<int:order_id>')
@login_required
def api_order_detail(order_id):
    """Get order details"""
    try:
        order = db.session.get(Order, order_id)
        if not order:
            return jsonify({'error': '訂單不存在'}), 404
        
        # Check if user owns this order
        if session.get('user_type') == 'user' and order.user_id != session['user_id']:
            return jsonify({'error': '無權限查看此訂單'}), 403
        
        order_data = {
            'id': order.id,
            'total': order.total,
            'status': order.status.value,
            'created_at': order.created_at.strftime('%Y-%m-%d %H:%M'),
            'items': []
        }
        
        for item in order.order_items:
            item_data = {
                'product_name': item.product_item.name if item.product_item else '未知商品',
                'quantity': item.quantity,
                'price': item.product_item.price if item.product_item else None
            }
            order_data['items'].append(item_data)
        
        return jsonify(order_data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/users/<int:user_id>')
@login_required
def api_user_detail(user_id):
    """Get user details"""
    try:
        user = db.session.get(User, user_id)
        if not user:
            return jsonify({'error': '用戶不存在'}), 404
        
        # Check if user can view this profile
        if session.get('user_type') == 'user' and session['user_id'] != user_id:
            return jsonify({'error': '無權限查看此用戶資料'}), 403
        
        user_data = {
            'id': user.id,
            'name': user.name,
            'email': user.email,
            'phone': user.phone,
            'level': user.level.value,
            'wallet': user.wallet,
            'award': user.award
        }
        
        return jsonify(user_data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/orders', methods=['GET'])
def api_get_orders():
    orders = Order.query.order_by(Order.created_at.desc()).all()
    result = []
    for order in orders:
        order_data = {
            'id': order.id,
            'user_email': order.user.email if order.user else None,
            'total': order.total,
            'status': order.status.value if isinstance(order.status, OrderStatus) else int(order.status),
            'created_at': order.created_at.isoformat() if hasattr(order, 'created_at') and order.created_at else None,
            'order_items': []
        }
        for item in order.order_items:
            order_data['order_items'].append({
                'product_name': item.product_item.name if item.product_item else None,
                'count': item.quantity,
                'price': item.product_item.price if item.product_item else None
            })
        result.append(order_data)
    return jsonify(result)

@app.route('/api/users', methods=['GET'])
def api_get_users():
    users = User.query.all()
    result = []
    for user in users:
        user_data = {
            'id': user.id,
            'account': user.account,
            'name': user.name,
            'email': user.email,
            'phone': user.phone,
            'level': user.level.value if isinstance(user.level, UserLevel) else str(user.level),
            'wallet': user.wallet,
            'award': user.award,
            'created_at': user.created_at.isoformat() if hasattr(user, 'created_at') and user.created_at else None
        }
        result.append(user_data)
    return jsonify(result)

@app.route('/api/stats')
@admin_required(AdminLevel.STAFF)
def api_stats():
    """Get store statistics"""
    try:
        store_id = session.get('store_id', 1)
        total_products = Product.query.filter_by(store_id=store_id).count()
        total_orders = Order.query.filter_by(store_id=store_id).count()
        total_users = db.session.query(User).join(Order).filter(Order.store_id == store_id).distinct().count()

        # Monthly metrics
        now = datetime.now()
        monthly_orders = Order.query.filter(
            Order.store_id == store_id,
            func.extract('year', Order.created_at) == now.year,
            func.extract('month', Order.created_at) == now.month,
        ).count()
        monthly_revenue = db.session.query(func.coalesce(func.sum(Order.total), 0)).filter(
            Order.store_id == store_id,
            Order.status == OrderStatus.PAID,
            func.extract('year', Order.created_at) == now.year,
            func.extract('month', Order.created_at) == now.month,
        ).scalar() or 0

        # Category stats (count products by catalog)
        category_counts = db.session.query(Product.catalog, func.count(Product.id)).filter_by(store_id=store_id).group_by(Product.catalog).all()
        category_stats = [{ 'category': c, 'count': int(n) } for c, n in category_counts]

        stats = {
            'total_products': total_products,
            'total_orders': total_orders,
            'total_users': total_users,
            'monthly_orders': monthly_orders,
            'monthly_revenue': int(monthly_revenue),
            'category_stats': category_stats,
            'store_id': store_id
        }
        return jsonify(stats)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/products/<int:product_id>/add-to-cart', methods=['POST'])
@login_required
def add_to_cart(product_id):
    """Add product to cart"""
    try:
        product = db.session.get(Product, product_id)
        if not product:
            return jsonify({'error': '商品不存在'}), 404
        
        data = request.get_json()
        product_item_id = data.get('product_item_id')
        quantity = int(data.get('quantity', 1))
        
        if product_item_id:
            product_item = db.session.get(ProductItem, product_item_id)
            if not product_item or product_item.product_id != product_id:
                return jsonify({'error': '商品細項不存在'}), 404
            
            if product_item.stock < quantity:
                return jsonify({'error': '庫存不足'}), 400
        
        # In a real app, you would save cart to database or session
        # For now, return success
        return jsonify({
            'message': '已加入購物車',
            'product_id': product_id,
            'product_item_id': product_item_id,
            'quantity': quantity
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/chat/session', methods=['POST'])
@login_required
def api_chat_new_session():
    try:
        store_id = session.get('store_id', 1)
        cs = ChatSession(store_id=store_id, user_id=session.get('user_id'), status='ai')
        db.session.add(cs)
        db.session.commit()
        return jsonify({'session_id': cs.id})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/about')
def about_page():
    store_id = session.get('store_id', 1)
    page = RawPage.query.filter_by(store_id=store_id, type=PageType.ABOUT_US).first()
    return render_template('raw_page.html', page=page)

@app.route('/contact')
def contact_page():
    store_id = session.get('store_id', 1)
    page = RawPage.query.filter_by(store_id=store_id, type=PageType.CONTACT_US).first()
    return render_template('raw_page.html', page=page)

@app.route('/privacy')
def privacy_page():
    store_id = session.get('store_id', 1)
    page = RawPage.query.filter_by(store_id=store_id, type=PageType.PRIVACY_POLICY).first()
    return render_template('raw_page.html', page=page)

@app.route('/terms')
def terms_page():
    store_id = session.get('store_id', 1)
    page = RawPage.query.filter_by(store_id=store_id, type=PageType.TERM_SERVICE).first()
    return render_template('raw_page.html', page=page)

@app.route('/api/product-items/bulk', methods=['POST'])
def api_product_items_bulk():
    try:
        data = request.get_json() or {}
        ids = data.get('ids', [])
        if not isinstance(ids, list) or not ids:
            return jsonify({'error': '缺少項目 ID'}), 400
        items = ProductItem.query.filter(ProductItem.id.in_(ids)).all()
        result = []
        for it in items:
            result.append({
                'id': it.id,
                'name': it.name,
                'price': it.price,
                'stock': it.stock,
                'product_id': it.product_id,
                'product_name': it.product.name if it.product else None
            })
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# -----------------
# Export Functions
# -----------------

@app.route('/admin/export/users')
@admin_required(AdminLevel.MANAGER)
def export_users():
    """匯出用戶資料為CSV"""
    try:
        store_id = session.get('store_id', 1)
        users = db.session.query(User).join(Order).filter(Order.store_id == store_id).distinct().all()
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # CSV表頭
        writer.writerow(['用戶ID', '帳號', '姓名', '電子郵件', '電話', '地址', '會員等級', '錢包餘額', '獎金餘額', '註冊時間'])
        
        # 數據行
        for user in users:
            writer.writerow([
                user.id,
                user.account,
                user.name,
                user.email,
                user.phone or '',
                user.address or '',
                user.level.name if hasattr(user.level, 'name') else str(user.level),
                user.wallet,
                user.award,
                user.created_at.strftime('%Y-%m-%d %H:%M:%S') if user.created_at else ''
            ])
        
        output.seek(0)
        return Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={
                'Content-Disposition': f'attachment; filename=users_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
            }
        )
    except Exception as e:
        flash(f'匯出失敗：{str(e)}', 'danger')
        return redirect(url_for('admin_users'))

@app.route('/admin/export/products')
@admin_required(AdminLevel.MANAGER)
def export_products():
    """匯出商品資料為CSV"""
    try:
        store_id = session.get('store_id', 1)
        products = Product.query.filter_by(store_id=store_id).all()
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # CSV表頭
        writer.writerow(['商品ID', '名稱', '分類', '簡介', '狀態', '建立時間'])
        
        # 數據行
        for product in products:
            writer.writerow([
                product.id,
                product.name,
                product.catalog,
                product.descriptions or '',
                '正常' if product.status.value == 1 else '隱藏',
                product.created_at.strftime('%Y-%m-%d %H:%M:%S') if product.created_at else ''
            ])
        
        output.seek(0)
        return Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={
                'Content-Disposition': f'attachment; filename=products_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
            }
        )
    except Exception as e:
        flash(f'匯出失敗：{str(e)}', 'danger')
        return redirect(url_for('admin_products'))

@app.route('/admin/export/orders')
@admin_required(AdminLevel.STAFF)
def export_orders():
    """匯出訂單資料為CSV"""
    try:
        store_id = session.get('store_id', 1)
        orders = Order.query.filter_by(store_id=store_id).order_by(Order.created_at.desc()).all()
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # CSV表頭
        writer.writerow(['訂單ID', '用戶姓名', '用戶電子郵件', '總金額', '狀態', '優惠券', '備註', '建立時間'])
        
        # 數據行
        for order in orders:
            writer.writerow([
                order.id,
                order.user.name if order.user else '',
                order.user.email if order.user else '',
                order.total,
                order.status.name if hasattr(order.status, 'name') else str(order.status),
                order.coupon or '',
                order.remark or '',
                order.created_at.strftime('%Y-%m-%d %H:%M:%S') if order.created_at else ''
            ])
        
        output.seek(0)
        return Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={
                'Content-Disposition': f'attachment; filename=orders_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
            }
        )
    except Exception as e:
        flash(f'匯出失敗：{str(e)}', 'danger')
        return redirect(url_for('admin_orders'))

# -----------------
# Image Upload API
# -----------------

def allowed_file(filename):
    """檢查文件是否為允許的圖片格式"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/api/upload/image', methods=['POST'])
@admin_required(AdminLevel.STAFF)
def upload_image():
    """上傳圖片API"""
    if 'file' not in request.files:
        return jsonify({'error': '沒有選擇文件'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': '沒有選擇文件'}), 400
    
    if file and allowed_file(file.filename):
        try:
            # 生成唯一文件名
            file_extension = file.filename.rsplit('.', 1)[1].lower()
            unique_filename = f"{uuid.uuid4().hex}.{file_extension}"
            
            # 保存文件
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
            file.save(file_path)
            
            # 返回文件URL
            file_url = url_for('uploaded_file', filename=unique_filename, _external=True)
            
            return jsonify({
                'message': '圖片上傳成功',
                'url': file_url,
                'filename': unique_filename
            })
            
        except Exception as e:
            return jsonify({'error': f'上傳失敗：{str(e)}'}), 500
    else:
        return jsonify({'error': '不支援的文件格式，請上傳 PNG, JPG, JPEG, GIF 或 WebP 格式'}), 400

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    """提供上傳的圖片文件"""
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('errors/500.html'), 500

if __name__ == '__main__':
    # init_db(seed=False)
    app.run(debug=True, host='localhost', port=8994)