from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.crud import (
    get_or_create_user,
    create_alert,
    get_active_alerts,
    delete_alert,
)
from bot.keyboards.inline import (
    alerts_menu_kb,
    coin_select_kb,
    alert_direction_kb,
    back_to_menu_kb,
)
from bot.services.coingecko import coingecko
from bot.states.states import AlertStates
from bot.utils.formatters import format_price

router = Router(name="alerts")


# ── Alerts Menu ───────────────────────────────────────────────────────────────

@router.callback_query(F.data == "alerts")
async def cb_alerts(callback: CallbackQuery) -> None:
    await callback.message.edit_text(
        "🔔 <b>Ценовые алерты</b>\n\n"
        "Получай уведомление, когда цена монеты "
        "достигнет целевого значения.",
        reply_markup=alerts_menu_kb(),
        parse_mode="HTML",
    )
    await callback.answer()


# ── Create Alert Flow ─────────────────────────────────────────────────────────

@router.callback_query(F.data == "create_alert")
async def cb_create_alert(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(AlertStates.waiting_for_coin_search)
    await callback.message.edit_text(
        "🔔 <b>Новый алерт</b>\n\n"
        "Введи название или тикер монеты:",
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(AlertStates.waiting_for_coin_search)
async def msg_search_alert(message: Message, state: FSMContext) -> None:
    coins = await coingecko.search_coins(message.text.strip())
    if not coins:
        await message.answer("😕 Ничего не найдено. Попробуй снова:")
        return

    await state.set_state(AlertStates.waiting_for_coin_select)
    await message.answer(
        "Выбери монету:",
        reply_markup=coin_select_kb(coins, prefix="alert_coin"),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("alert_coin:"), AlertStates.waiting_for_coin_select)
async def cb_select_alert_coin(callback: CallbackQuery, state: FSMContext) -> None:
    _, coin_id, symbol, name = callback.data.split(":", 3)
    await state.update_data(coin_id=coin_id, symbol=symbol, coin_name=name)

    # Show current price
    prices = await coingecko.get_price([coin_id])
    current = prices.get(coin_id, {}).get("usd", 0)
    await state.update_data(current_price=current)

    await state.set_state(AlertStates.waiting_for_price)
    await callback.message.edit_text(
        f"📌 <b>{name} ({symbol})</b>\n"
        f"💰 Текущая цена: <b>{format_price(current)}</b>\n\n"
        f"Введи целевую цену для алерта:",
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(AlertStates.waiting_for_price)
async def msg_alert_price(message: Message, state: FSMContext) -> None:
    try:
        price = float(message.text.strip().replace(",", "."))
        if price <= 0:
            raise ValueError
    except ValueError:
        await message.answer("❌ Введи корректное число > 0:")
        return

    await state.update_data(target_price=price)
    data = await state.get_data()
    current = data.get("current_price", 0)

    # Auto-suggest direction
    suggested = "above" if price > current else "below"
    await state.set_state(AlertStates.waiting_for_direction)

    await message.answer(
        f"🎯 Целевая цена: <b>{format_price(price)}</b>\n"
        f"💰 Текущая: <b>{format_price(current)}</b>\n\n"
        f"Уведомить когда цена будет:",
        reply_markup=alert_direction_kb(),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("alert_dir:"), AlertStates.waiting_for_direction)
async def cb_alert_direction(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    direction = callback.data.split(":")[1]
    data = await state.get_data()

    user = await get_or_create_user(session, callback.from_user.id)
    alert = await create_alert(
        session,
        user_id=user.id,
        coin_id=data["coin_id"],
        symbol=data["symbol"],
        target_price=data["target_price"],
        direction=direction,
    )

    dir_text = "выше" if direction == "above" else "ниже"
    arrow = "🔺" if direction == "above" else "🔻"

    await state.clear()
    await callback.message.edit_text(
        f"✅ <b>Алерт создан!</b>\n\n"
        f"🪙 {data['coin_name']} ({data['symbol']})\n"
        f"{arrow} Условие: цена {dir_text} <b>{format_price(data['target_price'])}</b>\n\n"
        f"Ты получишь уведомление, когда цена достигнет цели.",
        reply_markup=alerts_menu_kb(),
        parse_mode="HTML",
    )
    await callback.answer()


# ── View Alerts ───────────────────────────────────────────────────────────────

@router.callback_query(F.data == "my_alerts")
async def cb_my_alerts(callback: CallbackQuery, session: AsyncSession) -> None:
    user = await get_or_create_user(session, callback.from_user.id)
    alerts = await get_active_alerts(session, user.id)

    if not alerts:
        await callback.message.edit_text(
            "🔔 <b>Нет активных алертов</b>\n\n"
            "Создай новый алерт, чтобы отслеживать цены!",
            reply_markup=alerts_menu_kb(),
            parse_mode="HTML",
        )
        await callback.answer()
        return

    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton

    lines = ["🔔 <b>Активные алерты:</b>\n"]
    builder = InlineKeyboardBuilder()

    for alert in alerts:
        arrow = "🔺" if alert.direction == "above" else "🔻"
        dir_text = "выше" if alert.direction == "above" else "ниже"
        lines.append(
            f"{arrow} <b>{alert.symbol}</b> — {dir_text} {format_price(alert.target_price)}"
        )
        builder.row(
            InlineKeyboardButton(
                text=f"🗑 {alert.symbol} {format_price(alert.target_price)}",
                callback_data=f"del_alert:{alert.id}",
            )
        )

    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="alerts"))

    await callback.message.edit_text(
        "\n".join(lines),
        reply_markup=builder.as_markup(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("del_alert:"))
async def cb_delete_alert(callback: CallbackQuery, session: AsyncSession) -> None:
    alert_id = int(callback.data.split(":")[1])
    await delete_alert(session, alert_id)
    await callback.answer("✅ Алерт удалён")
    await cb_my_alerts(callback, session)
