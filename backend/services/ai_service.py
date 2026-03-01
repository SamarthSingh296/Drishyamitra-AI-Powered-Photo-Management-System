import os
import json
import logging
from groq import Groq
from services.chat_actions import ACTION_MAP

logger = logging.getLogger(__name__)


class AIService:
    def __init__(self):
        self.client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
        self.model = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")

        self.system_prompt = """
You are Drishyamitra, an intelligent AI assistant for photo management and delivery tracking.
Your goal is to help users manage their photos, identify persons, and view delivery history.

Available tools (intents):
1. get_deliveries
2. find_photos
3. list_persons
4. get_stats
5. share_photo

Instructions:
- If the user's request matches one of these intents, respond in JSON format ONLY:
  {"intent": "intent_name", "params": {...}}
- Otherwise respond conversationally.
- Be friendly, concise, and professional.
"""

    def _generate_final_response(self, user_query, action_result):
        messages = [
            {
                "role": "system",
                "content": "Summarize this database result in a friendly way."
            },
            {
                "role": "user",
                "content": f"Query: {user_query}\nData: {action_result}"
            }
        ]

        try:
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,
                max_tokens=512
            )

            content = completion.choices[0].message.content or ""
            return content.strip()

        except Exception:
            return f"I've updated your information: {action_result}"

    def _mock_fallback(self, message, user_id):
        return "Mock AI: No valid GROQ_API_KEY configured."

    def get_response(self, message, history=None, user_id=None):
        """
        Main synchronous Groq execution method
        """

        api_key = os.environ.get("GROQ_API_KEY")

        if not api_key or api_key == "your_actual_groq_api_key_here":
            return self._mock_fallback(message, user_id)

        # Start with system prompt
        messages = [
            {"role": "system", "content": self.system_prompt}
        ]

        # ✅ Proper history sanitization
        if history:
            for msg in history:
                role = msg.get("role", "user")
                content = msg.get("content", "")

                # Convert frontend role
                if role == "bot":
                    role = "assistant"

                if role not in ["system", "user", "assistant"]:
                    role = "user"

                if content:
                    messages.append({
                        "role": role,
                        "content": content
                    })

        # Add current user message
        messages.append({
            "role": "user",
            "content": message
        })

        try:
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.3,
                max_tokens=512
            )

            ai_content = completion.choices[0].message.content or ""
            ai_content = ai_content.strip()

            # Attempt intent parsing
            try:
                cleaned = ai_content

                if "```json" in cleaned:
                    cleaned = cleaned.split("```json")[1].split("```")[0].strip()
                elif "```" in cleaned:
                    cleaned = cleaned.split("```")[1].strip()

                intent_data = json.loads(cleaned)

                if isinstance(intent_data, dict) and "intent" in intent_data:
                    intent_name = intent_data.get("intent")
                    params = intent_data.get("params", {})
                    params["user_id"] = user_id

                    if intent_name in ACTION_MAP:
                        result = ACTION_MAP[intent_name](params)
                        return self._generate_final_response(message, result)

            except (json.JSONDecodeError, ValueError):
                pass

            return ai_content

        except Exception as e:
            logger.error(f"Groq API Error: {str(e)}")
            return f"Failed to generate AI response: {str(e)}"