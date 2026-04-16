"""Remote communication integrations (Telegram + optional SMS)."""

from __future__ import annotations

try:
    from telegram import Bot  # type: ignore
except Exception:  # pragma: no cover
    Bot = None


class CommunicationHub:
    def __init__(self, telegram_token: str = "", chat_id: str = ""):
        self.chat_id = chat_id
        self.bot = Bot(telegram_token) if telegram_token and Bot else None

    def send_telegram(self, text: str) -> bool:
        if not self.bot or not self.chat_id:
            return False
        self.bot.send_message(chat_id=self.chat_id, text=text)
        return True

    def send_sms(self, _text: str) -> bool:
        return False
