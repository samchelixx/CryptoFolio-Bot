from aiogram import Router, F
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.crud import get_or_create_user, update_user_settings
from bot.keyboards.inline import settings_menu_kb, currency_select_kb

router = Router(name="settings")


@router.callback_query(F.data == "settings")
async def cb_settings(callback: CallbackQuery, session: AsyncSession) -> None:
    user = await get_or_create_user(session, callback.from_user.id)
    await callback.message.edit_text(
        "⚙️ <b>Настройки</b>",
        reply_markup=settings_menu_kb(user.currency, user.language),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "change_currency")
async def cb_change_currency(callback: CallbackQuery) -> None:
    await callback.message.edit_text(
        "💱 <b>Выбери валюту отображения:</b>",
        reply_markup=currency_select_kb(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("set_currency:"))
async def cb_set_currency(callback: CallbackQuery, session: AsyncSession) -> None:
    currency = callback.data.split(":")[1]
    await update_user_settings(session, callback.from_user.id, currency=currency)

    names = {"usd": "🇺🇸 USD", "eur": "🇪🇺 EUR", "rub": "🇷🇺 RUB"}
    await callback.message.edit_text(
        f"✅ Валюта изменена на <b>{names.get(currency, currency.upper())}</b>",
        reply_markup=settings_menu_kb(currency),
        parse_mode="HTML",
    )
    await callback.answer()
