"""Telegram notification service."""

import requests


class TelegramNotifier:
    """Service for sending notifications to Telegram."""

    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.api_url = f"https://api.telegram.org/bot{bot_token}"

    def send_message(self, text: str, parse_mode: str = "HTML") -> bool:
        """Send a message to the configured chat."""
        url = f"{self.api_url}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": parse_mode,
        }
        try:
            response = requests.post(url, json=payload, timeout=10)
            return response.status_code == 200
        except requests.RequestException as e:
            print(f"Failed to send Telegram message: {e}")
            return False
