from __future__ import annotations

import logging

import aiohttp

from config import SMS_API_EMAIL, SMS_API_PASSWORD, SMS_PROVIDER, SMS_SENDER_NAME

logger = logging.getLogger(__name__)

_eskiz_token: str | None = None


async def _get_eskiz_token(session: aiohttp.ClientSession) -> str | None:
    global _eskiz_token
    if _eskiz_token:
        return _eskiz_token
    try:
        async with session.post(
            "https://notify.eskiz.uz/api/auth/login",
            data={"email": SMS_API_EMAIL, "password": SMS_API_PASSWORD},
        ) as resp:
            data = await resp.json()
            _eskiz_token = data.get("data", {}).get("token")
            return _eskiz_token
    except Exception:
        logger.exception("Eskiz.uz tokenini olishda xato")
        return None


async def send_sms(phone: str, text: str) -> bool:
    """SMS yuboradi. SMS_PROVIDER sozlanmagan bo'lsa (standart holat), xabarni
    shunchaki logga yozadi va True qaytaradi - bu haqiqiy SMS xizmatisiz ham
    ishlab chiqishni/sinashni osonlashtiradi. api_server.py OTP so'rovida bu
    holatda kodni javobda ham qaytaradi ("dev_code"), shuning uchun test qilish
    uchun SMS shart emas."""
    if SMS_PROVIDER != "eskiz":
        logger.info("[DEV SMS -> %s]: %s", phone, text)
        return True

    try:
        async with aiohttp.ClientSession() as session:
            token = await _get_eskiz_token(session)
            if not token:
                return False
            async with session.post(
                "https://notify.eskiz.uz/api/message/sms/send",
                headers={"Authorization": f"Bearer {token}"},
                data={
                    "mobile_phone": phone.lstrip("+"),
                    "message": text,
                    "from": SMS_SENDER_NAME,
                },
            ) as resp:
                return resp.status == 200
    except Exception:
        logger.exception("SMS yuborishda xato")
        return False
