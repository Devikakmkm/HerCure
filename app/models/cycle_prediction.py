from datetime import datetime, timedelta
from bson.objectid import ObjectId
from app import mongo
import joblib
import numpy as np

class CyclePrediction:
    """Model for storing ML-generated cycle predictions and analytics data"""
    
    def __init__(self, data=None):
        if data:
            self.id = data.get('_id')
            self.user_id = data.get('user_id')
            self.prediction_type = data.get('prediction_type')  # 'calendar', 'next_period', 'fertile_window'
            self.prediction_date = data.get('prediction_date')
            self.predicted_for_date = data.get('predicted_for_date')
            self.phase = data.get('phase')  # 'menstrual', 'follicular', 'ovulatory', 'luteal'
            self.start_date = data.get('start_date')
            self.end_date = data.get('end_date')
            self.confidence_score = data.get('confidence_score', 0.0)
            self.model_used = data.get('model_used')  # 'random_forest', 'average_based', 'default'
            self.features_used = data.get('features_used', {})
            self.is_active = data.get('is_active', True)
            self.created_at = data.get('created_at', datetime.utcnow())
            self.updated_at = data.get('updated_at')

    def save(self):
        """Save prediction to database"""
        prediction_data = {
            'user_id': ObjectId(self.user_id) if not isinstance(self.user_id, ObjectId) else self.user_id,
            'prediction_type': self.prediction_type,
            'prediction_date': self.prediction_date,
            'predicted_for_date': self.predicted_for_date,
            'phase': self.phase,
            'start_date': self.start_date,
            'end_date': self.end_date,
            'confidence_score': self.confidence_score,
            'model_used': self.model_used,
            'features_used': self.features_used,
            'is_active': self.is_active,
            'created_at': self.created_at,
            'updated_at': datetime.utcnow()
        }
        
        if self.id:
            return mongo.db.cycle_predictions.update_one(
                {'_id': self.id},
                {'$set': prediction_data}
            )
        else:
            result = mongo.db.cycle_predictions.insert_one(prediction_data)
            self.id = result.inserted_id
            return result

    @staticmethod
    def create_indexes():
        """Create database indexes for efficient querying"""
        mongo.db.cycle_predictions.create_index([('user_id', 1)])
        mongo.db.cycle_predictions.create_index([('user_id', 1), ('prediction_type', 1)])
        mongo.db.cycle_predictions.create_index([('user_id', 1), ('predicted_for_date', 1)])
        mongo.db.cycle_predictions.create_index([('user_id', 1), ('is_active', 1)])

    @staticmethod
    def get_user_predictions(user_id, prediction_type=None, start_date=None, end_date=None, limit=None):
        """Get predictions for a user with optional filters"""
        query = {
            'user_id': ObjectId(user_id),
            'is_active': True
        }
        
        if prediction_type:
            query['prediction_type'] = prediction_type
            
        if start_date and end_date:
            query['predicted_for_date'] = {
                '$gte': start_date,
                '$lte': end_date
            }
        
        cursor = mongo.db.cycle_predictions.find(query).sort('predicted_for_date', 1)
        
        if limit:
            cursor = cursor.limit(limit)
            
        return list(cursor)

    @staticmethod
    def get_calendar_predictions(user_id, year, month):
        """Get calendar predictions for a specific month"""
        from calendar import monthrange
        _, num_days = monthrange(year, month)
        start_date = datetime(year, month, 1)
        end_date = datetime(year, month, num_days)
        
        return CyclePrediction.get_user_predictions(
            user_id=user_id,
            prediction_type='calendar',
            start_date=start_date,
            end_date=end_date
        )

    @staticmethod
    def clear_old_predictions(user_id, prediction_type=None, days_old=30):
        """Clear old predictions to keep database clean"""
        cutoff_date = datetime.utcnow() - timedelta(days=days_old)
        query = {
            'user_id': ObjectId(user_id),
            'created_at': {'$lt': cutoff_date}
        }
        
        if prediction_type:
            query['prediction_type'] = prediction_type
            
        return mongo.db.cycle_predictions.delete_many(query)

    @staticmethod
    def store_calendar_predictions(user_id, predictions, model_used='random_forest'):
        """Store calendar predictions in bulk"""
        prediction_date = datetime.utcnow()
        
        # Clear existing calendar predictions for the same period
        CyclePrediction.clear_old_predictions(user_id, 'calendar', days_old=1)
        
        stored_predictions = []
        for prediction in predictions:
            for phase_name, (start_date, end_date) in prediction.items():
                phase = phase_name.replace('_phase', '')
                
                pred = CyclePrediction({
                    'user_id': user_id,
                    'prediction_type': 'calendar',
                    'prediction_date': prediction_date,
                    'predicted_for_date': start_date,
                    'phase': phase,
                    'start_date': start_date,
                    'end_date': end_date,
                    'model_used': model_used,
                    'confidence_score': 0.8 if model_used == 'random_forest' else 0.6
                })
                pred.save()
                stored_predictions.append(pred)
                
        return stored_predictions

class CycleAnalytics:
    """Model for storing cycle analytics and health insights"""
    
    def __init__(self, data=None):
        if data:
            self.id = data.get('_id')
            self.user_id = data.get('user_id')
            self.analysis_type = data.get('analysis_type')  # 'regularity', 'abnormality', 'health_score', 'medbert'
            self.analysis_date = data.get('analysis_date')
            self.data_period_start = data.get('data_period_start')
            self.data_period_end = data.get('data_period_end')
            self.results = data.get('results', {})
            self.confidence_score = data.get('confidence_score', 0.0)
            self.model_used = data.get('model_used')
            self.created_at = data.get('created_at', datetime.utcnow())

    def save(self):
        """Save analytics to database"""
        analytics_data = {
            'user_id': ObjectId(self.user_id) if not isinstance(self.user_id, ObjectId) else self.user_id,
            'analysis_type': self.analysis_type,
            'analysis_date': self.analysis_date,
            'data_period_start': self.data_period_start,
            'data_period_end': self.data_period_end,
            'results': self.results,
            'confidence_score': self.confidence_score,
            'model_used': self.model_used,
            'created_at': self.created_at
        }
        
        if self.id:
            return mongo.db.cycle_analytics.update_one(
                {'_id': self.id},
                {'$set': analytics_data}
            )
        else:
            result = mongo.db.cycle_analytics.insert_one(analytics_data)
            self.id = result.inserted_id
            return result

    @staticmethod
    def create_indexes():
        """Create database indexes for efficient querying"""
        mongo.db.cycle_analytics.create_index([('user_id', 1)])
        mongo.db.cycle_analytics.create_index([('user_id', 1), ('analysis_type', 1)])
        mongo.db.cycle_analytics.create_index([('analysis_date', -1)])

    @staticmethod
    def get_latest_analytics(user_id, analysis_type=None, limit=10):
        """Get latest analytics for a user"""
        query = {'user_id': ObjectId(user_id)}
        
        if analysis_type:
            query['analysis_type'] = analysis_type
            
        return list(mongo.db.cycle_analytics.find(query)
                   .sort('analysis_date', -1)
                   .limit(limit))

    @staticmethod
    def store_medbert_analysis(user_id, analysis_results, data_period_start, data_period_end):
        """Store MedBERT analysis results"""
        analytics = CycleAnalytics({
            'user_id': user_id,
            'analysis_type': 'medbert',
            'analysis_date': datetime.utcnow(),
            'data_period_start': data_period_start,
            'data_period_end': data_period_end,
            'results': analysis_results,
            'model_used': 'medbert',
            'confidence_score': 0.9
        })
        analytics.save()
        return analytics
