"""
Invio notifiche via Telegram Bot API.
"""

import logging

import httpx

logger = logging.getLogger(__name__)


TELEGRAM_API = "https://api.telegram.org"


class TelegramNotifier:
    def __init__(self, bot_token: str, chat_strong: str, chat_review: str):
        self.bot_token = bot_token
        self.chat_strong = chat_strong
        self.chat_review = chat_review

    def _send(self, chat_id: str, text: str) -> bool:
        url = f"{TELEGRAM_API}/bot{self.bot_token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": False,
        }
        try:
            r = httpx.post(url, json=payload, timeout=10)
            if r.status_code != 200:
                logger.error(f"Telegram error {r.status_code}: {r.text}")
                return False
            return True
        except Exception as e:
            logger.error(f"Telegram exception: {e}")
            return False

    def send_job(
        self,
        channel: str,
        company: str,
        title: str,
        location: str,
        url: str,
        url_native: str = None,
        reason: str = None,
    ):
        emoji = "🎯" if channel == "strong" else "👀"
        chat_id = self.chat_strong if channel == "strong" else self.chat_review

        # Escape HTML-sensitive chars
        def esc(s):
            return (
                (s or "")
                .replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
            )

        lines = [
            f"{emoji} <b>{esc(title)}</b>",
            f"🏢 {esc(company)}",
            f"📍 {esc(location)}",
        ]
        if reason:
            lines.append(f"🧩 {esc(reason)}")
        lines.append(f'🔗 <a href="{esc(url)}">Apri offerta</a>')
        if url_native and url_native != url:
            lines.append(f'🔗 <a href="{esc(url_native)}">Sito azienda</a>')

        self._send(chat_id, "\n".join(lines))

    def send_daily_log(self, text: str):
        """Invia riepilogo giornaliero al canale review"""
        self._send(self.chat_review, text)

    def send_error(self, text: str):
        """Segnala errore al canale review"""
        self._send(self.chat_review, f"⚠️ <b>Jobberto</b>\n{text}")
