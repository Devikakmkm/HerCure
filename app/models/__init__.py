from .user import User
from .chat import ChatMessage
from .menstrual_cycle import MenstrualCycle, CycleSymptom
from .menstrual_profile import MenstrualProfile, VoiceLog, DataExport
from .menstrual_reminder import MenstrualReminder, HealthReport, LifestyleRecommendation
from .community import Post, Comment, Category

def init_models():
    """Initialize all models and create indexes"""
    # Import modules to ensure models are registered
    from . import user, chat, menstrual_cycle, menstrual_profile, menstrual_reminder, community

    # Create indexes for all models
    User.create_indexes()
    ChatMessage.create_indexes()
    MenstrualCycle.create_indexes()
    CycleSymptom.create_indexes()
    MenstrualProfile.create_indexes()
    VoiceLog.create_indexes()
    DataExport.create_indexes()
    Post.create_indexes()
    Comment.create_indexes()
    Category.create_indexes()
    MenstrualReminder.create_indexes()
    HealthReport.create_indexes()
    LifestyleRecommendation.create_indexes()

    print("Database indexes for all models created successfully")