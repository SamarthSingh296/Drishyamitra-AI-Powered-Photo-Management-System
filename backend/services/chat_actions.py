import logging
from datetime import datetime, timedelta
from models.photo import Photo
from models.person import Person
from models.history import DeliveryHistory
from models.database import db

logger = logging.getLogger(__name__)

def get_recent_deliveries(params=None):
    """Retrieve recent delivery history"""
    try:
        days = params.get('days', 7) if params else 7
        user_id = params.get('user_id')
        
        since_date = datetime.utcnow() - timedelta(days=days)
        history = DeliveryHistory.query.filter(
            DeliveryHistory.user_id == user_id,
            DeliveryHistory.timestamp >= since_date
        ).order_by(DeliveryHistory.timestamp.desc()).all()
        
        if not history:
            return "No recent deliveries found."
            
        result = [f"- {h.action} on {h.timestamp.strftime('%Y-%m-%d %H:%M')}" for h in history]
        return "\n".join(result)
    except Exception as e:
        logger.error(f"Error in get_recent_deliveries: {e}")
        return "Sorry, I couldn't retrieve the delivery history right now."

def find_photos_by_person(params=None):
    """Find photos associated with a specific person"""
    try:
        name = params.get('name')
        user_id = params.get('user_id')
        
        if not name:
            return "Please provide a person's name."
            
        person = Person.query.filter(
            Person.user_id == user_id,
            Person.name.ilike(f"%{name}%")
        ).first()
        
        if not person:
            return f"I couldn't find anyone named '{name}' in your collection."
            
        photos = Photo.query.join(Photo.faces).filter(
            Photo.user_id == user_id,
            Person.id == person.id
        ).all()
        
        if not photos:
            return f"I found {person.name}, but there are no photos associated with them."
            
        return f"I found {len(photos)} photos of {person.name}."
    except Exception as e:
        logger.error(f"Error in find_photos_by_person: {e}")
        return "Sorry, I encountered an error while searching for photos."

def list_known_persons(params=None):
    """List all identified persons for the user"""
    try:
        user_id = params.get('user_id')
        persons = Person.query.filter_by(user_id=user_id).all()
        
        if not persons:
            return "You haven't added or identified any persons yet."
            
        names = [p.name for p in persons]
        return f"I've identified these people in your photos: {', '.join(names)}."
    except Exception as e:
        logger.error(f"Error in list_known_persons: {e}")
        return "Sorry, I couldn't retrieve the list of persons."

def get_system_stats(params=None):
    """Get general stats about the user's photos and persons"""
    try:
        user_id = params.get('user_id')
        photo_count = Photo.query.filter_by(user_id=user_id).count()
        person_count = Person.query.filter_by(user_id=user_id).count()
        
        return f"You have {photo_count} photos and {person_count} identified persons in your library."
    except Exception as e:
        logger.error(f"Error in get_system_stats: {e}")
        return "I'm having trouble retrieving your system stats."

# Map intents to functions
ACTION_MAP = {
    "get_deliveries": get_recent_deliveries,
    "find_photos": find_photos_by_person,
    "list_persons": list_known_persons,
    "get_stats": get_system_stats
}
