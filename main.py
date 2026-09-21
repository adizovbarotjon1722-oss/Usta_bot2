import asyncio
import datetime
import logging

from aiogram import Bot, Dispatcher
from sqlalchemy import select

import client_bot
import driver_bot
from config import CLIENT_BOT_TOKEN, DRIVER_BOT_TOKEN, SCHEDULED_ORDER_CHECK_INTERVAL_SECONDS
from database import Order, User, async_session, init_db
from monitoring import init_sentry
from throttling import ThrottlingMiddleware
from translations import t


async def scheduled_orders_worker(driver_bot_instance: Bot, client_bot_instance: Bot) -> None:
    """Fon vazifasi: rejalashtirilgan buyurtmalarning vaqti kelganini muntazam
    tekshiradi va o'sha payt kelganda haydovchilarga yuboradi."""
    while True:
        try:
            now = datetime.datetime.now()
            async with async_session() as session:
                result = await session.execute(
                    select(Order).where(
                        Order.scheduled_for.is_not(None),
                        Order.scheduled_for <= now,
                        Order.status == "pending",
                        Order.driver_id.is_(None),
                    )
                )
                due_orders = result.scalars().all()
                due_order_data = []
                for o in due_orders:
                    user = await session.get(User, o.user_id)
                    due_order_data.append((o.id, o.order_type, user.telegram_id, user.language))

            for order_id, order_type, user_telegram_id, user_lang in due_order_data:
                vehicle_type = "car" if order_type == "taxi" else None
                await client_bot.dispatch_order_to_driver(order_id, driver_bot_instance, vehicle_type=vehicle_type)
                try:
                    await client_bot_instance.send_message(
                        user_telegram_id, t("scheduled_dispatching", user_lang, order_id=order_id)
                    )
                except Exception:
                    pass
        except Exception:
            logging.exception("scheduled_orders_worker xatosi")

        await asyncio.sleep(SCHEDULED_ORDER_CHECK_INTERVAL_SECONDS)


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    init_sentry()

    if not CLIENT_BOT_TOKEN or not DRIVER_BOT_TOKEN:
        raise RuntimeError(
            "CLIENT_BOT_TOKEN va DRIVER_BOT_TOKEN .env faylida to'ldirilishi kerak. "
            "Namuna uchun .env.example fayliga qarang."
        )

    await init_db()

    client_bot_instance = Bot(token=CLIENT_BOT_TOKEN)
    driver_bot_instance = Bot(token=DRIVER_BOT_TOKEN)

    dp_client = Dispatcher()
    dp_client.update.outer_middleware(ThrottlingMiddleware())
    dp_client.include_router(client_bot.router)

    dp_driver = Dispatcher()
    dp_driver.update.outer_middleware(ThrottlingMiddleware())
    dp_driver.include_router(driver_bot.router)

    # Har bir bot ikkinchisining Bot obyektiga kirisha oladi (workflow_data orqali),
    # shunda mijoz botidan haydovchiga va aksincha xabar yuborish mumkin.
    # dp_client ham uzatiladi - driver_bot buyurtma yakunlanganda mijozning
    # FSM holatini "reyting kutmoqda" ga o'tkazishi uchun kerak.
    await asyncio.gather(
        dp_client.start_polling(client_bot_instance, driver_bot=driver_bot_instance),
        dp_driver.start_polling(driver_bot_instance, client_bot=client_bot_instance, client_dp=dp_client),
        scheduled_orders_worker(driver_bot_instance, client_bot_instance),
    )


if __name__ == "__main__":
    asyncio.run(main())
