from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from models.database import db
from models.history import DeliveryHistory
from utils.responses import success_response, error_response
from utils.validation import validate_json_fields
from services.delivery_service import DeliveryService

delivery_bp = Blueprint('delivery', __name__)

@delivery_bp.route('/log', methods=['POST'])
@jwt_required()
@validate_json_fields('action')
def log_activity():
    """Log a user-related activity or delivery action"""
    user_id = get_jwt_identity()
    data = request.get_json()
    action = data.get('action')
    details = data.get('details', {})
    
    try:
        new_entry = DeliveryHistory(
            user_id=user_id,
            action=action,
            details=details
        )
        db.session.add(new_entry)
        db.session.commit()
        
        return success_response(new_entry.to_dict(), "Activity logged successfully", 201)
    except Exception as e:
        db.session.rollback()
        return error_response(f"Failed to log activity: {str(e)}", 500)

@delivery_bp.route('/status', methods=['GET'])
@jwt_required()
def status():
    """Check status of delivery integration"""
    return success_response({"status": "active", "service": "Delivery Integration Service"})

@delivery_bp.route('/share/whatsapp', methods=['POST'])
@jwt_required()
def share_whatsapp():
    """Share a photo via WhatsApp"""
    user_id = get_jwt_identity()
    data = request.get_json()
    
    photo_id = data.get('photo_id')
    recipient = data.get('recipient')
    message = data.get('message', 'Here is your photo from Drishyamitra!')
    
    if not photo_id or not recipient:
        return error_response("photo_id and recipient are required", 400)
    
    success, result = DeliveryService.share_photo_via_whatsapp(
        user_id=user_id, 
        photo_id=photo_id, 
        recipient=recipient, 
        message=message
    )
    
    if success:
        return success_response({"status": "queued", "message": result}, "WhatsApp delivery queued successfully", 200)
    else:
        return error_response(f"Failed to queue WhatsApp delivery: {result}", 500)

@delivery_bp.route('/share/email', methods=['POST'])
@jwt_required()
def share_email():
    """Share a photo via Email"""
    user_id = get_jwt_identity()
    data = request.get_json()
    
    photo_id = data.get('photo_id')
    recipient = data.get('recipient')
    subject = data.get('subject', 'Photo shared from Drishyamitra')
    body = data.get('body', 'Here is your photo!')
    
    if not photo_id or not recipient:
        return error_response("photo_id and recipient are required", 400)
    
    success, result = DeliveryService.share_photo_via_email(
        user_id=user_id, 
        photo_id=photo_id, 
        recipient=recipient, 
        subject=subject,
        body=body
    )
    
    if success:
        return success_response({"status": "sent", "message": result}, "Email sent successfully", 200)
    else:
        return error_response(f"Failed to send Email: {result}", 500)
