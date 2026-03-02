import os
import requests
import logging
import time
from typing import Dict, Any, Tuple
from flask import current_app

logger = logging.getLogger(__name__)

class WhatsAppService:
    """WhatsApp automation service using whatsapp-web.js API or Twilio API"""
    
    def __init__(self, api_url=None):
        self.api_url = api_url or current_app.config.get('WHATSAPP_API_URL', 'http://localhost:3000')
        self.timeout = 30
        
    def _format_number(self, phone_number: str) -> str:
        """Format number based on standard requirements (remove +, add @c.us generally)"""
        # If it's a Twilio number, handling is different, but assuming whatsapp-web.js structure
        cleaned = "".join(filter(str.isdigit, phone_number))
        if len(cleaned) == 10:  # standard indian without country code
            cleaned = f"91{cleaned}"
        if not cleaned.endswith("@c.us") and not cleaned.endswith("@g.us"):
            cleaned = f"{cleaned}@c.us"
        return cleaned
        
    def send_message(self, recipient_number: str, message: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Send text message via WhatsApp
        """
        try:
            chat_id = self._format_number(recipient_number)
            
            response = requests.post(
                f"{self.api_url}/send-message",
                json={
                    'number': chat_id,
                    'message': message
                },
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get('success', True), data
            logger.error(f"WhatsApp API Error: HTTP {response.status_code} - {response.text}")
            return False, {"error": response.text}
            
        except requests.RequestException as e:
            logger.error(f"WhatsApp API Connection Error: {e}")
            return False, {"error": str(e)}

    def send_media(self, recipient_number: str, media_path: str, caption: str = "") -> Tuple[bool, Dict[str, Any]]:
        """
        Send a photo via WhatsApp
        Requires the absolute path to the media file or a base64 string
        """
        try:
            if not os.path.exists(media_path):
                return False, {"error": f"Media file not found: {media_path}"}
                
            chat_id = self._format_number(recipient_number)
            
            # Use multi-part form data to upload the file to the WhatsApp API
            with open(media_path, 'rb') as f:
                files = {'file': f}
                data = {'number': chat_id, 'caption': caption}
                
                response = requests.post(
                    f"{self.api_url}/send-media",
                    data=data,
                    files=files,
                    timeout=self.timeout
                )
                
            if response.status_code == 200:
                resp_data = response.json()
                return resp_data.get('success', True), resp_data
            
            logger.error(f"WhatsApp API Error (Media): HTTP {response.status_code} - {response.text}")
            return False, {"error": response.text}
            
        except requests.RequestException as e:
            logger.error(f"WhatsApp Media API Connection Error: {e}")
            return False, {"error": str(e)}
        except Exception as e:
            logger.error(f"Unexpected error in WhatsApp send_media: {e}")
            return False, {"error": str(e)}
