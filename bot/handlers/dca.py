from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, BufferedInputFile
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards.inline import (
    coin_select_kb,
    dca_interval_kb,
    dca_period_kb,
    back_to_menu_kb,
)
from bot.services.coingecko import coingecko
from bot.services.dca_service import simulate_dca
from bot.services.chart_service import generate_dca_chart
from bot.states.states import DCAStates
from bot.utils.formatters import format_price, format_percent, pnl_emoji

router = Router(name="dca")


# ── DCA Menu ──────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "dca")
async def cb_dca(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(DCAStates.waiting_for_coin_search)
    await callback.message.edit_text(
        "📐 <b>DCA Калькулятор</b>\n\n"
        "Симулируй стратегию Dollar Cost Averaging "
        "на исторических данных.\n\n"
        "Введи название или тикер монеты:",
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(DCAStates.waiting_for_coin_search)
async def msg_dca_search(message: Message, state: FSMContext) -> None:
    coins = await coingecko.search_coins(message.text.strip())
    if not coins:
        await message.answer("😕 Ничего не найдено. Попробуй снова:")
        return

    await state.set_state(DCAStates.waiting_for_coin_select)
    await message.answer(
        "Выбери монету:",
        reply_markup=coin_select_kb(coins, prefix="dca_coin"),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("dca_coin:"), DCAStates.waiting_for_coin_select)
async def cb_dca_select(callback: CallbackQuery, state: FSMContext) -> None:
    _, coin_id, symbol, name = callback.data.split(":", 3)
    await state.update_data(coin_id=coin_id, symbol=symbol, coin_name=name)
    await state.set_state(DCAStates.waiting_for_amount)

    await callback.message.edit_text(
        f"📌 <b>{name} ({symbol})</b>\n\n"
        f"Введи сумму покупки за один раз (в USD):\n"
        f"Например: <code>100</code>",
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(DCAStates.waiting_for_amount)
async def msg_dca_amount(message: Message, state: FSMContext) -> None:
    try:
        amount = float(message.text.strip().replace(",", "."))
        if amount <= 0:
            raise ValueError
    except ValueError:
        await message.answer("❌ Введи корректное число > 0:")
        return

    await state.update_data(amount_per_buy=amount)
    await state.set_state(DCAStates.waiting_for_interval)

    await message.answer(
        f"💵 Сумма: <b>{format_price(amount)}</b> за раз\n\n"
        f"Выбери интервал покупок:",
        reply_markup=dca_interval_kb(),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("dca_interval:"), DCAStates.waiting_for_interval)
async def cb_dca_interval(callback: CallbackQuery, state: FSMContext) -> None:
    interval = int(callback.data.split(":")[1])
    await state.update_data(interval_days=interval)
    await state.set_state(DCAStates.waiting_for_period)

    interval_names = {1: "ежедневно", 7: "еженедельно", 14: "каждые 2 нед.", 30: "ежемесячно"}
    await callback.message.edit_text(
        f"📅 Интервал: <b>{interval_names.get(interval, f'{interval} дн.')}</b>\n\n"
        f"Выбери период симуляции:",
        reply_markup=dca_period_kb(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("dca_period:"), DCAStates.waiting_for_period)
async def cb_dca_period(callback: CallbackQuery, state: FSMContext) -> None:
    total_days = int(callback.data.split(":")[1])
    data = await state.get_data()

    await callback.answer("📐 Запускаю симуляцию...")

    try:
        result = await simulate_dca(
            coin_id=data["coin_id"],
            amount_per_buy=data["amount_per_buy"],
            interval_days=data["interval_days"],
            total_days=total_days,
        )
    except Exception as e:
        await state.clear()
        await callback.message.edit_text(
            f"❌ Ошибка симуляции: {e}",
            reply_markup=back_to_menu_kb(),
            parse_mode="HTML",
        )
        return

    # Generate chart
    chart_bytes = generate_dca_chart(
        dates=result.dates,
        portfolio_values=result.portfolio_values,
        total_invested=result.invested_over_time,
        lump_sum_values=result.lump_sum_values,
        coin_name=f"{result.coin_name} ({result.symbol})",
    )

    emoji = pnl_emoji(result.pnl_percent)
    sign = "+" if result.pnl >= 0 else ""

    caption = (
        f"📐 <b>DCA Симуляция — {result.coin_name} ({result.symbol})</b>\n\n"
        f"💵 Инвестировано: <b>{format_price(result.total_invested)}</b>\n"
        f"📦 Накоплено: <b>{result.total_coins:.6g} {result.symbol}</b>\n"
        f"💰 Средняя цена: <b>{format_price(result.average_price)}</b>\n"
        f"📈 Текущая цена: <b>{format_price(result.current_price)}</b>\n"
        f"🏦 Стоимость: <b>{format_price(result.portfolio_value)}</b>\n"
        f"{emoji} P&L: <b>{sign}{format_price(result.pnl)}</b> ({format_percent(result.pnl_percent)})\n"
        f"🔢 Покупок: {result.num_purchases}"
    )

    await state.clear()
    await callback.message.delete()
    await callback.message.answer_photo(
        photo=BufferedInputFile(chart_bytes, filename="dca_simulation.png"),
        caption=caption,
        reply_markup=back_to_menu_kb(),
        parse_mode="HTML",
    )
