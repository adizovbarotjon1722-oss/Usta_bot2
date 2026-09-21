from __future__ import annotations

from fastapi import FastAPI

from database import init_db
from monitoring import init_sentry
from payments.click import router as click_router
from payments.payme import router as payme_router

init_sentry()

app = FastAPI(title="To'lov webhooklari")
app.include_router(payme_router)
app.include_router(click_router)


@app.on_event("startup")
async def on_startup() -> None:
    await init_db()


@app.get("/health")
async def health() -> dict:
    """Server ishlab turganini tekshirish uchun oddiy endpoint."""
    return {"status": "ok"}
