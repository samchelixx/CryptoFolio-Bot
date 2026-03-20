from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.crud import (
    get_or_create_user,
    add_to_watchlist,
    get_watchlist,
    remove_from_watchlist,
)
from bot.keyboards.inline import (
    tracking_menu_kb,
    coin_select_kb,
    back_to_menu_kb,
)
from bot.services.coingecko import coingecko
from bot.states.states import PriceCheckStates, WatchlistStates
from bot.utils.formatters import format_coin_price, format_price, change_emoji, format_percent

router = Router(name="tracking")


# ── Tracking Menu ─────────────────────────────────────────────────────────────

@router.callback_query(F.data == "tracking")
async def cb_tracking(callback: CallbackQuery) -> None:
    await callback.message.edit_text(
        "📈 <b>Отслеживание цен</b>\n\nВыбери действие:",
        reply_markup=tracking_menu_kb(),
        parse_mode="HTML",
    )
    await callback.answer()


# ── Quick Price Check ─────────────────────────────────────────────────────────

@router.message(Command("price"))
async def cmd_price(message: Message) -> None:
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer(
            "Использование: /price <code>BTC</code>",
            parse_mode="HTML",
        )
        return

    query = args[1].strip()
    coins = await coingecko.search_coins(query)
    if not coins:
        await message.answer("😕 Монета не найдена.")
        return

    coin = coins[0]
    coin_id = coin["id"]
    prices = await coingecko.get_price([coin_id], include_change=True)
    data = prices.get(coin_id, {})

    text = format_coin_price(
        name=coin["name"],
        symbol=coin.get("symbol", ""),
        price=data.get("usd", 0),
        change_24h=data.get("usd_24h_change"),
        market_cap=data.get("usd_market_cap"),
        volume=data.get("usd_24h_vol"),
    )
    await message.answer(text, parse_mode="HTML")


@router.callback_query(F.data == "check_price")
async def cb_check_price(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(PriceCheckStates.waiting_for_coin)
    await callback.message.edit_text(
        "🔍 Введи название или тикер монеты:",
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(PriceCheckStates.waiting_for_coin)
async def msg_price_check(message: Message, state: FSMContext) -> None:
    query = message.text.strip()
    coins = await coingecko.search_coins(query)
    if not coins:
        await message.answer("😕 Ничего не найдено. Попробуй снова:")
        return

    coin = coins[0]
    coin_id = coin["id"]
    prices = await coingecko.get_price([coin_id], include_change=True)
    data = prices.get(coin_id, {})

    text = format_coin_price(
        name=coin["name"],
        symbol=coin.get("symbol", ""),
        price=data.get("usd", 0),
        change_24h=data.get("usd_24h_change"),
        market_cap=data.get("usd_market_cap"),
        volume=data.get("usd_24h_vol"),
    )

    await state.clear()
    await message.answer(text, reply_markup=tracking_menu_kb(), parse_mode="HTML")


# ── Trending Coins ────────────────────────────────────────────────────────────

@router.callback_query(F.data == "trending")
async def cb_trending(callback: CallbackQuery) -> None:
    trending = await coingecko.get_trending()

    lines = ["🔥 <b>Трендовые монеты:</b>\n"]
    for i, coin in enumerate(trending[:10], 1):
        name = coin.get("name", "?")
        symbol = coin.get("symbol", "?").upper()
        rank = coin.get("market_cap_rank", "—")
        lines.append(f"{i}. <b>{symbol}</b> — {name} (#{rank})")

    await callback.message.edit_text(
        "\n".join(lines),
        reply_markup=tracking_menu_kb(),
        parse_mode="HTML",
    )
    await callback.answer()


# ── Top Coins ─────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "top_coins")
async def cb_top_coins(callback: CallbackQuery) -> None:
    markets = await coingecko.get_markets(per_page=15)

    lines = ["🏆 <b>Топ-15 по капитализации:</b>\n"]
    for coin in markets:
        symbol = coin.get("symbol", "?").upper()
        price = coin.get("current_price", 0)
        change = coin.get("price_change_percentage_24h", 0) or 0
        emoji = change_emoji(change)
        lines.append(
            f"{emoji} <b>{symbol}</b> — {format_price(price)} ({format_percent(change)})"
        )

    await callback.message.edit_text(
        "\n".join(lines),
        reply_markup=tracking_menu_kb(),
        parse_mode="HTML",
    )
    await callback.answer()


# ── Watchlist ─────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "watchlist")
async def cb_watchlist(callback: CallbackQuery, session: AsyncSession) -> None:
    user = await get_or_create_user(session, callback.from_user.id)
    items = await get_watchlist(session, user.id)

    if not items:
        await callback.message.edit_text(
            "👁 <b>Watchlist пуст</b>\n\n"
            "Добавь монеты для отслеживания!",
            reply_markup=tracking_menu_kb(),
            parse_mode="HTML",
        )
        await callback.answer()
        return

    coin_ids = [item.coin_id for item in items]
    prices = await coingecko.get_price(coin_ids, include_change=True)

    lines = ["👁 <b>Watchlist:</b>\n"]
    for item in items:
        data = prices.get(item.coin_id, {})
        price = data.get("usd", 0)
        change = data.get("usd_24h_change", 0) or 0
        emoji = change_emoji(change)
        lines.append(
            f"{emoji} <b>{item.symbol}</b> — {format_price(price)} ({format_percent(change)})"
        )

    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton

    builder = InlineKeyboardBuilder()
    for item in items:
        builder.row(
            InlineKeyboardButton(
                text=f"🗑 {item.symbol}",
                callback_data=f"rm_watch:{item.id}",
            )
        )
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="tracking"))

    await callback.message.edit_text(
        "\n".join(lines),
        reply_markup=builder.as_markup(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("rm_watch:"))
async def cb_remove_watchlist(callback: CallbackQuery, session: AsyncSession) -> None:
    item_id = int(callback.data.split(":")[1])
    await remove_from_watchlist(session, item_id)
    await callback.answer("✅ Удалено")
    # Refresh watchlist
    await cb_watchlist(callback, session)


# ── Add to Watchlist ──────────────────────────────────────────────────────────

@router.callback_query(F.data == "add_watchlist")
async def cb_add_watchlist(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(WatchlistStates.waiting_for_coin_search)
    await callback.message.edit_text(
        "➕ Введи название или тикер монеты для добавления в watchlist:",
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(WatchlistStates.waiting_for_coin_search)
async def msg_search_watchlist(message: Message, state: FSMContext) -> None:
    coins = await coingecko.search_coins(message.text.strip())
    if not coins:
        await message.answer("😕 Ничего не найдено. Попробуй снова:")
        return

    await state.set_state(WatchlistStates.waiting_for_coin_select)
    await message.answer(
        "Выбери монету:",
        reply_markup=coin_select_kb(coins, prefix="watch_coin"),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("watch_coin:"), WatchlistStates.waiting_for_coin_select)
async def cb_select_watchlist(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    _, coin_id, symbol, name = callback.data.split(":", 3)
    user = await get_or_create_user(session, callback.from_user.id)
    await add_to_watchlist(session, user.id, coin_id, symbol, name)

    await state.clear()
    await callback.message.edit_text(
        f"✅ <b>{name} ({symbol})</b> добавлен в watchlist!",
        reply_markup=tracking_menu_kb(),
        parse_mode="HTML",
    )
    await callback.answer()
