import os
import logging
from logging.handlers import RotatingFileHandler
from flask import Flask, current_app, request
from flask_wtf.csrf import CSRFProtect, generate_csrf
from dotenv import load_dotenv
from datetime import datetime, timedelta
import os
import sys

# Import extensions
from .extensions import mongo, mongodb, bcrypt, login_manager, jwt, oauth

# Load environment variables
load_dotenv()

def create_app(config_name='default'):
    """Application factory function"""
    app = Flask(__name__)

    # Make datetime available in all templates
    @app.context_processor
    def inject_datetime():
        return {'datetime': datetime}
    
    # Load configuration
    app.config['MONGO_URI'] = os.getenv('MONGO_URI', 'mongodb://localhost:27017/hercure')
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-key-please-change-in-production')
    app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'jwt-secret-key-change-in-production')
    app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=1)
    
    # AI Services Configuration
    app.config['GROQ_API_KEY'] = os.getenv('GROQ_API_KEY')
    
    # File upload configuration
    app.config['UPLOAD_FOLDER'] = os.path.join('app', 'static', 'uploads')
    app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 10MB max file size
    
    # Ensure upload directories exist
    os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'health_reports'), exist_ok=True)
    os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'profile_pictures'), exist_ok=True)
    
    # Configure logging
    if not app.debug and not app.testing:
        # Create logs directory if it doesn't exist
        if not os.path.exists('logs'):
            os.mkdir('logs')
            
        # File handler for errors
        file_handler = RotatingFileHandler('logs/hercure.log', maxBytes=10240, backupCount=10)
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'))
        file_handler.setLevel(logging.INFO)
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s'))
        console_handler.setLevel(logging.DEBUG)
        
        # Add handlers to the app
        app.logger.addHandler(file_handler)
        app.logger.addHandler(console_handler)
        app.logger.setLevel(logging.INFO)
        app.logger.info('Hercure startup')
    
    # Initialize all extensions with the app
    from .extensions import init_extensions
    init_extensions(app)
    
    # Initialize CSRF protection
    csrf = CSRFProtect(app)
    
    # Make mongo available on current_app for model access
    with app.app_context():
        current_app.mongo = mongodb
    
    # Make CSRF token available in all templates
    @app.context_processor
    def inject_csrf_token():
        return dict(csrf_token=generate_csrf)
    
    # Context processors
    @app.context_processor
    def inject_datetime():
        import datetime
        return {'datetime': datetime}
    
    # Initialize OAuth
    # oauth.init_app(app)
    oauth.init_app(app)
    
    # Configure Google OAuth
    oauth.register(
        name='google',
        client_id=os.getenv('GOOGLE_CLIENT_ID'),
        client_secret=os.getenv('GOOGLE_CLIENT_SECRET'),
        client_kwargs={
            'scope': 'openid email profile',
            'prompt': 'select_account',
            'access_type': 'offline'
        },
        server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
        api_base_url='https://www.googleapis.com/oauth2/v3/',
        userinfo_endpoint='https://openidconnect.googleapis.com/v1/userinfo',
        authorize_params={
            'access_type': 'offline',
            'prompt': 'consent'
        }
    )
    
    # Configure API keys
    app.config['GOOGLE_MAPS_API_KEY'] = os.environ.get('GOOGLE_MAPS_API_KEY')
    app.config['STRIPE_PUBLIC_KEY'] = os.environ.get('STRIPE_PUBLIC_KEY')
    app.config['STRIPE_SECRET_KEY'] = os.environ.get('STRIPE_SECRET_KEY')
    
    # Initialize models and create indexes
    from app.models import init_models
    with app.app_context():
        init_models()
    
    # Register blueprints with their correct names
    from .routes.auth import auth_bp
    from .routes.main import main_bp
    from .routes.menstrual import menstrual_bp
    from .routes.menstrual_enhanced import menstrual_enhanced_bp
    from .routes.reminders import reminder_bp
    from .routes.nearby import nearby_bp
    from .routes.shop import shop_bp
    
    # Register all blueprints
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(menstrual_bp)
    app.register_blueprint(menstrual_enhanced_bp)  # This is the main menstrual enhanced blueprint
    app.register_blueprint(reminder_bp, url_prefix='/api/reminders')
    app.register_blueprint(nearby_bp, url_prefix='/nearby')
    app.register_blueprint(shop_bp, url_prefix='/shop')
    
    # Add template global
    @app.context_processor
    def inject_config():
        return dict(
            GOOGLE_MAPS_API_KEY=app.config['GOOGLE_MAPS_API_KEY'],
            stripe_public_key=app.config['STRIPE_PUBLIC_KEY']
        )
    
    return app
