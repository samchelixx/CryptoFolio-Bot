def format_price(value: float, currency: str = "USD") -> str:
    symbols = {"usd": "$", "eur": "€", "rub": "₽", "gbp": "£"}
    sym = symbols.get(currency.lower(), "$")
    if abs(value) >= 1:
        return f"{sym}{value:,.2f}"
    elif abs(value) >= 0.01:
        return f"{sym}{value:.4f}"
    else:
        return f"{sym}{value:.8f}"


def format_number(value: float) -> str:
    if abs(value) >= 1_000_000_000:
        return f"{value / 1_000_000_000:.2f}B"
    elif abs(value) >= 1_000_000:
        return f"{value / 1_000_000:.2f}M"
    elif abs(value) >= 1_000:
        return f"{value / 1_000:.2f}K"
    else:
        return f"{value:,.2f}"


def format_percent(value: float) -> str:
    sign = "+" if value >= 0 else ""
    return f"{sign}{value:.2f}%"


def pnl_emoji(value: float) -> str:
    if value > 10:
        return "🚀"
    elif value > 0:
        return "📈"
    elif value == 0:
        return "➡️"
    elif value > -10:
        return "📉"
    else:
        return "💀"


def change_emoji(pct: float) -> str:
    if pct >= 10:
        return "🔥"
    elif pct >= 5:
        return "🟢"
    elif pct > 0:
        return "🟩"
    elif pct == 0:
        return "⬜"
    elif pct > -5:
        return "🟥"
    elif pct > -10:
        return "🔴"
    else:
        return "💀"


def format_asset_line(
    symbol: str,
    amount: float,
    current_value: float,
    pnl: float,
    pnl_pct: float,
    currency: str = "usd",
) -> str:
    emoji = pnl_emoji(pnl_pct)
    sign = "+" if pnl >= 0 else ""
    return (
        f"{emoji} <b>{symbol}</b>: {amount:.6g} шт.\n"
        f"   💰 {format_price(current_value, currency)} "
        f"({sign}{format_price(pnl, currency)} / {format_percent(pnl_pct)})"
    )


def format_coin_price(
    name: str,
    symbol: str,
    price: float,
    change_24h: float | None = None,
    market_cap: float | None = None,
    volume: float | None = None,
    currency: str = "usd",
) -> str:
    lines = [f"<b>{name}</b> ({symbol.upper()})\n"]
    lines.append(f"💰 Цена: <b>{format_price(price, currency)}</b>")

    if change_24h is not None:
        emoji = change_emoji(change_24h)
        lines.append(f"{emoji} 24ч: <b>{format_percent(change_24h)}</b>")

    if market_cap is not None:
        lines.append(f"📊 Капитализация: <b>{format_number(market_cap)}</b>")

    if volume is not None:
        lines.append(f"📈 Объём (24ч): <b>{format_number(volume)}</b>")

    return "\n".join(lines)
