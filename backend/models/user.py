from models.database import db
from flask_bcrypt import generate_password_hash, check_password_hash
from datetime import datetime

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256))
    role = db.Column(db.String(32), default='user')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships - Using string names to avoid circular imports during verification
    photos = db.relationship('Photo', backref='owner', lazy=True, cascade="all, delete-orphan")
    persons = db.relationship('Person', backref='owner', lazy=True, cascade="all, delete-orphan")
    history = db.relationship('DeliveryHistory', backref='user', lazy=True)

    def set_password(self, password):
        # Decode to string if it returns bytes (bcrypt does)
        self.password_hash = generate_password_hash(password).decode('utf-8')

    def check_password(self, password):
        """
        Support both bcrypt and legacy Werkzeug (scrypt/pbkdf2) hashes.
        Bcrypt hashes start with $2. Werkzeug hashes usually start with scrypt: or pbkdf2:.
        """
        if not self.password_hash:
            return False
            
        if self.password_hash.startswith('$2b$') or self.password_hash.startswith('$2a$'):
            try:
                return check_password_hash(self.password_hash, password)
            except ValueError:
                return False
        
        # Legacy Werkzeug check
        from werkzeug.security import check_password_hash as werkzeug_check
        return werkzeug_check(self.password_hash, password)

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "role": self.role,
            "created_at": self.created_at.isoformat()
        }
