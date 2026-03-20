from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


# ── Main Menu ─────────────────────────────────────────────────────────────────

def main_menu_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="💼 Портфель", callback_data="portfolio"),
        InlineKeyboardButton(text="📈 Цены", callback_data="tracking"),
    )
    builder.row(
        InlineKeyboardButton(text="📊 Аналитика", callback_data="analytics"),
        InlineKeyboardButton(text="🔔 Алерты", callback_data="alerts"),
    )
    builder.row(
        InlineKeyboardButton(text="📐 DCA Калькулятор", callback_data="dca"),
        InlineKeyboardButton(text="⚙️ Настройки", callback_data="settings"),
    )
    return builder.as_markup()


# ── Portfolio ─────────────────────────────────────────────────────────────────

def portfolio_menu_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="➕ Добавить актив", callback_data="add_asset"),
        InlineKeyboardButton(text="➖ Продать", callback_data="sell_asset"),
    )
    builder.row(
        InlineKeyboardButton(text="📜 Транзакции", callback_data="transactions"),
        InlineKeyboardButton(text="🗑 Удалить актив", callback_data="remove_asset"),
    )
    builder.row(
        InlineKeyboardButton(text="🔄 Обновить", callback_data="portfolio"),
        InlineKeyboardButton(text="🔙 Меню", callback_data="main_menu"),
    )
    return builder.as_markup()


# ── Coin Selection ────────────────────────────────────────────────────────────

def coin_select_kb(coins: list[dict], prefix: str = "select_coin") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for coin in coins:
        coin_id = coin.get("id", "")
        name = coin.get("name", "")
        symbol = coin.get("symbol", "").upper()
        builder.row(
            InlineKeyboardButton(
                text=f"{symbol} — {name}",
                callback_data=f"{prefix}:{coin_id}:{symbol}:{name[:30]}",
            )
        )
    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data="cancel"))
    return builder.as_markup()


# ── Asset Selection ───────────────────────────────────────────────────────────

def asset_select_kb(assets: list, prefix: str = "select_asset") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for asset in assets:
        builder.row(
            InlineKeyboardButton(
                text=f"{asset.symbol} — {asset.amount:.6g} шт.",
                callback_data=f"{prefix}:{asset.id}:{asset.coin_id}",
            )
        )
    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data="cancel"))
    return builder.as_markup()


# ── Tracking ──────────────────────────────────────────────────────────────────

def tracking_menu_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🔍 Проверить цену", callback_data="check_price"),
        InlineKeyboardButton(text="🔥 Тренды", callback_data="trending"),
    )
    builder.row(
        InlineKeyboardButton(text="👁 Watchlist", callback_data="watchlist"),
        InlineKeyboardButton(text="➕ В watchlist", callback_data="add_watchlist"),
    )
    builder.row(
        InlineKeyboardButton(text="🏆 Топ монеты", callback_data="top_coins"),
        InlineKeyboardButton(text="🔙 Меню", callback_data="main_menu"),
    )
    return builder.as_markup()


# ── Analytics ─────────────────────────────────────────────────────────────────

def analytics_menu_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📊 Распределение", callback_data="chart_pie"),
        InlineKeyboardButton(text="💰 P&L", callback_data="chart_pnl"),
    )
    builder.row(
        InlineKeyboardButton(text="📈 График цены", callback_data="chart_price"),
        InlineKeyboardButton(text="🕯 Свечи", callback_data="chart_candle"),
    )
    builder.row(
        InlineKeyboardButton(text="🔙 Меню", callback_data="main_menu"),
    )
    return builder.as_markup()


# ── Chart period selection ────────────────────────────────────────────────────

def period_select_kb(coin_id: str, chart_type: str = "line") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    periods = [("1D", 1), ("7D", 7), ("30D", 30), ("90D", 90), ("1Y", 365)]
    row = []
    for label, days in periods:
        row.append(
            InlineKeyboardButton(
                text=label,
                callback_data=f"period:{chart_type}:{coin_id}:{days}",
            )
        )
    builder.row(*row)
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="analytics"))
    return builder.as_markup()


# ── Alerts ────────────────────────────────────────────────────────────────────

def alerts_menu_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="➕ Новый алерт", callback_data="create_alert"),
        InlineKeyboardButton(text="📋 Мои алерты", callback_data="my_alerts"),
    )
    builder.row(
        InlineKeyboardButton(text="🔙 Меню", callback_data="main_menu"),
    )
    return builder.as_markup()


def alert_direction_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🔺 Выше", callback_data="alert_dir:above"),
        InlineKeyboardButton(text="🔻 Ниже", callback_data="alert_dir:below"),
    )
    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data="cancel"))
    return builder.as_markup()


# ── DCA ───────────────────────────────────────────────────────────────────────

def dca_interval_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="Ежедневно", callback_data="dca_interval:1"),
        InlineKeyboardButton(text="Еженедельно", callback_data="dca_interval:7"),
    )
    builder.row(
        InlineKeyboardButton(text="Каждые 2 нед.", callback_data="dca_interval:14"),
        InlineKeyboardButton(text="Ежемесячно", callback_data="dca_interval:30"),
    )
    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data="cancel"))
    return builder.as_markup()


def dca_period_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="30 дней", callback_data="dca_period:30"),
        InlineKeyboardButton(text="90 дней", callback_data="dca_period:90"),
    )
    builder.row(
        InlineKeyboardButton(text="180 дней", callback_data="dca_period:180"),
        InlineKeyboardButton(text="1 год", callback_data="dca_period:365"),
    )
    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data="cancel"))
    return builder.as_markup()


# ── Settings ──────────────────────────────────────────────────────────────────

def settings_menu_kb(current_currency: str = "usd", current_lang: str = "ru") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    currencies = {"usd": "🇺🇸 USD", "eur": "🇪🇺 EUR", "rub": "🇷🇺 RUB"}
    curr_label = currencies.get(current_currency, current_currency.upper())
    builder.row(
        InlineKeyboardButton(text=f"💱 Валюта: {curr_label}", callback_data="change_currency"),
    )
    builder.row(
        InlineKeyboardButton(text="🔙 Меню", callback_data="main_menu"),
    )
    return builder.as_markup()


def currency_select_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🇺🇸 USD", callback_data="set_currency:usd"),
        InlineKeyboardButton(text="🇪🇺 EUR", callback_data="set_currency:eur"),
        InlineKeyboardButton(text="🇷🇺 RUB", callback_data="set_currency:rub"),
    )
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="settings"))
    return builder.as_markup()


# ── Confirm / Cancel ──────────────────────────────────────────────────────────

def confirm_kb(action: str = "confirm") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"{action}:yes"),
        InlineKeyboardButton(text="❌ Отмена", callback_data="cancel"),
    )
    return builder.as_markup()


def back_to_menu_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🔙 Главное меню", callback_data="main_menu"))
    return builder.as_markup()
