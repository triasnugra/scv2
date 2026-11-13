"""Notifikasi Telegram opsional (secret TELEGRAM_BOT_TOKEN & TELEGRAM_CHAT_ID). Gagal = diabaikan."""
import os
import requests


def send(text: str) -> None:
    tok, chat = os.environ.get("TELEGRAM_BOT_TOKEN"), os.environ.get("TELEGRAM_CHAT_ID")
    if not tok or not chat:
        return
    try:
        requests.post(f"https://api.telegram.org/bot{tok}/sendMessage", json={"chat_id": chat, "text": text}, timeout=10)
    except Exception:  # noqa
        pass
