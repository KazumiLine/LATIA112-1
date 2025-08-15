from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date
import json
import os
from typing import List, Dict, Any

# Import models
from .models import (
    Base, Store, User, Product, ProductItem, Order, OrderItem, 
    Delivery, Payment, Coupon, Admin, RealName, WalletRecord, Interrogation,
    PageType, AdminLevel, CouponType, DeliveryStatus, ProductStatus, 
    OrderStatus, PaymentStatus, UserLevel, WalletType,
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

# Routes
@app.route('/')
def index():
    products = Product.query.filter_by(status=ProductStatus.NORMAL).all()
    return render_template('index.html', products=products)

@app.route('/admin')
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

@app.route('/admin/products')
def admin_products():
    products = Product.query.all()
    return render_template('admin/products.html', products=products)

@app.route('/admin/orders')
def admin_orders():
    orders = Order.query.order_by(Order.created_at.desc()).all()
    return render_template('admin/orders.html', orders=orders)

@app.route('/admin/users')
def admin_users():
    users = User.query.all()
    return render_template('admin/users.html', users=users)

# API Routes
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
def api_create_product():
    try:
        data = request.get_json() or {}
        # Accept both new and legacy field names
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

@app.route('/api/orders/<int:order_id>/status', methods=['PUT'])
def api_update_order_status(order_id):
    try:
        order = Order.query.get_or_404(order_id)
        data = request.get_json() or {}
        order.status = OrderStatus(data['status'])
        db.session.commit()
        return jsonify({'success': True})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400

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
    
    # Monthly revenue
    now = datetime.now()
    start_month = datetime(now.year, now.month, 1)
    monthly_orders = Order.query.filter(
        Order.status == OrderStatus.PAID,
        Order.created_at >= start_month
    ).all()
    monthly_revenue = sum(order.total for order in monthly_orders)
    
    # Product categories
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