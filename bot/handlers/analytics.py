import io

from aiogram import Router, F
from aiogram.types import CallbackQuery, BufferedInputFile, Message
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.crud import get_or_create_user, get_default_portfolio
from bot.keyboards.inline import (
    analytics_menu_kb,
    period_select_kb,
    coin_select_kb,
    back_to_menu_kb,
)
from bot.services.coingecko import coingecko
from bot.services.portfolio_service import calculate_portfolio
from bot.services.chart_service import (
    generate_portfolio_pie,
    generate_pnl_chart,
    generate_price_chart,
    generate_candlestick,
)
from bot.utils.formatters import format_price, format_percent

router = Router(name="analytics")


# ── Analytics Menu ────────────────────────────────────────────────────────────

@router.callback_query(F.data == "analytics")
async def cb_analytics(callback: CallbackQuery) -> None:
    await callback.message.edit_text(
        "📊 <b>Аналитика</b>\n\nВыбери тип графика:",
        reply_markup=analytics_menu_kb(),
        parse_mode="HTML",
    )
    await callback.answer()


# ── Portfolio Pie Chart ───────────────────────────────────────────────────────

@router.callback_query(F.data == "chart_pie")
async def cb_chart_pie(callback: CallbackQuery, session: AsyncSession) -> None:
    user = await get_or_create_user(session, callback.from_user.id)
    portfolio = await get_default_portfolio(session, user.id)

    if not portfolio or not portfolio.assets:
        await callback.message.edit_text(
            "📭 Портфель пуст — нечего анализировать.",
            reply_markup=back_to_menu_kb(),
            parse_mode="HTML",
        )
        await callback.answer()
        return

    await callback.answer("📊 Генерирую график...")

    summary = await calculate_portfolio(portfolio.assets, user.currency)
    labels = [a.symbol for a in summary.assets]
    values = [a.current_value for a in summary.assets]

    chart_bytes = generate_portfolio_pie(labels, values, user.currency)

    await callback.message.delete()
    await callback.message.answer_photo(
        photo=BufferedInputFile(chart_bytes, filename="portfolio_pie.png"),
        caption=(
            f"📊 <b>Распределение портфеля</b>\n\n"
            f"💰 Стоимость: <b>{format_price(summary.total_value, user.currency)}</b>\n"
            f"📦 Активов: {summary.num_assets}"
        ),
        reply_markup=analytics_menu_kb(),
        parse_mode="HTML",
    )


# ── P&L Chart ─────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "chart_pnl")
async def cb_chart_pnl(callback: CallbackQuery, session: AsyncSession) -> None:
    user = await get_or_create_user(session, callback.from_user.id)
    portfolio = await get_default_portfolio(session, user.id)

    if not portfolio or not portfolio.assets:
        await callback.message.edit_text(
            "📭 Портфель пуст.", reply_markup=back_to_menu_kb(), parse_mode="HTML"
        )
        await callback.answer()
        return

    await callback.answer("💰 Генерирую P&L...")

    summary = await calculate_portfolio(portfolio.assets, user.currency)
    symbols = [a.symbol for a in summary.assets]
    pnl_vals = [a.pnl for a in summary.assets]
    pnl_pcts = [a.pnl_percent for a in summary.assets]

    chart_bytes = generate_pnl_chart(symbols, pnl_vals, pnl_pcts)

    sign = "+" if summary.total_pnl >= 0 else ""
    await callback.message.delete()
    await callback.message.answer_photo(
        photo=BufferedInputFile(chart_bytes, filename="pnl_chart.png"),
        caption=(
            f"💰 <b>Profit & Loss</b>\n\n"
            f"Общий P&L: <b>{sign}{format_price(summary.total_pnl, user.currency)}</b> "
            f"({format_percent(summary.total_pnl_percent)})"
        ),
        reply_markup=analytics_menu_kb(),
        parse_mode="HTML",
    )


# ── Price Chart (Line) ────────────────────────────────────────────────────────

@router.callback_query(F.data == "chart_price")
async def cb_chart_price_menu(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    user = await get_or_create_user(session, callback.from_user.id)
    portfolio = await get_default_portfolio(session, user.id)

    if portfolio and portfolio.assets:
        from aiogram.utils.keyboard import InlineKeyboardBuilder
        from aiogram.types import InlineKeyboardButton

        builder = InlineKeyboardBuilder()
        for asset in portfolio.assets:
            builder.row(
                InlineKeyboardButton(
                    text=f"📈 {asset.symbol} — {asset.name}",
                    callback_data=f"price_chart_coin:{asset.coin_id}",
                )
            )
        builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="analytics"))

        await callback.message.edit_text(
            "📈 <b>График цены</b>\nВыбери монету:",
            reply_markup=builder.as_markup(),
            parse_mode="HTML",
        )
    else:
        await callback.message.edit_text(
            "📈 <b>График цены</b>\n\n"
            "Введи название монеты:",
            parse_mode="HTML",
        )
        from bot.states.states import PriceCheckStates
        await state.set_state(PriceCheckStates.waiting_for_coin)

    await callback.answer()


@router.callback_query(F.data.startswith("price_chart_coin:"))
async def cb_price_chart_select(callback: CallbackQuery) -> None:
    coin_id = callback.data.split(":")[1]
    await callback.message.edit_text(
        "📅 Выбери период:",
        reply_markup=period_select_kb(coin_id, chart_type="line"),
        parse_mode="HTML",
    )
    await callback.answer()


# ── Candlestick Chart ────────────────────────────────────────────────────────

@router.callback_query(F.data == "chart_candle")
async def cb_chart_candle_menu(callback: CallbackQuery, session: AsyncSession) -> None:
    user = await get_or_create_user(session, callback.from_user.id)
    portfolio = await get_default_portfolio(session, user.id)

    if portfolio and portfolio.assets:
        from aiogram.utils.keyboard import InlineKeyboardBuilder
        from aiogram.types import InlineKeyboardButton

        builder = InlineKeyboardBuilder()
        for asset in portfolio.assets:
            builder.row(
                InlineKeyboardButton(
                    text=f"🕯 {asset.symbol} — {asset.name}",
                    callback_data=f"candle_chart_coin:{asset.coin_id}",
                )
            )
        builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="analytics"))

        await callback.message.edit_text(
            "🕯 <b>Свечной график</b>\nВыбери монету:",
            reply_markup=builder.as_markup(),
            parse_mode="HTML",
        )
    else:
        await callback.message.edit_text(
            "📭 Добавь монеты в портфель для просмотра графиков.",
            reply_markup=back_to_menu_kb(),
            parse_mode="HTML",
        )
    await callback.answer()


@router.callback_query(F.data.startswith("candle_chart_coin:"))
async def cb_candle_chart_select(callback: CallbackQuery) -> None:
    coin_id = callback.data.split(":")[1]
    await callback.message.edit_text(
        "📅 Выбери период:",
        reply_markup=period_select_kb(coin_id, chart_type="candle"),
        parse_mode="HTML",
    )
    await callback.answer()


# ── Period Selection → Generate Chart ─────────────────────────────────────────

@router.callback_query(F.data.startswith("period:"))
async def cb_period_selected(callback: CallbackQuery) -> None:
    _, chart_type, coin_id, days_str = callback.data.split(":")
    days = int(days_str)

    await callback.answer(f"📊 Генерирую {days}D график...")

    if chart_type == "line":
        chart_data = await coingecko.get_market_chart(coin_id, days=days)
        prices_raw = chart_data.get("prices", [])

        if not prices_raw:
            await callback.message.edit_text("❌ Нет данных.", reply_markup=back_to_menu_kb())
            return

        timestamps = [p[0] for p in prices_raw]
        prices = [p[1] for p in prices_raw]

        coin_info = await coingecko.get_coin_info(coin_id)
        name = coin_info.get("name", coin_id)
        symbol = coin_info.get("symbol", coin_id)

        chart_bytes = generate_price_chart(timestamps, prices, name, symbol, days=days)

        await callback.message.delete()
        await callback.message.answer_photo(
            photo=BufferedInputFile(chart_bytes, filename=f"{coin_id}_price.png"),
            caption=f"📈 <b>{name} ({symbol.upper()})</b> — {days} дн.",
            reply_markup=analytics_menu_kb(),
            parse_mode="HTML",
        )

    elif chart_type == "candle":
        ohlc_data = await coingecko.get_ohlc(coin_id, days=days)

        if not ohlc_data:
            await callback.message.edit_text("❌ Нет данных.", reply_markup=back_to_menu_kb())
            return

        coin_info = await coingecko.get_coin_info(coin_id)
        name = coin_info.get("name", coin_id)
        symbol = coin_info.get("symbol", coin_id)

        chart_bytes = generate_candlestick(ohlc_data, name, symbol, days=days)

        await callback.message.delete()
        await callback.message.answer_photo(
            photo=BufferedInputFile(chart_bytes, filename=f"{coin_id}_candle.png"),
            caption=f"🕯 <b>{name} ({symbol.upper()})</b> — {days} дн. свечи",
            reply_markup=analytics_menu_kb(),
            parse_mode="HTML",
        )
