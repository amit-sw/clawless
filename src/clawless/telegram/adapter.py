from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

import requests


@dataclass
class TelegramUpdate:
    update_id: int
    message_id: int
    user_id: int
    chat_id: int
    text: str


class TelegramAdapter:
    def __init__(self, token: str, owner_user_id: int, timeout: int = 30):
        self.token = token
        self.owner_user_id = owner_user_id
        self.timeout = timeout
        self.base_url = f"https://api.telegram.org/bot{token}"
        self.offset = None

    def poll(self) -> list[TelegramUpdate]:
        params: dict[str, Any] = {"timeout": self.timeout}
        if self.offset is not None:
            params["offset"] = self.offset
        resp = requests.get(f"{self.base_url}/getUpdates", params=params, timeout=self.timeout + 5)
        resp.raise_for_status()
        data = resp.json()
        if not data.get("ok"):
            return []
        updates = []
        for item in data.get("result", []):
            update = self._parse_update(item)
            if update:
                updates.append(update)
                self.offset = update.update_id + 1
        return updates

    def send_message(self, chat_id: int, text: str) -> None:
        resp = requests.post(
            f"{self.base_url}/sendMessage",
            data={"chat_id": chat_id, "text": text},
            timeout=self.timeout,
        )
        resp.raise_for_status()

    def _parse_update(self, item: dict[str, Any]) -> TelegramUpdate | None:
        message = item.get("message")
        if not message:
            return None
        text = message.get("text")
        if not text:
            return None
        user = message.get("from", {})
        if user.get("id") != self.owner_user_id:
            return None
        return TelegramUpdate(
            update_id=int(item.get("update_id")),
            message_id=int(message.get("message_id")),
            user_id=int(user.get("id")),
            chat_id=int(message.get("chat", {}).get("id")),
            text=str(text),
        )
