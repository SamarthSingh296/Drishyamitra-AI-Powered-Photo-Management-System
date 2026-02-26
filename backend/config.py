import os
from dotenv import load_dotenv

load_dotenv()

basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    # Database
    db_uri = os.environ.get('DATABASE_URL') or 'sqlite:///database/drishyamitra.db'
    if db_uri.startswith('sqlite:///'):
        # Extract the path after sqlite:///
        db_path = db_uri.split('sqlite:///')[1]
        # Convert to absolute path relative to basedir (backend ROOT)
        abs_db_path = os.path.join(basedir, db_path)
        SQLALCHEMY_DATABASE_URI = f'sqlite:///{abs_db_path}'
    else:
        SQLALCHEMY_DATABASE_URI = db_uri
    
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Upload Configurations
    UPLOAD_FOLDER = os.path.join(basedir, 'data', 'photos')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
    
    @staticmethod
    def init_app(app):
        # Create upload folder if it doesn't exist
        os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
        
        # Ensure database directory exists for SQLite
        db_uri = app.config.get('SQLALCHEMY_DATABASE_URI')
        if db_uri and db_uri.startswith('sqlite:///'):
            db_path = db_uri.split('sqlite:///')[1]
            db_dir = os.path.dirname(os.path.join(os.getcwd(), db_path))
            if db_dir:
                os.makedirs(db_dir, exist_ok=True)
