import os
import json
import logging
from groq import Groq
from flask import current_app
from services.chat_actions import ACTION_MAP

logger = logging.getLogger(__name__)

class AIService:
    def __init__(self):
        self.client = Groq(api_key=os.environ.get('GROQ_API_KEY'))
        self.model = os.environ.get('GROQ_MODEL', 'llama-3.3-70b-versatile')
        self.system_prompt = """
        You are Drishyamitra, an intelligent AI assistant for photo management and delivery tracking.
        Your goal is to help users manage their photos, identify persons, and view delivery history.
        
        Available tools (intents):
        1. get_deliveries: Use this to retrieve recent delivery history.
        2. find_photos: Use this to find photos of a specific person. Params: {"name": "person name"}
        3. list_persons: Use this to list all identified persons in the library.
        4. get_stats: Use this to get general statistics (counts of photos/persons).

        Instructions:
        - If the user's request matches one of these intents, respond in JSON format ONLY:
          {"intent": "intent_name", "params": {"param_key": "param_value"}}
        - If the request is a general question or doesn't match an intent, respond conversationally with helpful information.
        - Be friendly, concise, and professional.
        """

    async def get_response_async(self, message, history=None, user_id=None):
        """Asynchronous call to Groq API with intent extraction and action dispatch"""
        if not os.environ.get('GROQ_API_KEY'):
            return "AI service is currently unavailable. Please check your configuration."

        messages = [{"role": "system", "content": self.system_prompt}]
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": message})

        try:
            # 1. Get initial response from Groq (Intent Extraction)
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.2, # Lower temperature for better JSON adherence
                max_tokens=512,
                response_format={"type": "json_object"} if "intent" in message.lower() or "find" in message.lower() or "show" in message.lower() else None
            )
            
            ai_content = completion.choices[0].message.content.strip()
            
            # 2. Check if the response contains an intent
            try:
                intent_data = json.loads(ai_content)
                if isinstance(intent_data, dict) and "intent" in intent_data:
                    intent_name = intent_data.get("intent")
                    params = intent_data.get("params", {})
                    params['user_id'] = user_id # Inject user_id context
                    
                    if intent_name in ACTION_MAP:
                        # 3. Dispatch to action handler
                        action_result = ACTION_MAP[intent_name](params)
                        # 4. Generate final conversational response based on action result
                        return self._generate_final_response(message, action_result)
                    else:
                        logger.warning(f"Extracted unrecognized intent: {intent_name}")
            except json.JSONDecodeError:
                # Not JSON, proceed with conversational response
                pass
            
            return ai_content

        except Exception as e:
            logger.error(f"Groq API Error: {str(e)}")
            return "I'm having trouble connecting to my brain right now. Please try again later!"

    def _generate_final_response(self, user_query, action_result):
        """Generate a conversational response based on the result of an action"""
        messages = [
            {"role": "system", "content": "You are Drishyamitra Assistant. A user asked a question, and we retrieved some data from the database. Summarize this data for the user in a friendly way."},
            {"role": "user", "content": f"Query: {user_query}\nData: {action_result}"}
        ]
        
        try:
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,
                max_tokens=512
            )
            return completion.choices[0].message.content.strip()
        except:
            return f"I've updated your information: {action_result}"

    def get_response(self, message, history=None, user_id=None):
        """Synchronous wrapper for async call"""
        import asyncio
        import concurrent.futures

        # Since Groq SDK is synchronous itself (unless using .async_client),
        # and we want to avoid event loop issues in Flask, we call it directly here.
        # However, we'll keep the async-like structure for future-proofing.
        
        # NOTE: Groq has an AsyncGroq client if needed, but for simplicity in Flask routes, 
        # we'll perform a standard synchronous execution here.
        
        # Redefining for sync execution
        messages = [{"role": "system", "content": self.system_prompt}]
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": message})

        try:
            # 1. Get initial response (Intent Extraction)
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.2,
                max_tokens=512
            )
            
            ai_content = completion.choices[0].message.content.strip()
            
            # Attempt to parse intent
            try:
                # Handle cases where LLM might wrap JSON in Markdown code blocks
                clean_content = ai_content
                if "```json" in clean_content:
                    clean_content = clean_content.split("```json")[1].split("```")[0].strip()
                elif "```" in clean_content:
                    clean_content = clean_content.split("```")[1].strip()
                    
                intent_data = json.loads(clean_content)
                if isinstance(intent_data, dict) and "intent" in intent_data:
                    intent_name = intent_data.get("intent")
                    params = intent_data.get("params", {})
                    params['user_id'] = user_id
                    
                    if intent_name in ACTION_MAP:
                        action_result = ACTION_MAP[intent_name](params)
                        return self._generate_final_response(message, action_result)
            except (json.JSONDecodeError, ValueError):
                pass
            
            return ai_content
            
        except Exception as e:
            logger.error(f"Groq API Error: {str(e)}")
            return "I'm having trouble connecting to my brain right now. Please try again later!"
