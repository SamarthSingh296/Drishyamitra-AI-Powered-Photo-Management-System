import os
import httpx
import asyncio
from flask import current_app

class AIService:
    def __init__(self):
        self.api_key = os.getenv('GROQ_API_KEY')
        self.api_url = "https://api.groq.com/openai/v1/chat/completions"
        self.model = "llama3-8b-8192" # Robust default model

    async def get_response_async(self, message, history=None):
        """Asynchronous call to AI API"""
        if not self.api_key:
            return "AI service is currently unavailable (Missing API Key)."

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        messages = history if history else []
        messages.append({"role": "user", "content": message})

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 1024
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.api_url, 
                    headers=headers, 
                    json=payload, 
                    timeout=30.0
                )
                response.raise_for_status()
                data = response.json()
                return data['choices'][0]['message']['content']
        except Exception as e:
            current_app.logger.error(f"AI API Error: {str(e)}")
            return "I'm having trouble connecting to my brain right now. Please try again later!"

    def get_response(self, message, history=None):
        """Synchronous wrapper for async call"""
        try:
            return asyncio.run(self.get_response_async(message, history))
        except RuntimeError:
            # Fallback for when an event loop is already running
            new_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(new_loop)
            return new_loop.run_until_complete(self.get_response_async(message, history))
