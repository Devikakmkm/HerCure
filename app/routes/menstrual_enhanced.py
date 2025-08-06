from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for, current_app, send_file, session
from flask_login import login_required, current_user
from datetime import datetime, date, timedelta
import os
from bson.objectid import ObjectId

from app.models.menstrual_cycle import MenstrualCycle, CycleSymptom
from app.models.menstrual_reminder import MenstrualReminder

from app.models.menstrual_profile import MenstrualProfile, VoiceLog, DataExport
from app.models.community import Post, Comment
from datetime import date

# Enhanced menstrual tracking blueprint
menstrual_enhanced_bp = Blueprint('menstrual_enhanced', __name__)

@menstrual_enhanced_bp.route('/')
@menstrual_enhanced_bp.route('/dashboard')
@login_required
def dashboard():
    """Enhanced menstrual tracking dashboard with AI/ML analytics and real-time stats"""
    cycles = MenstrualCycle.get_user_cycles(current_user.id)
    current_cycle = MenstrualCycle.get_current_cycle(current_user.id)
    now = datetime.utcnow()
    # Current cycle day
    if current_cycle and current_cycle.get('start_date'):
        current_cycle_day = (now.date() - current_cycle['start_date'].date()).days + 1
    else:
        current_cycle_day = None
    # Next period prediction (Random Forest)
    rf_pred = MenstrualCycle.predict_next_cycle_rf(current_user.id)
    if current_cycle and rf_pred:
        next_period = current_cycle['start_date'] + timedelta(days=rf_pred)
        next_period_days = (next_period.date() - now.date()).days
    else:
        next_period = MenstrualCycle.predict_next_period(current_user.id)
        next_period_days = (next_period.date() - now.date()).days if next_period else None
    # Fertile window status
    fertile_start, ovulation_day = MenstrualCycle.get_fertile_window(current_user.id)
    if fertile_start and ovulation_day:
        if fertile_start.date() <= now.date() <= ovulation_day.date():
            fertile_window_status = 'In Window'
        else:
            fertile_window_status = f"{fertile_start.strftime('%b %d')} - {ovulation_day.strftime('%b %d')}"
    else:
        fertile_window_status = None
    # Cycle regularity (std dev of last 6 cycles)
    if cycles and len(cycles) > 5:
        cycle_lengths = [(cycles[i]['start_date'] - cycles[i+1]['start_date']).days for i in range(len(cycles)-1)]
        avg = sum(cycle_lengths) / len(cycle_lengths)
        std = (sum((x-avg)**2 for x in cycle_lengths) / len(cycle_lengths))**0.5
        cycle_regularity = int(100 - min(std/avg*100, 100))
    else:
        cycle_regularity = None
    # AI Insights (MedBERT on notes)
    ai_insights = []
    for c in cycles[:3]:
        if c.get('notes'):
            emb = MenstrualCycle.analyze_notes_with_medbert(c['notes'])
            ai_insights.append({'title': 'MedBERT Embedding', 'description': str(emb)})
    # Recent symptoms
    recent_symptoms = CycleSymptom.get_symptom_history(current_user.id, limit=5)
    # Get upcoming reminders for the next 3 days
    upcoming_reminders = []
    try:
        # Get all upcoming reminders
        reminders = MenstrualReminder.get_user_reminders(
            user_id=current_user.id,
            active_only=True,
            upcoming_only=True,
            limit=10  # Limit to 10 to avoid too many results
        )
        
        # Filter for reminders in the next 3 days
        three_days_later = datetime.utcnow() + timedelta(days=3)
        for reminder in reminders:
            if reminder.scheduled_date <= three_days_later:
                upcoming_reminders.append(reminder.to_dict())
    except Exception as e:
        current_app.logger.error(f"Error fetching upcoming reminders: {e}")
        upcoming_reminders = []
    
    return render_template('menstrual_enhanced/dashboard.html',
                         cycles=cycles,
                         current_cycle=current_cycle,
                         current_cycle_day=current_cycle_day,
                         next_period=next_period,
                         next_period_days=next_period_days,
                         fertile_start=fertile_start,
                         ovulation_day=ovulation_day,
                         fertile_window_status=fertile_window_status,
                         cycle_regularity=cycle_regularity,
                         ai_insights=ai_insights,
                         recent_symptoms=recent_symptoms,
                         upcoming_reminders=upcoming_reminders)

def allowed_file(filename):
    """Check if file type is allowed"""
    ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ============================================================================
# REMINDER & NOTIFICATION ROUTES
# ============================================================================

@menstrual_enhanced_bp.route('/reminders')
@login_required
def reminders():
    """Render the reminders and notifications page"""
    return render_template('menstrual_enhanced/reminders.html')

# ============================================================================
# API ROUTES FOR REMINDERS
# ============================================================================


@menstrual_enhanced_bp.route('/api/reminders', methods=['POST'])
@login_required
def create_reminder_api():
    """API endpoint to create a new reminder"""
    data = request.get_json()
    if not data or not data.get('title') or not data.get('scheduled_date'):
        return jsonify({'status': 'error', 'message': 'Missing required fields: title and scheduled_date are required.'}), 400
    
    try:
        scheduled_date = datetime.fromisoformat(data['scheduled_date'].replace('Z', '+00:00'))

        reminder = MenstrualReminder({
            'user_id': current_user.id,
            'reminder_type': data.get('reminder_type', 'custom'),
            'title': data['title'],
            'message': data.get('message', ''),
            'scheduled_date': scheduled_date,
            'notification_methods': data.get('notification_methods', ['in_app']),
            'is_recurring': data.get('is_recurring', False)
        })
        reminder.save()
        return jsonify({'status': 'success', 'message': 'Reminder created successfully', 'reminder': reminder.to_dict()}), 201
    except Exception as e:
        current_app.logger.error(f"Error creating reminder for user {current_user.id}: {e}")
        return jsonify({'status': 'error', 'message': 'Could not create reminder.'}), 500

@menstrual_enhanced_bp.route('/api/reminders/<string:reminder_id>', methods=['DELETE'])
@login_required
def delete_reminder_api(reminder_id):
    """API endpoint to deactivate (delete) a reminder"""
    try:
        reminder = MenstrualReminder.find_by_id(reminder_id)
        if not reminder or str(reminder.user_id) != str(current_user.id):
            return jsonify({'status': 'error', 'message': 'Reminder not found or you do not have permission to delete it.'}), 404
        
        MenstrualReminder.deactivate_reminder(reminder_id)
        return jsonify({'status': 'success', 'message': 'Reminder deleted successfully'}), 200
    except Exception as e:
        current_app.logger.error(f"Error deleting reminder {reminder_id} for user {current_user.id}: {e}")
        return jsonify({'status': 'error', 'message': 'Could not delete reminder.'}), 500


# ============================================================================
# LIFESTYLE RECOMMENDATIONS ROUTES
# ============================================================================

@menstrual_enhanced_bp.route('/lifestyle')
@login_required
def lifestyle_recommendations():
    """View personalized lifestyle recommendations"""
    # Dummy data for template rendering
    current_phase = 'Luteal'
    recommendations = {
        'diet': [
            {'recommendation': 'Increase intake of magnesium-rich foods like spinach and nuts.', 'icon': 'fas fa-leaf'},
            {'recommendation': 'Focus on complex carbohydrates to stabilize mood.', 'icon': 'fas fa-bread-slice'}
        ],
        'exercise': [
            {'recommendation': 'Engage in light to moderate activities like yoga or swimming.', 'icon': 'fas fa-swimmer'},
            {'recommendation': 'Avoid overly strenuous workouts that could increase stress.', 'icon': 'fas fa-walking'}
        ],
        'wellness': [
            {'recommendation': 'Prioritize sleep, aiming for 7-9 hours per night.', 'icon': 'fas fa-moon'},
            {'recommendation': 'Practice mindfulness or meditation to manage mood swings.', 'icon': 'fas fa-brain'}
        ]
    }
    return render_template('menstrual_enhanced/lifestyle.html', 
                         current_phase=current_phase,
                         recommendations=recommendations)

# ============================================================================
# MULTI-USER PROFILE ROUTES
# ============================================================================

@menstrual_enhanced_bp.route('/profiles')
@login_required
def profiles():
    """Manage multiple tracking profiles"""
    # Dummy data for template rendering
    profiles_data = [
        {'id': '1', 'name': 'My Cycle', 'relationship': 'Self', 'avatar_url': 'https://via.placeholder.com/150'},
        {'id': '2', 'name': 'Jane Doe', 'relationship': 'Sister', 'avatar_url': 'https://via.placeholder.com/150'}
    ]
    active_profile_id = '1'
    return render_template('menstrual_enhanced/profiles.html', profiles=profiles_data, active_profile_id=active_profile_id)

@menstrual_enhanced_bp.route('/profiles/create', methods=['GET', 'POST'])
@login_required
def create_profile():
    """Create a new tracking profile"""
    if request.method == 'POST':
        profile_name = request.form.get('profile_name')
        dob_str = request.form.get('date_of_birth')

        if not profile_name or not dob_str:
            flash('Please fill out all fields.', 'danger')
            return render_template('menstrual_enhanced/create_profile.html')

        try:
            date_of_birth = datetime.strptime(dob_str, '%Y-%m-%d')
            age = (datetime.utcnow() - date_of_birth).days // 365
        except ValueError:
            flash('Invalid date format. Please use YYYY-MM-DD.', 'danger')
            return render_template('menstrual_enhanced/create_profile.html')

        MenstrualProfile.create_primary_profile(
            user_id=current_user.id,
            profile_name=profile_name,
            age=age,
            date_of_birth=date_of_birth
        )
        
        flash('Profile created successfully! You can now start tracking.', 'success')
        return redirect(url_for('menstrual_enhanced.dashboard'))
        
    return render_template('menstrual_enhanced/create_profile.html')

@menstrual_enhanced_bp.route('/profiles/<profile_id>/switch')
@login_required
def switch_profile(profile_id):
    """Switch to a different profile for tracking"""
    session['active_profile_id'] = profile_id
    flash('Switched profile successfully!', 'success')
    return redirect(url_for('menstrual.tracker')) # Assuming menstrual.tracker is the main dashboard

# ============================================================================
# VOICE LOGGING ROUTES
# ============================================================================

@menstrual_enhanced_bp.route('/voice-log', methods=['GET', 'POST'])
@login_required
def voice_log():
    """Voice-based cycle and symptom logging"""
    if request.method == 'POST':
        flash('Voice log recorded! Processing will begin shortly.', 'success')
        return jsonify({'status': 'success'})
    # Dummy data for template rendering
    voice_logs = [
        {'id': '1', 'upload_date': '2023-11-10 09:15', 'status': 'processed', 'transcript': 'Logged headache and light flow.', 'audio_url': '#'},
        {'id': '2', 'upload_date': '2023-11-09 08:30', 'status': 'processing', 'transcript': '...', 'audio_url': '#'}
    ]
    return render_template('menstrual_enhanced/voice_log.html', voice_logs=voice_logs)

# ============================================================================

# ============================================================================
# DATA EXPORT & PRIVACY ROUTES
# ============================================================================

@menstrual_enhanced_bp.route('/data-export')
@login_required
def data_export():
    """Manage data exports"""
    # Dummy data for template rendering
    exports = [
        {'id': '1', 'export_type': 'Cycle History', 'format': 'PDF', 'created_at': '2023-11-01', 'status': 'Completed', 'download_url': '#'},
        {'id': '2', 'export_type': 'All Symptoms', 'format': 'CSV', 'created_at': '2023-11-10', 'status': 'Processing', 'download_url': None}
    ]
    return render_template('menstrual_enhanced/data_export.html', exports=exports)

@menstrual_enhanced_bp.route('/privacy-settings', methods=['GET', 'POST'])
@login_required
def privacy_settings():
    """Manage privacy and data security settings"""
    if request.method == 'POST':
        flash('Privacy settings updated successfully!', 'success')
        return redirect(url_for('menstrual_enhanced.privacy_settings'))
    # Dummy data for template rendering
    settings = {
        'password_protection': True,
        'two_factor_auth': False,
        'data_sharing_anonymous': True
    }
    return render_template('menstrual_enhanced/privacy.html', settings=settings)

# ============================================================================
# COMMUNITY & EDUCATION ROUTES
# ============================================================================

@menstrual_enhanced_bp.route('/community')
@login_required
def community():
    """Community forum for menstrual health discussions"""
    # Dummy data for template rendering
    posts = [
        {'id': '1', 'author': {'username': 'CycleSavvy', 'avatar_url': 'https://via.placeholder.com/150'}, 'created_at': '2 hours ago', 'title': 'Tips for managing PCOS symptoms?', 'content': 'Hey everyone, I was recently diagnosed with PCOS and was wondering if anyone had tips for managing symptoms like irregular periods and fatigue. Any advice is appreciated!', 'comments_count': 12, 'likes_count': 45},
        {'id': '2', 'author': {'username': 'WellnessWarrior', 'avatar_url': 'https://via.placeholder.com/150'}, 'created_at': '1 day ago', 'title': 'Best exercises during the luteal phase', 'content': 'I always feel so sluggish during my luteal phase. What are some exercises that you all find helpful during this time?', 'comments_count': 8, 'likes_count': 32}
    ]
    categories = [
        {'name': 'General Health', 'slug': 'general-health', 'icon': 'fas fa-heartbeat', 'post_count': 42},
        {'name': 'PCOS & Endometriosis', 'slug': 'pcos-endo', 'icon': 'fas fa-notes-medical', 'post_count': 23},
        {'name': 'Fertility & TTC', 'slug': 'fertility', 'icon': 'fas fa-baby', 'post_count': 15}
    ]
    featured_articles = [
        {'title': 'Understanding Your Hormones', 'source': 'Healthline', 'url': '#'},
        {'title': 'Nutrition for a Healthy Cycle', 'source': 'Mayo Clinic', 'url': '#'}
    ]
    return render_template('menstrual_enhanced/community.html', 
                         posts=posts, 
                         categories=categories, 
                         featured_articles=featured_articles)

# ============================================================================

# ============================================================================
# CYCLE LOGGING ROUTES
# ============================================================================

@menstrual_enhanced_bp.route('/log-cycle', methods=['GET', 'POST'])
@login_required
def log_cycle():
    """Log a new menstrual cycle with MedBERT analytics"""
    symptoms = [
        {'value': 'headache', 'label': 'Headache'},
        {'value': 'cramps', 'label': 'Cramps'},
        {'value': 'bloating', 'label': 'Bloating'},
        {'value': 'fatigue', 'label': 'Fatigue'},
        {'value': 'mood_swings', 'label': 'Mood Swings'},
        {'value': 'acne', 'label': 'Acne'},
        {'value': 'breast_tenderness', 'label': 'Breast Tenderness'},
    ]
    if request.method == 'POST':
        data = request.form
        notes = data.get('notes', '')
        medbert_analytics = None
        if notes:
            medbert_analytics = MenstrualCycle.analyze_notes_with_medbert(notes)
        # Save cycle with medbert_analytics in DB (as an example, add to notes field)
            cycle = MenstrualCycle(
                user_id=current_user.id,
            start_date=datetime.strptime(data['start_date'], '%Y-%m-%d'),
            end_date=datetime.strptime(data['end_date'], '%Y-%m-%d') if data.get('end_date') else None,
            flow_intensity=data.get('flow_intensity', 'moderate'),
            pain_level=data.get('pain_level', 'none'),
            mood=data.get('mood', 'normal'),
            symptoms=data.getlist('symptoms'),
            notes=notes + f"\nMedBERT: {medbert_analytics}" if medbert_analytics else notes
            )
            cycle.save()
        # Optionally retrain RF model
        MenstrualCycle.train_random_forest(current_user.id)
        flash('Cycle logged with AI analytics!', 'success')
        return redirect(url_for('menstrual_enhanced.dashboard'))
    return render_template('menstrual_enhanced/log_cycle.html', symptoms=symptoms)

# ============================================================================
# SYMPTOM LOGGING ROUTES
# ============================================================================

@menstrual_enhanced_bp.route('/log-symptoms', methods=['GET', 'POST'])
@login_required
def log_symptoms():
    """Log menstrual symptoms for a specific day."""
    if request.method == 'POST':
        date_str = request.form.get('date')
        flash(f'Symptoms logged successfully for {date_str}!', 'success')
        return redirect(url_for('menstrual_enhanced.log_symptoms'))
    return render_template('menstrual_enhanced/log_symptoms.html', today=date.today().isoformat())

# ============================================================================
# INTEGRATION ROUTES (Google Fit, Fitbit, etc.)
# ============================================================================

@menstrual_enhanced_bp.route('/integrations')
@login_required
def integrations():
    """Manage third-party integrations"""
    # Dummy data for template rendering
    integrations_data = {
        'google_fit': {'connected': True, 'last_synced': 'Today at 10:00 AM'},
        'fitbit': {'connected': False}
    }
    return render_template('menstrual_enhanced/integrations.html', integrations=integrations_data)

@menstrual_enhanced_bp.route('/integrations/google-fit/connect')
@login_required
def connect_google_fit():
    """Connect Google Fit integration"""
    flash('Google Fit integration coming soon!', 'info')
    return redirect(url_for('menstrual_enhanced.integrations'))

@menstrual_enhanced_bp.route('/integrations/fitbit/connect')
@login_required
def connect_fitbit():
    """Connect Fitbit integration"""
    flash('Fitbit integration coming soon!', 'info')
    return redirect(url_for('menstrual_enhanced.integrations'))

# ============================================================================
# API ENDPOINTS FOR MOBILE/AJAX
# ============================================================================

@menstrual_enhanced_bp.route('/api/reminders', methods=['GET'])
@login_required
def get_reminders_api():
    """Get all reminders for the current user"""
    show_all = request.args.get('all', 'false').lower() == 'true'
    if show_all:
        reminders = MenstrualReminder.get_user_reminders(current_user.id, active_only=False)
    else:
        # By default, only show active, non-expired reminders
        reminders = MenstrualReminder.get_user_reminders(
            current_user.id,
            active_only=True,
            upcoming_only=False
        )
    return jsonify([reminder.to_dict() for reminder in reminders])

@menstrual_enhanced_bp.route('/api/reminders/upcoming', methods=['GET'])
@login_required
def get_upcoming_reminders():
    """Get the next two upcoming reminders for the current user"""
    limit = min(int(request.args.get('limit', 2)), 10)  # Max 10 upcoming reminders
    reminders = MenstrualReminder.get_upcoming_reminders(current_user.id, limit=limit)
    return jsonify([reminder.to_dict() for reminder in reminders]), 200

@menstrual_enhanced_bp.route('/api/reminders', methods=['POST'])
@login_required
def create_reminder():
    """Create a new reminder"""
    data = request.get_json()
    
    # Basic validation
    if not data or 'title' not in data or 'scheduled_date' not in data:
        return jsonify({'error': 'Title and scheduled_date are required'}), 400
    
    try:
        scheduled_date = datetime.fromisoformat(data['scheduled_date'].replace('Z', '+00:00'))
        expires_at = None
        if 'expires_at' in data and data['expires_at']:
            expires_at = datetime.fromisoformat(data['expires_at'].replace('Z', '+00:00'))
    except (ValueError, TypeError) as e:
        return jsonify({'error': f'Invalid date format. Use ISO 8601 format: {str(e)}'}), 400
    
    # Set default expiration to 24 hours after scheduled date if not provided
    if not expires_at:
        expires_at = scheduled_date + timedelta(days=1)
    
    reminder_data = {
        'user_id': current_user.id,
        'title': data['title'],
        'message': data.get('message', ''),
        'scheduled_date': scheduled_date,
        'expires_at': expires_at,
        'notification_methods': data.get('notification_methods', ['in_app']),
        'is_recurring': data.get('is_recurring', False),
        'recurrence_pattern': data.get('recurrence_pattern'),
        'metadata': data.get('metadata', {})
    }
    
    # If this is a recurring reminder, set up the next occurrence
    if reminder_data['is_recurring'] and not reminder_data.get('recurrence_pattern'):
        reminder_data['recurrence_pattern'] = 'daily'  # Default to daily if not specified
    
    reminder = MenstrualReminder(reminder_data)
    reminder.save()
    
    # Send immediate notification if the reminder is due soon (within 5 minutes)
    now = datetime.utcnow()
    if scheduled_date <= now + timedelta(minutes=5) and scheduled_date >= now:
        # In a real app, you would call your notification service here
        pass
    
    return jsonify({
        'message': 'Reminder created successfully',
        'reminder': reminder.to_dict()
    }), 201

@menstrual_enhanced_bp.route('/api/reminders/<reminder_id>', methods=['PUT'])
@login_required
def update_reminder(reminder_id):
    """API endpoint to update a reminder"""
    reminder = MenstrualReminder.find_by_id(reminder_id)
    if not reminder or str(reminder.user_id) != str(current_user.id):
        return jsonify({'error': 'Reminder not found or unauthorized'}), 404

    data = request.get_json()

    reminder.title = data.get('title', reminder.title)
    reminder.message = data.get('message', reminder.message)
    if data.get('scheduled_date'):
        reminder.scheduled_date = datetime.fromisoformat(data.get('scheduled_date'))
    reminder.is_active = data.get('is_active', reminder.is_active)
    
    reminder.save()
    return jsonify(reminder.to_dict()), 200

@menstrual_enhanced_bp.route('/api/reminders/<reminder_id>', methods=['DELETE'])
@login_required
def delete_reminder(reminder_id):
    """API endpoint to deactivate a reminder"""
    result = MenstrualReminder.deactivate_reminder(reminder_id, current_user.id)
    if result.modified_count == 0:
        return jsonify({'error': 'Reminder not found or unauthorized'}), 404
    return jsonify({'status': 'success', 'message': 'Reminder deactivated'}), 200

@menstrual_enhanced_bp.route('/api/quick-log', methods=['POST'])
@login_required
def api_quick_log():
    """Quick API endpoint for logging symptoms"""
    data = request.get_json()
    # Logic to save data would go here
    return jsonify({'status': 'success', 'message': 'Log received', 'data': data})


@menstrual_enhanced_bp.route('/api/predictions')
@login_required
def api_predictions():
    """API endpoint for cycle predictions using Random Forest"""
    rf_pred = MenstrualCycle.predict_next_cycle_rf(current_user.id)
    current_cycle = MenstrualCycle.get_current_cycle(current_user.id)
    if current_cycle and rf_pred:
        next_period = current_cycle['start_date'] + timedelta(days=rf_pred)
    else:
        next_period = MenstrualCycle.predict_next_period(current_user.id)
    fertile_start, ovulation_day = MenstrualCycle.get_fertile_window(current_user.id)
    return jsonify({
        'next_period': next_period.isoformat() if next_period else None,
        'fertile_start': fertile_start.isoformat() if fertile_start else None,
        'ovulation_day': ovulation_day.isoformat() if ovulation_day else None,
        'rf_pred_days': rf_pred
    })

