from dataclasses import dataclass
from datetime import datetime

from bot.services.coingecko import coingecko


@dataclass
class DCAResult:
    coin_name: str
    symbol: str
    total_invested: float
    total_coins: float
    average_price: float
    current_price: float
    portfolio_value: float
    pnl: float
    pnl_percent: float
    num_purchases: int
    dates: list[datetime]
    portfolio_values: list[float]
    invested_over_time: list[float]
    lump_sum_values: list[float]


async def simulate_dca(
    coin_id: str,
    amount_per_buy: float,
    interval_days: int,
    total_days: int,
    currency: str = "usd",
) -> DCAResult:
    chart = await coingecko.get_market_chart(coin_id, vs_currency=currency, days=total_days)
    price_data = chart.get("prices", [])

    if not price_data:
        raise ValueError(f"No price data available for {coin_id}")

    try:
        coin_info = await coingecko.get_coin_info(coin_id)
        coin_name = coin_info.get("name", coin_id)
        symbol = coin_info.get("symbol", coin_id).upper()
    except Exception:
        coin_name = coin_id.title()
        symbol = coin_id.upper()

    total_invested = 0.0
    total_coins = 0.0
    num_purchases = 0

    dates: list[datetime] = []
    portfolio_values: list[float] = []
    invested_list: list[float] = []
    lump_sum_values: list[float] = []

    first_price = price_data[0][1]
    lump_sum_total = amount_per_buy * (total_days // interval_days)
    lump_sum_coins = lump_sum_total / first_price if first_price > 0 else 0

    buy_interval_ms = interval_days * 24 * 3600 * 1000
    next_buy_ts = price_data[0][0]

    for ts, price in price_data:
        if price <= 0:
            continue

        dt = datetime.fromtimestamp(ts / 1000)

        if ts >= next_buy_ts:
            coins_bought = amount_per_buy / price
            total_coins += coins_bought
            total_invested += amount_per_buy
            num_purchases += 1
            next_buy_ts = ts + buy_interval_ms

        dates.append(dt)
        portfolio_values.append(total_coins * price)
        invested_list.append(total_invested)
        lump_sum_values.append(lump_sum_coins * price)

    current_price = price_data[-1][1] if price_data else 0
    portfolio_value = total_coins * current_price
    avg_price = total_invested / total_coins if total_coins > 0 else 0
    pnl = portfolio_value - total_invested
    pnl_pct = (pnl / total_invested * 100) if total_invested > 0 else 0

    return DCAResult(
        coin_name=coin_name, symbol=symbol,
        total_invested=total_invested, total_coins=total_coins,
        average_price=avg_price, current_price=current_price,
        portfolio_value=portfolio_value, pnl=pnl, pnl_percent=pnl_pct,
        num_purchases=num_purchases, dates=dates,
        portfolio_values=portfolio_values,
        invested_over_time=invested_list,
        lump_sum_values=lump_sum_values,
    )
