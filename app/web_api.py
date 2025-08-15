from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date
import json
import os
from typing import List, Dict, Any
from functools import wraps

# Import models
from .models import (
    Base, Store, User, Product, ProductItem, Order, OrderItem, 
    Delivery, Payment, Coupon, Admin, RealName, WalletRecord, Interrogation,
    PageType, AdminLevel, CouponType, DeliveryStatus, ProductStatus, 
    OrderStatus, PaymentStatus, UserLevel, WalletType, OrderLog,
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
        # Demo admin credential
        if username == 'admin' and password == 'admin1234':
            # In a real app, lookup Admin and its store
            session['user_id'] = 0
            session['user_type'] = 'admin'
            session['username'] = 'admin'
            session['store_id'] = int(request.form.get('store_id', 1))
            session.permanent = True
            flash('管理員登入成功', 'success')
            return redirect(url_for('admin_dashboard'))
        flash('帳號或密碼錯誤', 'danger')
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
    total_products = Product.query.count()
    total_orders = Order.query.count()
    total_users = User.query.count()
    recent_orders = Order.query.order_by(Order.created_at.desc()).limit(5).all()
    
    return render_template('admin/dashboard.html', 
                         total_products=total_products,
                         total_orders=total_orders,
                         total_users=total_users,
                         recent_orders=recent_orders)

# -----------------
# Admin: Orders
# -----------------

@app.route('/admin/orders')
@admin_required(AdminLevel.STAFF)
def admin_orders():
    orders = Order.query.order_by(Order.created_at.desc()).all()
    return render_template('admin/orders.html', orders=orders)

@app.route('/admin/orders/<int:order_id>')
@admin_required(AdminLevel.STAFF)
def admin_order_detail(order_id):
    order = Order.query.get(order_id)
    if not order:
        flash('訂單不存在', 'danger')
        return redirect(url_for('admin_orders'))
    return render_template('admin/order_detail.html', order=order)

@app.route('/admin/orders/<int:order_id>/status', methods=['POST'])
@admin_required(AdminLevel.STAFF)
def admin_order_update_status(order_id):
    try:
        order = Order.query.get(order_id)
        if not order:
            flash('訂單不存在', 'danger')
            return redirect(url_for('admin_orders'))
        to_status_val = int(request.form.get('status'))
        to_status = OrderStatus(to_status_val)
        from_status = order.status
        # Validate transitions
        if from_status == OrderStatus.PENDING and to_status not in [OrderStatus.PAID, OrderStatus.REFUND]:
            flash('非法狀態轉移：待付款只能改為 已付款 或 退款', 'warning')
            return redirect(url_for('admin_orders'))
        if from_status == OrderStatus.PAID and to_status not in [OrderStatus.SHIPPED, OrderStatus.REFUND]:
            flash('非法狀態轉移：已付款只能改為 已發貨 或 退款', 'warning')
            return redirect(url_for('admin_orders'))
        # Sync payment and stock
        if to_status == OrderStatus.PAID:
            if order.payment:
                order.payment.status = PaymentStatus.PAID
        if to_status == OrderStatus.REFUND:
            # restock items
            for oi in order.order_items:
                if oi.product_item:
                    oi.product_item.stock += oi.quantity
            if order.payment:
                order.payment.status = PaymentStatus.REFUNDED
        order.status = to_status
        log = OrderLog(order_id=order.id, action='status_change', from_status=str(from_status.name), to_status=str(to_status.name), note='admin panel update')
        db.session.add(log)
        db.session.commit()
        flash('訂單狀態已更新', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'更新失敗：{e}', 'danger')
    return redirect(url_for('admin_orders'))

@app.route('/admin/orders/<int:order_id>/delivery', methods=['POST'])
@admin_required(AdminLevel.STAFF)
def admin_order_update_delivery(order_id):
    try:
        order = Order.query.get(order_id)
        if not order:
            flash('訂單不存在', 'danger')
            return redirect(url_for('admin_order_detail', order_id=order_id))
        
        # Create or update delivery info
        if not order.delivery:
            order.delivery = Delivery()
        
        order.delivery.destination = request.form.get('destination', '')
        order.delivery.method = DeliveryMethod(request.form.get('method', 'HOME_DELIVERY'))
        order.delivery.freight = int(request.form.get('freight', 0) or 0)
        order.delivery.remark = request.form.get('remark', '')
        
        # Update delivery status based on order status
        if order.status == OrderStatus.SHIPPED:
            order.delivery.status = DeliveryStatus.SHIPPED
        elif order.status == OrderStatus.REFUND:
            order.delivery.status = DeliveryStatus.REFUND
        
        db.session.commit()
        flash('物流資訊已更新', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'更新失敗：{e}', 'danger')
    return redirect(url_for('admin_order_detail', order_id=order_id))

@app.route('/admin/orders/<int:order_id>/payment', methods=['POST'])
@admin_required(AdminLevel.STAFF)
def admin_order_update_payment(order_id):
    try:
        order = Order.query.get(order_id)
        if not order:
            flash('訂單不存在', 'danger')
            return redirect(url_for('admin_order_detail', order_id=order_id))
        
        # Create or update payment info
        if not order.payment:
            order.payment = Payment()
        
        order.payment.payment_method = request.form.get('payment_method', 'credit_card')
        order.payment.details = request.form.get('details', '')
        
        # Update payment status based on order status
        if order.status == OrderStatus.PAID:
            order.payment.status = PaymentStatus.PAID
        elif order.status == OrderStatus.REFUND:
            order.payment.status = PaymentStatus.REFUNDED
        
        db.session.commit()
        flash('付款資訊已更新', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'更新失敗：{e}', 'danger')
    return redirect(url_for('admin_order_detail', order_id=order_id))

# -----------------
# Admin: Users
# -----------------

@app.route('/admin/users')
@admin_required(AdminLevel.MANAGER)
def admin_users():
    users = User.query.order_by(User.created_at.desc()).all()
    return render_template('admin/users.html', users=users)

@app.route('/admin/users', methods=['POST'])
@admin_required(AdminLevel.MANAGER)
def admin_users_add():
    try:
        account = request.form.get('account', '').strip()
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        phone = request.form.get('phone', '').strip()
        level = int(request.form.get('level', 1))
        wallet = int(request.form.get('wallet', 0) or 0)
        address = request.form.get('address', '').strip()
        
        if not account or not name or not email:
            flash('帳號、姓名與Email為必填欄位', 'warning')
            return redirect(url_for('admin_users'))
        
        # Check if account or email already exists
        existing_user = User.query.filter((User.account == account) | (User.email == email)).first()
        if existing_user:
            flash('帳號或Email已存在', 'warning')
            return redirect(url_for('admin_users'))
        
        user = User(
            account=account,
            password=generate_password_hash('changeme'),  # Default password
            name=name,
            email=email,
            phone=phone,
            address=address,
            wallet=wallet,
            award=0,
            level=UserLevel(level),
            register_ip=request.remote_addr
        )
        db.session.add(user)
        db.session.commit()
        flash('用戶已新增', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'新增失敗：{e}', 'danger')
    return redirect(url_for('admin_users'))

@app.route('/admin/users/<int:user_id>/edit', methods=['POST'])
@admin_required(AdminLevel.MANAGER)
def admin_users_edit(user_id):
    try:
        user = User.query.get(user_id)
        if not user:
            flash('用戶不存在', 'danger')
            return redirect(url_for('admin_users'))
        
        user.name = request.form.get('name', user.name)
        user.email = request.form.get('email', user.email)
        user.phone = request.form.get('phone', user.phone)
        user.level = UserLevel(int(request.form.get('level', user.level.value)))
        user.wallet = int(request.form.get('wallet', user.wallet) or 0)
        user.award = int(request.form.get('award', user.award) or 0)
        user.address = request.form.get('address', user.address)
        
        db.session.commit()
        flash('用戶已更新', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'更新失敗：{e}', 'danger')
    return redirect(url_for('admin_users'))

@app.route('/admin/users/<int:user_id>/details')
@admin_required(AdminLevel.MANAGER)
def admin_users_details(user_id):
    try:
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': '用戶不存在'}), 404
        
        return jsonify({
            'id': user.id,
            'account': user.account,
            'name': user.name,
            'email': user.email,
            'phone': user.phone,
            'level': user.level.value,
            'level_name': user.level.name,
            'wallet': user.wallet,
            'award': user.award,
            'address': user.address,
            'created_at': user.created_at.strftime('%Y-%m-%d %H:%M') if user.created_at else '—'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# -----------------
# Admin: Product CRUD with store_id support
# -----------------

@app.route('/admin/products')
@admin_required(AdminLevel.STAFF)
def admin_products():
    q = request.args.get('q', '').strip()
    store_id = int(request.args.get('store_id', 1))  # Default to store 1
    status_filter = request.args.get('status', '')
    
    query = Product.query.filter_by(store_id=store_id)
    
    if q:
        like = f"%{q}%"
        query = query.filter((Product.name.like(like)) | (Product.catalog.like(like)))
    
    if status_filter:
        status_enum = ProductStatus(int(status_filter))
        query = query.filter_by(status=status_enum)
    
    products = query.order_by(Product.id.desc()).all()
    
    # Get available stores for filter
    stores = Store.query.all()
    
    return render_template('admin/products.html', products=products, q=q, stores=stores, current_store_id=store_id)

@app.route('/admin/products/new', methods=['GET', 'POST'])
@admin_required(AdminLevel.MANAGER)
def admin_product_new():
    if request.method == 'POST':
        store_id = int(request.form.get('store_id', 1))
        name = request.form.get('name', '').strip()
        catalog = request.form.get('catalog', '').strip()
        if not name or not catalog:
            flash('名稱與分類不可空白', 'warning')
            return redirect(url_for('admin_product_new'))
        p = Product(
            store_id=store_id,
            name=name,
            catalog=catalog,
            descriptions=request.form.get('descriptions',''),
            detail=request.form.get('detail',''),
            picture=request.form.get('picture',''),
            status=ProductStatus.NORMAL,
        )
        db.session.add(p)
        db.session.commit()
        flash('商品已新增', 'success')
        return redirect(url_for('admin_products'))
    
    stores = Store.query.all()
    return render_template('admin/product_form.html', product=None, stores=stores)

@app.route('/admin/products/<int:pid>/edit', methods=['GET', 'POST'])
@admin_required(AdminLevel.MANAGER)
def admin_product_edit(pid):
    p = Product.query.get(pid)
    if not p:
        flash('商品不存在', 'danger')
        return redirect(url_for('admin_products'))
    if request.method == 'POST':
        p.name = request.form.get('name', p.name)
        p.catalog = request.form.get('catalog', p.catalog)
        p.descriptions = request.form.get('descriptions', p.descriptions)
        p.detail = request.form.get('detail', p.detail)
        p.picture = request.form.get('picture', p.picture)
        db.session.commit()
        flash('商品已更新', 'success')
        return redirect(url_for('admin_products'))
    
    stores = Store.query.all()
    return render_template('admin/product_form.html', product=p, stores=stores)

@app.route('/admin/products/<int:pid>/delete', methods=['POST'])
@admin_required(AdminLevel.MANAGER)
def admin_product_delete(pid):
    p = Product.query.get(pid)
    if not p:
        flash('商品不存在', 'danger')
        return redirect(url_for('admin_products'))
    p.status = ProductStatus.HIDE
    db.session.commit()
    flash('商品已隱藏', 'info')
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

@app.route('/admin/items/<int:item_id>/edit', methods=['POST'])
@admin_required(AdminLevel.MANAGER)
def admin_item_edit(item_id):
    it = ProductItem.query.get(item_id)
    if not it:
        flash('商品細項不存在', 'danger')
        return redirect(url_for('admin_products'))
    it.name = request.form.get('name', it.name)
    it.price = int(request.form.get('price', it.price))
    it.stock = int(request.form.get('stock', it.stock))
    it.discount = request.form.get('discount', it.discount)
    db.session.commit()
    flash('細項已更新', 'success')
    return redirect(url_for('admin_product_items', pid=it.product_id))

@app.route('/admin/items/<int:item_id>/delete', methods=['POST'])
@admin_required(AdminLevel.MANAGER)
def admin_item_delete(item_id):
    it = ProductItem.query.get(item_id)
    if not it:
        flash('商品細項不存在', 'danger')
        return redirect(url_for('admin_products'))
    pid = it.product_id
    db.session.delete(it)
    db.session.commit()
    flash('細項已刪除', 'info')
    return redirect(url_for('admin_product_items', pid=pid))

# -----------------
# Admin: Coupons
# -----------------

@app.route('/admin/coupons', methods=['GET', 'POST'])
@admin_required(AdminLevel.MANAGER)
def admin_coupons():
    if request.method == 'POST':
        ctype = int(request.form.get('type'))
        discount = int(request.form.get('discount'))
        min_price = int(request.form.get('min_price'))
        remain = int(request.form.get('remain_count'))
        cp = Coupon(store_id=1, type=CouponType(ctype), discount=discount, min_price=min_price, remain_count=remain)
        db.session.add(cp)
        db.session.commit()
        flash('優惠券已建立', 'success')
        return redirect(url_for('admin_coupons'))
    coupons = Coupon.query.order_by(Coupon.id.desc()).all()
    return render_template('admin/coupons.html', coupons=coupons)

@app.route('/admin/coupons/<int:cid>/edit', methods=['POST'])
@admin_required(AdminLevel.MANAGER)
def admin_coupons_edit(cid):
    cp = Coupon.query.get(cid)
    if not cp:
        flash('優惠券不存在', 'danger')
        return redirect(url_for('admin_coupons'))
    cp.type = CouponType(int(request.form.get('type', cp.type.value)))
    cp.discount = int(request.form.get('discount', cp.discount))
    cp.min_price = int(request.form.get('min_price', cp.min_price))
    cp.remain_count = int(request.form.get('remain_count', cp.remain_count))
    db.session.commit()
    flash('優惠券已更新', 'success')
    return redirect(url_for('admin_coupons'))

@app.route('/admin/coupons/<int:cid>/delete', methods=['POST'])
@admin_required(AdminLevel.MANAGER)
def admin_coupons_delete(cid):
    cp = Coupon.query.get(cid)
    if not cp:
        flash('優惠券不存在', 'danger')
        return redirect(url_for('admin_coupons'))
    db.session.delete(cp)
    flash('優惠券已刪除', 'info')
    return redirect(url_for('admin_coupons'))

# -----------------
# Admin: RawPage management with TinyMCE
# -----------------

@app.route('/admin/raw-pages')
@admin_required(AdminLevel.MANAGER)
def admin_raw_pages():
    pages = Interrogation.query.limit(0)  # placeholder to reference models
    raw_pages = []
    from .models import RawPage
    raw_pages = RawPage.query.order_by(RawPage.created_at.desc()).all()
    return render_template('admin/raw_pages.html', pages=raw_pages)

@app.route('/admin/raw-pages/new', methods=['GET','POST'])
@admin_required(AdminLevel.MANAGER)
def admin_raw_page_new():
    from .models import RawPage
    if request.method == 'POST':
        rp = RawPage(
            store_id=1,
            type=PageType[request.form.get('type')],
            title=request.form.get('title','').strip(),
            image=request.form.get('image',''),
            content=request.form.get('content',''),
        )
        db.session.add(rp)
        db.session.commit()
        flash('頁面已建立', 'success')
        return redirect(url_for('admin_raw_pages'))
    return render_template('admin/raw_page_form.html', page=None, page_types=list(PageType))

@app.route('/admin/raw-pages/<int:rid>/edit', methods=['GET','POST'])
@admin_required(AdminLevel.MANAGER)
def admin_raw_page_edit(rid):
    from .models import RawPage
    rp = RawPage.query.get(rid)
    if not rp:
        flash('頁面不存在', 'danger')
        return redirect(url_for('admin_raw_pages'))
    if request.method == 'POST':
        rp.type = PageType[request.form.get('type')] if request.form.get('type') else rp.type
        rp.title = request.form.get('title', rp.title)
        rp.image = request.form.get('image', rp.image)
        rp.content = request.form.get('content', rp.content)
        db.session.commit()
        flash('頁面已更新', 'success')
        return redirect(url_for('admin_raw_pages'))
    return render_template('admin/raw_page_form.html', page=rp, page_types=list(PageType))

# -----------------
# Admin: Customer Service
# -----------------

@app.route('/admin/customer-service')
@admin_required(AdminLevel.STAFF)
def admin_customer_service():
    # Get chat history from chat_store (simulated for now)
    # In real implementation, this would connect to AgentBuilder's chat_store
    chats = [
        {
            'id': 1,
            'user_id': 'user123',
            'user_name': '張小明',
            'last_message': '請問商品什麼時候會到貨？',
            'status': 'unresolved',
            'created_at': '2025-08-15 10:30:00',
            'last_activity': '2025-08-15 14:20:00'
        },
        {
            'id': 2,
            'user_id': 'user456',
            'user_name': '李小華',
            'last_message': '我想退貨，該怎麼處理？',
            'status': 'resolved',
            'created_at': '2025-08-15 09:15:00',
            'last_activity': '2025-08-15 11:45:00'
        }
    ]
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
def api_create_order():
    try:
        data = request.get_json() or {}
        email = data.get('email')
        items = data.get('items', [])  # [{product_item_id, quantity}]
        coupon_code = data.get('coupon_code')  # simple string matches Coupon.id? we use id numeric or ignore code
        if not email or not items:
            return jsonify({'success': False, 'error': '缺少 email 或 items'}), 400
        # find or create user
        user = User.query.filter_by(email=email).first()
        if not user:
            user = User(account=email.split('@')[0], password=generate_password_hash('changeme'), name=email.split('@')[0], email=email, level=UserLevel.FIRST)
            db.session.add(user)
            db.session.flush()
        # compute total and validate stock
        total = 0
        order_items = []
        for it in items:
            pii = ProductItem.query.get(int(it['product_item_id']))
            qty = int(it['quantity'])
            if not pii or qty <= 0:
                return jsonify({'success': False, 'error': '無效的商品或數量'}), 400
            if pii.stock < qty:
                return jsonify({'success': False, 'error': f'庫存不足: {pii.name}'}), 400
            total += pii.price * qty
            order_items.append((pii, qty))
        # apply coupon if any (use first coupon with remain and min_price)
        discount_applied = 0
        if coupon_code:
            cp = Coupon.query.get(int(coupon_code)) if coupon_code.isdigit() else None
            if cp and cp.remain_count > 0 and total >= cp.min_price:
                if cp.type == CouponType.DISCOUNT_PERCENT:
                    discount_applied = int(total * (cp.discount/100.0))
                else:
                    discount_applied = cp.discount
                cp.remain_count -= 1
        total = max(0, total - discount_applied)
        # create order
        order = Order(store_id=1, user_id=user.id, total=total, status=OrderStatus.PENDING, remark=data.get('remark'), coupon=str(coupon_code) if coupon_code else None)
        db.session.add(order)
        db.session.flush()
        # create order items and decrement stock
        for pii, qty in order_items:
            db.session.add(OrderItem(order_id=order.id, product_item_id=pii.id, quantity=qty))
            pii.stock -= qty
        # create payment pending
        order.payment = Payment(amount=total, status=PaymentStatus.PENDING, payment_method=data.get('payment_method','credit_card'), details='')
        # log
        db.session.add(OrderLog(order_id=order.id, action='create', from_status=None, to_status=str(OrderStatus.PENDING.name), note=f'discount={discount_applied}'))
        db.session.commit()
        return jsonify({'success': True, 'order_id': order.id, 'total': total, 'discount': discount_applied})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/orders/<int:order_id>/status', methods=['PUT'])
def api_update_order_status(order_id):
    try:
        order = Order.query.get(order_id)
        if not order:
            return jsonify({'success': False, 'error': '訂單不存在'}), 404
        data = request.get_json() or {}
        to_status = OrderStatus(data['status'])
        from_status = order.status
        if from_status == OrderStatus.PENDING and to_status not in [OrderStatus.PAID, OrderStatus.REFUND]:
            return jsonify({'success': False, 'error': '非法狀態轉移'}), 400
        if from_status == OrderStatus.PAID and to_status not in [OrderStatus.SHIPPED, OrderStatus.REFUND]:
            return jsonify({'success': False, 'error': '非法狀態轉移'}), 400
        # Sync payment status
        if to_status == OrderStatus.PAID:
            if order.payment:
                order.payment.status = PaymentStatus.PAID
        if to_status == OrderStatus.REFUND:
            # restock items
            for oi in order.order_items:
                if oi.product_item:
                    oi.product_item.stock += oi.quantity
            if order.payment:
                order.payment.status = PaymentStatus.REFUNDED
        order.status = to_status
        log = OrderLog(order_id=order.id, action='status_change', from_status=str(from_status.name), to_status=str(to_status.name), note=data.get('note'))
        db.session.add(log)
        db.session.commit()
        return jsonify({'success': True})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400

# -----------------
# Existing APIs (products, users, stats) remain below
# -----------------

@app.route('/api/products', methods=['GET'])
def api_get_products():
    products = Product.query.all()
    result = []
    for product in products:
        product_data = {
            'id': product.id,
            'name': product.name,
            'category': product.catalog,
            'outline': product.descriptions,
            'picture': product.picture,
            'status': product.status.value if isinstance(product.status, ProductStatus) else str(product.status),
            'product_items': []
        }
        for item in product.product_items:
            product_data['product_items'].append({
                'id': item.id,
                'name': item.name,
                'price': item.price,
                'stock': item.stock,
                'discount': item.discount
            })
        result.append(product_data)
    return jsonify(result)

@app.route('/api/products', methods=['POST'])
def api_create_product_api():
    try:
        data = request.get_json() or {}
        catalog = data.get('category') or data.get('catalog') or '未分類'
        descriptions = data.get('outline') or data.get('descriptions') or ''

        product = Product(
            store_id=data.get('store_id', 1),
            catalog=catalog,
            name=data['name'],
            descriptions=descriptions,
            detail=data.get('detail', ''),
            picture=data.get('picture', ''),
            status=ProductStatus.NORMAL,
        )
        db.session.add(product)
        db.session.flush()
        
        for item_data in data.get('product_items', []):
            item = ProductItem(
                product_id=product.id,
                name=item_data['name'],
                price=int(item_data['price']),
                stock=int(item_data['stock']),
                discount=item_data.get('discount', '')
            )
            db.session.add(item)
        
        db.session.commit()
        return jsonify({'success': True, 'product_id': product.id}), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/products/<int:product_id>', methods=['PUT'])
def api_update_product(product_id):
    try:
        product = Product.query.get(product_id)
        if not product:
            return jsonify({'success': False, 'error': '商品不存在'}), 404
        data = request.get_json() or {}
        
        product.catalog = data.get('category', data.get('catalog', product.catalog))
        product.name = data.get('name', product.name)
        product.descriptions = data.get('outline', data.get('descriptions', product.descriptions))
        product.detail = data.get('detail', product.detail)
        product.picture = data.get('picture', product.picture)
        status_val = data.get('status', product.status.value if isinstance(product.status, ProductStatus) else product.status)
        product.status = ProductStatus(status_val) if not isinstance(status_val, ProductStatus) else status_val
        
        db.session.commit()
        return jsonify({'success': True})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/products/<int:product_id>', methods=['DELETE'])
def api_delete_product(product_id):
    try:
        product = Product.query.get(product_id)
        if not product:
            return jsonify({'success': False, 'error': '商品不存在'}), 404
        product.status = ProductStatus.HIDE
        db.session.commit()
        return jsonify({'success': True})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400

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
def api_get_stats():
    total_products = Product.query.count()
    total_orders = Order.query.count()
    total_users = User.query.count()
    
    now = datetime.now()
    start_month = datetime(now.year, now.month, 1)
    monthly_orders = Order.query.filter(
        Order.status == OrderStatus.PAID,
        Order.created_at >= start_month
    ).all()
    monthly_revenue = sum(order.total for order in monthly_orders)
    
    categories = db.session.query(Product.catalog, db.func.count(Product.id)).group_by(Product.catalog).all()
    category_stats = [{'category': cat, 'count': count} for cat, count in categories]
    
    return jsonify({
        'total_products': total_products,
        'total_orders': total_orders,
        'total_users': total_users,
        'monthly_revenue': monthly_revenue,
        'category_stats': category_stats
    })

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