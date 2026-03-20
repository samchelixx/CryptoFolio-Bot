from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.crud import (
    get_or_create_user,
    get_default_portfolio,
    get_portfolio_assets,
    add_or_update_asset,
    remove_asset,
    get_recent_transactions,
)
from bot.keyboards.inline import (
    portfolio_menu_kb,
    coin_select_kb,
    asset_select_kb,
    confirm_kb,
    back_to_menu_kb,
)
from bot.services.coingecko import coingecko
from bot.services.portfolio_service import calculate_portfolio
from bot.states.states import AddAssetStates, SellAssetStates
from bot.utils.formatters import format_asset_line, format_price, format_percent, pnl_emoji

router = Router(name="portfolio")


# ── View Portfolio ────────────────────────────────────────────────────────────

@router.callback_query(F.data == "portfolio")
async def cb_portfolio(callback: CallbackQuery, session: AsyncSession) -> None:
    user = await get_or_create_user(session, callback.from_user.id)
    portfolio = await get_default_portfolio(session, user.id)

    if not portfolio or not portfolio.assets:
        text = (
            "💼 <b>Портфель пуст</b>\n\n"
            "Добавь первый актив, чтобы начать отслеживать свои инвестиции!"
        )
        await callback.message.edit_text(text, reply_markup=portfolio_menu_kb(), parse_mode="HTML")
        await callback.answer()
        return

    summary = await calculate_portfolio(portfolio.assets, user.currency)

    emoji = pnl_emoji(summary.total_pnl_percent)
    sign = "+" if summary.total_pnl >= 0 else ""

    lines = [
        f"💼 <b>Портфель «{portfolio.name}»</b>\n",
        f"💰 Стоимость: <b>{format_price(summary.total_value, user.currency)}</b>",
        f"💵 Инвестировано: {format_price(summary.total_invested, user.currency)}",
        f"{emoji} P&L: <b>{sign}{format_price(summary.total_pnl, user.currency)}</b> ({format_percent(summary.total_pnl_percent)})",
        f"📦 Активов: {summary.num_assets}\n",
        "━━━━━━━━━━━━━━━━━━━━\n",
    ]

    for asset_a in summary.assets:
        lines.append(
            format_asset_line(
                asset_a.symbol, asset_a.amount,
                asset_a.current_value, asset_a.pnl,
                asset_a.pnl_percent, user.currency,
            )
        )
        lines.append("")

    if summary.best_performer:
        lines.append(
            f"\n🏆 Лучший: <b>{summary.best_performer.symbol}</b> "
            f"({format_percent(summary.best_performer.pnl_percent)})"
        )
    if summary.worst_performer:
        lines.append(
            f"💀 Худший: <b>{summary.worst_performer.symbol}</b> "
            f"({format_percent(summary.worst_performer.pnl_percent)})"
        )

    await callback.message.edit_text(
        "\n".join(lines), reply_markup=portfolio_menu_kb(), parse_mode="HTML"
    )
    await callback.answer()


# ── Add Asset Flow ────────────────────────────────────────────────────────────

@router.callback_query(F.data == "add_asset")
async def cb_add_asset(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(AddAssetStates.waiting_for_coin_search)
    await callback.message.edit_text(
        "🔍 <b>Добавление актива</b>\n\n"
        "Введи название или тикер монеты (например: <code>bitcoin</code> или <code>ETH</code>):",
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(AddAssetStates.waiting_for_coin_search)
async def msg_search_coin_add(message: Message, state: FSMContext) -> None:
    query = message.text.strip()
    coins = await coingecko.search_coins(query)

    if not coins:
        await message.answer(
            "😕 Ничего не найдено. Попробуй другой запрос:",
            parse_mode="HTML",
        )
        return

    await state.set_state(AddAssetStates.waiting_for_coin_select)
    await message.answer(
        "🔍 <b>Результаты поиска:</b>\nВыбери монету:",
        reply_markup=coin_select_kb(coins, prefix="add_coin"),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("add_coin:"), AddAssetStates.waiting_for_coin_select)
async def cb_select_coin_add(callback: CallbackQuery, state: FSMContext) -> None:
    _, coin_id, symbol, name = callback.data.split(":", 3)
    await state.update_data(coin_id=coin_id, symbol=symbol, coin_name=name)
    await state.set_state(AddAssetStates.waiting_for_amount)

    # Fetch current price for reference
    prices = await coingecko.get_price([coin_id])
    current = prices.get(coin_id, {}).get("usd", 0)
    await state.update_data(current_price=current)

    await callback.message.edit_text(
        f"📌 <b>{name} ({symbol})</b>\n"
        f"💰 Текущая цена: <b>{format_price(current)}</b>\n\n"
        f"Введи количество монет для покупки:",
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(AddAssetStates.waiting_for_amount)
async def msg_amount_add(message: Message, state: FSMContext) -> None:
    try:
        amount = float(message.text.strip().replace(",", "."))
        if amount <= 0:
            raise ValueError
    except ValueError:
        await message.answer("❌ Введи корректное число > 0:")
        return

    await state.update_data(amount=amount)
    data = await state.get_data()
    await state.set_state(AddAssetStates.waiting_for_price)

    await message.answer(
        f"💵 Введи цену покупки за 1 {data['symbol']}.\n"
        f"Или отправь <code>0</code> для текущей цены ({format_price(data.get('current_price', 0))}):",
        parse_mode="HTML",
    )


@router.message(AddAssetStates.waiting_for_price)
async def msg_price_add(message: Message, state: FSMContext, session: AsyncSession) -> None:
    try:
        price = float(message.text.strip().replace(",", "."))
        if price < 0:
            raise ValueError
    except ValueError:
        await message.answer("❌ Введи корректное число ≥ 0:")
        return

    data = await state.get_data()
    if price == 0:
        price = data.get("current_price", 0)

    total = data["amount"] * price

    # Save directly
    user = await get_or_create_user(session, message.from_user.id)
    portfolio = await get_default_portfolio(session, user.id)

    await add_or_update_asset(
        session,
        portfolio_id=portfolio.id,
        coin_id=data["coin_id"],
        symbol=data["symbol"],
        name=data["coin_name"],
        amount=data["amount"],
        price=price,
        tx_type="buy",
    )

    await state.clear()
    await message.answer(
        f"✅ <b>Актив добавлен!</b>\n\n"
        f"🪙 {data['coin_name']} ({data['symbol']})\n"
        f"📦 Количество: <b>{data['amount']:.6g}</b>\n"
        f"💰 Цена: <b>{format_price(price)}</b>\n"
        f"💵 Итого: <b>{format_price(total)}</b>",
        reply_markup=back_to_menu_kb(),
        parse_mode="HTML",
    )


# ── Sell Asset Flow ───────────────────────────────────────────────────────────

@router.callback_query(F.data == "sell_asset")
async def cb_sell_asset(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    user = await get_or_create_user(session, callback.from_user.id)
    portfolio = await get_default_portfolio(session, user.id)

    if not portfolio or not portfolio.assets:
        await callback.message.edit_text("📭 Портфель пуст.", reply_markup=back_to_menu_kb(), parse_mode="HTML")
        await callback.answer()
        return

    await state.set_state(SellAssetStates.waiting_for_asset_select)
    await callback.message.edit_text(
        "➖ <b>Продажа актива</b>\nВыбери монету:",
        reply_markup=asset_select_kb(portfolio.assets, prefix="sell_coin"),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("sell_coin:"), SellAssetStates.waiting_for_asset_select)
async def cb_select_coin_sell(callback: CallbackQuery, state: FSMContext) -> None:
    _, asset_id, coin_id = callback.data.split(":", 2)
    await state.update_data(asset_id=int(asset_id), coin_id=coin_id)
    await state.set_state(SellAssetStates.waiting_for_amount)

    await callback.message.edit_text(
        "📦 Введи количество монет для продажи:",
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(SellAssetStates.waiting_for_amount)
async def msg_amount_sell(message: Message, state: FSMContext) -> None:
    try:
        amount = float(message.text.strip().replace(",", "."))
        if amount <= 0:
            raise ValueError
    except ValueError:
        await message.answer("❌ Введи корректное число > 0:")
        return

    await state.update_data(sell_amount=amount)
    await state.set_state(SellAssetStates.waiting_for_price)
    await message.answer(
        "💵 Введи цену продажи за 1 монету.\n"
        "Или отправь <code>0</code> для текущей рыночной цены:",
        parse_mode="HTML",
    )


@router.message(SellAssetStates.waiting_for_price)
async def msg_price_sell(message: Message, state: FSMContext, session: AsyncSession) -> None:
    try:
        price = float(message.text.strip().replace(",", "."))
        if price < 0:
            raise ValueError
    except ValueError:
        await message.answer("❌ Введи корректное число ≥ 0:")
        return

    data = await state.get_data()

    if price == 0:
        prices = await coingecko.get_price([data["coin_id"]])
        price = prices.get(data["coin_id"], {}).get("usd", 0)

    user = await get_or_create_user(session, message.from_user.id)
    portfolio = await get_default_portfolio(session, user.id)

    # Find the asset
    from bot.database.crud import get_asset
    asset = await get_asset(session, portfolio.id, data["coin_id"])
    if not asset:
        await message.answer("❌ Актив не найден.", reply_markup=back_to_menu_kb())
        await state.clear()
        return

    await add_or_update_asset(
        session,
        portfolio_id=portfolio.id,
        coin_id=data["coin_id"],
        symbol=asset.symbol,
        name=asset.name,
        amount=data["sell_amount"],
        price=price,
        tx_type="sell",
    )

    total = data["sell_amount"] * price
    await state.clear()
    await message.answer(
        f"✅ <b>Продажа записана!</b>\n\n"
        f"🪙 {asset.name} ({asset.symbol})\n"
        f"📦 Продано: <b>{data['sell_amount']:.6g}</b>\n"
        f"💰 Цена: <b>{format_price(price)}</b>\n"
        f"💵 Итого: <b>{format_price(total)}</b>",
        reply_markup=back_to_menu_kb(),
        parse_mode="HTML",
    )


# ── Remove Asset ──────────────────────────────────────────────────────────────

@router.callback_query(F.data == "remove_asset")
async def cb_remove_asset(callback: CallbackQuery, session: AsyncSession) -> None:
    user = await get_or_create_user(session, callback.from_user.id)
    portfolio = await get_default_portfolio(session, user.id)

    if not portfolio or not portfolio.assets:
        await callback.message.edit_text("📭 Портфель пуст.", reply_markup=back_to_menu_kb(), parse_mode="HTML")
        await callback.answer()
        return

    await callback.message.edit_text(
        "🗑 <b>Удаление актива</b>\nВыбери монету для полного удаления:",
        reply_markup=asset_select_kb(portfolio.assets, prefix="del_asset"),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("del_asset:"))
async def cb_confirm_remove(callback: CallbackQuery, session: AsyncSession) -> None:
    _, asset_id, _ = callback.data.split(":", 2)
    await remove_asset(session, int(asset_id))
    await callback.message.edit_text(
        "✅ Актив удалён из портфеля.",
        reply_markup=back_to_menu_kb(),
        parse_mode="HTML",
    )
    await callback.answer()


# ── Transactions ──────────────────────────────────────────────────────────────

@router.callback_query(F.data == "transactions")
async def cb_transactions(callback: CallbackQuery, session: AsyncSession) -> None:
    user = await get_or_create_user(session, callback.from_user.id)
    portfolio = await get_default_portfolio(session, user.id)

    if not portfolio:
        await callback.message.edit_text("📭 Портфель пуст.", reply_markup=back_to_menu_kb(), parse_mode="HTML")
        await callback.answer()
        return

    txs = await get_recent_transactions(session, portfolio.id, limit=15)

    if not txs:
        await callback.message.edit_text(
            "📜 <b>Транзакции</b>\n\nПока нет транзакций.",
            reply_markup=back_to_menu_kb(),
            parse_mode="HTML",
        )
        await callback.answer()
        return

    lines = ["📜 <b>Последние транзакции:</b>\n"]
    for tx in txs:
        emoji = "🟢" if tx.type == "buy" else "🔴"
        action = "Покупка" if tx.type == "buy" else "Продажа"
        dt = tx.created_at.strftime("%d.%m %H:%M")
        lines.append(
            f"{emoji} <b>{action}</b> — {format_price(tx.total)}\n"
            f"   {tx.amount:.6g} × {format_price(tx.price)} • {dt}"
        )
        lines.append("")

    await callback.message.edit_text(
        "\n".join(lines), reply_markup=back_to_menu_kb(), parse_mode="HTML"
    )
    await callback.answer()
