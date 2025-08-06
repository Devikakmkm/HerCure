from app import mongo
from bson.objectid import ObjectId
from datetime import datetime

class Post:
    """Post model for community forum"""
    def __init__(self, data):
        self.id = str(data.get('_id')) if data.get('_id') else None
        self.user_id = data.get('user_id')
        self.author_username = data.get('author_username') # Denormalized for performance
        self.title = data.get('title')
        self.content = data.get('content')
        self.category_slug = data.get('category_slug')
        self.tags = data.get('tags', [])
        self.created_at = data.get('created_at', datetime.utcnow())
        self.updated_at = data.get('updated_at', datetime.utcnow())
        self.comment_count = data.get('comment_count', 0)

    def save(self):
        """Save or update a post"""
        collection = mongo.db.posts
        data = self.__dict__
        if self.id:
            data['updated_at'] = datetime.utcnow()
            collection.update_one({'_id': ObjectId(self.id)}, {'$set': data})
        else:
            result = collection.insert_one(data)
            self.id = str(result.inserted_id)

    def to_dict(self):
        """Convert post object to a dictionary"""
        return self.__dict__

    @staticmethod
    def find_by_id(post_id):
        """Find a post by its ID"""
        data = mongo.db.posts.find_one({'_id': ObjectId(post_id)})
        return Post(data) if data else None

    @staticmethod
    def get_all_posts(page=1, per_page=10):
        """Get all posts with pagination"""
        skip = (page - 1) * per_page
        posts_cursor = mongo.db.posts.find().sort('created_at', -1).skip(skip).limit(per_page)
        return [Post(post_data) for post_data in posts_cursor]

    @staticmethod
    def get_recent_posts(limit=5):
        """Get the most recent posts"""
        posts_cursor = mongo.db.posts.find().sort('created_at', -1).limit(limit)
        return [Post(post_data) for post_data in posts_cursor]

    @staticmethod
    def create_indexes():
        """Create indexes for the posts collection"""
        collection = mongo.db.posts
        collection.create_index('user_id')
        collection.create_index('category_slug')
        collection.create_index('created_at')

class Comment:
    """Comment model for posts"""
    def __init__(self, data):
        self.id = str(data.get('_id')) if data.get('_id') else None
        self.post_id = data.get('post_id')
        self.user_id = data.get('user_id')
        self.author_username = data.get('author_username')
        self.content = data.get('content')
        self.created_at = data.get('created_at', datetime.utcnow())

    def save(self):
        """Save a new comment"""
        collection = mongo.db.comments
        result = collection.insert_one(self.__dict__)
        self.id = str(result.inserted_id)
        # Increment comment count on the post
        mongo.db.posts.update_one({'_id': ObjectId(self.post_id)}, {'$inc': {'comment_count': 1}})

    @staticmethod
    def get_for_post(post_id):
        """Get all comments for a specific post"""
        comments_cursor = mongo.db.comments.find({'post_id': post_id}).sort('created_at', 1)
        return [Comment(comment_data) for comment_data in comments_cursor]

    @staticmethod
    def create_indexes():
        """Create indexes for the comments collection"""
        collection = mongo.db.comments
        collection.create_index('post_id')
        collection.create_index('user_id')

class Category:
    """Category model for posts"""
    def __init__(self, data):
        self.id = str(data.get('_id')) if data.get('_id') else None
        self.name = data.get('name')
        self.slug = data.get('slug')
        self.description = data.get('description')

    @staticmethod
    def get_all():
        """Get all categories"""
        # This can be prepopulated or managed via an admin interface
        # For now, returning a static list
        return [
            Category({'name': 'General Discussion', 'slug': 'general', 'description': 'Talk about anything related to menstrual health.'}),
            Category({'name': 'PCOS/PCOD', 'slug': 'pcos', 'description': 'Support and information for PCOS/PCOD.'}),
            Category({'name': 'Endometriosis', 'slug': 'endo', 'description': 'Living with and managing Endometriosis.'}),
            Category({'name': 'Nutrition & Fitness', 'slug': 'lifestyle', 'description': 'Diet and exercise tips for a healthy cycle.'}),
            Category({'name': 'Mental Health', 'slug': 'mental-health', 'description': 'Discussing the mental and emotional aspects of menstrual cycles.'})
        ]

    @staticmethod
    def create_indexes():
        """Create indexes for the categories collection"""
        # If categories were stored in the DB, we would create indexes here
        pass
