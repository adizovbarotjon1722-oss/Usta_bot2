from __future__ import annotations

import datetime
import random

import jwt
from fastapi import Header, HTTPException
from sqlalchemy import select

from config import JWT_EXPIRY_DAYS, JWT_SECRET_KEY, OTP_EXPIRY_MINUTES, OTP_LENGTH, OTP_MAX_ATTEMPTS, OTP_REQUEST_COOLDOWN_SECONDS
from database import OtpCode, User, async_session


class OtpCooldownError(Exception):
    """Shu telefon uchun juda tez-tez kod so'ralganda ko'tariladi."""

    def __init__(self, retry_after_seconds: int):
        self.retry_after_seconds = retry_after_seconds
        super().__init__(f"{retry_after_seconds} soniyadan keyin qayta urining")


def generate_otp_code() -> str:
    return "".join(random.choices("0123456789", k=OTP_LENGTH))


async def create_otp(phone: str) -> str:
    async with async_session() as session:
        result = await session.execute(
            select(OtpCode).where(OtpCode.phone == phone).order_by(OtpCode.created_at.desc())
        )
        last = result.scalars().first()
        if last:
            elapsed = (datetime.datetime.utcnow() - last.created_at).total_seconds()
            if elapsed < OTP_REQUEST_COOLDOWN_SECONDS:
                raise OtpCooldownError(int(OTP_REQUEST_COOLDOWN_SECONDS - elapsed))

        code = generate_otp_code()
        expires_at = datetime.datetime.utcnow() + datetime.timedelta(minutes=OTP_EXPIRY_MINUTES)
        session.add(OtpCode(phone=phone, code=code, expires_at=expires_at))
        await session.commit()
    return code


async def verify_otp(phone: str, code: str) -> bool:
    """Kod to'g'ri va muddati o'tmagan bo'lsa True qaytaradi, va uni "ishlatilgan"
    deb belgilaydi (qayta ishlatib bo'lmaydi). Noto'g'ri urinishlar sanaladi -
    OTP_MAX_ATTEMPTS dan oshsa, kod avtomatik bloklanadi (bruteforce himoyasi)."""
    async with async_session() as session:
        result = await session.execute(
            select(OtpCode)
            .where(OtpCode.phone == phone, OtpCode.is_used.is_(False))
            .order_by(OtpCode.created_at.desc())
        )
        otp = result.scalars().first()
        if not otp or otp.expires_at < datetime.datetime.utcnow():
            return False
        if otp.attempts >= OTP_MAX_ATTEMPTS:
            otp.is_used = True
            await session.commit()
            return False
        if otp.code != code:
            otp.attempts += 1
            await session.commit()
            return False
        otp.is_used = True
        await session.commit()
    return True


def create_access_token(user_id: int) -> str:
    payload = {
        "sub": str(user_id),
        "exp": datetime.datetime.utcnow() + datetime.timedelta(days=JWT_EXPIRY_DAYS),
        "iat": datetime.datetime.utcnow(),
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm="HS256")


async def get_current_user(authorization: str = Header(default="")) -> User:
    """FastAPI dependency: `Authorization: Bearer <token>` headerini tekshiradi
    va joriy foydalanuvchini qaytaradi. Noto'g'ri/eskirgan token bo'lsa 401."""
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token talab qilinadi")
    token = authorization.removeprefix("Bearer ").strip()
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=["HS256"])
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Token yaroqsiz yoki muddati tugagan")

    user_id = int(payload["sub"])
    async with async_session() as session:
        user = await session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=401, detail="Foydalanuvchi topilmadi")
    return user
