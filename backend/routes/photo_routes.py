import os
from flask import Blueprint, request, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from werkzeug.utils import secure_filename
from models.database import db
from models.photo import Photo
from utils.responses import success_response, error_response
from datetime import datetime

photo_bp = Blueprint('photos', __name__)

@photo_bp.route('/', methods=['GET'])
@jwt_required()
def list_photos():
    user_id = get_jwt_identity()
    photos = Photo.query.filter_by(user_id=user_id).all()
    return success_response([p.to_dict() for p in photos])

@photo_bp.route('/upload', methods=['POST'])
@jwt_required()
def upload():
    if 'photo' not in request.files:
        return error_response("No photo part", 400)
    
    file = request.files['photo']
    if file.filename == '':
        return error_response("No selected file", 400)

    user_id = get_jwt_identity()
    filename = secure_filename(f"{user_id}_{datetime.utcnow().timestamp()}_{file.filename}")
    filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
    
    try:
        file.save(filepath)
        # Get file stats
        stats = os.stat(filepath)
        
        photo = Photo(
            filename=filename, 
            filepath=filepath, 
            user_id=user_id,
            size=stats.st_size,
            mime_type=file.content_type
        )
        db.session.add(photo)
        db.session.commit()
        
        return success_response(photo.to_dict(), "Photo uploaded successfully", 201)
    except Exception as e:
        return error_response(f"Upload failed: {str(e)}", 500)
