from datetime import datetime
from bson import ObjectId
from app import mongo

class ChatMessage:
    @staticmethod
    def get_collection():
        return mongo.db.chat_messages

    @staticmethod
    def create_indexes():
        ChatMessage.get_collection().create_index([
            ('user_id', 1),
            ('timestamp', -1)
        ])

    @classmethod
    def save_message(cls, user_id, message, is_user=True, **kwargs):
        msg = {
            'user_id': ObjectId(user_id),
            'message': message,
            'is_user': is_user,
            'timestamp': datetime.utcnow(),
            'metadata': kwargs.get('metadata', {})
        }
        if 'intent' in kwargs:
            msg['intent'] = kwargs['intent']
        return cls.get_collection().insert_one(msg)
