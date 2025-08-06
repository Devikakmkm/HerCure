from flask import Blueprint, render_template, redirect, url_for, jsonify
from flask_login import login_required, current_user
from app.models.menstrual_profile import MenstrualProfile
from app.models.menstrual_cycle import MenstrualCycle

# Create a Blueprint for main routes
main_bp = Blueprint('main', __name__)

@main_bp.route('/')
@main_bp.route('/index')
def index():
    return render_template('index.html', title='Home')

@main_bp.route('/dashboard')
@login_required
def dashboard():
    user_id = current_user.id
    profile = MenstrualProfile.get_primary_profile(user_id)
    
    # Check if user has any cycle data
    has_cycle_data = MenstrualCycle.get_user_cycles(user_id, limit=1)
    
    dashboard_data = {
        'has_cycle_data': bool(has_cycle_data),
        'next_period': None,
        'fertile_window': None,
        'cycle_stats': None,
        'current_phase': None
    }
    
    # Only fetch cycle data if user has started tracking
    if has_cycle_data:
        dashboard_data.update({
            'next_period': MenstrualCycle.predict_next_period(user_id),
            'fertile_window': MenstrualCycle.get_fertile_window(user_id),
            'cycle_stats': MenstrualCycle.get_cycle_statistics(user_id),
            'current_phase': MenstrualCycle.get_current_phase(user_id)[0] if MenstrualCycle.get_current_cycle(user_id) else 'Not Tracking'
        })

    return render_template('dashboard.html', title='Dashboard', data=dashboard_data)

# Shop routes are now handled by shop_bp

@main_bp.route('/login')
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    return render_template('login.html', title='Login')

@main_bp.route('/register')
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    return render_template('register.html', title='Register')
