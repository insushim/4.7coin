"""Telegram notifier with lazy import."""

from __future__ import annotations

from ..config import settings
from ..utils.logger import logger


class TelegramNotifier:
    def __init__(self) -> None:
        self.token = settings.telegram_bot_token
        self.chat_id = settings.telegram_chat_id
        self._bot = None

    async def _get_bot(self):
        if not self.token or not self.chat_id:
            return None
        if self._bot is None:
            try:
                from telegram import Bot

                self._bot = Bot(token=self.token)
            except ImportError:
                logger.warning("python-telegram-bot not installed")
                return None
        return self._bot

    async def send(self, message: str, parse_mode: str = "Markdown") -> bool:
        bot = await self._get_bot()
        if bot is None:
            logger.debug(f"[telegram stub] {message}")
            return False
        try:
            await bot.send_message(chat_id=self.chat_id, text=message, parse_mode=parse_mode)
            return True
        except Exception as exc:  # noqa: BLE001
            logger.error(f"Telegram send failed: {exc}")
            return False


telegram = TelegramNotifier()
