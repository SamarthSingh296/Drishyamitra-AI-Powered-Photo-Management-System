import os
from flask import Blueprint, request, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from werkzeug.utils import secure_filename
from models.database import db
from models.photo import Photo
from utils.responses import success_response, error_response
from utils.validation import validate_file_upload
from datetime import datetime
from services.tasks import process_photo_faces

photo_bp = Blueprint('photos', __name__)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

@photo_bp.route('/', methods=['GET'])
@jwt_required()
def list_photos():
    user_id = get_jwt_identity()
    photos = Photo.query.filter_by(user_id=user_id).all()
    return success_response([p.to_dict() for p in photos])

@photo_bp.route('/upload', methods=['POST'])
@jwt_required()
@validate_file_upload('photo', allowed_extensions=ALLOWED_EXTENSIONS)
def upload():
    file = request.files['photo']
    user_id = get_jwt_identity()
    
    # 1. Secure filename and path
    ext = file.filename.rsplit('.', 1)[1].lower()
    timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
    filename = secure_filename(f"user_{user_id}_{timestamp}.{ext}")
    filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
    
    try:
        # Create upload folder if not exists
        os.makedirs(current_app.config['UPLOAD_FOLDER'], exist_ok=True)
        
        # 2. Save file
        file.save(filepath)
        
        # 3. Verify file size after saving
        stats = os.stat(filepath)
        if stats.st_size > current_app.config['MAX_CONTENT_LENGTH']:
            os.remove(filepath)
            return error_response(f"File too large. Maximum size is {current_app.config['MAX_CONTENT_LENGTH'] // (1024*1024)}MB", 413)
        
        # 4. Register metadata in database
        photo = Photo(
            filename=filename, 
            filepath=filepath, 
            user_id=user_id,
            size=stats.st_size,
            mime_type=file.content_type
        )
        db.session.add(photo)
        db.session.commit()
        
        # 5. Trigger background face processing task
        process_photo_faces.delay(photo.id)
        
        return success_response(photo.to_dict(), "Photo uploaded and registered successfully", 201)
    
    except Exception as e:
        # Cleanup file if error occurs after saving
        if os.path.exists(filepath):
            os.remove(filepath)
        current_app.logger.error(f"Upload failed: {str(e)}")
        return error_response(f"An error occurred during upload: {str(e)}", 500)
