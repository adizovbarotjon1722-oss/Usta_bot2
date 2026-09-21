from __future__ import annotations

import time
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject


class ThrottlingMiddleware(BaseMiddleware):
    """Bitta foydalanuvchidan juda tez-tez kelgan xabar/tugma bosishlarni
    jimgina e'tiborsiz qoldiradi - spam va ortiqcha server yuklamasidan
    himoya qiladi. Xotirada ishlaydi (bitta jarayon uchun yetarli)."""

    def __init__(self, rate_limit_seconds: float = 0.6):
        self.rate_limit_seconds = rate_limit_seconds
        self._last_seen: dict[int, float] = {}

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user = data.get("event_from_user")
        if user is not None:
            now = time.monotonic()
            last = self._last_seen.get(user.id, 0.0)
            if now - last < self.rate_limit_seconds:
                return None
            self._last_seen[user.id] = now
        return await handler(event, data)
