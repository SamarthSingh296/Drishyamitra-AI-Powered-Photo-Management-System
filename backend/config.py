import os
import logging
from dotenv import load_dotenv
from sqlalchemy import create_engine

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    # Database
    DATABASE_URL = os.environ.get('DATABASE_URL') or 'sqlite:///database/drishyamitra.db'
    
    if DATABASE_URL.startswith('sqlite:///'):
        # Extract the path after sqlite:///
        db_path = DATABASE_URL.split('sqlite:///')[1]
        # Convert to absolute path relative to basedir (backend ROOT)
        abs_db_path = os.path.join(basedir, db_path)
        SQLALCHEMY_DATABASE_URI = f'sqlite:///{abs_db_path}'
    else:
        SQLALCHEMY_DATABASE_URI = DATABASE_URL
    
    # Create the SQLAlchemy engine
    try:
        engine = create_engine(SQLALCHEMY_DATABASE_URI)
        logger.info(f"Database engine created for: {SQLALCHEMY_DATABASE_URI.split('@')[-1] if '@' in SQLALCHEMY_DATABASE_URI else SQLALCHEMY_DATABASE_URI}")
    except Exception as e:
        logger.error(f"Failed to create database engine: {e}")
        engine = None

    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # JWT Configurations
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or 'jwt-secret-key-change-me'
    JWT_ACCESS_TOKEN_EXPIRES = 3600  # 1 hour
    JWT_REFRESH_TOKEN_EXPIRES = 2592000  # 30 days
    
    # HTTPS & Security Requirements
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    JWT_COOKIE_SECURE = True
    
    # Upload Configurations
    UPLOAD_FOLDER = os.path.join(basedir, 'data', 'photos')
    EMBEDDINGS_FOLDER = os.path.join(basedir, 'data', 'embeddings')
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
