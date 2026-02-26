from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from utils.responses import success_response, error_response
from utils.decorators import log_request

face_bp = Blueprint('face', __name__)

@face_bp.route('/recognize', methods=['POST'])
@jwt_required()
@log_request
def recognize():
    # In a real app, this would trigger an AI model (OpenCV/MTCNN)
    # For now, we return a mock success
    return success_response({
        "faces_detected": 2,
        "matches": ["Person A", "Person B"]
    }, message="Face recognition processing triggered")
