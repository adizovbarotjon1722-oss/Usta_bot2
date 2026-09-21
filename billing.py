from __future__ import annotations


def apply_promo_discount(base_price: float, discount_percent: float) -> float:
    """Promo-kod chegirmasi miqdorini (so'mda) qaytaradi."""
    return base_price * discount_percent / 100


def apply_bonus_balance(price_after_promo: float, bonus_balance: float) -> tuple[float, float]:
    """Bonus balansidan qancha ishlatilishini va yakuniy narxni hisoblaydi.
    Qaytaradi: (yakuniy_narx, ishlatilgan_bonus)."""
    bonus_used = max(min(bonus_balance, price_after_promo), 0.0)
    final_price = price_after_promo - bonus_used
    return final_price, bonus_used


def calculate_commission(price: float, commission_percent: float) -> float:
    """Platforma komissiyasi miqdorini (so'mda) hisoblaydi."""
    return price * commission_percent / 100
