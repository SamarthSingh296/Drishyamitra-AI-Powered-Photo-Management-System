from flask import Blueprint, request, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from utils.responses import success_response, error_response
from utils.validation import validate_json_fields
from services.ai_service import AIService
from models.database import db
from models.chat_log import ChatLog
from datetime import datetime
import threading

chat_bp = Blueprint('chat', __name__)
ai_service = AIService()

def log_chat_async(app, user_id, query, response, is_fallback=False):
    """Background task to log chat interactions"""
    with app.app_context():
        try:
            new_log = ChatLog(
                user_id=user_id,
                query=query,
                response=response,
                is_fallback=is_fallback
            )
            db.session.add(new_log)
            db.session.commit()
        except Exception as e:
            app.logger.error(f"Failed to log chat: {e}")

@chat_bp.route('/', methods=['POST'])
@jwt_required()
@validate_json_fields('message')
def chat():
    """AI Chat Endpoint with Intent Extraction and Action Dispatch"""
    user_id = get_jwt_identity()
    data = request.get_json()
    user_message = data.get('message')
    history = data.get('history', [])
    
    try:
        # Get AI response (using Groq + Intent Extraction)
        ai_response = ai_service.get_response(user_message, history, user_id=user_id)
        
        # Log the interaction asynchronously
        is_fallback = "trouble connecting" in ai_response.lower() or "unrecognised intent" in ai_response.lower()
        threading.Thread(
            target=log_chat_async,
            args=(current_app._get_current_object(), user_id, user_message, ai_response, is_fallback)
        ).start()
        
        return success_response({
            "answer": ai_response,
            "timestamp": datetime.utcnow().isoformat()
        }, message="AI response generated successfully")
    
    except Exception as e:
        current_app.logger.error(f"Chat Route Error: {e}")
        return error_response(message=f"Failed to generate AI response: {str(e)}", status_code=500)
