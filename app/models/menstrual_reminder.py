from datetime import datetime, timedelta
from bson import ObjectId
from app import mongo
from typing import List, Dict, Optional
import json

class MenstrualReminder:
    """Model for managing menstrual cycle reminders and notifications"""
    
    REMINDER_TYPES = [
        'period_start',
        'period_end', 
        'fertile_window',
        'ovulation',
        'medication',
        'appointment',
        'symptom_log',
        'health_checkup'
    ]
    
    NOTIFICATION_METHODS = ['email', 'sms', 'push', 'in_app']
    
    def __init__(self, data=None):
        if data:
            self.id = data.get('_id')
            self.user_id = data.get('user_id')
            self.reminder_type = data.get('reminder_type')
            self.title = data.get('title')
            self.message = data.get('message')
            self.scheduled_date = data.get('scheduled_date')
            # Set expiration to 24 hours after scheduled date by default
            self.expires_at = data.get('expires_at')
            if not self.expires_at and self.scheduled_date:
                self.expires_at = self.scheduled_date + timedelta(days=1)
            self.notification_methods = data.get('notification_methods', ['in_app'])
            self.is_recurring = data.get('is_recurring', False)
            self.recurrence_pattern = data.get('recurrence_pattern')  # daily, weekly, monthly
            self.is_active = data.get('is_active', True)
            self.is_sent = data.get('is_sent', False)
            self.sent_at = data.get('sent_at')
            self.metadata = data.get('metadata', {})  # Additional data like medication name, appointment details
            self.created_at = data.get('created_at', datetime.utcnow())
            self.updated_at = data.get('updated_at')

    def to_dict(self):
        """Convert reminder object to a dictionary"""
        return {
            'id': str(self.id) if self.id else None,
            'user_id': str(self.user_id),
            'reminder_type': self.reminder_type,
            'title': self.title,
            'message': self.message,
            'scheduled_date': self.scheduled_date.isoformat() if self.scheduled_date else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'notification_methods': self.notification_methods,
            'is_recurring': self.is_recurring,
            'recurrence_pattern': self.recurrence_pattern,
            'is_active': self.is_active,
            'is_sent': self.is_sent,
            'sent_at': self.sent_at.isoformat() if self.sent_at else None,
            'metadata': self.metadata,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def save(self):
        """Save reminder to database"""
        reminder_data = {
            'user_id': ObjectId(self.user_id) if not isinstance(self.user_id, ObjectId) else self.user_id,
            'reminder_type': self.reminder_type,
            'title': self.title,
            'message': self.message,
            'scheduled_date': self.scheduled_date,
            'notification_methods': self.notification_methods,
            'is_recurring': self.is_recurring,
            'recurrence_pattern': self.recurrence_pattern,
            'is_active': self.is_active,
            'is_sent': self.is_sent,
            'sent_at': self.sent_at,
            'metadata': self.metadata,
            'created_at': self.created_at,
            'updated_at': datetime.utcnow()
        }
        
        if self.id:
            return mongo.db.menstrual_reminders.update_one(
                {'_id': self.id}, 
                {'$set': reminder_data}
            )
        else:
            result = mongo.db.menstrual_reminders.insert_one(reminder_data)
            self.id = result.inserted_id
            return result
    
    @staticmethod
    def create_indexes():
        mongo.db.menstrual_reminders.create_index([('user_id', 1)])
        mongo.db.menstrual_reminders.create_index([('user_id', 1), ('scheduled_date', 1)])
        mongo.db.menstrual_reminders.create_index([('is_sent', 1), ('scheduled_date', 1)])
        mongo.db.menstrual_reminders.create_index([('expires_at', 1)])

    @staticmethod
    def create_period_reminders(user_id, next_period_date, days_before=[3, 1]):
        """Create automatic period start reminders"""
        reminders = []
        
        for days in days_before:
            reminder_date = next_period_date - timedelta(days=days)
            
            reminder = MenstrualReminder({
                'user_id': user_id,
                'reminder_type': 'period_start',
                'title': f'Period Starting in {days} Day{"s" if days > 1 else ""}',
                'message': f'Your period is expected to start in {days} day{"s" if days > 1 else ""}. Make sure you have supplies ready!',
                'scheduled_date': reminder_date,
                'notification_methods': ['email', 'in_app'],
                'is_recurring': False,
                'metadata': {'days_before': days, 'predicted_date': next_period_date}
            })
            
            reminder.save()
            reminders.append(reminder)
        
        return reminders
    
    @staticmethod
    def create_medication_reminder(user_id, medication_name, schedule_time, recurrence='daily'):
        """Create medication reminder"""
        reminder = MenstrualReminder({
            'user_id': user_id,
            'reminder_type': 'medication',
            'title': f'Take {medication_name}',
            'message': f'Time to take your {medication_name}',
            'scheduled_date': schedule_time,
            'notification_methods': ['push', 'in_app'],
            'is_recurring': True,
            'recurrence_pattern': recurrence,
            'metadata': {'medication_name': medication_name}
        })
        
        reminder.save()
        return reminder
    
    @staticmethod
    def create_appointment_reminder(user_id, appointment_type, appointment_date, doctor_name=None):
        """Create appointment reminder"""
        title = f'{appointment_type} Appointment'
        message = f'You have a {appointment_type.lower()} appointment'
        
        if doctor_name:
            message += f' with Dr. {doctor_name}'
        
        reminder = MenstrualReminder({
            'user_id': user_id,
            'reminder_type': 'appointment',
            'title': title,
            'message': message,
            'scheduled_date': appointment_date - timedelta(days=1),  # Remind 1 day before
            'notification_methods': ['email', 'sms', 'in_app'],
            'is_recurring': False,
            'metadata': {
                'appointment_type': appointment_type,
                'appointment_date': appointment_date,
                'doctor_name': doctor_name
            }
        })
        
        reminder.save()
        return reminder
    
    @staticmethod
    def find_by_id(reminder_id):
        """Find a reminder by its ID"""
        reminder_data = mongo.db.menstrual_reminders.find_one({'_id': ObjectId(reminder_id)})
        return MenstrualReminder(reminder_data) if reminder_data else None

    @staticmethod
    def get_user_reminders(user_id, active_only=True, limit=50, upcoming_only=False):
        """Get reminders for a user
        
        Args:
            user_id: ID of the user
            active_only: If True, only return active reminders
            limit: Maximum number of reminders to return
            upcoming_only: If True, only return future reminders that haven't expired
        """
        query = {'user_id': ObjectId(user_id)}
        if active_only:
            query['is_active'] = True
        
        now = datetime.utcnow()
        if upcoming_only:
            query['scheduled_date'] = {'$gte': now}
            # Only include reminders that haven't expired or don't have an expiration
            query['$or'] = [
                {'expires_at': {'$exists': False}},
                {'expires_at': None},
                {'expires_at': {'$gt': now}}
            ]
        
        reminders = mongo.db.menstrual_reminders.find(query).sort('scheduled_date', 1).limit(limit)
        return [MenstrualReminder(reminder) for reminder in reminders]
        
    @staticmethod
    def get_upcoming_reminders(user_id, limit=2):
        """Get the next upcoming reminders for a user"""
        return MenstrualReminder.get_user_reminders(
            user_id=user_id,
            active_only=True,
            upcoming_only=True,
            limit=limit
        )
    
    @staticmethod
    def get_pending_reminders(user_id):
        """Get pending reminders that need to be sent"""
        now = datetime.utcnow()
        query = {
            'user_id': ObjectId(user_id),
            'is_active': True,
            'is_sent': False,
            'scheduled_date': {'$lte': now}
        }
        
        reminders = mongo.db.menstrual_reminders.find(query).sort('scheduled_date', 1)
        return [MenstrualReminder(reminder) for reminder in reminders]
    
    @staticmethod
    def mark_as_sent(reminder_id):
        """Mark reminder as sent"""
        return mongo.db.menstrual_reminders.update_one(
            {'_id': ObjectId(reminder_id)},
            {
                '$set': {
                    'is_sent': True,
                    'sent_at': datetime.utcnow()
                }
            }
        )
    
    @staticmethod
    def deactivate_reminder(reminder_id, user_id):
        """Deactivate a reminder"""
        return mongo.db.menstrual_reminders.update_one(
            {'_id': ObjectId(reminder_id), 'user_id': ObjectId(user_id)},
            {'$set': {'is_active': False, 'updated_at': datetime.utcnow()}}
        )


class HealthReport:
    """Model for managing uploaded health reports and analysis"""
    
    REPORT_TYPES = [
        'gynecologist_report',
        'blood_test',
        'ultrasound',
        'hormone_test',
        'general_checkup',
        'prescription'
    ]
    
    def __init__(self, data=None):
        if data:
            self.id = data.get('_id')
            self.user_id = data.get('user_id')
            self.report_type = data.get('report_type')
            self.file_path = data.get('file_path')
            self.file_name = data.get('file_name')
            self.file_size = data.get('file_size')
            self.upload_date = data.get('upload_date', datetime.utcnow())
            self.extracted_text = data.get('extracted_text')  # OCR result
            self.ai_analysis = data.get('ai_analysis')  # MedBERT analysis
            self.key_findings = data.get('key_findings', [])
            self.recommendations = data.get('recommendations', [])
            self.is_processed = data.get('is_processed', False)
            self.processing_status = data.get('processing_status', 'pending')  # pending, processing, completed, failed
            self.metadata = data.get('metadata', {})
            self.created_at = data.get('created_at', datetime.utcnow())
    
    def save(self):
        """Save health report to database"""
        report_data = {
            'user_id': ObjectId(self.user_id) if not isinstance(self.user_id, ObjectId) else self.user_id,
            'report_type': self.report_type,
            'file_path': self.file_path,
            'file_name': self.file_name,
            'file_size': self.file_size,
            'upload_date': self.upload_date,
            'extracted_text': self.extracted_text,
            'ai_analysis': self.ai_analysis,
            'key_findings': self.key_findings,
            'recommendations': self.recommendations,
            'is_processed': self.is_processed,
            'processing_status': self.processing_status,
            'metadata': self.metadata,
            'created_at': self.created_at,
            'updated_at': datetime.utcnow()
        }
        
        if self.id:
            return mongo.db.health_reports.update_one(
                {'_id': self.id},
                {'$set': report_data}
            )
        else:
            result = mongo.db.health_reports.insert_one(report_data)
            self.id = result.inserted_id
            return result
    
    @staticmethod
    def create_indexes():
        mongo.db.health_reports.create_index([('user_id', 1)])
        mongo.db.health_reports.create_index([('processing_status', 1)])

    @staticmethod
    def get_user_reports(user_id, report_type=None, limit=20):
        """Get health reports for a user"""
        query = {'user_id': ObjectId(user_id)}
        if report_type:
            query['report_type'] = report_type
        
        reports = mongo.db.health_reports.find(query).sort('upload_date', -1).limit(limit)
        return [HealthReport(report) for report in reports]
    
    @staticmethod
    def get_pending_processing():
        """Get reports pending AI processing"""
        reports = mongo.db.health_reports.find({
            'processing_status': 'pending'
        }).sort('upload_date', 1)
        return [HealthReport(report) for report in reports]


class LifestyleRecommendation:
    """Model for cycle-based lifestyle recommendations"""
    
    RECOMMENDATION_TYPES = [
        'nutrition',
        'exercise',
        'mental_wellness',
        'sleep',
        'hydration',
        'supplements'
    ]
    
    CYCLE_PHASES = [
        'menstrual',      # Days 1-5
        'follicular',     # Days 1-13
        'ovulation',      # Days 13-15
        'luteal'          # Days 15-28
    ]
    
    def __init__(self, data=None):
        if data:
            self.id = data.get('_id')
            self.user_id = data.get('user_id')
            self.cycle_phase = data.get('cycle_phase')
            self.recommendation_type = data.get('recommendation_type')
            self.title = data.get('title')
            self.description = data.get('description')
            self.tips = data.get('tips', [])
            self.is_personalized = data.get('is_personalized', False)
            self.personalization_factors = data.get('personalization_factors', [])
            self.created_at = data.get('created_at', datetime.utcnow())
    
    @staticmethod
    def create_indexes():
        mongo.db.lifestyle_recommendations.create_index([('user_id', 1)])
        mongo.db.lifestyle_recommendations.create_index([('user_id', 1), ('cycle_phase', 1)])

    @staticmethod
    def get_recommendations_for_phase(user_id, cycle_phase, recommendation_type=None):
        """Get lifestyle recommendations for a specific cycle phase"""
        query = {
            'user_id': ObjectId(user_id),
            'cycle_phase': cycle_phase
        }
        
        if recommendation_type:
            query['recommendation_type'] = recommendation_type
        
        recommendations = mongo.db.lifestyle_recommendations.find(query)
        return [LifestyleRecommendation(rec) for rec in recommendations]
    
    @staticmethod
    def create_default_recommendations(user_id):
        """Create default lifestyle recommendations for all cycle phases"""
        default_recommendations = [
            # Menstrual Phase (Days 1-5)
            {
                'cycle_phase': 'menstrual',
                'recommendation_type': 'nutrition',
                'title': 'Iron-Rich Foods',
                'description': 'Focus on iron-rich foods to replenish what you lose during menstruation.',
                'tips': ['Eat leafy greens like spinach', 'Include lean red meat or lentils', 'Pair iron foods with vitamin C']
            },
            {
                'cycle_phase': 'menstrual',
                'recommendation_type': 'exercise',
                'title': 'Gentle Movement',
                'description': 'Light exercises can help reduce cramps and improve mood.',
                'tips': ['Try gentle yoga', 'Take walks', 'Avoid high-intensity workouts']
            },
            # Follicular Phase (Days 1-13)
            {
                'cycle_phase': 'follicular',
                'recommendation_type': 'exercise',
                'title': 'Build Strength',
                'description': 'Your energy is building - perfect time for strength training.',
                'tips': ['Try weight lifting', 'High-intensity workouts', 'Build new exercise habits']
            },
            # Ovulation Phase (Days 13-15)
            {
                'cycle_phase': 'ovulation',
                'recommendation_type': 'nutrition',
                'title': 'Anti-inflammatory Foods',
                'description': 'Support your body during ovulation with anti-inflammatory foods.',
                'tips': ['Eat berries and cherries', 'Include omega-3 rich fish', 'Add turmeric to meals']
            },
            # Luteal Phase (Days 15-28)
            {
                'cycle_phase': 'luteal',
                'recommendation_type': 'mental_wellness',
                'title': 'Stress Management',
                'description': 'PMS symptoms can be managed with stress reduction techniques.',
                'tips': ['Practice meditation', 'Try deep breathing exercises', 'Maintain regular sleep schedule']
            }
        ]
        
        for rec_data in default_recommendations:
            rec_data['user_id'] = user_id
            rec_data['is_personalized'] = False
            
            recommendation = LifestyleRecommendation(rec_data)
            mongo.db.lifestyle_recommendations.insert_one(rec_data)
        
        return len(default_recommendations)
