from dataclasses import dataclass
from typing import Sequence

from bot.database.models import Asset
from bot.services.coingecko import coingecko


@dataclass
class AssetAnalytics:
    coin_id: str
    symbol: str
    name: str
    amount: float
    avg_buy_price: float
    current_price: float
    total_invested: float
    current_value: float
    pnl: float
    pnl_percent: float
    weight: float


@dataclass
class PortfolioSummary:
    total_invested: float
    total_value: float
    total_pnl: float
    total_pnl_percent: float
    assets: list[AssetAnalytics]
    best_performer: AssetAnalytics | None
    worst_performer: AssetAnalytics | None
    num_assets: int


async def calculate_portfolio(
    assets: Sequence[Asset], currency: str = "usd"
) -> PortfolioSummary:
    if not assets:
        return PortfolioSummary(
            total_invested=0, total_value=0, total_pnl=0,
            total_pnl_percent=0, assets=[], best_performer=None,
            worst_performer=None, num_assets=0,
        )

    coin_ids = [a.coin_id for a in assets]
    prices = await coingecko.get_price(coin_ids, vs_currency=currency)

    total_invested = 0.0
    total_value = 0.0
    analytics_list: list[AssetAnalytics] = []

    for asset in assets:
        price_data = prices.get(asset.coin_id, {})
        current_price = price_data.get(currency, 0)
        current_value = asset.amount * current_price
        pnl = current_value - asset.total_invested
        pnl_pct = (pnl / asset.total_invested * 100) if asset.total_invested > 0 else 0

        total_invested += asset.total_invested
        total_value += current_value

        analytics_list.append(
            AssetAnalytics(
                coin_id=asset.coin_id, symbol=asset.symbol, name=asset.name,
                amount=asset.amount, avg_buy_price=asset.avg_buy_price,
                current_price=current_price, total_invested=asset.total_invested,
                current_value=current_value, pnl=pnl, pnl_percent=pnl_pct, weight=0,
            )
        )

    for a in analytics_list:
        a.weight = (a.current_value / total_value) if total_value > 0 else 0

    analytics_list.sort(key=lambda x: x.current_value, reverse=True)

    total_pnl = total_value - total_invested
    total_pnl_pct = (total_pnl / total_invested * 100) if total_invested > 0 else 0

    best = max(analytics_list, key=lambda x: x.pnl_percent) if analytics_list else None
    worst = min(analytics_list, key=lambda x: x.pnl_percent) if analytics_list else None

    return PortfolioSummary(
        total_invested=total_invested, total_value=total_value,
        total_pnl=total_pnl, total_pnl_percent=total_pnl_pct,
        assets=analytics_list, best_performer=best,
        worst_performer=worst, num_assets=len(analytics_list),
    )
