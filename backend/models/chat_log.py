from models.database import db
from datetime import datetime

class ChatLog(db.Model):
    __tablename__ = 'chat_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    query = db.Column(db.Text, nullable=False)
    response = db.Column(db.Text)
    is_fallback = db.Column(db.Boolean, default=False)
    metadata_json = db.Column(db.JSON) # Additional context or extracted params
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "query": self.query,
            "response": self.response,
            "is_fallback": self.is_fallback,
            "timestamp": self.timestamp.isoformat()
        }
