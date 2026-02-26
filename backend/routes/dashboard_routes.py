from flask import Blueprint, jsonify, send_from_directory, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from models.photo import Photo
from models.person import Person
from models.history import DeliveryHistory

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/stats', methods=['GET'])
@jwt_required()
def get_stats():
    user_id = get_jwt_identity()
    
    photo_count = Photo.query.filter_by(user_id=user_id).count()
    person_count = Person.query.filter_by(user_id=user_id).count()
    history_count = DeliveryHistory.query.filter_by(user_id=user_id).count()
    
    return jsonify({
        "status": "success",
        "data": {
            "photo_count": photo_count,
            "person_count": person_count,
            "history_count": history_count
        }
    })

@dashboard_bp.route('/media/<path:filename>')
def serve_media(filename):
    return send_from_directory(current_app.config['UPLOAD_FOLDER'], filename)
