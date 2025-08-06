from flask_pymongo import PyMongo
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from flask_jwt_extended import JWTManager
from authlib.integrations.flask_client import OAuth
from pymongo import MongoClient
from bson.objectid import ObjectId

# Initialize extensions
class MongoDB:
    _instance = None
    
    def __new__(cls, app=None):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            if app is not None:
                cls._instance.init_app(app)
        return cls._instance
    
    def init_app(self, app):
        self.client = MongoClient(app.config['MONGO_URI'])
        self.db = self.client.get_database()
        
        # Ensure all collections exist
        required_collections = [
            'health_reports',
            'products',
            'carts',
            'orders',
            'users'
        ]
        
        existing_collections = self.db.list_collection_names()
        
        # Create collections if they don't exist
        for collection in required_collections:
            if collection not in existing_collections:
                self.db.create_collection(collection)
        
        # Create indexes
        # Health reports
        self.db.health_reports.create_index([('user_id', 1)])
        self.db.health_reports.create_index([('upload_date', -1)])
        
        # Products
        self.db.products.create_index([('name', 'text'), ('description', 'text')])
        self.db.products.create_index([('category', 1)])
        self.db.products.create_index([('price', 1)])
        self.db.products.create_index([('in_stock', 1)])
        
        # Carts
        self.db.carts.create_index([('user_id', 1)], unique=True)
        self.db.carts.create_index([('updated_at', -1)])
        
        # Orders
        self.db.orders.create_index([('user_id', 1)])
        self.db.orders.create_index([('status', 1)])
        self.db.orders.create_index([('created_at', -1)])
        self.db.orders.create_index([('payment_status', 1)])
        
        # Users (if not already indexed by auth system)
        if 'users' in self.db.list_collection_names():
            self.db.users.create_index([('email', 1)], unique=True)
    
    def get_collection(self, name):
        return self.db[name]

# Initialize extensions
mongo = PyMongo()
mongodb = MongoDB()  # Our custom MongoDB wrapper
bcrypt = Bcrypt()
login_manager = LoginManager()
jwt = JWTManager()
oauth = OAuth()

# Setup login manager
login_manager.login_view = 'auth.login'
login_manager.login_message_category = 'info'

def init_extensions(app):
    """Initialize all extensions with the Flask app"""
    # Initialize MongoDB extensions
    mongo.init_app(app)
    mongodb.init_app(app)
    
    # Make mongo available on app context
    app.mongo = mongodb
    
    # Initialize other extensions
    bcrypt.init_app(app)
    login_manager.init_app(app)
    jwt.init_app(app)
    oauth.init_app(app)
