from app.extensions import mongo, bcrypt, login_manager
from flask_login import UserMixin
from bson.objectid import ObjectId

@login_manager.user_loader
def load_user(user_id):
    user_json = mongo.db.users.find_one({'_id': ObjectId(user_id)})
    if user_json:
        return User(user_json)
    return None

class User(UserMixin):
    def __init__(self, user_json):
        self.user_json = user_json
        self.id = str(user_json['_id'])
        self.email = user_json['email']
        self.name = user_json['name']
        self.password = user_json.get('password')

    def get_age(self):
        """Calculate age from date_of_birth."""
        from datetime import datetime
        dob_str = self.user_json.get('healthProfile', {}).get('date_of_birth')
        if not dob_str:
            return 30  # Return a default age if not set
        try:
            dob = datetime.strptime(dob_str, '%Y-%m-%d')
            today = datetime.utcnow()
            age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
            return age
        except (ValueError, TypeError):
            return 30 # Return default age on parsing error

    def update_profile(self, profile_data):
        """Update the user's health profile."""
        mongo.db.users.update_one(
            {'_id': ObjectId(self.id)},
            {'$set': {'healthProfile': profile_data}}
        )

    def check_password(self, password):
        # Users who signed up with Google won't have a password
        if not self.password:
            return False
        return bcrypt.check_password_hash(self.password, password)

    @staticmethod
    def create_user(name, email, password=None):
        user_data = {
            'name': name,
            'email': email
        }
        if password:
            hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
            user_data['password'] = hashed_password
        user_data["healthProfile"] = {}
        return mongo.db.users.insert_one(user_data)

    @staticmethod
    def get_by_id(user_id):
        """Find a user by their ID."""
        try:
            user_json = mongo.db.users.find_one({'_id': ObjectId(user_id)})
            if user_json:
                return User(user_json)
        except Exception as e:
            # Log the exception, e.g., for invalid ObjectId format
            print(f"Error finding user by ID {user_id}: {e}")
        return None

    @staticmethod
    def find_user_by_email(email):
        """Find a user by their email address."""
        return mongo.db.users.find_one({"email": email})
        
    @classmethod
    def create_indexes(cls):
        """Create database indexes for the users collection."""
        mongo.db.users.create_index("email", unique=True)
        print("Created indexes for users collection")
        
    @staticmethod
    def hash_password(password):
        """Hash a password for storing in the database."""
        return bcrypt.generate_password_hash(password).decode('utf-8')
