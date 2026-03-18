"""Telegram notification service."""

from typing import Any, Dict, List, Optional

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

    def send_message_with_buttons(
        self,
        text: str,
        buttons: List[List[Dict[str, str]]],
        parse_mode: str = "HTML",
    ) -> bool:
        """Send a message with inline keyboard buttons.

        Args:
            text: Message text.
            buttons: List of rows, each row is a list of button dicts
                     with keys 'text' and 'callback_data'.
        """
        url = f"{self.api_url}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": parse_mode,
            "reply_markup": {"inline_keyboard": buttons},
        }
        try:
            response = requests.post(url, json=payload, timeout=10)
            return response.status_code == 200
        except requests.RequestException as e:
            print(f"Failed to send Telegram message: {e}")
            return False

    def edit_message_with_buttons(
        self,
        message_id: int,
        text: str,
        buttons: List[List[Dict[str, str]]],
        chat_id: Optional[str] = None,
        parse_mode: str = "HTML",
    ) -> bool:
        """Edit an existing message's text and inline keyboard."""
        url = f"{self.api_url}/editMessageText"
        payload: Dict[str, Any] = {
            "chat_id": chat_id or self.chat_id,
            "message_id": message_id,
            "text": text,
            "parse_mode": parse_mode,
            "reply_markup": {"inline_keyboard": buttons},
        }
        try:
            response = requests.post(url, json=payload, timeout=10)
            return response.status_code == 200
        except requests.RequestException as e:
            print(f"Failed to edit message: {e}")
            return False

    def get_updates(self, offset: Optional[int] = None, timeout: int = 30) -> List[Dict[str, Any]]:
        """Fetch pending updates (callback queries) from Telegram.

        Uses long-polling: blocks up to *timeout* seconds waiting for new updates.
        """
        url = f"{self.api_url}/getUpdates"
        params: Dict[str, Any] = {"timeout": timeout}
        if offset is not None:
            params["offset"] = offset
        try:
            response = requests.get(url, params=params, timeout=timeout + 5)
            if response.status_code == 200:
                return response.json().get("result", [])
        except requests.RequestException as e:
            print(f"Failed to get updates: {e}")
        return []

    def answer_callback_query(self, callback_query_id: str, text: str = "") -> bool:
        """Acknowledge a callback query (dismiss the loading indicator)."""
        url = f"{self.api_url}/answerCallbackQuery"
        payload: Dict[str, Any] = {"callback_query_id": callback_query_id}
        if text:
            payload["text"] = text
        try:
            response = requests.post(url, json=payload, timeout=10)
            return response.status_code == 200
        except requests.RequestException as e:
            print(f"Failed to answer callback query: {e}")
            return False

    def is_chat_admin(self, user_id: int) -> bool:
        """Check if a user is an admin or creator of the configured chat."""
        url = f"{self.api_url}/getChatMember"
        payload = {"chat_id": self.chat_id, "user_id": user_id}
        try:
            response = requests.post(url, json=payload, timeout=10)
            if response.status_code == 200:
                status = response.json().get("result", {}).get("status", "")
                return status in ("creator", "administrator")
        except requests.RequestException as e:
            print(f"Failed to check admin status: {e}")
        return False
