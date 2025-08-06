from flask import Blueprint, request, jsonify, render_template
from flask_jwt_extended import jwt_required, get_jwt_identity
from bson import ObjectId
from app.models.chat import ChatMessage

chat_bp = Blueprint('chat', __name__)

@chat_bp.route('', methods=['GET'])
@jwt_required()
def chat_page():
    return render_template('chat.html')

@chat_bp.route('/api/messages', methods=['POST'])
@jwt_required()
def send_message():
    user_id = get_jwt_identity()
    data = request.get_json()
    message = data.get('message')
    
    if not message:
        return jsonify({'error': 'Message is required'}), 400
    
    # Save user message
    ChatMessage.save_message(user_id, message, is_user=True)
    
    # Simple echo response for now - we'll enhance this later
    response = {
        'message': f"You said: {message}",
        'intent': 'echo'
    }
    
    # Save bot response
    ChatMessage.save_message(
        user_id, 
        response['message'], 
        is_user=False,
        intent=response.get('intent')
    )
    
    return jsonify(response)

@chat_bp.route('/api/messages', methods=['GET'])
@jwt_required()
def get_messages():
    user_id = get_jwt_identity()
    limit = int(request.args.get('limit', 50))
    
    messages = list(ChatMessage.get_collection().find(
        {'user_id': ObjectId(user_id)}
    ).sort('timestamp', -1).limit(limit))
    
    # Convert ObjectId to string for JSON serialization
    for msg in messages:
        msg['_id'] = str(msg['_id'])
        msg['user_id'] = str(msg['user_id'])
        if 'timestamp' in msg and isinstance(msg['timestamp'], datetime):
            msg['timestamp'] = msg['timestamp'].isoformat()
    
    return jsonify(messages[::-1])  # Return in chronological order
