"""
Celery background task: process faces in an uploaded photo.
Uses FaceRecognitionService (Facenet512 + RetinaFace + MTCNN pipeline).
"""

import logging
import os
import shutil

from celery_app import celery

logger = logging.getLogger(__name__)

_flask_app = None


def get_app():
    global _flask_app
    if _flask_app is None:
        import sys
        import os
        basedir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if basedir not in sys.path:
            sys.path.insert(0, basedir)
        from app import create_app
        _flask_app = create_app()
    return _flask_app


@celery.task(bind=True, name="services.tasks.process_photo_faces", max_retries=3)
def process_photo_faces(self, photo_id: int):
    """
    Celery task: detect, embed, and match faces in a photo.

    Pipeline
    --------
    1. Fetch Photo record and resolve absolute path.
    2. Run FaceRecognitionService.detect_and_extract_faces (Facenet512 / RetinaFace).
    3. Run .extract_faces_with_landmarks (MTCNN landmarks).
    4. For each face — match against user's existing profiles (cosine similarity).
    5. Auto-create an unknown-person record if no match found.
    6. Persist Face records (bbox, embedding, landmarks, confidence, model_version).
    7. Optionally copy photo into a per-person organised folder.
    """
    app = get_app()
    with app.app_context():
        from models.database import db
        from models.photo import Photo
        from models.face import Face
        from models.person import Person
        from services.face_recognition import FaceRecognitionService

        try:
            photo = Photo.query.get(photo_id)
            if not photo:
                logger.error(f"process_photo_faces: Photo {photo_id} not found")
                return {"status": "error", "message": "Photo not found"}

            abs_path = os.path.join(app.config["UPLOAD_FOLDER"], photo.filename)
            if not os.path.exists(abs_path):
                logger.error(f"process_photo_faces: Image missing at {abs_path}")
                return {"status": "error", "message": "Image file missing"}

            service = FaceRecognitionService()

            # ---- Stage 1: Detection + Facenet512 embeddings ----
            faces_data = service.detect_and_extract_faces(abs_path)
            if not faces_data:
                logger.info(f"No faces found in photo {photo_id}")
                return {"status": "success", "message": "No faces detected", "count": 0}

            # ---- Stage 2: MTCNN landmarks (best-effort) ----
            landmark_items = service.extract_faces_with_landmarks(abs_path)
            landmark_map = {i: item.get("landmarks", {}) for i, item in enumerate(landmark_items)}

            matched_names  = []
            faces_stored   = 0

            for idx, face_info in enumerate(faces_data):
                embedding   = face_info.get("embedding")
                facial_area = face_info.get("facial_area", {})
                confidence  = face_info.get("face_confidence", face_info.get("confidence", 0.0))
                landmarks   = landmark_map.get(idx, {})

                bbox = [
                    facial_area.get("x", 0),
                    facial_area.get("y", 0),
                    facial_area.get("w", 0),
                    facial_area.get("h", 0),
                ]

                if not embedding:
                    logger.warning(f"Skipping face #{idx} in photo {photo_id} — empty embedding")
                    continue

                # ---- Stage 3: Match ----
                matched_person, scores = service.match_face(embedding, photo.user_id)

                # ---- Stage 4: Auto-create if unknown ----
                if matched_person is None:
                    matched_person = service.auto_create_person(photo.user_id)
                    logger.info(
                        f"Created new unknown person '{matched_person.name}' "
                        f"for user {photo.user_id}"
                    )
                else:
                    matched_names.append(matched_person.name)
                    logger.info(
                        f"Matched face to '{matched_person.name}' "
                        f"(cos_dist={scores['cosine_distance']:.4f}, "
                        f"sim={scores['similarity']:.4f})"
                    )

                # ---- Stage 5: Persist ----
                new_face = Face(
                    photo_id      = photo.id,
                    person_id     = matched_person.id,
                    bounding_box  = bbox,
                    embedding     = embedding,
                    landmarks     = landmarks,
                    confidence    = float(confidence),
                    model_version = FaceRecognitionService.MODEL_VERSION,
                )
                db.session.add(new_face)
                faces_stored += 1

            db.session.commit()
            service.invalidate_cache(photo.user_id)

            # ---- Stage 6: Organise photos into per-person folders ----
            if matched_names:
                organized_root = app.config.get(
                    "ORGANIZED_FOLDER",
                    os.path.join(app.config.get("UPLOAD_FOLDER", ""), "organized"),
                )
                user_dir = os.path.join(organized_root, f"user_{photo.user_id}")

                for name in set(matched_names):
                    safe_name   = "".join(c for c in name if c.isalnum() or c in " -_").strip()
                    person_dir  = os.path.join(user_dir, safe_name)
                    os.makedirs(person_dir, exist_ok=True)
                    target      = os.path.join(person_dir, photo.filename)
                    if not os.path.exists(target):
                        shutil.copy2(abs_path, target)
                        logger.info(f"Organised photo → {target}")

            logger.info(
                f"Photo {photo_id} processed: "
                f"{len(faces_data)} detected, {faces_stored} stored, "
                f"matches={matched_names}"
            )
            return {
                "status":         "success",
                "faces_detected": len(faces_data),
                "faces_stored":   faces_stored,
                "matches":        matched_names,
            }

        except Exception as exc:
            db.session.rollback()
            logger.error(f"process_photo_faces exception (photo {photo_id}): {exc}")
            # Retry with exponential back-off
            raise self.retry(exc=exc, countdown=2 ** self.request.retries)

@celery.task(bind=True, name="services.tasks.send_whatsapp_photo_task", max_retries=3)
def send_whatsapp_photo_task(self, log_id: int, user_id: int, photo_id: int, recipient: str, message: str):
    """
    Celery task: Send photo via WhatsApp with retry mechanism.
    Tracks status in DeliveryHistory. Compliance with WhatsApp constraints can be 
    added via rate_limit or countdown on delays between similar tasks if needed.
    """
    import time
    app = get_app()
    with app.app_context():
        from models.database import db
        from models.photo import Photo
        from models.history import DeliveryHistory
        from services.whatsapp_service import WhatsAppService
        
        try:
            log_record = DeliveryHistory.query.get(log_id)
            if not log_record:
                logger.error(f"Delivery log {log_id} not found.")
                return {"status": "error", "message": "Log record not found"}
                
            photo = Photo.query.filter_by(id=photo_id, user_id=user_id).first()
            if not photo:
                error_msg = f"Photo {photo_id} missing or permission denied."
                logger.error(error_msg)
                
                # Update log to failed
                details = dict(log_record.details or {})
                details['status'] = 'failed'
                details['error'] = error_msg
                log_record.action = 'whatsapp_share_failed'
                log_record.details = details
                db.session.commit()
                return {"status": "error", "message": error_msg}

            abs_path = os.path.join(app.config.get("UPLOAD_FOLDER", ""), photo.filename)
            whatsapp_service = WhatsAppService()
            
            # Comply with WhatsApp policies: avoid sending instantly, wait 2 seconds
            # In a production app with multiple deliveries, tasks can be scheduled with countdowns
            time.sleep(2)
            
            # Send file via WhatsApp Service
            success, response = whatsapp_service.send_media(
                recipient_number=recipient,
                media_path=abs_path,
                caption=message
            )
            
            details = log_record.details or {}
            
            if success:
                details['status'] = 'delivered'
                details['response'] = response
                log_record.action = 'whatsapp_share_success'
                log_record.details = details
                db.session.commit()
                logger.info(f"WhatsApp message successfully sent to {recipient}")
                return {"status": "success", "response": response}
            else:
                error_info = response.get('error', 'Unknown Error')
                details['status'] = 'failed'
                details['error'] = error_info
                log_record.action = 'whatsapp_share_failed'
                log_record.details = details
                db.session.commit()
                
                logger.error(f"Failed to send WhatsApp message: {error_info}")
                
                # If API gave an error, we might want to retry
                raise Exception(f"WhatsApp API Error: {error_info}")

        except Exception as exc:
            logger.error(f"send_whatsapp_photo_task exception (log_id {log_id}): {exc}")
            # Retry with exponential back-off (2s, 4s, 8s...) to avoid spamming the API and getting banned
            db.session.rollback()
            try:
                raise self.retry(exc=exc, countdown=2 ** self.request.retries)
            except self.MaxRetriesExceededError:
                # Mark as final failure when all retries are exhausted
                with app.app_context():
                    final_log = DeliveryHistory.query.get(log_id)
                    if final_log:
                        final_details = dict(final_log.details or {})
                        final_details['status'] = 'failed'
                        final_details['error'] = 'Max retries exceeded'
                        final_log.action = 'whatsapp_share_failed'
                        final_log.details = final_details
                        db.session.commit()
                raise

@celery.task(bind=True, name="services.tasks.cleanup_temp_storage")
def cleanup_temp_storage(self):
    """
    Periodic task to clean up old files in the temporary/cache storage.
    """
    app = get_app()
    with app.app_context():
        import time
        tmp_folder = os.path.join(app.config.get("UPLOAD_FOLDER", ""), "temp")
        if not os.path.exists(tmp_folder):
            return {"status": "success", "message": "No temp folder to clean"}
            
        now = time.time()
        deleted_count = 0
        
        for filename in os.listdir(tmp_folder):
            filepath = os.path.join(tmp_folder, filename)
            # Delete if older than 24 hours
            if os.path.isfile(filepath):
                if os.stat(filepath).st_mtime < now - 86400:
                    try:
                        os.remove(filepath)
                        deleted_count += 1
                    except Exception as e:
                        logger.error(f"Error deleting temp file {filepath}: {e}")
                        
        logger.info(f"Cleaned up {deleted_count} temporary files.")
        return {"status": "success", "deleted_count": deleted_count}

@celery.task(bind=True, name="services.tasks.organize_all_photos")
def organize_all_photos(self, user_id: int):
    """
    Bulk folder organization task for a user.
    Categorizes all processed photos into person-specific directories based on recognition results.
    """
    app = get_app()
    with app.app_context():
        from models.photo import Photo
        from models.face import Face
        from models.person import Person
        
        photos = Photo.query.filter_by(user_id=user_id).all()
        organized_count = 0
        
        organized_root = app.config.get(
            "ORGANIZED_FOLDER",
            os.path.join(app.config.get("UPLOAD_FOLDER", ""), "organized"),
        )
        user_dir = os.path.join(organized_root, f"user_{user_id}")
        
        for photo in photos:
            faces = Face.query.filter_by(photo_id=photo.id).all()
            if not faces:
                continue
                
            abs_path = os.path.join(app.config["UPLOAD_FOLDER"], photo.filename)
            if not os.path.exists(abs_path):
                continue
                
            matched_names = set()
            for face in faces:
                person = Person.query.get(face.person_id)
                if person and person.name:
                    matched_names.add(person.name)
            
            for name in matched_names:
                safe_name = "".join(c for c in name if c.isalnum() or c in " -_").strip()
                person_dir = os.path.join(user_dir, safe_name)
                os.makedirs(person_dir, exist_ok=True)
                target = os.path.join(person_dir, photo.filename)
                
                if not os.path.exists(target):
                    try:
                        shutil.copy2(abs_path, target)
                        organized_count += 1
                    except Exception as exc:
                        logger.error(f"Failed to organize photo {photo.filename}: {exc}")
                        
        return {"status": "success", "organized_count": organized_count, "user_id": user_id}
