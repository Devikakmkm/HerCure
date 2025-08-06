from flask import current_app
from bson import ObjectId
from datetime import datetime
from typing import List, Dict, Any, Optional

class Product:
    def __init__(self, **kwargs):
        self._id = kwargs.get('_id', ObjectId())
        self.name = kwargs.get('name', '')
        self.description = kwargs.get('description', '')
        self.price = float(kwargs.get('price', 0.0))
        self.image_url = kwargs.get('image_url', '')
        self.category = kwargs.get('category', 'general')
        self.in_stock = kwargs.get('in_stock', True)
        self.stock_quantity = int(kwargs.get('stock_quantity', 100))  # Default stock
        self.sku = kwargs.get('sku', f"PROD-{ObjectId()}")
        self.tags = kwargs.get('tags', [])
        self.created_at = kwargs.get('created_at', datetime.utcnow())
        self.updated_at = kwargs.get('updated_at', datetime.utcnow())

    def to_dict(self):
        """Convert product to dictionary for MongoDB"""
        data = self.__dict__.copy()
        data['_id'] = str(data['_id'])  # Convert ObjectId to string for JSON serialization
        return data

    @classmethod
    def from_dict(cls, data: dict) -> 'Product':
        """Create Product instance from dictionary"""
        if '_id' in data and not isinstance(data['_id'], ObjectId):
            data['_id'] = ObjectId(data['_id'])
        return cls(**data)

    def save(self) -> ObjectId:
        """Save the product to MongoDB"""
        db = current_app.mongo.db
        self.updated_at = datetime.utcnow()
        
        product_data = self.__dict__.copy()
        product_id = product_data.pop('_id', None)
        
        if product_id:
            # Update existing product
            result = db.products.update_one(
                {'_id': product_id},
                {'$set': product_data},
                upsert=True
            )
            return product_id
        else:
            # Insert new product
            result = db.products.insert_one(product_data)
            self._id = result.inserted_id
            return self._id

    @classmethod
    def find_by_id(cls, product_id: str) -> Optional['Product']:
        """Find a product by ID"""
        try:
            db = current_app.mongo.db
            if not isinstance(product_id, ObjectId):
                product_id = ObjectId(product_id)
            product_data = db.products.find_one({'_id': product_id})
            return cls.from_dict(product_data) if product_data else None
        except:
            return None

    @classmethod
    def find_all(cls, query: Optional[Dict] = None, page: int = 1, per_page: int = 20) -> List['Product']:
        """Find all products with optional pagination"""
        db = current_app.mongo.db
        query = query or {}
        skip = (page - 1) * per_page
        
        cursor = db.products.find(query).skip(skip).limit(per_page)
        return [cls.from_dict(p) for p in cursor]

    @classmethod
    def search(cls, search_term: str) -> List['Product']:
        """Search products by name or description"""
        db = current_app.mongo.db
        cursor = db.products.find({
            '$text': {'$search': search_term}
        }, {
            'score': {'$meta': 'textScore'}
        }).sort([('score', {'$meta': 'textScore'})])
        
        return [cls.from_dict(p) for p in cursor]

    @classmethod
    def get_categories(cls) -> List[str]:
        """Get all unique product categories"""
        db = current_app.mongo.db
        return db.products.distinct('category')

    def update_stock(self, quantity: int) -> bool:
        """Update product stock quantity"""
        if not isinstance(quantity, int) or quantity < 0:
            return False
            
        self.stock_quantity = quantity
        self.in_stock = quantity > 0
        self.save()
        return True

class CartItem:
    def __init__(self, **kwargs):
        self.product_id = kwargs.get('product_id')
        self.quantity = int(kwargs.get('quantity', 1))
        self.added_at = kwargs.get('added_at', datetime.utcnow())
        
    def to_dict(self):
        """Convert cart item to dictionary for MongoDB"""
        return {
            'product_id': str(self.product_id) if hasattr(self.product_id, 'hex') else self.product_id,
            'quantity': self.quantity,
            'added_at': self.added_at
        }
        
    @classmethod
    def from_dict(cls, data: dict) -> 'CartItem':
        """Create CartItem from dictionary"""
        return cls(**data)

class Cart:
    def __init__(self, **kwargs):
        self._id = kwargs.get('_id', ObjectId())
        self.user_id = kwargs.get('user_id')
        self.items = [CartItem.from_dict(item) if isinstance(item, dict) else item 
                     for item in kwargs.get('items', [])]
        self.created_at = kwargs.get('created_at', datetime.utcnow())
        self.updated_at = kwargs.get('updated_at', datetime.utcnow())
        self.is_active = kwargs.get('is_active', True)
        self.coupon_code = kwargs.get('coupon_code')
        self.discount_amount = float(kwargs.get('discount_amount', 0.0))
        self.shipping_address = kwargs.get('shipping_address', {})
        self.billing_address = kwargs.get('billing_address', {})

    def to_dict(self) -> dict:
        """Convert cart to dictionary for MongoDB"""
        return {
            '_id': self._id,
            'user_id': self.user_id,
            'items': [item.to_dict() for item in self.items],
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'is_active': self.is_active,
            'coupon_code': self.coupon_code,
            'discount_amount': self.discount_amount,
            'shipping_address': self.shipping_address,
            'billing_address': self.billing_address
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Cart':
        """Create Cart from dictionary"""
        if '_id' in data and not isinstance(data['_id'], ObjectId):
            data['_id'] = ObjectId(data['_id'])
        return cls(**data)

    def save(self) -> ObjectId:
        """Save cart to MongoDB"""
        db = current_app.mongo.db
        self.updated_at = datetime.utcnow()
        
        cart_data = self.to_dict()
        cart_id = cart_data.pop('_id', None)
        
        if cart_id:
            # Update existing cart
            result = db.carts.update_one(
                {'_id': cart_id},
                {'$set': cart_data},
                upsert=True
            )
            return cart_id
        else:
            # Insert new cart
            result = db.carts.insert_one(cart_data)
            self._id = result.inserted_id
            return self._id

    def calculate_total(self) -> float:
        """Calculate the total price of all items in the cart"""
        total = 0.0
        for item in self.items:
            product = Product.find_by_id(item.product_id)
            if product:
                total += product.price * item.quantity
        return total - self.discount_amount

    def add_item(self, product_id: str, quantity: int = 1) -> bool:
        """Add an item to the cart"""
        # Check if product exists
        if not Product.find_by_id(product_id):
            return False
            
        # Check if item already in cart
        for item in self.items:
            if str(item.product_id) == str(product_id):
                item.quantity += quantity
                self.save()
                return True
                
        # Add new item
        self.items.append(CartItem(
            product_id=product_id,
            quantity=quantity
        ))
        self.save()
        return True

    def remove_item(self, product_id: str) -> bool:
        """Remove an item from the cart"""
        initial_count = len(self.items)
        self.items = [item for item in self.items if str(item.product_id) != str(product_id)]
        if len(self.items) < initial_count:
            self.save()
            return True
        return False

    def update_quantity(self, product_id: str, quantity: int) -> bool:
        """Update the quantity of an item in the cart"""
        if quantity <= 0:
            return self.remove_item(product_id)
            
        for item in self.items:
            if str(item.product_id) == str(product_id):
                item.quantity = quantity
                self.save()
                return True
        return False

    def clear(self) -> None:
        """Clear all items from the cart"""
        self.items = []
        self.discount_amount = 0.0
        self.coupon_code = None
        self.save()

    def item_count(self) -> int:
        """Get the total number of items in the cart"""
        return sum(item.quantity for item in self.items)

    @classmethod
    def find_by_user_id(cls, user_id: str) -> Optional['Cart']:
        """Find a user's active cart"""
        try:
            db = current_app.mongo.db
            cart_data = db.carts.find_one({
                'user_id': str(user_id),
                'is_active': True
            })
            
            if cart_data:
                return cls.from_dict(cart_data)
                
            # Create new cart if none exists
            cart = cls(user_id=user_id)
            cart.save()
            return cart
            
        except Exception as e:
            current_app.logger.error(f"Error finding cart for user {user_id}: {str(e)}")
            return None

class OrderItem:
    def __init__(self, **kwargs):
        self.product_id = kwargs.get('product_id')
        self.quantity = int(kwargs.get('quantity', 1))
        self.price_at_purchase = float(kwargs.get('price_at_purchase', 0.0))
        self.product_name = kwargs.get('product_name', '')
        self.product_image = kwargs.get('product_image', '')
        self.sku = kwargs.get('sku', '')
        
    def to_dict(self) -> dict:
        """Convert order item to dictionary for MongoDB"""
        return {
            'product_id': str(self.product_id) if hasattr(self.product_id, 'hex') else self.product_id,
            'quantity': self.quantity,
            'price_at_purchase': self.price_at_purchase,
            'product_name': self.product_name,
            'product_image': self.product_image,
            'sku': self.sku,
            'subtotal': self.price_at_purchase * self.quantity
        }
        
    @classmethod
    def from_dict(cls, data: dict) -> 'OrderItem':
        """Create OrderItem from dictionary"""
        return cls(**data)
        
    @property
    def subtotal(self) -> float:
        """Calculate the subtotal for this order item"""
        return self.price_at_purchase * self.quantity

class Order:
    # Order statuses
    STATUS_PENDING = 'pending'
    STATUS_PROCESSING = 'processing'
    STATUS_SHIPPED = 'shipped'
    STATUS_DELIVERED = 'delivered'
    STATUS_CANCELLED = 'cancelled'
    STATUS_REFUNDED = 'refunded'
    
    # Payment statuses
    PAYMENT_PENDING = 'pending'
    PAYMENT_PAID = 'paid'
    PAYMENT_FAILED = 'failed'
    PAYMENT_REFUNDED = 'refunded'
    
    def __init__(self, **kwargs):
        self._id = kwargs.get('_id', ObjectId())
        self.user_id = kwargs.get('user_id')
        self.order_number = kwargs.get('order_number', f"ORD-{datetime.utcnow().strftime('%Y%m%d')}-{ObjectId().hex[:6].upper()}")
        self.items = [OrderItem.from_dict(item) if isinstance(item, dict) else item 
                     for item in kwargs.get('items', [])]
        self.subtotal = float(kwargs.get('subtotal', 0.0))
        self.shipping_cost = float(kwargs.get('shipping_cost', 0.0))
        self.tax_amount = float(kwargs.get('tax_amount', 0.0))
        self.discount_amount = float(kwargs.get('discount_amount', 0.0))
        self.total_amount = float(kwargs.get('total_amount', 0.0))
        self.status = kwargs.get('status', self.STATUS_PENDING)
        self.payment_status = kwargs.get('payment_status', self.PAYMENT_PENDING)
        self.payment_method = kwargs.get('payment_method', '')
        self.payment_intent_id = kwargs.get('payment_intent_id', '')
        self.shipping_address = kwargs.get('shipping_address', {})
        self.billing_address = kwargs.get('billing_address', {})
        self.customer_notes = kwargs.get('customer_notes', '')
        self.tracking_number = kwargs.get('tracking_number', '')
        self.coupon_code = kwargs.get('coupon_code')
        self.created_at = kwargs.get('created_at', datetime.utcnow())
        self.updated_at = kwargs.get('updated_at', datetime.utcnow())
        self.completed_at = kwargs.get('completed_at')
        self.cancelled_at = kwargs.get('cancelled_at')
    
    def to_dict(self) -> dict:
        """Convert order to dictionary for MongoDB"""
        return {
            '_id': self._id,
            'user_id': self.user_id,
            'order_number': self.order_number,
            'items': [item.to_dict() for item in self.items],
            'subtotal': self.subtotal,
            'shipping_cost': self.shipping_cost,
            'tax_amount': self.tax_amount,
            'discount_amount': self.discount_amount,
            'total_amount': self.total_amount,
            'status': self.status,
            'payment_status': self.payment_status,
            'payment_method': self.payment_method,
            'payment_intent_id': self.payment_intent_id,
            'shipping_address': self.shipping_address,
            'billing_address': self.billing_address,
            'customer_notes': self.customer_notes,
            'tracking_number': self.tracking_number,
            'coupon_code': self.coupon_code,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'completed_at': self.completed_at,
            'cancelled_at': self.cancelled_at
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Order':
        """Create Order from dictionary"""
        if '_id' in data and not isinstance(data['_id'], ObjectId):
            data['_id'] = ObjectId(data['_id'])
        return cls(**data)
    
    def calculate_totals(self) -> None:
        """Calculate order totals based on items and adjustments"""
        self.subtotal = sum(item.subtotal for item in self.items)
        self.total_amount = self.subtotal + self.shipping_cost + self.tax_amount - self.discount_amount
    
    def save(self) -> ObjectId:
        """Save order to MongoDB"""
        db = current_app.mongo.db
        self.updated_at = datetime.utcnow()
        
        # Ensure totals are up to date
        self.calculate_totals()
        
        order_data = self.to_dict()
        order_id = order_data.pop('_id', None)
        
        if order_id:
            # Update existing order
            result = db.orders.update_one(
                {'_id': order_id},
                {'$set': order_data},
                upsert=True
            )
            return order_id
        else:
            # Insert new order
            result = db.orders.insert_one(order_data)
            self._id = result.inserted_id
            return self._id
    
    def update_status(self, new_status: str) -> bool:
        """Update order status with validation"""
        valid_statuses = [self.STATUS_PENDING, self.STATUS_PROCESSING, 
                         self.STATUS_SHIPPED, self.STATUS_DELIVERED, 
                         self.STATUS_CANCELLED, self.STATUS_REFUNDED]
        
        if new_status not in valid_statuses:
            return False
            
        self.status = new_status
        self.updated_at = datetime.utcnow()
        
        # Handle status-specific logic
        if new_status == self.STATUS_DELIVERED and not self.completed_at:
            self.completed_at = datetime.utcnow()
        elif new_status == self.STATUS_CANCELLED and not self.cancelled_at:
            self.cancelled_at = datetime.utcnow()
            
        self.save()
        return True
    
    def update_payment_status(self, new_status: str, payment_intent_id: str = '') -> bool:
        """Update payment status with validation"""
        valid_statuses = [self.PAYMENT_PENDING, self.PAYMENT_PAID, 
                         self.PAYMENT_FAILED, self.PAYMENT_REFUNDED]
        
        if new_status not in valid_statuses:
            return False
            
        self.payment_status = new_status
        if payment_intent_id:
            self.payment_intent_id = payment_intent_id
            
        self.updated_at = datetime.utcnow()
        self.save()
        return True
    
    def add_note(self, note: str, is_customer_note: bool = False) -> None:
        """Add a note to the order"""
        if not note:
            return
            
        if is_customer_note:
            self.customer_notes = f"{self.customer_notes}\n{note}"
        else:
            # Add internal note
            if not hasattr(self, 'internal_notes'):
                self.internal_notes = []
            self.internal_notes.append({
                'note': note,
                'created_at': datetime.utcnow()
            })
        
        self.save()
    
    @classmethod
    def find_by_id(cls, order_id: str) -> Optional['Order']:
        """Find an order by ID"""
        try:
            db = current_app.mongo.db
            if not isinstance(order_id, ObjectId):
                order_id = ObjectId(order_id)
            order_data = db.orders.find_one({'_id': order_id})
            return cls.from_dict(order_data) if order_data else None
        except:
            return None
    
    @classmethod
    def find_by_order_number(cls, order_number: str) -> Optional['Order']:
        """Find an order by order number"""
        try:
            db = current_app.mongo.db
            order_data = db.orders.find_one({'order_number': order_number})
            return cls.from_dict(order_data) if order_data else None
        except:
            return None
    
    @classmethod
    def find_by_user_id(cls, user_id: str, page: int = 1, per_page: int = 10) -> dict:
        """Find all orders for a user with pagination"""
        try:
            db = current_app.mongo.db
            skip = (page - 1) * per_page
            
            # Get total count for pagination
            total = db.orders.count_documents({'user_id': str(user_id)})
            
            # Get paginated results
            cursor = db.orders.find({'user_id': str(user_id)}) \
                            .sort('created_at', -1) \
                            .skip(skip) \
                            .limit(per_page)
            
            orders = [cls.from_dict(order_data) for order_data in cursor]
            
            return {
                'items': orders,
                'total': total,
                'page': page,
                'per_page': per_page,
                'pages': (total + per_page - 1) // per_page
            }
        except Exception as e:
            current_app.logger.error(f"Error finding orders for user {user_id}: {str(e)}")
            return {'items': [], 'total': 0, 'page': page, 'per_page': per_page, 'pages': 0}
    
    @classmethod
    def create_from_cart(cls, cart: 'Cart', user_id: str, **kwargs) -> 'Order':
        """Create a new order from a shopping cart"""
        # Create order items from cart items
        order_items = []
        for item in cart.items:
            product = Product.find_by_id(item.product_id)
            if product:
                order_items.append(OrderItem(
                    product_id=item.product_id,
                    quantity=item.quantity,
                    price_at_purchase=product.price,
                    product_name=product.name,
                    product_image=product.image_url,
                    sku=product.sku
                ))
        
        # Calculate order totals
        subtotal = sum(item.subtotal for item in order_items)
        shipping_cost = 0.0  # This would be calculated based on shipping method
        tax_amount = 0.0     # This would be calculated based on location
        
        # Create the order
        order = cls(
            user_id=user_id,
            items=order_items,
            subtotal=subtotal,
            shipping_cost=shipping_cost,
            tax_amount=tax_amount,
            discount_amount=cart.discount_amount,
            shipping_address=cart.shipping_address,
            billing_address=cart.billing_address,
            coupon_code=cart.coupon_code,
            **kwargs
        )
        
        # Calculate final total
        order.calculate_totals()
        
        return order
