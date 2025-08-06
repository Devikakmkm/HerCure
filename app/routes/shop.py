from flask import Blueprint, request, jsonify, current_app, redirect, url_for, flash, render_template
from flask_login import login_required, current_user
from app.models.shop import Product, Cart, CartItem, Order
from bson import ObjectId
import stripe
from datetime import datetime
import os

shop_bp = Blueprint('shop', __name__, template_folder='templates')

# Initialize Stripe
stripe.api_key = os.getenv('STRIPE_SECRET_KEY')
stripe_public_key = os.getenv('STRIPE_PUBLIC_KEY')

@shop_bp.route('', methods=['GET'])
@shop_bp.route('/', methods=['GET'])
def shop():
    """Render the shop page"""
    # Get products for the template
    products = Product.find_all()
    if not products:
        # If no products in DB, add sample products
        for product_data in SAMPLE_PRODUCTS:
            product = Product(**product_data)
            product.save()
        products = Product.find_all()
    
    # Convert products to a list of dicts for the template
    products_data = [{
        'id': str(p._id),
        'name': p.name,
        'description': p.description,
        'price': float(p.price),
        'image_url': p.image_url,
        'category': p.category,
        'in_stock': p.in_stock
    } for p in products]
    
    return render_template('shop.html', 
                         products=products_data,
                         stripe_public_key=stripe_public_key)

# Sample products data (you can move this to a separate file or database)
SAMPLE_PRODUCTS = [
    {
        'name': 'Organic Cotton Tampons',
        'description': 'Comfortable and reliable protection, made with 100% organic cotton.',
        'price': 9.99,
        'image_url': 'https://placehold.co/600x400/4FD1C5/white?text=Hygiene',
        'category': 'hygiene',
    },
    {
        'name': 'Iron & Vitamin C Gummies',
        'description': 'Boost your energy levels with these tasty, easy-to-take supplements.',
        'price': 14.99,
        'image_url': 'https://placehold.co/600x400/F687B3/white?text=Supplement',
        'category': 'supplements',
    },
    {
        'name': 'Smart Water Bottle',
        'description': 'Tracks your water intake and glows to remind you to stay hydrated.',
        'price': 29.99,
        'image_url': 'https://placehold.co/600x400/718096/white?text=Wellness',
        'category': 'wellness',
    },
]

@shop_bp.route('/api/products', methods=['GET'])
def get_products():
    """Get all available products"""
    products = Product.find_all()
    if not products:
        # If no products in DB, add sample products
        for product_data in SAMPLE_PRODUCTS:
            product = Product(**product_data)
            product.save()
        products = Product.find_all()
    
    return jsonify([{
        'id': str(p._id),
        'name': p.name,
        'description': p.description,
        'price': p.price,
        'image_url': p.image_url,
        'category': p.category,
        'in_stock': p.in_stock
    } for p in products])

@shop_bp.route('/api/cart', methods=['GET', 'POST', 'PUT', 'DELETE'])
@login_required
def manage_cart():
    """Handle cart operations"""
    if request.method == 'GET':
        # Get user's cart
        cart = Cart.find_by_user_id(str(current_user.id))
        if not cart:
            return jsonify({'items': [], 'total': 0})
        
        # Calculate total
        total = 0
        items = []
        for item in cart.items:
            product = Product.find_by_id(str(item.product_id))
            if product:
                item_total = item.quantity * product.price
                total += item_total
                items.append({
                    'product_id': str(product._id),
                    'name': product.name,
                    'price': float(product.price),
                    'quantity': item.quantity,
                    'item_total': item_total,
                    'image_url': product.image_url
                })
        
        return jsonify({
            'items': items,
            'total': total,
            'cart_id': str(cart._id)
        })
    
    elif request.method == 'POST':
        # Add item to cart
        data = request.get_json()
        product_id = data.get('product_id')
        quantity = int(data.get('quantity', 1))
        
        if not product_id:
            return jsonify({'error': 'Product ID is required'}), 400
        
        product = Product.find_by_id(product_id)
        if not product:
            return jsonify({'error': 'Product not found'}), 404
        
        # Get or create cart
        cart = Cart.find_by_user_id(str(current_user.id))
        if not cart:
            cart = Cart(user_id=str(current_user.id), items=[])
        
        # Check if product already in cart
        item_exists = False
        for item in cart.items:
            if str(item.product_id) == product_id:
                item.quantity += quantity
                item_exists = True
                break
        
        if not item_exists:
            cart_item = CartItem(product_id=product_id, quantity=quantity)
            cart.items.append(cart_item)
        
        cart.save()
        return jsonify({'message': 'Item added to cart', 'cart_id': str(cart._id)}), 201
    
    elif request.method == 'PUT':
        # Update cart item quantity
        data = request.get_json()
        product_id = data.get('product_id')
        quantity = int(data.get('quantity', 1))
        
        if not product_id:
            return jsonify({'error': 'Product ID is required'}), 400
        
        cart = Cart.find_by_user_id(str(current_user.id))
        if not cart:
            return jsonify({'error': 'Cart not found'}), 404
        
        # Find and update item
        item_updated = False
        for item in cart.items:
            if str(item.product_id) == product_id:
                if quantity <= 0:
                    cart.items.remove(item)
                else:
                    item.quantity = quantity
                item_updated = True
                break
        
        if not item_updated:
            return jsonify({'error': 'Item not found in cart'}), 404
        
        cart.save()
        return jsonify({'message': 'Cart updated'})
    
    elif request.method == 'DELETE':
        # Clear cart
        cart = Cart.find_by_user_id(str(current_user.id))
        if cart:
            cart.is_active = False
            cart.save()
        return jsonify({'message': 'Cart cleared'})

@shop_bp.route('/api/checkout', methods=['POST'])
@login_required
def create_checkout_session():
    """Create a Stripe checkout session"""
    cart = Cart.find_by_user_id(str(current_user.id))
    if not cart or not cart.items:
        return jsonify({'error': 'Cart is empty'}), 400
    
    # Calculate total and prepare line items
    line_items = []
    for item in cart.items:
        product = Product.find_by_id(str(item.product_id))
        if product:
            line_items.append({
                'price_data': {
                    'currency': 'usd',
                    'product_data': {
                        'name': product.name,
                        'description': product.description[:200] if product.description else '',
                        'images': [product.image_url] if product.image_url else [],
                    },
                    'unit_amount': int(product.price * 100),  # Amount in cents
                },
                'quantity': item.quantity,
            })
    
    try:
        # Create Stripe Checkout session
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=line_items,
            mode='payment',
            success_url=url_for('shop.order_success', _external=True) + '?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=url_for('shop.manage_cart', _external=True),
            customer_email=current_user.email,
            metadata={
                'user_id': str(current_user.id),
                'cart_id': str(cart._id)
            }
        )
        
        return jsonify({'sessionId': checkout_session.id})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@shop_bp.route('/order/success')
@login_required
def order_success():
    """Handle successful order placement"""
    session_id = request.args.get('session_id')
    if not session_id:
        return redirect(url_for('shop.get_orders'))
    
    try:
        # Get checkout session
        checkout_session = stripe.checkout.Session.retrieve(session_id)
        
        # Verify this session belongs to the current user
        if checkout_session.metadata.get('user_id') != str(current_user.id):
            flash('Invalid order', 'error')
            return redirect(url_for('shop.get_orders'))
        
        # Get cart
        cart_id = checkout_session.metadata.get('cart_id')
        cart = Cart.find_by_user_id(str(current_user.id))
        
        if not cart or str(cart._id) != cart_id:
            flash('Cart not found', 'error')
            return redirect(url_for('shop.get_orders'))
        
        # Create order items
        order_items = []
        total_amount = 0
        
        for item in cart.items:
            product = Product.find_by_id(str(item.product_id))
            if product:
                item_total = product.price * item.quantity
                total_amount += item_total
                order_items.append({
                    'product_id': str(product._id),
                    'quantity': item.quantity,
                    'price_at_purchase': float(product.price)
                })
        
        # Create order
        order = Order(
            user_id=str(current_user.id),
            items=order_items,
            total_amount=total_amount,
            status='processing',
            payment_intent_id=checkout_session.payment_intent,
            payment_status='paid' if checkout_session.payment_status == 'paid' else 'pending',
            shipping_address=checkout_session.shipping or {}
        )
        order.save()
        
        # Deactivate cart
        cart.is_active = False
        cart.save()
        
        return redirect(url_for('shop.get_orders'))
    
    except Exception as e:
        current_app.logger.error(f'Error processing order: {str(e)}')
        flash('Error processing your order. Please contact support.', 'error')
        return redirect(url_for('shop.get_orders'))

@shop_bp.route('/api/orders', methods=['GET'])
@login_required
def get_orders():
    """Get user's order history"""
    orders = Order.find_by_user_id(str(current_user.id)).order_by('-created_at')
    
    return jsonify([{
        'id': str(order._id),
        'id': str(order.id),
        'total_amount': order.total_amount,
        'status': order.status,
        'payment_status': order.payment_status,
        'created_at': order.created_at.isoformat(),
        'items': [{
            'name': item.product_id.name,
            'quantity': item.quantity,
            'price': item.price_at_purchase,
            'image_url': item.product_id.image_url
        } for item in order.items]
    } for order in orders])
