from datetime import datetime, timedelta
from bson.objectid import ObjectId
from app.extensions import mongo
import joblib
import numpy as np
from app.models.cycle_prediction import CyclePrediction
from app.models.cycle_prediction import CyclePrediction
from typing import List, Dict, Optional, Tuple
from transformers import AutoTokenizer, AutoModel
import torch
from sklearn.ensemble import RandomForestRegressor
import numpy as np
import joblib

# MedBERT setup (singleton)
_medbert_tokenizer = None
_medbert_model = None

def get_medbert():
    global _medbert_tokenizer, _medbert_model
    if _medbert_tokenizer is None or _medbert_model is None:
        _medbert_tokenizer = AutoTokenizer.from_pretrained("Charangan/MedBERT")
        _medbert_model = AutoModel.from_pretrained("Charangan/MedBERT")
    return _medbert_tokenizer, _medbert_model

def medbert_infer(text):
    tokenizer, model = get_medbert()
    inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=256)
    with torch.no_grad():
        outputs = model(**inputs)
    return outputs

class MenstrualCycle:
    COLLECTION = 'menstrual_cycles'
    
    def __init__(self, user_id, start_date, end_date=None, flow_intensity='moderate', 
                 pain_level='none', mood='normal', symptoms=None, notes=''):
        self.user_id = user_id
        self.start_date = start_date
        self.end_date = end_date
        self.flow_intensity = flow_intensity  # light, moderate, heavy
        self.pain_level = pain_level  # none, mild, moderate, severe
        self.mood = mood
        self.symptoms = symptoms or []
        self.notes = notes
        self.created_at = datetime.utcnow()
        self.updated_at = self.created_at

    @classmethod
    def get_cycle_statistics(cls, user_id, months=12):
        """Get default cycle statistics without database access
        
        Args:
            user_id: ID of the user (ignored in this implementation)
            months: Number of months (ignored in this implementation)
            
        Returns:
            dict: Dictionary containing default cycle statistics
        """
        return {
            'total_cycles': 0,
            'avg_cycle_length': 28,  # Default average cycle length
            'avg_period_length': 5,  # Default average period length
            'cycle_regularity': 0,   # Default regularity score
            'cycle_history': [],     # Empty list for cycle history
            'symptom_frequency': {}  # Empty dict for symptom frequency
        }

    @classmethod
    def from_dict(cls, data):
        """Create a MenstrualCycle instance from a dictionary."""
        if not data:
            return None
        
        # To prevent errors if a key is missing, use .get()
        cycle = cls(
            user_id=data.get('user_id'),
            start_date=data.get('start_date'),
            end_date=data.get('end_date'),
            flow_intensity=data.get('flow_intensity', 'moderate'),
            pain_level=data.get('pain_level', 'none'),
            mood=data.get('mood', 'normal'),
            symptoms=data.get('symptoms', []),
            notes=data.get('notes', '')
        )
        # Manually set the id if it exists in the dictionary
        if '_id' in data:
            cycle.id = data['_id']
            
        return cycle

    def save(self):
        try:
            # Ensure start_date and end_date are datetime.datetime
            import datetime as dt
            start_date = self.start_date
            end_date = self.end_date
            
            # Convert date to datetime if needed
            if isinstance(start_date, dt.date) and not isinstance(start_date, dt.datetime):
                start_date = dt.datetime.combine(start_date, dt.time())
            if end_date and isinstance(end_date, dt.date) and not isinstance(end_date, dt.datetime):
                end_date = dt.datetime.combine(end_date, dt.time())
                
            # Ensure user_id is ObjectId
            user_id = ObjectId(self.user_id) if not isinstance(self.user_id, ObjectId) else self.user_id
            
            cycle_data = {
                'user_id': user_id,
                'start_date': start_date,
                'end_date': end_date,
                'flow_intensity': self.flow_intensity,
                'pain_level': self.pain_level,
                'mood': self.mood,
                'symptoms': self.symptoms,
                'notes': self.notes,
                'created_at': self.created_at,
                'updated_at': self.updated_at
            }
            
            # Insert the document
            result = mongo.db[self.COLLECTION].insert_one(cycle_data)
            
            # Verify the insert was successful
            if not result.acknowledged:
                raise Exception("Database operation not acknowledged")
                
            # Update the instance with the new _id
            self.id = result.inserted_id
            
            # Return the result object for further checking if needed
            return result
            
        except Exception as e:
            # Log the error for debugging
            import traceback
            print(f"Error saving menstrual cycle: {str(e)}\n{traceback.format_exc()}")
            raise  # Re-raise the exception to be handled by the caller
    
    @classmethod
    def create_indexes(cls):
        mongo.db[cls.COLLECTION].create_index([('user_id', 1)])
        mongo.db[cls.COLLECTION].create_index([('user_id', 1), ('start_date', -1)])

    @classmethod
    def get_user_cycles(cls, user_id, limit=12):
        return list(mongo.db[cls.COLLECTION].find(
            {'user_id': ObjectId(user_id) if not isinstance(user_id, ObjectId) else user_id}
        ).sort('start_date', -1).limit(limit))
        
    @classmethod
    def get_last_completed_cycle(cls, user_id):
        """Get the most recent completed cycle for a user"""
        return mongo.db[cls.COLLECTION].find_one({
            'user_id': ObjectId(user_id) if not isinstance(user_id, ObjectId) else user_id,
            'end_date': {'$ne': None}  # Only completed cycles have an end_date
        }, sort=[('start_date', -1)])  # Get the most recent one
        
    @classmethod
    def get_current_cycle(cls, user_id):
        """Get the current (in-progress) cycle if one exists"""
        return mongo.db[cls.COLLECTION].find_one({
            'user_id': ObjectId(user_id) if not isinstance(user_id, ObjectId) else user_id,
            'end_date': None  # Current cycle won't have an end_date yet
        }, sort=[('start_date', -1)])  # Get the most recent one
        
    @classmethod
    def get_cycles_in_date_range(cls, user_id, start_date, end_date):
        """Get all cycles that overlap with the given date range"""
        return mongo.db[cls.COLLECTION].find({
            'user_id': ObjectId(user_id) if not isinstance(user_id, ObjectId) else user_id,
            '$or': [
                # Cycle starts within the date range
                {'start_date': {'$gte': start_date, '$lte': end_date}},
                # Cycle ends within the date range
                {'end_date': {'$gte': start_date, '$lte': end_date}},
                # Cycle spans the entire date range
                {
                    'start_date': {'$lte': start_date},
                    '$or': [
                        {'end_date': None},  # Ongoing cycle
                        {'end_date': {'$gte': end_date}}  # Cycle that spans the range
                    ]
                }
            ]
        }).sort('start_date', 1)
        
    # Analytics Methods
    @classmethod
    def get_cycle_statistics(cls, user_id, months=12):
        """Get statistics about the user's menstrual cycles"""
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=30 * months)  # Approximate months to days
        
        # Get all cycles in the date range, including incomplete ones
        cycles = list(mongo.db[cls.COLLECTION].find({
            'user_id': ObjectId(user_id) if not isinstance(user_id, ObjectId) else user_id,
            'start_date': {'$gte': start_date}
        }).sort('start_date', 1))
        
        if not cycles:
            return None
            
        # Calculate cycle lengths and other statistics
        cycle_lengths = []
        period_lengths = []
        symptoms = {}
        
        # First, handle completed cycles (those with end dates)
        completed_cycles = [c for c in cycles if c.get('end_date') is not None]
        
        for i in range(1, len(completed_cycles)):
            prev_cycle = completed_cycles[i-1]
            curr_cycle = completed_cycles[i]
            
            # Calculate cycle length (days between start dates)
            if prev_cycle['start_date'] and curr_cycle['start_date']:
                cycle_length = (curr_cycle['start_date'] - prev_cycle['start_date']).days
                if 15 <= cycle_length <= 60:  # Sanity check for cycle length
                    cycle_lengths.append(cycle_length)
            
            # Calculate period length (days between start and end dates, inclusive)
            if curr_cycle['start_date'] and curr_cycle['end_date']:
                # Ensure end_date is after or equal to start_date, and within a reasonable range
                days_diff = (curr_cycle['end_date'] - curr_cycle['start_date']).days
                if days_diff >= 0:  # Only process if end_date is after start_date
                    period_length = days_diff + 1  # +1 to make it inclusive
                    if 1 <= period_length <= 14:  # Sanity check for period length
                        period_lengths.append(period_length)
        
        # Handle the current cycle if it's in progress
        current_cycle = cycles[-1]
        if not current_cycle.get('end_date') and len(cycles) > 1:
            # For current cycle, we can calculate days since start
            days_since_start = (datetime.utcnow() - current_cycle['start_date']).days
            if days_since_start > 0:
                period_lengths.append(days_since_start)
        
        # Calculate statistics
        avg_cycle = round(sum(cycle_lengths) / len(cycle_lengths), 1) if cycle_lengths else 28
        avg_period = round(sum(period_lengths) / len(period_lengths), 1) if period_lengths else 5
        
        stats = {
            'total_cycles': len(cycle_lengths) if cycle_lengths else 0,
            'avg_cycle_length': avg_cycle,
            'min_cycle_length': min(cycle_lengths) if cycle_lengths else avg_cycle,
            'max_cycle_length': max(cycle_lengths) if cycle_lengths else avg_cycle,
            'avg_period_length': avg_period,
            'cycle_regularity': cls._calculate_regularity(cycle_lengths) if cycle_lengths else 0,
            'cycle_history': cycles[-6:],  # Last 6 cycles for the chart
            'symptom_frequency': cls._get_symptom_frequency(user_id, start_date, end_date)
        }
        
        return stats
    
    @staticmethod
    def analyze_cycle_abnormalities(cycle, user_stats):
        """Analyze a single cycle for abnormalities based on user statistics."""
        abnormalities = []
        
        # Check cycle length
        cycle_length = cycle.get('cycle_length')
        if cycle_length:
            if cycle_length < 21 or cycle_length > 35:
                abnormalities.append({
                    'type': 'Irregular Length',
                    'description': f'Cycle length of {cycle_length} days is outside the typical range (21-35 days).',
                    'icon': 'fas fa-ruler-horizontal'
                })
            elif user_stats['avg_cycle_length'] > 0 and abs(cycle_length - user_stats['avg_cycle_length']) > 7:
                abnormalities.append({
                    'type': 'Length Variation',
                    'description': f'Cycle length deviates significantly from your average of {user_stats["avg_cycle_length"]} days.',
                    'icon': 'fas fa-chart-line'
                })

        # Check period duration
        period_length = cycle.get('period_length')
        if period_length:
            if period_length > 7:
                abnormalities.append({
                    'type': 'Long Period',
                    'description': f'Period duration of {period_length} days is longer than the typical 7 days.',
                    'icon': 'fas fa-tint-slash'
                })
        
        # Check for severe pain
        if cycle.get('pain_level') == 'severe':
            abnormalities.append({
                'type': 'Severe Pain',
                'description': 'High level of pain reported during this cycle.',
                'icon': 'fas fa-bolt'
            })
            
        return abnormalities
    
    @classmethod
    def _calculate_regularity(cls, cycle_lengths):
        """Calculate how regular the cycles are (0-100%)"""
        if not cycle_lengths or len(cycle_lengths) < 3:
            return 0
            
        avg_length = sum(cycle_lengths) / len(cycle_lengths)
        differences = [abs(length - avg_length) for length in cycle_lengths]
        avg_difference = sum(differences) / len(differences)
        
        # Calculate regularity as a percentage (lower difference = higher regularity)
        # Assuming a max difference of 14 days is the least regular (0%)
        max_expected_difference = 14
        regularity = max(0, 100 - (avg_difference / max_expected_difference * 100))
        
        return round(min(regularity, 100), 1)
    
    @classmethod
    def _get_symptom_frequency(cls, user_id, start_date, end_date):
        """Get frequency of symptoms in the given date range"""
        pipeline = [
            {
                '$match': {
                    'user_id': ObjectId(user_id) if not isinstance(user_id, ObjectId) else user_id,
                    'date': {'$gte': start_date, '$lte': end_date}
                }
            },
            {'$unwind': '$symptoms'},
            {
                '$group': {
                    '_id': '$symptoms',
                    'count': {'$sum': 1},
                    'last_occurrence': {'$max': '$date'}
                }
            },
            {'$sort': {'count': -1}},
            {'$limit': 5}  # Top 5 most frequent symptoms
        ]
        
        return list(mongo.db['cycle_symptoms'].aggregate(pipeline))
    
    @classmethod
    def get_current_cycle(cls, user_id):
        return mongo.db[cls.COLLECTION].find_one(
            {'user_id': ObjectId(user_id) if not isinstance(user_id, ObjectId) else user_id},
            sort=[('start_date', -1)]
        )
    
    @classmethod
    def predict_next_period(cls, user_id):
        """Predict next period based on average cycle length"""
        cycles = cls.get_user_cycles(user_id, limit=6)
        if len(cycles) < 2:
            return None
            
        # Calculate average cycle length
        cycle_lengths = []
        for i in range(1, len(cycles)):
            if cycles[i-1].get('end_date') and cycles[i].get('start_date'):
                length = (cycles[i-1]['start_date'] - cycles[i]['start_date']).days
                if 20 <= length <= 45:  # Sanity check for cycle length
                    cycle_lengths.append(length)
        
        if not cycle_lengths:
            return None
            
        avg_cycle = sum(cycle_lengths) // len(cycle_lengths)
        last_cycle = cycles[0]
        return last_cycle['start_date'] + timedelta(days=avg_cycle)
    
    @classmethod
    def get_fertile_window(cls, user_id):
        """Predict fertile window (5 days before and including ovulation)
        
        Args:
            user_id: ID of the user
            
        Returns:
            tuple: (fertile_start_date, ovulation_date) or (None, None) if not enough data
        """
        next_period = cls.predict_next_period(user_id)
        if not next_period:
            return None, None
            
        # Calculate ovulation date (typically 14 days before next period)
        ovulation_day = next_period - timedelta(days=14)
        
        # Fertile window is typically 5 days before ovulation including ovulation day
        fertile_start = ovulation_day - timedelta(days=4)
        
        # Ensure the dates are timezone-naive for consistency
        if hasattr(fertile_start, 'tzinfo') and fertile_start.tzinfo is not None:
            fertile_start = fertile_start.replace(tzinfo=None)
        if hasattr(ovulation_day, 'tzinfo') and ovulation_day.tzinfo is not None:
            ovulation_day = ovulation_day.replace(tzinfo=None)
            
        return fertile_start, ovulation_day

    @staticmethod
    def get_current_phase(user_id):
        """Determine the current phase of the user's cycle."""
        today = datetime.utcnow()
        current_cycle = MenstrualCycle.get_current_cycle(user_id)

        # 1. Check if currently in period (Menstrual Phase)
        if current_cycle and current_cycle.get('start_date') and not current_cycle.get('end_date'):
            day_of_cycle = (today - current_cycle['start_date']).days + 1
            return 'Menstrual', day_of_cycle

        # 2. Use predictions for other phases
        stats = MenstrualCycle.get_cycle_statistics(user_id)
        if not stats or not stats.get('avg_cycle_length') or not stats.get('avg_period_length'):
            return 'Unknown', None # Not enough data

        last_cycle = MenstrualCycle.get_last_completed_cycle(user_id)
        if not last_cycle or not last_cycle.get('start_date'):
            return 'Unknown', None

        # Predict phases based on the start of the last cycle
        last_period_start = last_cycle['start_date']
        avg_cycle_len = stats['avg_cycle_length']
        avg_period_len = stats['avg_period_length']

        # Estimate current cycle start date
        estimated_current_cycle_start = last_period_start + timedelta(days=avg_cycle_len)
        # Adjust if today is before the estimated start (still in the previous cycle's luteal phase)
        if today < estimated_current_cycle_start:
            cycle_start_for_calc = last_period_start
        else:
            # This logic assumes a new cycle has started close to the average
            # A more robust solution might need to find the most recent start date
            num_cycles_since = (today - last_period_start).days // avg_cycle_len
            cycle_start_for_calc = last_period_start + timedelta(days=num_cycles_since * avg_cycle_len)

        day_of_cycle = (today - cycle_start_for_calc).days + 1

        # Determine phase based on day
        ovulation_day = round(avg_cycle_len / 2)
        follicular_end = ovulation_day - 3
        ovulatory_end = ovulation_day + 2

        if 1 <= day_of_cycle <= avg_period_len:
            return 'Menstrual', day_of_cycle # Should be caught by the first check, but as a fallback
        elif avg_period_len < day_of_cycle <= follicular_end:
            return 'Follicular', day_of_cycle
        elif follicular_end < day_of_cycle <= ovulatory_end:
            return 'Ovulatory', day_of_cycle
        elif ovulatory_end < day_of_cycle <= avg_cycle_len:
            return 'Luteal', day_of_cycle
        else:
            # We are likely in the next cycle, recalculate based on new estimated start
            new_cycle_start = cycle_start_for_calc + timedelta(days=avg_cycle_len)
            day_of_cycle = (today - new_cycle_start).days + 1
            return 'Menstrual', day_of_cycle # Assume new cycle starts with Menstrual phase

            
        # This return statement was a duplicate and used undefined variables
        # The method already returns a tuple of (phase, day_of_cycle) above
        pass

    @classmethod
    def analyze_notes_with_medbert(cls, notes):
        """Run MedBERT on notes and return embeddings (NER can be added later)"""
        outputs = medbert_infer(notes)
        # For now, just return pooled output
        return outputs.last_hidden_state.mean(dim=1).cpu().numpy().tolist()

    @classmethod
    def train_random_forest(cls, user_id):
        """Train a Random Forest model for cycle prediction for a user."""
        cycles = cls.get_user_cycles(user_id, limit=24)
        if len(cycles) < 6:
            return None
        # Example: Use previous cycle lengths to predict next
        X, y = [], []
        for i in range(2, len(cycles)):
            prev1 = (cycles[i-1]['start_date'] - cycles[i-2]['start_date']).days
            prev2 = (cycles[i]['start_date'] - cycles[i-1]['start_date']).days
            X.append([prev1])
            y.append(prev2)
        if not X or not y:
            return None
        model = RandomForestRegressor(n_estimators=100, random_state=42)
        model.fit(X, y)
        joblib.dump(model, f"rf_model_{user_id}.joblib")
        return model

    @classmethod
    def predict_future_cycles(cls, user_id, num_cycles=3):
        """Predict future cycles with all four phases using Random Forest."""
        model_path = f'./models/rf_cycle_model_{user_id}.joblib'
        try:
            model = joblib.load(model_path)
        except FileNotFoundError:
            # If no model, fall back to average-based prediction
            stats = cls.get_cycle_statistics(user_id)
            # If no stats, use default averages for new users
            if not stats or not stats.get('avg_cycle_length') or stats['avg_cycle_length'] < 1:
                stats = {'avg_cycle_length': 28, 'avg_period_length': 5}
            
            predictions = []
            last_cycle = cls.get_user_cycles(user_id, limit=1)
            if not last_cycle:
                return []

            last_start_date = last_cycle[0]['start_date']
            for i in range(num_cycles):
                start_date = last_start_date + timedelta(days=stats['avg_cycle_length'] * (i + 1))
                end_date = start_date + timedelta(days=stats['avg_period_length'])
                ovulation_date = start_date + timedelta(days=stats['avg_cycle_length'] / 2)
                predictions.append({
                    'menstrual_phase': (start_date, end_date),
                    'follicular_phase': (end_date + timedelta(days=1), ovulation_date - timedelta(days=1)),
                    'ovulatory_phase': (ovulation_date, ovulation_date + timedelta(days=1)),
                    'luteal_phase': (ovulation_date + timedelta(days=2), start_date + timedelta(days=stats['avg_cycle_length'] - 1))
                })
            CyclePrediction.store_calendar_predictions(user_id, predictions, model_used='average_based')
            return predictions

        # Use RF model for prediction
        cycles = cls.get_user_cycles(user_id, limit=10)
        if len(cycles) < 2:
            return []

        last_cycle = cycles[0]
        last_start_date = last_cycle['start_date']
        last_period_length = (last_cycle['end_date'] - last_start_date).days if last_cycle.get('end_date') else 5

        predictions = []
        for i in range(num_cycles):
            # Create features for prediction (e.g., last cycle length, last period length)
            # This should match the features used during training
            last_cycle_length = (cycles[0]['start_date'] - cycles[1]['start_date']).days if len(cycles) > 1 else 28
            features = np.array([[last_cycle_length, last_period_length]])
            
            predicted_length = int(model.predict(features)[0])
            
            start_date = last_start_date + timedelta(days=predicted_length)
            end_date = start_date + timedelta(days=last_period_length) # Assume period length is consistent
            ovulation_date = start_date + timedelta(days=predicted_length / 2)

            predictions.append({
                'menstrual_phase': (start_date, end_date),
                'follicular_phase': (end_date + timedelta(days=1), ovulation_date - timedelta(days=1)),
                'ovulatory_phase': (ovulation_date, ovulation_date + timedelta(days=1)),
                'luteal_phase': (ovulation_date + timedelta(days=2), start_date + timedelta(days=predicted_length - 1))
            })
            
            # Update for next iteration
            last_start_date = start_date
            cycles.insert(0, {'start_date': start_date, 'end_date': end_date})

        CyclePrediction.store_calendar_predictions(user_id, predictions, model_used='random_forest')
        return predictions

    @classmethod
    def predict_next_cycle_rf(cls, user_id):
        """Predict next cycle length using Random Forest."""
        try:
            model = joblib.load(f'./models/rf_cycle_model_{user_id}.joblib')
        except Exception:
            model = cls.train_random_forest(user_id)
            if model is None:
                return None
        cycles = cls.get_user_cycles(user_id, limit=3)
        if len(cycles) < 2:
            return None
        prev1 = (cycles[0]['start_date'] - cycles[1]['start_date']).days
        pred = model.predict(np.array([[prev1]]))[0]
        return int(round(pred))


class CycleSymptom:
    COMMON_SYMPTOMS = [
        'headache', 'cramps', 'bloating', 'fatigue', 'mood_swings',
        'acne', 'breast_tenderness', 'back_pain', 'food_cravings',
        'insomnia', 'nausea', 'dizziness', 'constipation', 'diarrhea'
    ]
    
    def __init__(self, data=None):
        if data:
            self.id = data.get('_id')
            self.user_id = data.get('user_id')
            self.cycle_id = data.get('cycle_id')
            self.date = data.get('date')
            self.symptoms = data.get('symptoms', [])
            self.mood = data.get('mood')
            self.pain_level = data.get('pain_level')
            self.notes = data.get('notes')
            self.severity = data.get('severity', 'mild')  # mild, moderate, severe
            self.emoji_rating = data.get('emoji_rating')  # emoji-based symptom rating
            self.voice_note_url = data.get('voice_note_url')  # for voice logging
            self.created_at = data.get('created_at', datetime.utcnow())
            self.updated_at = data.get('updated_at')
        self.updated_at = self.created_at

    @classmethod
    def get_symptoms_in_date_range(cls, user_id, start_date, end_date):
        """Get all symptoms for a user within a date range.
        
        Args:
            user_id: ID of the user
            start_date: Start date of the range (inclusive)
            end_date: End date of the range (inclusive)
            
        Returns:
            list: List of symptom documents with their details
        """
        # Ensure user_id is ObjectId
        user_id = ObjectId(user_id) if not isinstance(user_id, ObjectId) else user_id
        
        # Query symptoms within date range
        symptoms = list(mongo.db.cycle_symptoms.find({
            'user_id': user_id,
            'date': {
                '$gte': start_date,
                '$lte': end_date
            }
        }))
        
        return symptoms
    
    def save(self):
        try:
            # Ensure user_id and cycle_id are ObjectId
            user_id = ObjectId(self.user_id) if not isinstance(self.user_id, ObjectId) else self.user_id
            cycle_id = ObjectId(self.cycle_id) if self.cycle_id and not isinstance(self.cycle_id, ObjectId) else self.cycle_id
            
            # Prepare symptom data
            symptom_data = {
                'user_id': user_id,
                'cycle_id': cycle_id,
                'date': self.date,
                'symptoms': self.symptoms,
                'mood': self.mood,
                'pain_level': self.pain_level,
                'notes': self.notes,
                'severity': self.severity,
                'emoji_rating': self.emoji_rating,
                'voice_note_url': self.voice_note_url,
                'created_at': self.created_at,
                'updated_at': self.updated_at
            }
            
            # Insert the document
            result = mongo.db['cycle_symptoms'].insert_one(symptom_data)
            
            # Verify the insert was successful
            if not result.acknowledged:
                raise Exception("Database operation not acknowledged")
                
            # Update the instance with the new _id
            self.id = result.inserted_id
            
            return result
            
        except Exception as e:
            # Log the error for debugging
            import traceback
            print(f"Error saving cycle symptom: {str(e)}\n{traceback.format_exc()}")
            raise  # Re-raise the exception to be handled by the caller
    
    @staticmethod
    def create_indexes():
        mongo.db['cycle_symptoms'].create_index([('user_id', 1)])
        mongo.db['cycle_symptoms'].create_index([('cycle_id', 1)])
        mongo.db['cycle_symptoms'].create_index([('user_id', 1), ('date', -1)])

    @staticmethod
    def get_symptoms_in_date_range(user_id, start_date, end_date):
        """Get all symptoms logged within a date range"""
        return mongo.db['cycle_symptoms'].find({
            'user_id': ObjectId(user_id) if not isinstance(user_id, ObjectId) else user_id,
            'date': {
                '$gte': start_date,
                '$lte': end_date
            }
        }).sort('date', 1)
    
    @staticmethod
    def track_symptom(user_id, symptom_name, severity='mild', notes=''):
        """Track a specific symptom"""
        if symptom_name not in CycleSymptom.COMMON_SYMPTOMS:
            return False
            
        symptom_data = {
            'user_id': ObjectId(user_id) if not isinstance(user_id, ObjectId) else user_id,
            'symptom': symptom_name,
            'severity': severity,
            'notes': notes,
            'date': datetime.utcnow()
        }
        return mongo.db['cycle_symptoms'].insert_one(symptom_data)
    
    @staticmethod
    def get_symptom_history(user_id, symptom_name=None, limit=30):
        """Get symptom history for a user"""
        query = {'user_id': ObjectId(user_id) if not isinstance(user_id, ObjectId) else user_id}
        if symptom_name:
            query['symptom'] = symptom_name
            
        return list(mongo.db['cycle_symptoms'].find(query)
                   .sort('date', -1)
                   .limit(limit))
    
    @staticmethod
    def get_symptom_patterns(user_id, days=90):
        """Analyze symptom patterns for PMS and hormonal insights"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        symptoms = mongo.db.cycle_symptoms.find({
            'user_id': ObjectId(user_id),
            'date': {'$gte': cutoff_date}
        }).sort('date', 1)
        
        patterns = {
            'pms_indicators': [],
            'mood_trends': [],
            'pain_frequency': {},
            'symptom_correlation': {}
        }
        
        for symptom in symptoms:
            # Analyze PMS patterns (symptoms 1-7 days before period)
            cycles = MenstrualCycle.get_user_cycles(user_id)
            for cycle in cycles:
                if cycle.start_date:
                    days_before = (cycle.start_date - symptom['date']).days
                    if 1 <= days_before <= 7:
                        patterns['pms_indicators'].append({
                            'symptoms': symptom['symptoms'],
                            'mood': symptom['mood'],
                            'days_before_period': days_before
                        })
        
        return patterns
    
    @staticmethod
    def get_emoji_summary(user_id, days=30):
        """Get emoji-based symptom summary"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        symptoms = mongo.db.cycle_symptoms.find({
            'user_id': ObjectId(user_id),
            'date': {'$gte': cutoff_date},
            'emoji_rating': {'$exists': True}
        })
        
        emoji_counts = {}
        for symptom in symptoms:
            emoji = symptom.get('emoji_rating')
            if emoji:
                emoji_counts[emoji] = emoji_counts.get(emoji, 0) + 1
        
        return emoji_counts
