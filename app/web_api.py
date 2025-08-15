from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date
import json
import os
from typing import List, Dict, Any
from functools import wraps
from sqlalchemy import func

# Import models
from .models import (
    Base, Store, User, Product, ProductItem, Order, OrderItem, 
    Delivery, Payment, Coupon, Admin, RealName, WalletRecord, Interrogation,
    PageType, AdminLevel, CouponType, DeliveryStatus, ProductStatus, 
    OrderStatus, PaymentStatus, UserLevel, WalletType, OrderLog, RawPage,
    init_db as models_init_db,
)

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-here')
DB_PATH = os.environ.get("APP_DB_PATH", os.path.join(os.getcwd(), "storage", "app.db"))
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', f"sqlite:///{DB_PATH}")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
CORS(app)

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
        # if not check_password_hash(user.password, password):
        #     flash('密碼錯誤', 'danger')
        #     return render_template('login.html')
        
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
    return render_template('index.html', products=products)

# Remove duplicate /login here; keep admin /login defined earlier

@app.route('/user/login', methods=['GET', 'POST'])
def user_login():
    """Frontend user login page"""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        
        if username == 'user' and password == 'user1234':
            session['user_id'] = 'user'
            session['user_type'] = 'user'
            session['username'] = 'user'
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
    
    # Get user's orders
    user_orders = Order.query.filter_by(user_id=session['user_id']).order_by(Order.created_at.desc()).limit(5).all()
    return render_template('user/dashboard.html', orders=user_orders)

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
        
        if not message:
            return jsonify({'error': '訊息不能為空'}), 400
        
        # Simple AI response simulation
        # In real implementation, this would call the AI service from main.py
        ai_response = generate_ai_response(message)
        
        return jsonify({
            'success': True,
            'response': ai_response,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def generate_ai_response(message):
    """Generate AI response based on user message"""
    message_lower = message.lower()
    
    if '你好' in message or 'hello' in message_lower:
        return '您好！我是智能客服助手，很高興為您服務。請問有什麼可以幫助您的嗎？'
    elif '商品' in message or '產品' in message:
        return '我們有各種優質商品，包括電子產品、居家用品、戶外裝備等。您可以在首頁瀏覽所有商品，或告訴我您感興趣的類別。'
    elif '訂單' in message or '購買' in message:
        return '您可以在用戶儀表板查看您的訂單狀態。如需協助，請提供訂單編號，我會為您查詢。'
    elif '退貨' in message or '退款' in message:
        return '退貨政策：商品收到後7天內，如發現商品有瑕疵或不符合描述，可申請退貨。請聯繫客服處理。'
    elif '運費' in message or '配送' in message:
        return '我們提供多種配送方式：宅配、自取、快遞、郵寄。運費根據配送方式和地區計算，通常在結帳時會顯示。'
    elif '無法解決' in message or '真人' in message:
        return '如果無法解決您的問題，請等待真人客服回覆。我們會盡快為您處理。'
    else:
        return '感謝您的詢問。如果我的回答無法解決您的問題，請等待真人客服回覆，或嘗試重新描述您的問題。'

# -----------------
# Admin Routes (Protected)
# -----------------

@app.route('/admin')
@admin_required(AdminLevel.STAFF)
def admin_dashboard():
    store_id = session.get('store_id', 1)
    total_products = Product.query.filter_by(store_id=store_id).count()
    total_orders = Order.query.filter_by(store_id=store_id).count()
    
    recent_orders = Order.query.filter_by(store_id=store_id).order_by(Order.created_at.desc()).limit(5).all()
    
    return render_template('admin/dashboard.html', 
                         total_products=total_products,
                         total_orders=total_orders,
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
        return jsonify({'error': '訂單不存在'}), 404
    
    try:
        new_status = OrderStatus(int(request.form.get('status')))
        order.status = new_status
        
        # Add order log
        log = OrderLog(
            order_id=order_id,
            action='status_update',
            from_status=order.status.name,
            to_status=new_status.name,
            note=request.form.get('note', '')
        )
        db.session.add(log)
        
        db.session.commit()
        return jsonify({'message': '訂單狀態已更新'})
    except Exception as e:
        return jsonify({'error': f'更新失敗：{str(e)}'}), 500

@app.route('/admin/orders/<int:order_id>/delivery', methods=['POST'])
@admin_required(AdminLevel.STAFF)
def admin_order_update_delivery(order_id):
    store_id = session.get('store_id', 1)
    order = Order.query.filter_by(id=order_id, store_id=store_id).first()
    if not order:
        return jsonify({'error': '訂單不存在'}), 404
    
    try:
        # Create or update delivery info
        delivery = order.delivery
        if not delivery:
            delivery = Delivery(order_id=order_id)
            db.session.add(delivery)
        
        delivery.destination = request.form.get('destination')
        delivery.method = request.form.get('method')
        delivery.freight = int(request.form.get('freight', 0))
        delivery.remark = request.form.get('remark')
        
        db.session.commit()
        return jsonify({'message': '配送資訊已更新'})
    except Exception as e:
        return jsonify({'error': f'更新失敗：{str(e)}'}), 500

@app.route('/admin/orders/<int:order_id>/payment', methods=['POST'])
@admin_required(AdminLevel.STAFF)
def admin_order_update_payment(order_id):
    store_id = session.get('store_id', 1)
    order = Order.query.filter_by(id=order_id, store_id=store_id).first()
    if not order:
        return jsonify({'error': '訂單不存在'}), 404
    
    try:
        # Create or update payment info
        payment = order.payment
        if not payment:
            payment = Payment(order_id=order_id)
            db.session.add(payment)
        
        payment.method = request.form.get('method')
        payment.details = request.form.get('details')
        
        db.session.commit()
        return jsonify({'message': '付款資訊已更新'})
    except Exception as e:
        return jsonify({'error': f'更新失敗：{str(e)}'}), 500

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
        user = User(
            account=request.form.get('account'),
            password=generate_password_hash(request.form.get('password')),
            name=request.form.get('name'),
            email=request.form.get('email'),
            phone=request.form.get('phone'),
            address=request.form.get('address'),
            level=UserLevel.FIRST
        )
        db.session.add(user)
        db.session.commit()
        return jsonify({'message': '用戶已新增'})
    except Exception as e:
        return jsonify({'error': f'新增失敗：{str(e)}'}), 500

@app.route('/admin/users/<int:user_id>/edit', methods=['POST'])
@admin_required(AdminLevel.MANAGER)
def admin_users_edit(user_id):
    try:
        user = db.session.get(User, user_id)
        if not user:
            return jsonify({'error': '用戶不存在'}), 404
        
        user.name = request.form.get('name')
        user.email = request.form.get('email')
        user.phone = request.form.get('phone')
        user.address = request.form.get('address')
        user.level = UserLevel(int(request.form.get('level', 1)))
        
        db.session.commit()
        return jsonify({'message': '用戶已更新'})
    except Exception as e:
        return jsonify({'error': f'更新失敗：{str(e)}'}), 500

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
        store_id = session.get('store_id', 1)
        p = Product(
            store_id=store_id,
            catalog=request.form.get('catalog'),
            name=request.form.get('name'),
            descriptions=request.form.get('descriptions'),
            detail=request.form.get('detail'),
            picture=request.form.get('picture'),
            status=ProductStatus.NORMAL
        )
        db.session.add(p)
        db.session.commit()
        flash('商品已建立', 'success')
        return redirect(url_for('admin_products'))
    return render_template('admin/product_form.html')

@app.route('/admin/products/<int:pid>/edit', methods=['GET', 'POST'])
@admin_required(AdminLevel.MANAGER)
def admin_product_edit(pid):
    store_id = session.get('store_id', 1)
    p = Product.query.filter_by(id=pid, store_id=store_id).first()
    if not p:
        flash('商品不存在', 'danger')
        return redirect(url_for('admin_products'))
    
    if request.method == 'POST':
        p.catalog = request.form.get('catalog')
        p.name = request.form.get('name')
        p.descriptions = request.form.get('descriptions')
        p.detail = request.form.get('detail')
        p.picture = request.form.get('picture')
        p.status = ProductStatus(int(request.form.get('status', 1)))
        db.session.commit()
        flash('商品已更新', 'success')
        return redirect(url_for('admin_products'))
    
    return render_template('admin/product_form.html', product=p)

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

# -----------------
# Admin: Product Items
# -----------------

@app.route('/admin/products/<int:pid>/items', methods=['GET', 'POST'])
@admin_required(AdminLevel.MANAGER)
def admin_product_items(pid):
    p = Product.query.get(pid)
    if not p:
        flash('商品不存在', 'danger')
        return redirect(url_for('admin_products'))
    if request.method == 'POST':
        name = request.form.get('name','').strip()
        price = int(request.form.get('price','0') or 0)
        stock = int(request.form.get('stock','0') or 0)
        if not name or price <= 0:
            flash('名稱與價格必填', 'warning')
        else:
            it = ProductItem(product_id=p.id, name=name, price=price, stock=stock, discount=request.form.get('discount',''))
            db.session.add(it)
            db.session.commit()
            flash('細項已新增', 'success')
        return redirect(url_for('admin_product_items', pid=pid))
    items = ProductItem.query.filter_by(product_id=p.id).all()
    return render_template('admin/product_items.html', product=p, items=items)

@app.route('/admin/product-items/<int:item_id>/edit', methods=['POST'])
@admin_required(AdminLevel.MANAGER)
def admin_product_item_edit(item_id):
    try:
        item = db.session.get(ProductItem, item_id)
        if not item:
            return jsonify({'error': '商品細項不存在'}), 404
        
        # Check if item belongs to current store
        store_id = session.get('store_id', 1)
        if item.product.store_id != store_id:
            return jsonify({'error': '無權限編輯此商品'}), 403
        
        item.price = int(request.form.get('price'))
        item.stock = int(request.form.get('stock'))
        item.discount = request.form.get('discount')
        item.carousel = request.form.get('carousel')
        item.status = ProductStatus(int(request.form.get('status', 1)))
        
        db.session.commit()
        return jsonify({'message': '商品細項已更新'})
    except Exception as e:
        return jsonify({'error': f'更新失敗：{str(e)}'}), 500

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
    cp = Coupon.query.filter_by(id=cid, store_id=store_id).first()
    if not cp:
        return jsonify({'error': '優惠券不存在'}), 404
    
    try:
        cp.type = CouponType(int(request.form.get('type')))
        cp.discount = int(request.form.get('discount'))
        cp.min_price = int(request.form.get('min_price'))
        cp.remain_count = int(request.form.get('remain_count'))
        db.session.commit()
        return jsonify({'message': '優惠券已更新'})
    except Exception as e:
        return jsonify({'error': f'更新失敗：{str(e)}'}), 500

@app.route('/admin/coupons/<int:cid>/delete', methods=['POST'])
@admin_required(AdminLevel.MANAGER)
def admin_coupon_delete(cid):
    store_id = session.get('store_id', 1)
    cp = Coupon.query.filter_by(id=cid, store_id=store_id).first()
    if not cp:
        return jsonify({'error': '優惠券不存在'}), 404
    
    try:
        db.session.delete(cp)
        db.session.commit()
        return jsonify({'message': '優惠券已刪除'})
    except Exception as e:
        return jsonify({'error': f'刪除失敗：{str(e)}'}), 500

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
        flash('頁面已建立', 'success')
        return redirect(url_for('admin_raw_pages'))
    return render_template('admin/raw_page_form.html')

@app.route('/admin/raw-pages/<int:rid>/edit', methods=['GET', 'POST'])
@admin_required(AdminLevel.MANAGER)
def admin_raw_page_edit(rid):
    store_id = session.get('store_id', 1)
    rp = RawPage.query.filter_by(id=rid, store_id=store_id).first()
    if not rp:
        flash('頁面不存在', 'danger')
        return redirect(url_for('admin_raw_pages'))
    
    if request.method == 'POST':
        rp.type = PageType[request.form.get('type')]
        rp.title = request.form.get('title')
        rp.image = request.form.get('image')
        rp.content = request.form.get('content')
        db.session.commit()
        flash('頁面已更新', 'success')
        return redirect(url_for('admin_raw_pages'))
    
    return render_template('admin/raw_page_form.html', page=rp)

# -----------------
# Admin: Customer Service
# -----------------

@app.route('/admin/customer-service')
@admin_required(AdminLevel.STAFF)
def admin_customer_service():
    store_id = session.get('store_id', 1)
    # Get chat history from chat_store (simulated for now)
    # In real implementation, this would connect to AgentBuilder's chat_store
    # For now, simulate chat records based on store_id
    chats = []
    for i in range(10):
        chat = {
            'id': i + 1,
            'user_id': f'user_{i+1}',
            'username': f'用戶{i+1}',
            'last_message': f'這是第{i+1}個聊天的最後一條訊息',
            'status': 'unresolved' if i < 5 else 'resolved',
            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M'),
            'store_id': store_id
        }
        chats.append(chat)
    
    # Sort unresolved chats first
    chats.sort(key=lambda x: (x['status'] == 'resolved', x['created_at']), reverse=True)
    
    return render_template('admin/customer_service.html', chats=chats)

@app.route('/admin/customer-service/<int:chat_id>')
@admin_required(AdminLevel.STAFF)
def admin_customer_service_chat(chat_id):
    # Get specific chat details
    chat = {
        'id': chat_id,
        'user_id': 'user123',
        'user_name': '張小明',
        'messages': [
            {
                'id': 1,
                'sender': 'user',
                'content': '請問商品什麼時候會到貨？',
                'timestamp': '2025-08-15 10:30:00'
            },
            {
                'id': 2,
                'sender': 'ai',
                'content': '根據您的訂單狀態，商品預計明天會到貨。',
                'timestamp': '2025-08-15 10:31:00'
            },
            {
                'id': 3,
                'sender': 'user',
                'content': '可以幫我追蹤物流嗎？',
                'timestamp': '2025-08-15 14:20:00'
            }
        ],
        'status': 'unresolved'
    }
    return render_template('admin/customer_service_chat.html', chat=chat)

@app.route('/admin/customer-service/<int:chat_id>/resolve', methods=['POST'])
@admin_required(AdminLevel.STAFF)
def admin_customer_service_resolve(chat_id):
    try:
        # Mark chat as resolved
        # In real implementation, this would update the chat_store
        flash('聊天已標記為已解決', 'success')
    except Exception as e:
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
        
        # Add admin reply to chat
        # In real implementation, this would update the chat_store
        flash('回覆已發送', 'success')
    except Exception as e:
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
                quantity=item_data['quantity'],
                price=price
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
        store_id = request.args.get('store_id', 1, type=int)
        category = request.args.get('category', '')
        status = request.args.get('status', '')
        
        query = Product.query.filter_by(store_id=store_id)
        
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
                'status': p.status.value,
                'items': []
            }
            
            for item in items:
                item_data = {
                    'id': item.id,
                    'price': item.price,
                    'stock': item.stock,
                    'discount': item.discount,
                    'carousel': item.carousel,
                    'status': item.status.value
                }
                product_data['items'].append(item_data)
            
            result.append(product_data)
        
        return jsonify(result)
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
                'product_name': item.product.name if item.product else '未知商品',
                'quantity': item.quantity,
                'price': item.price
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
            'status': order.status.value if isinstance(order.status, OrderStatus) else str(order.status),
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
        
        # Monthly orders
        current_month = datetime.now().month
        monthly_orders = Order.query.filter_by(store_id=store_id).filter(
            func.extract('month', Order.created_at) == current_month
        ).count()
        
        # Revenue calculation
        orders = Order.query.filter_by(store_id=store_id, status=OrderStatus.PAID).all()
        total_revenue = sum(order.total for order in orders)
        
        stats = {
            'total_products': total_products,
            'total_orders': total_orders,
            'monthly_orders': monthly_orders,
            'total_revenue': total_revenue,
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
    app.run(debug=True, host='localhost', port=8833)