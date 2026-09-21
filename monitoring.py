from __future__ import annotations

from config import SENTRY_DSN


def init_sentry() -> None:
    """SENTRY_DSN sozlangan bo'lsa, xatolarni kuzatishni yoqadi.
    Bo'sh bo'lsa, hech narsa qilmaydi - Sentry ixtiyoriy."""
    if not SENTRY_DSN:
        return
    import sentry_sdk

    sentry_sdk.init(dsn=SENTRY_DSN, traces_sample_rate=0.1, send_default_pii=False)
