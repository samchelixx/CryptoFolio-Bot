import logging
from typing import TYPE_CHECKING

from aiogram import Bot

from bot.database import async_session_factory
from bot.database.crud import get_active_alerts, deactivate_alert
from bot.services.coingecko import coingecko
from bot.utils.formatters import format_price

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


async def check_alerts(bot: Bot) -> None:
    async with async_session_factory() as session:
        alerts = await get_active_alerts(session)
        if not alerts:
            return

        coin_ids = list({a.coin_id for a in alerts})
        try:
            prices = await coingecko.get_price(coin_ids, vs_currency="usd")
        except Exception as e:
            logger.error("Failed to fetch prices for alerts: %s", e)
            return

        triggered = []
        for alert in alerts:
            price_data = prices.get(alert.coin_id, {})
            current_price = price_data.get("usd", 0)
            if current_price <= 0:
                continue

            should_trigger = False
            if alert.direction == "above" and current_price >= alert.target_price:
                should_trigger = True
            elif alert.direction == "below" and current_price <= alert.target_price:
                should_trigger = True

            if should_trigger:
                triggered.append((alert, current_price))
                await deactivate_alert(session, alert.id)

        for alert, current_price in triggered:
            arrow = "🔺" if alert.direction == "above" else "🔻"
            direction_text = "выше" if alert.direction == "above" else "ниже"

            text = (
                f"{arrow} <b>Алерт сработал!</b>\n\n"
                f"Монета: <b>{alert.symbol}</b>\n"
                f"Текущая цена: <b>{format_price(current_price)}</b>\n"
                f"Целевая цена: <b>{format_price(alert.target_price)}</b>\n"
                f"Условие: цена {direction_text} {format_price(alert.target_price)}\n\n"
                f"⏰ Алерт деактивирован."
            )

            try:
                from bot.database.models import User
                from sqlalchemy import select
                stmt = select(User).where(User.id == alert.user_id)
                result = await session.execute(stmt)
                user = result.scalar_one_or_none()
                if user:
                    await bot.send_message(
                        chat_id=user.telegram_id,
                        text=text,
                        parse_mode="HTML",
                    )
                    logger.info(
                        "Alert triggered: %s %s at %s for user %s",
                        alert.symbol, alert.direction, current_price, user.telegram_id,
                    )
            except Exception as e:
                logger.error("Failed to send alert notification: %s", e)
