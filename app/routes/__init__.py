import os
from .main import main_bp
from .auth import auth_bp
from .chat import chat_bp
from .menstrual import menstrual_bp
from .menstrual_enhanced import menstrual_enhanced_bp
from .reminders import reminder_bp

def init_app(app):
    """Initialize application with all routes"""
    # Register blueprints
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(chat_bp, url_prefix='/chat')
    app.register_blueprint(menstrual_bp, url_prefix='/menstrual')
    app.register_blueprint(menstrual_enhanced_bp, url_prefix='/menstrual-tracking')
    app.register_blueprint(reminder_bp, url_prefix='/')
    
    # Ensure upload directories exist
    os.makedirs(os.path.join(app.root_path, 'static', 'uploads', 'health_reports'), exist_ok=True)
    
    # Create indexes for collections
    with app.app_context():
        from app.extensions import mongo
        
        # Reminders collection indexes
        mongo.db.reminders.create_index([('user_id', 1)])
        mongo.db.reminders.create_index([('scheduled_date', 1)])
        mongo.db.reminders.create_index([('is_completed', 1)])
        
        # Health reports collection indexes
        mongo.db.health_reports.create_index([('user_id', 1)])
        mongo.db.health_reports.create_index([('created_at', -1)])