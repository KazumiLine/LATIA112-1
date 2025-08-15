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
            flash('請先登入', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return wrapper

def admin_required(level: AdminLevel = AdminLevel.STAFF):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if 'user_id' not in session:
                flash('請先登入', 'warning')
                return redirect(url_for('login'))
            user = User.query.get(session['user_id'])
            if not user:
                session.clear()
                return redirect(url_for('login'))
            if user.level.value < level.value:
                flash('權限不足', 'danger')
                return redirect(url_for('admin_dashboard'))
            return f(*args, **kwargs)
        return wrapper
    return decorator

# -----------------
# Auth routes
# -----------------

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        account = request.form.get('account')
        password = request.form.get('password')
        user = User.query.filter_by(account=account).first()
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            flash('登入成功', 'success')
            return redirect(url_for('admin_dashboard'))
        flash('帳號或密碼錯誤', 'danger')
    return render_template('auth/login.html')

@app.route('/logout')
@login_required
def logout():
    session.clear()
    flash('已登出', 'info')
    return redirect(url_for('login'))

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
# Pages
# -----------------

@app.route('/')
def index():
    products = Product.query.filter_by(status=ProductStatus.NORMAL).all()
    return render_template('index.html', products=products)

@app.route('/admin')
@login_required
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

# -----------------
# Admin: Product CRUD
# -----------------

@app.route('/admin/products')
@admin_required(AdminLevel.STAFF)
def admin_products():
    products = Product.query.all()
    return render_template('admin/products.html', products=products)

@app.route('/admin/products/new', methods=['GET', 'POST'])
@admin_required(AdminLevel.MANAGER)
def admin_product_new():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        catalog = request.form.get('catalog', '').strip()
        if not name or not catalog:
            flash('名稱與分類不可空白', 'warning')
            return redirect(url_for('admin_product_new'))
        p = Product(
            store_id=1,
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
    return render_template('admin/product_form.html', product=None)

@app.route('/admin/products/<int:pid>/edit', methods=['GET', 'POST'])
@admin_required(AdminLevel.MANAGER)
def admin_product_edit(pid):
    p = Product.query.get_or_404(pid)
    if request.method == 'POST':
        p.name = request.form.get('name', p.name)
        p.catalog = request.form.get('catalog', p.catalog)
        p.descriptions = request.form.get('descriptions', p.descriptions)
        p.detail = request.form.get('detail', p.detail)
        p.picture = request.form.get('picture', p.picture)
        db.session.commit()
        flash('商品已更新', 'success')
        return redirect(url_for('admin_products'))
    return render_template('admin/product_form.html', product=p)

@app.route('/admin/products/<int:pid>/delete', methods=['POST'])
@admin_required(AdminLevel.MANAGER)
def admin_product_delete(pid):
    p = Product.query.get_or_404(pid)
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
    p = Product.query.get_or_404(pid)
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
    it = ProductItem.query.get_or_404(item_id)
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
    it = ProductItem.query.get_or_404(item_id)
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
    cp = Coupon.query.get_or_404(cid)
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
    cp = Coupon.query.get_or_404(cid)
    db.session.delete(cp)
    db.session.commit()
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
    rp = RawPage.query.get_or_404(rid)
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
        order = Order.query.get_or_404(order_id)
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
        product = Product.query.get_or_404(product_id)
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
        product = Product.query.get_or_404(product_id)
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