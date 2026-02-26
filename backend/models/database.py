from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

def init_db(app):
    db.init_app(app)
    with app.app_context():
        # Import models here so SQLAlchemy knows about them
        from models.user import User
        from models.photo import Photo
        from models.face import Face
        from models.person import Person
        from models.history import DeliveryHistory
        # This will create tables if they don't exist
        db.create_all() 
