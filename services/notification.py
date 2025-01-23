import os
import logging
from telethon import TelegramClient
from dotenv import load_dotenv

load_dotenv()

class NotificationService:
    def __init__(self):
        self.client = TelegramClient(
            'notifications',
            int(os.getenv("TELEGRAM_API_ID")),
            os.getenv("TELEGRAM_API_HASH")
        ).start(bot_token=os.getenv("TELEGRAM_BOT_TOKEN"))
        
    async def send_reminder(self, user_id: str, message: str):
        try:
            await self.client.send_message(
                entity=user_id,
                message=message
            )
        except Exception as e:
            logging.error(f"Notification error: {e}")

    async def send_daily_tip(self, user_id: str, tip: dict):
        message = f"💡 Conseil du jour : {tip['title']}\n\n{tip['content']}"
        await self.send_reminder(user_id, message)

    async def send_progress_update(self, user_id: str, progress: dict):
        message = (
            f"📊 Votre progression :\n"
            f"Poids actuel : {progress['current_weight']}kg\n"
            f"Objectif : {progress['target_weight']}kg\n"
            f"Jours restants : {progress['days_left']}"
        )
        await self.send_reminder(user_id, message)

# Singleton instance
notification_service = NotificationService()