from openai import AsyncOpenAI
import os
from dotenv import load_dotenv

load_dotenv()

class AIService:
    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=os.getenv("DEEPSEEK_API_KEY"),
            base_url="https://api.deepseek.com"
        )
    
    async def get_response(self, prompt: str, messages: list) -> str:
        response = await self.client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "system", "content": prompt}] + messages,
            temperature=0.7,
            max_tokens=500
        )
        return response.choices[0].message.content

ai_service = AIService()