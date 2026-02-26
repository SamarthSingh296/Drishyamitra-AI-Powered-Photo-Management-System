from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from config import Config
from models.database import init_db, db
import os
from datetime import datetime
from flask_migrate import Migrate
from dotenv import load_dotenv
from routes.face_routes import face_bp

load_dotenv()

def create_app():
    """Application factory function"""
    app = Flask(__name__)
    app.config.from_object(Config)

    # Initialize extensions FIRST
    CORS(app, resources={r"/api/*": {"origins": "*"}})
    JWTManager(app)
    Config.init_app(app)
    init_db(app)
    migrate = Migrate(app, db)

    # Register blueprints - ALL imports here
    from routes.auth_routes import auth_bp
    from routes.chat_routes import chat_bp
    from routes.photo_routes import photo_bp
    from routes.delivery_routes import delivery_bp
    from routes.history_routes import history_bp
    from routes.edit_routes import edit_bp
    from routes.dashboard_routes import dashboard_bp

    # Register all blueprints
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(chat_bp, url_prefix='/api/chat')
    app.register_blueprint(photo_bp, url_prefix='/api/photos')
    app.register_blueprint(delivery_bp, url_prefix='/api/delivery')
    app.register_blueprint(history_bp, url_prefix='/api/history')
    app.register_blueprint(edit_bp, url_prefix='/api/edit')
    app.register_blueprint(face_bp, url_prefix='/api/face') 
    app.register_blueprint(dashboard_bp, url_prefix='/api/dashboard')

    # Global Error Handler
    @app.errorhandler(Exception)
    def handle_exception(e):
        """Global exception handler to return JSON instead of HTML"""
        import traceback
        error_msg = f"Unhandled Exception: {str(e)}\n{traceback.format_exc()}"
        app.logger.error(error_msg)
        
        # Also write to a file we can read
        with open("backend_error.log", "a") as f:
            f.write(f"\n--- {datetime.utcnow()} ---\n{error_msg}\n")
            
        return jsonify({
            "status": "error",
            "message": "Internal Server Error",
            "details": str(e) if app.config.get('DEBUG') else "Check server logs"
        }), 500

    # Health check endpoint
    @app.route('/api/health', methods=['GET'])
    def health():
        return jsonify({
            'status': 'healthy',
            'app': 'Drishyamitra',
            'timestamp': datetime.utcnow().isoformat(),
            'version': '1.0.0'
        }), 200

    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({'error': 'Resource not found'}), 404

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return jsonify({'error': 'Internal server error'}), 500

    # Request logging
    @app.before_request
    def log_request():
        app.logger.info(f"{request.method} {request.path} - {request.remote_addr}")

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=True
    )