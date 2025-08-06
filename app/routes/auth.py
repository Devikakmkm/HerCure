from flask import Blueprint, redirect, url_for, flash, request, session
from flask_login import login_user, logout_user, current_user
from bson.objectid import ObjectId
from app.models.user import User
from app import oauth, mongo, login_manager

# Create a Blueprint for auth routes
auth_bp = Blueprint('auth', __name__)

@login_manager.user_loader
def load_user(user_id):
    user_json = mongo.db.users.find_one({'_id': ObjectId(user_id)})
    if user_json:
        return User(user_json)
    return None

@auth_bp.route('/login', methods=['POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
        
    email = request.form.get('email')
    password = request.form.get('password')
    remember = True if request.form.get('remember') else False
    
    user_json = User.find_user_by_email(email)
    user = User(user_json) if user_json else None

    if user and user.check_password(password):
        login_user(user, remember=remember)
        next_page = request.args.get('next')
        return redirect(next_page or url_for('main.dashboard'))
    
    # If we get here, login failed
    flash('Invalid email or password.', 'danger')
    return redirect(url_for('main.login'))

@auth_bp.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('main.index'))

@auth_bp.route('/register', methods=['POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
        
    name = request.form.get('name')
    email = request.form.get('email')
    password = request.form.get('password')
    
    # Check if user already exists
    if User.find_user_by_email(email):
        flash('Email address already registered', 'danger')
        return redirect(url_for('main.register'))
    
    try:
        # Create new user
        user_data = {
            'name': name,
            'email': email,
            'password': User.hash_password(password),
            'is_google_user': False
        }
        user_id = mongo.db.users.insert_one(user_data).inserted_id
        user_json = mongo.db.users.find_one({'_id': user_id})
        
        # Log the user in
        user = User(user_json)
        login_user(user)
        
        flash('Registration successful!', 'success')
        return redirect(url_for('main.dashboard'))
        
    except Exception as e:
        print(f"Error during registration: {str(e)}")
        flash('Registration failed. Please try again.', 'danger')
        return redirect(url_for('main.register'))

@auth_bp.route('/login/google')
def google_login():
    # Store the next page in the session for after login
    session['next'] = request.args.get('next', url_for('main.dashboard'))
    redirect_uri = url_for('auth.google_authorize', _external=True)
    return oauth.google.authorize_redirect(redirect_uri)

@auth_bp.route('/authorize/google')
def google_authorize():
    try:
        # Get the token and user info from Google
        token = oauth.google.authorize_access_token()
        user_info = oauth.google.get('userinfo').json()
        
        if not user_info.get('email_verified'):
            flash('Google account not verified', 'danger')
            return redirect(url_for('main.login'))
        
        email = user_info['email']
        user_json = User.find_user_by_email(email)
        
        if not user_json:
            # Create new user if they don't exist
            user_data = {
                'name': user_info.get('name', 'HerCure User'),
                'email': email,
                'picture': user_info.get('picture'),
                'google_id': user_info.get('sub'),
                'is_google_user': True
            }
            user_id = mongo.db.users.insert_one(user_data).inserted_id
            user_json = mongo.db.users.find_one({'_id': user_id})
        
        # Log the user in
        user = User(user_json)
        login_user(user)
        
        # Redirect to the originally requested page or dashboard
        next_page = session.pop('next', None) or url_for('main.dashboard')
        return redirect(next_page)
        
    except Exception as e:
        print(f"Error during Google OAuth: {str(e)}")
        return redirect(url_for('main.login'))