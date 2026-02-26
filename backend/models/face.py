from models.database import db

class Face(db.Model):
    __tablename__ = 'faces'
    
    id = db.Column(db.Integer, primary_key=True)
    photo_id = db.Column(db.Integer, db.ForeignKey('photos.id'), nullable=False)
    person_id = db.Column(db.Integer, db.ForeignKey('persons.id'), nullable=True) # Initially unknown
    bounding_box = db.Column(db.JSON) # [x, y, w, h]
    embedding = db.Column(db.JSON) # Latent vector for AI matching
    confidence = db.Column(db.Float)
    
    def to_dict(self):
        return {
            "id": self.id,
            "photo_id": self.photo_id,
            "person_id": self.person_id,
            "bounding_box": self.bounding_box,
            "confidence": self.confidence
        }
