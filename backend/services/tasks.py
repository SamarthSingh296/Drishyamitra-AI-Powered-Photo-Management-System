import logging
from celery_app import celery
from flask import current_app
import os
import shutil

_flask_app = None

def get_app():
    global _flask_app
    if _flask_app is None:
        from app import create_app
        _flask_app = create_app()
    return _flask_app

@celery.task(bind=True, name="services.tasks.process_photo_faces")
def process_photo_faces(self, photo_id):
    """Background task to detect and match faces in an uploaded photo"""
    app = get_app()
    with app.app_context():
        # Imports needed inside the app context
        from models.database import db
        from models.photo import Photo
        from models.face import Face
        from models.person import Person
        from services.face_recognition import FaceRecognitionService
        
        try:
            photo = Photo.query.get(photo_id)
            if not photo:
                logging.error(f"process_photo_faces task failed: Photo {photo_id} not found.")
                return {"status": "error", "message": "Photo not found"}
                
            service = FaceRecognitionService()
            # Construct absolute path to the image
            abs_image_path = os.path.join(app.config['UPLOAD_FOLDER'], photo.filename)
            
            if not os.path.exists(abs_image_path):
                logging.error(f"Image file missing: {abs_image_path}")
                return {"status": "error", "message": "Image file missing"}
                
            # 1. Detect faces and embeddings
            faces_data = service.detect_and_extract_faces(abs_image_path)
            
            if not faces_data:
                logging.info(f"No faces found in photo {photo_id}")
                return {"status": "success", "message": "No faces found", "count": 0}
            
            matches = []
            new_faces_created = 0
            
            # 2. Iterate each detected face
            for face_info in faces_data:
                embedding = face_info.get("embedding")
                facial_area = face_info.get("facial_area", {})
                confidence = face_info.get("face_confidence", 0.0)
                
                # Bounding box as JSON list: [x, y, w, h]
                bbox = [
                    facial_area.get("x", 0), 
                    facial_area.get("y", 0), 
                    facial_area.get("w", 0), 
                    facial_area.get("h", 0)
                ]
                
                if not embedding:
                    continue
                    
                # 3. Match against existing DB profiles for this user
                matched_person, similarity = service.match_face(embedding, photo.user_id)
                person_id = matched_person.id if matched_person else None
                
                if matched_person:
                    matches.append(matched_person.name)
                
                # 4. Store the face embedding and results in DB
                new_face = Face(
                    photo_id=photo.id,
                    person_id=person_id,
                    bounding_box=bbox,
                    embedding=embedding,
                    confidence=confidence
                )
                db.session.add(new_face)
                new_faces_created += 1
                
            # Update DB with all new faces
            db.session.commit()
            
            # --- Automated Folder Organization ---
            if matches:
                organized_folder = app.config.get('ORGANIZED_FOLDER', os.path.join(app.config.get('UPLOAD_FOLDER', ''), 'organized'))
                user_folder = os.path.join(organized_folder, f"user_{photo.user_id}")
                
                for match_name in set(matches):
                    try:
                        safe_name = "".join([c for c in match_name if c.isalpha() or c.isdigit() or c in (' ', '-', '_')]).rstrip()
                        person_dir = os.path.join(user_folder, safe_name)
                        os.makedirs(person_dir, exist_ok=True)
                        
                        target_path = os.path.join(person_dir, photo.filename)
                        if not os.path.exists(target_path):
                            shutil.copy2(abs_image_path, target_path)
                            logging.info(f"Organized photo into {target_path}")
                    except Exception as e:
                        logging.error(f"Error organizing photo into {match_name} folder: {e}")
            # -------------------------------------
            
            logging.info(f"Processed photo {photo_id}: Found {len(faces_data)} faces. Matches: {matches}")
            return {
                "status": "success",
                "faces_detected": len(faces_data),
                "faces_stored": new_faces_created,
                "matches": matches
            }

        except Exception as e:
            db.session.rollback()
            logging.error(f"Exception in process_photo_faces: {e}")
            return {"status": "error", "message": str(e)}
