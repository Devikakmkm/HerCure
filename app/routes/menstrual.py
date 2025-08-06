import os
import io
import base64
from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for, current_app, send_file
from flask_login import login_required, current_user
from datetime import datetime, timedelta, date
from bson import ObjectId
from calendar import monthrange, month_name
import matplotlib
matplotlib.use('Agg')  # Set the backend to non-interactive
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
from app.forms.cycle_forms import CycleLogForm

# Helper function to create and save a chart as base64
def create_chart(fig):
    """Convert a matplotlib figure to base64 for HTML display"""
    img = io.BytesIO()
    fig.savefig(img, format='png', bbox_inches='tight', dpi=100)
    img.seek(0)
    return base64.b64encode(img.getvalue()).decode('utf-8')

def create_bar_chart(labels, values, title, xlabel, ylabel, color='skyblue'):
    """Create a bar chart and return as base64"""
    fig, ax = plt.subplots(figsize=(10, 5))
    y_pos = np.arange(len(labels))
    ax.bar(y_pos, values, color=color)
    ax.set_xticks(y_pos)
    ax.set_xticklabels(labels, rotation=45, ha='right')
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    plt.tight_layout()
    chart_url = create_chart(fig)
    plt.close(fig)
    return chart_url

def create_line_chart(dates, values, title, xlabel, ylabel, color='tab:blue'):
    """Create a line chart and return as base64"""
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(dates, values, marker='o', color=color)
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=1))
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    plt.xticks(rotation=45)
    plt.tight_layout()
    chart_url = create_chart(fig)
    plt.close(fig)
    return chart_url
import pandas as pd
import numpy as np
from ..models.menstrual_cycle import MenstrualCycle, CycleSymptom
from app.forms.wellness_forms import WellnessQuizForm
from app.models.user import User
from app.services.ai_service import generate_wellness_recommendations

# Define the Blueprint at the top level
menstrual_bp = Blueprint('menstrual', __name__)

@menstrual_bp.route('/tracker/analytics_enhanced')
@login_required
def analytics_enhanced():
    """Enhanced analytics dashboard with AI-powered insights and visualizations"""
    # Get basic cycle statistics
    stats = MenstrualCycle.get_cycle_statistics(current_user.id)
    
    # Get recent cycles for visualization
    cycles = list(MenstrualCycle.get_user_cycles(current_user.id, limit=12))  # Last 12 months
    
    # Prepare data for charts
    chart_data = {
        'cycle_lengths': [],
        'period_lengths': [],
        'dates': [],
        'symptoms': {}
    }
    
    if cycles and len(cycles) > 1:
        for i in range(len(cycles) - 1):
            cycle = cycles[i]
            next_cycle = cycles[i + 1]
            
            if 'start_date' in cycle and 'start_date' in next_cycle:
                cycle_length = (next_cycle['start_date'] - cycle['start_date']).days
                chart_data['cycle_lengths'].append(cycle_length)
                chart_data['dates'].append(cycle['start_date'].strftime('%Y-%m-%d'))
            
            if 'start_date' in cycle and 'end_date' in cycle and cycle['end_date']:
                period_length = (cycle['end_date'] - cycle['start_date']).days + 1
                chart_data['period_lengths'].append(period_length)
    
    # Get recent symptoms for analysis
    six_months_ago = datetime.utcnow() - timedelta(days=180)
    symptoms = CycleSymptom.get_symptoms_in_date_range(current_user.id, six_months_ago, datetime.utcnow())
    
    # Process symptoms data safely
    symptom_frequency = {}
    if symptoms:
        # Flatten symptoms list and count frequencies
        all_symptoms = []
        for symptom_record in symptoms:
            if 'symptoms' in symptom_record and isinstance(symptom_record['symptoms'], list):
                all_symptoms.extend(symptom_record['symptoms'])
        
        # Count symptom frequencies
        for symptom in all_symptoms:
            symptom_frequency[symptom] = symptom_frequency.get(symptom, 0) + 1
    
    chart_data['symptoms'] = symptom_frequency
    
    # Get current cycle phase and predictions
    current_phase, day_of_cycle = MenstrualCycle.get_current_phase(current_user.id)
    next_period = MenstrualCycle.predict_next_period(current_user.id)
    fertile_start, ovulation_day = MenstrualCycle.get_fertile_window(current_user.id)
    
    return render_template('menstrual/analytics_enhanced.html',
                         stats=stats,
                         chart_data=chart_data,
                         current_phase=current_phase,
                         day_of_cycle=day_of_cycle,
                         next_period=next_period,
                         fertile_start=fertile_start,
                         ovulation_day=ovulation_day)

# Calendar helper functions
def get_calendar_data(user_id, year=None, month=None):
    """Generate calendar data for a given month, including predictions."""
    import datetime as dt
    today = dt.datetime.combine(date.today(), dt.time())
    if not year:
        year = today.year
    if not month:
        month = today.month

    _, num_days = monthrange(year, month)
    first_day = dt.datetime(year, month, 1)
    last_day = dt.datetime(year, month, num_days)
    first_weekday = first_day.weekday()

    # Get historical data
    cycles = list(MenstrualCycle.get_cycles_in_date_range(user_id, first_day, last_day + timedelta(days=1)))
    symptoms = list(CycleSymptom.get_symptoms_in_date_range(user_id, first_day, last_day + timedelta(days=1)))

    # Get predictions for both past and future months
    predicted_cycles = MenstrualCycle.predict_future_cycles(user_id, num_cycles=6)

    calendar_days = []
    for _ in range(first_weekday):
        calendar_days.append({'day': '', 'date': None, 'is_today': False, 'cycle': None, 'symptoms': []})

    for day in range(1, num_days + 1):
        current_date = dt.datetime(year, month, day)
        is_today = (current_date.date() == today.date())
        cycle_data = None

        # Check for historical cycle data first
        for cycle in cycles:
            if cycle['start_date'].date() <= current_date.date() and (cycle.get('end_date') is None or cycle['end_date'].date() >= current_date.date()):
                cycle_data = {'is_period': True, 'flow': cycle.get('flow_intensity', 'moderate')}
                break
        
        # If no historical data, check for predicted phases
        if not cycle_data:
            for prediction in predicted_cycles:
                for phase_name, (start, end) in prediction.items():
                    if start.date() <= current_date.date() <= end.date():
                        cycle_data = {'predicted_phase': phase_name.split('_')[0].capitalize(), 'is_predicted': True}
                        break
                if cycle_data:
                    break

        day_symptoms = [s for s in symptoms if s['date'].date() == current_date.date()]
        
        calendar_days.append({
            'day': day,
            'date': current_date,
            'is_today': is_today,
            'cycle': cycle_data,
            'symptoms': day_symptoms
        })

    prev_month = month - 1 if month > 1 else 12
    prev_year = year if month > 1 else year - 1
    next_month = month + 1 if month < 12 else 1
    next_year = year if month < 12 else year + 1

    return {
        'year': year,
        'month': month,
        'month_name': month_name[month],
        'days': calendar_days,
        'prev_month': {'month': prev_month, 'year': prev_year},
        'next_month': {'month': next_month, 'year': next_year},
        'today': today
    }

@menstrual_bp.route('/')
@menstrual_bp.route('/tracker')
@login_required
def tracker():
    """Main menstrual tracking dashboard"""
    cycles = MenstrualCycle.get_user_cycles(current_user.id)
    current_cycle = MenstrualCycle.get_current_cycle(current_user.id)
    next_period = MenstrualCycle.predict_next_period(current_user.id)
    fertile_start, ovulation_day = MenstrualCycle.get_fertile_window(current_user.id)
    current_phase, day_of_cycle = MenstrualCycle.get_current_phase(current_user.id)
    cycle_stats = MenstrualCycle.get_cycle_statistics(current_user.id)
    
    return render_template('menstrual/tracker.html',
                         cycles=cycles,
                         current_cycle=current_cycle,
                         next_period=next_period,
                         fertile_start=fertile_start,
                         ovulation_day=ovulation_day,
                         current_phase=current_phase,
                         day_of_cycle=day_of_cycle,
                         cycle_stats=cycle_stats,
                         now=datetime.utcnow())

@menstrual_bp.route('/tracker/log', methods=['GET', 'POST'])
@login_required
def log_cycle():
    """Log a new menstrual cycle"""
    form = CycleLogForm(request.form)
    symptoms_list = [
        {'value': 'headache', 'label': 'Headache'},
        {'value': 'cramps', 'label': 'Cramps'},
        {'value': 'bloating', 'label': 'Bloating'},
        {'value': 'fatigue', 'label': 'Fatigue'},
        {'value': 'mood_swings', 'label': 'Mood Swings'},
        {'value': 'acne', 'label': 'Acne'},
        {'value': 'breast_tenderness', 'label': 'Breast Tenderness'},
        {'value': 'back_pain', 'label': 'Back Pain'},
        {'value': 'food_cravings', 'label': 'Food Cravings'},
        {'value': 'insomnia', 'label': 'Insomnia'},
        {'value': 'nausea', 'label': 'Nausea'},
        {'value': 'dizziness', 'label': 'Dizziness'},
        {'value': 'constipation', 'label': 'Constipation'},
        {'value': 'diarrhea', 'label': 'Diarrhea'},
        {'value': 'hot_flashes', 'label': 'Hot Flashes'},
        {'value': 'night_sweats', 'label': 'Night Sweats'}
    ]

    if request.method == 'POST' and form.validate():
        try:
            cycle = MenstrualCycle(
                user_id=current_user.id,
                start_date=form.start_date.data,
                end_date=form.end_date.data,
                flow_intensity=form.flow_intensity.data,
                pain_level=form.pain_level.data,
                mood=form.mood.data,
                symptoms=form.symptoms.data,
                notes=form.notes.data
            )
            cycle.save()
            flash('Cycle logged successfully!', 'success')
            return redirect(url_for('menstrual.tracker'))
        except Exception as e:
            current_app.logger.error(f"Error logging cycle: {e}", exc_info=True)
            flash('An unexpected error occurred while saving your cycle.', 'danger')
    
    # For GET requests or if form validation fails, render the template with the form object.
    return render_template('menstrual/log_cycle.html', 
                         form=form, 
                         symptoms=symptoms_list, 
                         today=date.today().isoformat())

@menstrual_bp.route('/tracker/symptom', methods=['POST'])
@login_required
def log_symptom():
    """Log a new symptom"""
    try:
        symptom_data = request.get_json()
        CycleSymptom.track_symptom(
            user_id=current_user.id,
            symptom_name=symptom_data.get('symptom'),
            severity=symptom_data.get('severity', 'mild'),
            notes=symptom_data.get('notes', '')
        )
        return jsonify({'status': 'success'})
    except Exception as e:
        current_app.logger.error(f"Error logging symptom: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 400

@menstrual_bp.route('/tracker/cycles')
@login_required
def cycle_history():
    """View cycle history with abnormality analysis."""
    all_cycles = MenstrualCycle.get_user_cycles(current_user.id, limit=0)

    if not all_cycles:
        return render_template('menstrual/cycle_history.html', cycles=[])

    user_stats = MenstrualCycle.get_cycle_statistics(current_user.id)
    
    cycles_with_analysis = []
    for i in range(len(all_cycles)):
        cycle = all_cycles[i]
        
        if cycle.get('start_date') and cycle.get('end_date'):
            cycle['period_length'] = (cycle['end_date'] - cycle['start_date']).days + 1
        else:
            cycle['period_length'] = None
            
        if i + 1 < len(all_cycles):
            prev_cycle_start = all_cycles[i+1]['start_date']
            cycle['cycle_length'] = (cycle['start_date'] - prev_cycle_start).days
        else:
            cycle['cycle_length'] = None
            
        cycle['abnormalities'] = MenstrualCycle.analyze_cycle_abnormalities(cycle, user_stats)
        cycles_with_analysis.append(cycle)

    return render_template('menstrual/cycle_history.html', cycles=cycles_with_analysis)

@menstrual_bp.route('/tracker/calendar')
@menstrual_bp.route('/tracker/calendar/<int:year>/<int:month>')
@login_required
def cycle_calendar(year=None, month=None):
    """Interactive calendar view"""
    form = CycleLogForm()
    calendar_data = get_calendar_data(current_user.id, year, month)
    next_period = MenstrualCycle.predict_next_period(current_user.id)
    fertile_window = MenstrualCycle.get_fertile_window(current_user.id)
    fertile_start, ovulation_day = (None, None) if fertile_window is None else fertile_window
    
    return render_template('menstrual/calendar.html',
                         calendar=calendar_data,
                         next_period=next_period,
                         fertile_start=fertile_start,
                         ovulation_day=ovulation_day,
                         CycleSymptom=CycleSymptom,
                         form=form)

@menstrual_bp.route('/tracker/analytics')
@login_required
def analytics():
    """Analytics dashboard with AI-powered insights and visualizations"""
    # Get cycle statistics
    stats = MenstrualCycle.get_cycle_statistics(current_user.id)
    cycles = list(MenstrualCycle.get_user_cycles(current_user.id, limit=12))  # Last 12 months
    
    # Initialize chart data structure
    chart_data = {
        'cycle_lengths': [],
        'period_lengths': [],
        'dates': [],
        'symptoms': {},
        'moods': {},
        'flow_intensity': {},
        'pain_levels': {}
    }
    
    # Process cycle data
    if cycles and len(cycles) > 1:
        for i in range(len(cycles) - 1):
            cycle = cycles[i]
            next_cycle = cycles[i + 1]
            
            # Calculate cycle length (days between start dates)
            if 'start_date' in cycle and 'start_date' in next_cycle:
                cycle_length = (next_cycle['start_date'] - cycle['start_date']).days
                chart_data['cycle_lengths'].append(cycle_length)
                chart_data['dates'].append(cycle['start_date'])
            
            # Calculate period length (days between start and end dates)
            if 'start_date' in cycle and 'end_date' in cycle and cycle['end_date']:
                period_length = (cycle['end_date'] - cycle['start_date']).days + 1
                chart_data['period_lengths'].append(period_length)
                
            # Track flow intensity
            if 'flow_intensity' in cycle and cycle['flow_intensity']:
                chart_data['flow_intensity'][cycle['flow_intensity']] = chart_data['flow_intensity'].get(cycle['flow_intensity'], 0) + 1
            
            # Track pain levels
            if 'pain_level' in cycle and cycle['pain_level']:
                chart_data['pain_levels'][cycle['pain_level']] = chart_data['pain_levels'].get(cycle['pain_level'], 0) + 1
    
    # Get symptoms data for the last 6 months
    six_months_ago = datetime.utcnow() - timedelta(days=180)
    symptoms = CycleSymptom.get_symptoms_in_date_range(current_user.id, six_months_ago, datetime.utcnow())
    
    # Process symptoms and mood data
    symptom_frequency = {}
    mood_frequency = {}
    
    if symptoms:
        for symptom_record in symptoms:
            # Process symptoms
            if 'symptoms' in symptom_record and isinstance(symptom_record['symptoms'], list):
                for symptom in symptom_record['symptoms']:
                    symptom_frequency[symptom] = symptom_frequency.get(symptom, 0) + 1
            
            # Process moods
            if 'mood' in symptom_record and symptom_record['mood']:
                mood = symptom_record['mood'].lower()
                mood_frequency[mood] = mood_frequency.get(mood, 0) + 1
    
    chart_data['symptoms'] = dict(sorted(symptom_frequency.items(), key=lambda x: x[1], reverse=True)[:10])  # Top 10 symptoms
    chart_data['moods'] = mood_frequency
    
    # Ensure all pain levels are included, even if count is 0
    for level in ['none', 'mild', 'moderate', 'severe']:
        if level not in chart_data['pain_levels']:
            chart_data['pain_levels'][level] = 0
    
    # Ensure all flow intensities are included, even if count is 0
    for intensity in ['light', 'moderate', 'heavy']:
        if intensity not in chart_data['flow_intensity']:
            chart_data['flow_intensity'][intensity] = 0
    
    # Generate charts
    charts = {}
    
    # Cycle Length Chart
    if chart_data['dates'] and chart_data['cycle_lengths']:
        try:
            charts['cycle_length'] = create_line_chart(
                chart_data['dates'],
                chart_data['cycle_lengths'],
                'Cycle Length Over Time',
                'Cycle Start Date',
                'Days',
                'tab:purple'
            )
        except Exception as e:
            current_app.logger.error(f"Error creating cycle length chart: {e}")
    
    # Period Length Chart
    if chart_data['period_lengths'] and len(chart_data['period_lengths']) >= 2:
        try:
            charts['period_length'] = create_line_chart(
                chart_data['dates'][:len(chart_data['period_lengths'])],
                chart_data['period_lengths'],
                'Period Length Over Time',
                'Period Start Date',
                'Days',
                'tab:red'
            )
        except Exception as e:
            current_app.logger.error(f"Error creating period length chart: {e}")
    
    # Symptoms Chart
    if chart_data['symptoms']:
        try:
            symptoms = list(chart_data['symptoms'].keys())
            counts = list(chart_data['symptoms'].values())
            charts['symptoms'] = create_bar_chart(
                symptoms,
                counts,
                'Most Common Symptoms',
                'Symptom',
                'Frequency',
                'tab:green'
            )
        except Exception as e:
            current_app.logger.error(f"Error creating symptoms chart: {e}")
    
    # Mood Chart
    if chart_data['moods']:
        try:
            moods = list(chart_data['moods'].keys())
            counts = list(chart_data['moods'].values())
            charts['moods'] = create_bar_chart(
                moods,
                counts,
                'Mood Distribution',
                'Mood',
                'Frequency',
                'tab:blue'
            )
        except Exception as e:
            current_app.logger.error(f"Error creating mood chart: {e}")
    
    # Flow Intensity Chart
    if any(count > 0 for count in chart_data['flow_intensity'].values()):
        try:
            intensities = list(chart_data['flow_intensity'].keys())
            counts = [chart_data['flow_intensity'][i] for i in intensities]
            charts['flow_intensity'] = create_bar_chart(
                [i.capitalize() for i in intensities],
                counts,
                'Flow Intensity Distribution',
                'Intensity',
                'Count',
                'tab:orange'
            )
        except Exception as e:
            current_app.logger.error(f"Error creating flow intensity chart: {e}")
    
    # Pain Level Chart
    if any(count > 0 for count in chart_data['pain_levels'].values()):
        try:
            pain_levels = ['None', 'Mild', 'Moderate', 'Severe']
            counts = [chart_data['pain_levels'].get(level.lower(), 0) for level in pain_levels]
            charts['pain_levels'] = create_bar_chart(
                pain_levels,
                counts,
                'Pain Level Distribution',
                'Pain Level',
                'Count',
                'tab:red'
            )
        except Exception as e:
            current_app.logger.error(f"Error creating pain level chart: {e}")
    
    # Get predictions
    next_period = MenstrualCycle.predict_next_period(current_user.id)
    fertile_window = MenstrualCycle.get_fertile_window(current_user.id)
    fertile_start, ovulation_day = (None, None) if fertile_window is None else fertile_window
    
    # Get current cycle phase
    current_phase, day_of_cycle = MenstrualCycle.get_current_phase(current_user.id)
    
    # Prepare next periods for display
    next_periods = []
    if next_period:
        next_periods = [next_period + timedelta(days=i*28) for i in range(3)]  # Next 3 predicted periods
    
    # Get current date for template
    now = datetime.utcnow()
    
    # Calculate fertile window end if fertile_start exists
    fertile_end = None
    if fertile_start:
        fertile_end = fertile_start + timedelta(days=5)
    
    return render_template('menstrual/analytics.html', 
                         stats=stats, 
                         charts=charts,
                         next_periods=next_periods,
                         fertile_start=fertile_start,
                         fertile_end=fertile_end,
                         ovulation_day=ovulation_day,
                         current_phase=current_phase,
                         day_of_cycle=day_of_cycle,
                         now=now)

@menstrual_bp.route('/wellness-quiz', methods=['GET', 'POST'])
@menstrual_bp.route('/tracker/wellness-quiz', methods=['GET', 'POST'])
@login_required
def wellness_quiz():
    """Display a quiz to generate a wellness plan using a WTForm."""
    form = WellnessQuizForm()
    if form.validate_on_submit():
        try:
            user_profile_for_ai = {
                "age": form.age.data,
                "cycle_info": {
                    "average_cycle_length": form.cycle_length.data,
                    "average_period_length": form.period_length.data,
                },
                "recent_symptoms": form.symptoms.data
            }

            recommendations = generate_wellness_recommendations(user_profile_for_ai)

            if not recommendations:
                flash('Could not generate recommendations. Please try again.', 'danger')
                return redirect(url_for('menstrual.wellness_quiz'))

            return render_template('menstrual/wellness_results.html', recommendations=recommendations)

        except Exception as e:
            current_app.logger.error(f"Error in wellness_quiz: {e}", exc_info=True)
            flash('An unexpected error occurred. Please try again.', 'danger')
            return redirect(url_for('menstrual.wellness_quiz'))

    return render_template('menstrual/wellness_quiz.html', form=form)
    

