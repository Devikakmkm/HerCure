from datetime import datetime, timedelta
from bson import ObjectId
from app import mongo
from typing import List, Dict, Optional
import json

class MenstrualProfile:
    """Model for managing multiple menstrual tracking profiles per user"""
    
    def __init__(self, data=None):
        if data:
            self.id = data.get('_id')
            self.user_id = data.get('user_id')  # Main account holder
            self.profile_name = data.get('profile_name')
            self.relationship = data.get('relationship')  # self, daughter, sister, friend
            self.age = data.get('age')
            self.date_of_birth = data.get('date_of_birth')
            self.is_primary = data.get('is_primary', False)
            self.privacy_settings = data.get('privacy_settings', {})
            self.notification_preferences = data.get('notification_preferences', {})
            self.cycle_preferences = data.get('cycle_preferences', {})
            self.is_active = data.get('is_active', True)
            self.created_at = data.get('created_at', datetime.utcnow())
            self.updated_at = data.get('updated_at')
    
    def save(self):
        """Save profile to database"""
        profile_data = {
            'user_id': ObjectId(self.user_id) if not isinstance(self.user_id, ObjectId) else self.user_id,
            'profile_name': self.profile_name,
            'relationship': self.relationship,
            'age': self.age,
            'date_of_birth': self.date_of_birth,
            'is_primary': self.is_primary,
            'privacy_settings': self.privacy_settings,
            'notification_preferences': self.notification_preferences,
            'cycle_preferences': self.cycle_preferences,
            'is_active': self.is_active,
            'created_at': self.created_at,
            'updated_at': datetime.utcnow()
        }
        
        if self.id:
            return mongo.db.menstrual_profiles.update_one(
                {'_id': self.id},
                {'$set': profile_data}
            )
        else:
            result = mongo.db.menstrual_profiles.insert_one(profile_data)
            self.id = result.inserted_id
            return result
    
    @staticmethod
    def create_indexes():
        mongo.db.menstrual_profiles.create_index([('user_id', 1)])
        mongo.db.menstrual_profiles.create_index([('user_id', 1), ('is_primary', -1)])

    @staticmethod
    def get_user_profiles(user_id, active_only=True):
        """Get all profiles for a user"""
        query = {'user_id': ObjectId(user_id)}
        if active_only:
            query['is_active'] = True
        
        profiles = mongo.db.menstrual_profiles.find(query).sort('is_primary', -1)
        return [MenstrualProfile(profile) for profile in profiles]
    
    @staticmethod
    def get_primary_profile(user_id):
        """Get the primary profile for a user"""
        profile = mongo.db.menstrual_profiles.find_one({
            'user_id': ObjectId(user_id),
            'is_primary': True,
            'is_active': True
        })
        return MenstrualProfile(profile) if profile else None
    
    @staticmethod
    def create_primary_profile(user_id, profile_name, age=None):
        """Create primary profile for a new user"""
        profile = MenstrualProfile({
            'user_id': user_id,
            'profile_name': profile_name,
            'relationship': 'self',
            'age': age,
            'is_primary': True,
            'privacy_settings': {
                'data_encryption': True,
                'share_with_doctor': False,
                'anonymous_analytics': True
            },
            'notification_preferences': {
                'period_reminders': True,
                'fertile_window': True,
                'symptom_logging': True,
                'medication_reminders': True
            },
            'cycle_preferences': {
                'average_cycle_length': 28,
                'average_period_length': 5,
                'tracking_start_date': datetime.utcnow()
            }
        })
        
        profile.save()
        return profile


class VoiceLog:
    """Model for managing voice-based menstrual logging"""
    
    def __init__(self, data=None):
        if data:
            self.id = data.get('_id')
            self.user_id = data.get('user_id')
            self.profile_id = data.get('profile_id')
            self.audio_file_path = data.get('audio_file_path')
            self.transcription = data.get('transcription')
            self.processed_data = data.get('processed_data', {})  # Extracted cycle/symptom data
            self.confidence_score = data.get('confidence_score', 0.0)
            self.processing_status = data.get('processing_status', 'pending')  # pending, processing, completed, failed
            self.created_cycle_entry = data.get('created_cycle_entry')  # ID of created cycle entry
            self.created_symptom_entries = data.get('created_symptom_entries', [])  # IDs of created symptom entries
            self.created_at = data.get('created_at', datetime.utcnow())
            self.processed_at = data.get('processed_at')
    
    def save(self):
        """Save voice log to database"""
        voice_data = {
            'user_id': ObjectId(self.user_id) if not isinstance(self.user_id, ObjectId) else self.user_id,
            'profile_id': ObjectId(self.profile_id) if self.profile_id and not isinstance(self.profile_id, ObjectId) else self.profile_id,
            'audio_file_path': self.audio_file_path,
            'transcription': self.transcription,
            'processed_data': self.processed_data,
            'confidence_score': self.confidence_score,
            'processing_status': self.processing_status,
            'created_cycle_entry': self.created_cycle_entry,
            'created_symptom_entries': self.created_symptom_entries,
            'created_at': self.created_at,
            'processed_at': self.processed_at,
            'updated_at': datetime.utcnow()
        }
        
        if self.id:
            return mongo.db.voice_logs.update_one(
                {'_id': self.id},
                {'$set': voice_data}
            )
        else:
            result = mongo.db.voice_logs.insert_one(voice_data)
            self.id = result.inserted_id
            return result
    
    @staticmethod
    def create_indexes():
        mongo.db.voice_logs.create_index([('user_id', 1)])
        mongo.db.voice_logs.create_index([('status', 1)])

    @staticmethod
    def get_user_voice_logs(user_id, limit=20):
        """Get voice logs for a user"""
        logs = mongo.db.voice_logs.find({
            'user_id': ObjectId(user_id)
        }).sort('created_at', -1).limit(limit)
        return [VoiceLog(log) for log in logs]
    
    @staticmethod
    def get_pending_processing():
        """Get voice logs pending processing"""
        logs = mongo.db.voice_logs.find({
            'processing_status': 'pending'
        }).sort('created_at', 1)
        return [VoiceLog(log) for log in logs]
    
    @staticmethod
    def process_voice_command(transcription):
        """Process voice transcription to extract menstrual data"""
        # This would integrate with NLP models to extract:
        # - Period start/end dates
        # - Symptoms mentioned
        # - Pain levels
        # - Mood indicators
        
        processed_data = {
            'intent': None,
            'entities': {},
            'confidence': 0.0
        }
        
        # Simple keyword extraction (would be replaced with proper NLP)
        text = transcription.lower()
        
        # Period tracking intents
        if any(word in text for word in ['period started', 'menstruation began', 'cycle started']):
            processed_data['intent'] = 'log_period_start'
            processed_data['confidence'] = 0.8
        elif any(word in text for word in ['period ended', 'menstruation finished', 'cycle ended']):
            processed_data['intent'] = 'log_period_end'
            processed_data['confidence'] = 0.8
        
        # Symptom tracking
        symptoms = []
        symptom_keywords = {
            'cramps': ['cramps', 'cramping', 'pain'],
            'headache': ['headache', 'head pain', 'migraine'],
            'mood_swings': ['moody', 'irritable', 'emotional'],
            'bloating': ['bloated', 'bloating', 'swollen'],
            'fatigue': ['tired', 'exhausted', 'fatigue']
        }
        
        for symptom, keywords in symptom_keywords.items():
            if any(keyword in text for keyword in keywords):
                symptoms.append(symptom)
        
        if symptoms:
            processed_data['entities']['symptoms'] = symptoms
            if not processed_data['intent']:
                processed_data['intent'] = 'log_symptoms'
                processed_data['confidence'] = 0.7
        
        # Pain level extraction
        if 'severe pain' in text or 'intense pain' in text:
            processed_data['entities']['pain_level'] = 'severe'
        elif 'mild pain' in text or 'light pain' in text:
            processed_data['entities']['pain_level'] = 'mild'
        elif 'moderate pain' in text:
            processed_data['entities']['pain_level'] = 'moderate'
        
        return processed_data


class DataExport:
    """Model for managing data exports and privacy features"""
    
    EXPORT_FORMATS = ['pdf', 'csv', 'json']
    EXPORT_TYPES = ['full_data', 'cycle_history', 'symptom_history', 'analytics_report']
    
    def __init__(self, data=None):
        if data:
            self.id = data.get('_id')
            self.user_id = data.get('user_id')
            self.profile_id = data.get('profile_id')
            self.export_type = data.get('export_type')
            self.export_format = data.get('export_format')
            self.date_range = data.get('date_range', {})
            self.file_path = data.get('file_path')
            self.file_size = data.get('file_size')
            self.password_protected = data.get('password_protected', False)
            self.download_count = data.get('download_count', 0)
            self.expires_at = data.get('expires_at')
            self.status = data.get('status', 'pending')  # pending, processing, completed, failed
            self.created_at = data.get('created_at', datetime.utcnow())
            self.completed_at = data.get('completed_at')
    
    def save(self):
        """Save export request to database"""
        export_data = {
            'user_id': ObjectId(self.user_id) if not isinstance(self.user_id, ObjectId) else self.user_id,
            'profile_id': ObjectId(self.profile_id) if self.profile_id and not isinstance(self.profile_id, ObjectId) else self.profile_id,
            'export_type': self.export_type,
            'export_format': self.export_format,
            'date_range': self.date_range,
            'file_path': self.file_path,
            'file_size': self.file_size,
            'password_protected': self.password_protected,
            'download_count': self.download_count,
            'expires_at': self.expires_at,
            'status': self.status,
            'created_at': self.created_at,
            'completed_at': self.completed_at,
            'updated_at': datetime.utcnow()
        }
        
        if self.id:
            return mongo.db.data_exports.update_one(
                {'_id': self.id},
                {'$set': export_data}
            )
        else:
            result = mongo.db.data_exports.insert_one(export_data)
            self.id = result.inserted_id
            return result
    
    @staticmethod
    def create_indexes():
        mongo.db.data_exports.create_index([('user_id', 1)])
        mongo.db.data_exports.create_index([('expires_at', 1)])

    @staticmethod
    def create_export_request(user_id, export_type, export_format, date_range=None, password_protected=False):
        """Create a new data export request"""
        expires_at = datetime.utcnow() + timedelta(days=7)  # Exports expire after 7 days
        
        export = DataExport({
            'user_id': user_id,
            'export_type': export_type,
            'export_format': export_format,
            'date_range': date_range or {},
            'password_protected': password_protected,
            'expires_at': expires_at
        })
        
        export.save()
        return export
    
    @staticmethod
    def get_user_exports(user_id, active_only=True):
        """Get export history for a user"""
        query = {'user_id': ObjectId(user_id)}
        if active_only:
            query['expires_at'] = {'$gt': datetime.utcnow()}
        
        exports = mongo.db.data_exports.find(query).sort('created_at', -1)
        return [DataExport(export) for export in exports]
    
    @staticmethod
    def cleanup_expired_exports():
        """Remove expired export files"""
        expired_exports = mongo.db.data_exports.find({
            'expires_at': {'$lt': datetime.utcnow()},
            'status': 'completed'
        })
        
        # This would also delete the actual files from storage
        return mongo.db.data_exports.delete_many({
            'expires_at': {'$lt': datetime.utcnow()}
        })

