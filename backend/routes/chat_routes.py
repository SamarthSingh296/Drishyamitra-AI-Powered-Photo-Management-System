from flask import Blueprint, request
from utils.responses import success_response, error_response
from utils.decorators import validate_json, log_request
from services.ai_service import AIService
from datetime import datetime

chat_bp = Blueprint('chat', __name__)
ai_service = AIService()

@chat_bp.route('/', methods=['POST'])
@log_request
@validate_json('message')
def chat():
    """AI Chat Endpoint"""
    data = request.get_json()
    user_message = data.get('message')
    history = data.get('history', [])

    try:
        # Get AI response
        ai_response = ai_service.get_response(user_message, history)
        
        return success_response({
            "response": ai_response,
            "timestamp": datetime.utcnow().isoformat()
        }, message="AI response generated successfully")
    
    except Exception as e:
        return error_response(message=f"Failed to generate AI response: {str(e)}", status_code=500)
