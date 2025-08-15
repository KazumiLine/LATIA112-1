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
    OrderStatus, PaymentStatus, UserLevel, WalletType
)

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-here')
DB_PATH = os.environ.get("APP_DB_PATH", os.path.join(os.getcwd(), "storage", "app.db"))
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', f"sqlite:///{DB_PATH}")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
CORS(app)

# Initialize database
# def init_db():
#     with app.app_context():
#         db.create_all()
        
#         # Create default store if not exists
#         if not Store.query.first():
#             default_store = Store(
#                 prefix="DEFAULT",
#                 store_name="Default Store",
#                 store_info="Welcome to our store!",
#                 email="admin@example.com",
#                 address="123 Main St, City",
#                 phone="+886-2-1234-5678",
#                 business_hours="9:00-18:00",
#                 marquee=["Welcome!", "New products available!"]
#             )
#             db.session.add(default_store)
#             db.session.commit()
            
#             # Create default admin user
#             admin_user = User(
#                 account="admin",
#                 password=generate_password_hash("admin123"),
#                 name="Administrator",
#                 email="admin@example.com",
#                 level=UserLevel.THIRD
#             )
#             db.session.add(admin_user)
#             db.session.commit()
            
#             # Create admin role
#             admin_role = Admin(
#                 store_id=default_store.id,
#                 user_id=admin_user.id,
#                 level=AdminLevel.OWNER
#             )
#             db.session.add(admin_role)
#             db.session.commit()

# Routes
@app.route('/')
def index():
    """Main page with product catalog"""
    products = Product.query.filter_by(status=ProductStatus.NORMAL).all()
    return render_template('index.html', products=products)

@app.route('/admin')
def admin_dashboard():
    """Admin dashboard"""
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
    """Product management page"""
    products = Product.query.all()
    return render_template('admin/products.html', products=products)

@app.route('/admin/orders')
def admin_orders():
    """Order management page"""
    orders = Order.query.order_by(Order.created_at.desc()).all()
    return render_template('admin/orders.html', orders=orders)

@app.route('/admin/users')
def admin_users():
    """User management page"""
    users = User.query.all()
    return render_template('admin/users.html', users=users)

# API Routes
@app.route('/api/products', methods=['GET'])
def api_get_products():
    """Get all products"""
    products = Product.query.all()
    result = []
    for product in products:
        product_data = {
            'id': product.id,
            'name': product.name,
            'category': product.category,
            'outline': product.outline,
            'picture': product.picture,
            'status': product.status.value,
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
    """Create a new product"""
    try:
        data = request.get_json()
        
        # Create product
        product = Product(
            store_id=data.get('store_id', 1),
            category=data['category'],
            name=data['name'],
            outline=data.get('outline', ''),
            detail=data.get('detail', ''),
            picture=data.get('picture', ''),
            status=ProductStatus.NORMAL
        )
        db.session.add(product)
        db.session.flush()
        
        # Create product items
        for item_data in data.get('product_items', []):
            item = ProductItem(
                product_id=product.id,
                name=item_data['name'],
                price=item_data['price'],
                stock=item_data['stock'],
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
    """Update a product"""
    try:
        product = Product.query.get_or_404(product_id)
        data = request.get_json()
        
        product.category = data.get('category', product.category)
        product.name = data.get('name', product.name)
        product.outline = data.get('outline', product.outline)
        product.detail = data.get('detail', product.detail)
        product.picture = data.get('picture', product.picture)
        product.status = ProductStatus(data.get('status', product.status.value))
        
        db.session.commit()
        return jsonify({'success': True})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/products/<int:product_id>', methods=['DELETE'])
def api_delete_product(product_id):
    """Delete a product"""
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
    """Get all orders"""
    orders = Order.query.order_by(Order.created_at.desc()).all()
    result = []
    for order in orders:
        order_data = {
            'id': order.id,
            'user_email': order.user.email,
            'total': order.total,
            'status': order.status.value,
            'created_at': order.created_at.isoformat(),
            'order_items': []
        }
        for item in order.order_items:
            order_data['order_items'].append({
                'product_name': item.product_item.name,
                'count': item.count,
                'price': item.product_item.price
            })
        result.append(order_data)
    return jsonify(result)

@app.route('/api/orders/<int:order_id>/status', methods=['PUT'])
def api_update_order_status(order_id):
    """Update order status"""
    try:
        order = Order.query.get_or_404(order_id)
        data = request.get_json()
        order.status = OrderStatus(data['status'])
        db.session.commit()
        return jsonify({'success': True})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/users', methods=['GET'])
def api_get_users():
    """Get all users"""
    users = User.query.all()
    result = []
    for user in users:
        user_data = {
            'id': user.id,
            'account': user.account,
            'name': user.name,
            'email': user.email,
            'phone': user.phone,
            'level': user.level.value,
            'wallet': user.wallet,
            'award': user.award,
            'created_at': user.created_at.isoformat()
        }
        result.append(user_data)
    return jsonify(result)

@app.route('/api/stats')
def api_get_stats():
    """Get dashboard statistics"""
    total_products = Product.query.count()
    total_orders = Order.query.count()
    total_users = User.query.count()
    
    # Monthly revenue
    current_month = datetime.now().month
    monthly_orders = Order.query.filter(
        Order.status == OrderStatus.PAID,
        Order.created_at >= datetime(datetime.now().year, current_month, 1)
    ).all()
    monthly_revenue = sum(order.total for order in monthly_orders)
    
    # Product categories
    categories = db.session.query(Product.category, db.func.count(Product.id)).group_by(Product.category).all()
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
    # init_db()
    app.run(debug=True, host='localhost', port=8833)