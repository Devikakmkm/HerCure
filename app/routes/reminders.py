from flask import Blueprint, request, jsonify, current_app
from bson import ObjectId
from datetime import datetime, timedelta
from app.extensions import mongo
from flask_login import current_user, login_required
import json

def init_reminders_collection():
    """Initialize the reminders collection with proper indexes"""
    if 'reminders' not in mongo.db.list_collection_names():
        current_app.logger.info("Creating 'reminders' collection")
        mongo.db.create_collection('reminders')
    
    # Create indexes
    mongo.db.reminders.create_index([('user_id', 1)])
    mongo.db.reminders.create_index([('scheduled_date', 1)])
    mongo.db.reminders.create_index([('is_completed', 1)])
    current_app.logger.info("Reminders collection initialized with indexes")

reminder_bp = Blueprint('reminders', __name__)

@reminder_bp.route('/api/reminders', methods=['GET'])
@login_required
def get_reminders():
    """Get all upcoming reminders for the current user"""
    try:
        # Get query parameters
        show_completed = request.args.get('show_completed', 'false').lower() == 'true'
        
        # Build query
        query = {'user_id': str(current_user.id)}
        if not show_completed:
            query['is_completed'] = False
        
        # Get reminders from database
        reminders = list(mongo.db.reminders.find(query)
                         .sort('scheduled_date', 1)  # Sort by date ascending
                         .limit(10))  # Limit to 10 reminders
        
        # Convert ObjectId to string for JSON serialization
        for reminder in reminders:
            reminder['_id'] = str(reminder['_id'])
            # Convert datetime to ISO format for the frontend
            if 'scheduled_date' in reminder and reminder['scheduled_date']:
                reminder['scheduled_date'] = reminder['scheduled_date'].isoformat()
        
        return jsonify({
            'status': 'success',
            'reminders': reminders
        })
    except Exception as e:
        current_app.logger.error(f"Error fetching reminders: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Failed to fetch reminders'
        }), 500

@reminder_bp.route('/api/reminders', methods=['POST', 'OPTIONS'])
@login_required
def create_reminder():
    """Create a new reminder"""
    if request.method == 'OPTIONS':
        # Handle preflight request
        response = current_app.make_response()
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type, X-Requested-With')
        response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
        return response

    try:
        current_app.logger.info(f"Received request to create reminder: {request.data}")
        
        # Ensure we have JSON data
        if not request.is_json:
            current_app.logger.error("Request must be JSON")
            return jsonify({
                'status': 'error',
                'message': 'Request must be JSON'
            }), 400
            
        data = request.get_json()
        current_app.logger.info(f"Parsed JSON data: {data}")
        
        # Validate required fields
        if not data or not data.get('title') or not data.get('scheduled_date'):
            current_app.logger.error("Missing required fields in create reminder request")
            return jsonify({
                'status': 'error',
                'message': 'Title and scheduled date are required',
                'received_data': str(data)[:500]  # Log first 500 chars to help with debugging
            }), 400
        
        # Create reminder document
        try:
            scheduled_date = datetime.fromisoformat(data['scheduled_date'].replace('Z', '+00:00'))
        except ValueError as ve:
            current_app.logger.error(f"Invalid date format: {data['scheduled_date']} - {str(ve)}")
            return jsonify({
                'status': 'error',
                'message': f'Invalid date format. Please use ISO format (e.g., 2023-01-01T12:00:00)'
            }), 400
            
        reminder = {
            'user_id': str(current_user.id),
            'title': data['title'],
            'message': data.get('message', ''),
            'scheduled_date': scheduled_date,
            'is_completed': False,
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }
        
        current_app.logger.info(f"Inserting reminder into database: {reminder}")
        
        try:
            # Ensure the collection exists and has the right indexes
            if 'reminders' not in mongo.db.list_collection_names():
                current_app.logger.info("Creating 'reminders' collection")
                mongo.db.create_collection('reminders')
            
            # Insert into database
            result = mongo.db.reminders.insert_one(reminder)
            current_app.logger.info(f"Inserted reminder with ID: {result.inserted_id}")
            
            response = jsonify({
                'status': 'success',
                'message': 'Reminder created successfully',
                'reminder_id': str(result.inserted_id)
            })
            
            # Add CORS headers
            response.headers.add('Access-Control-Allow-Origin', '*')
            response.headers.add('Content-Type', 'application/json')
            
            return response, 201
            
        except Exception as db_error:
            current_app.logger.error(f"Database error: {str(db_error)}")
            return jsonify({
                'status': 'error',
                'message': 'Database error while creating reminder',
                'error': str(db_error)
            }), 500
            
    except Exception as e:
        current_app.logger.error(f"Unexpected error in create_reminder: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': 'An unexpected error occurred',
            'error': str(e)
        }), 500

@reminder_bp.route('/api/reminders/<reminder_id>', methods=['DELETE'])
@login_required
def delete_reminder(reminder_id):
    """Delete a reminder"""
    try:
        # Verify the reminder exists and belongs to the user
        result = mongo.db.reminders.delete_one({
            '_id': ObjectId(reminder_id),
            'user_id': str(current_user.id)
        })
        
        if result.deleted_count == 0:
            return jsonify({
                'status': 'error',
                'message': 'Reminder not found or access denied'
            }), 404
            
        return jsonify({
            'status': 'success',
            'message': 'Reminder deleted successfully'
        })
        
    except Exception as e:
        current_app.logger.error(f"Error deleting reminder: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Failed to delete reminder'
        }), 500

@reminder_bp.route('/api/reminders/check', methods=['GET'])
@login_required
def check_reminders():
    """Check for due reminders and return them"""
    try:
        now = datetime.utcnow()
        
        # Find reminders that are due and not completed
        due_reminders = list(mongo.db.reminders.find({
            'user_id': str(current_user.id),
            'scheduled_date': {'$lte': now},
            'is_completed': False
        }))
        
        # Mark reminders as completed
        if due_reminders:
            reminder_ids = [ObjectId(r['_id']) for r in due_reminders]
            mongo.db.reminders.update_many(
                {'_id': {'$in': reminder_ids}},
                {'$set': {'is_completed': True, 'completed_at': now}}
            )
        
        # Format response
        for reminder in due_reminders:
            reminder['_id'] = str(reminder['_id'])
            if 'scheduled_date' in reminder and reminder['scheduled_date']:
                reminder['scheduled_date'] = reminder['scheduled_date'].isoformat()
        
        return jsonify({
            'status': 'success',
            'due_reminders': due_reminders
        })
        
    except Exception as e:
        current_app.logger.error(f"Error checking reminders: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Failed to check reminders'
        }), 500
