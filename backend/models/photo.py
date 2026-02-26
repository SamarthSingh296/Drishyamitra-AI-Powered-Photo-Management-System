from models.database import db
from datetime import datetime

class Photo(db.Model):
    __tablename__ = 'photos'
    
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(256), nullable=False)
    filepath = db.Column(db.String(512), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    upload_date = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    size = db.Column(db.Integer) # size in bytes
    mime_type = db.Column(db.String(64))
    
    # Relationships
    faces = db.relationship('Face', backref='photo', lazy=True, cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "filename": self.filename,
            "filepath": self.filepath,
            "upload_date": self.upload_date.isoformat(),
            "user_id": self.user_id,
            "mime_type": self.mime_type
        }
