from typing import Optional, Sequence

from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from bot.database.models import (
    User,
    Portfolio,
    Asset,
    Transaction,
    Alert,
    WatchlistItem,
)


async def get_or_create_user(
    session: AsyncSession,
    telegram_id: int,
    username: Optional[str] = None,
    first_name: Optional[str] = None,
) -> User:
    stmt = select(User).where(User.telegram_id == telegram_id)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()

    if user is None:
        user = User(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
        )
        session.add(user)
        await session.flush()

        portfolio = Portfolio(user_id=user.id, name="Main", is_default=True)
        session.add(portfolio)
        await session.commit()
    else:
        if user.username != username or user.first_name != first_name:
            user.username = username
            user.first_name = first_name
            await session.commit()

    return user


async def get_user_by_telegram_id(session: AsyncSession, telegram_id: int) -> Optional[User]:
    stmt = select(User).where(User.telegram_id == telegram_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def update_user_settings(
    session: AsyncSession, telegram_id: int, **kwargs
) -> None:
    stmt = (
        update(User)
        .where(User.telegram_id == telegram_id)
        .values(**kwargs)
    )
    await session.execute(stmt)
    await session.commit()


async def get_default_portfolio(session: AsyncSession, user_id: int) -> Optional[Portfolio]:
    stmt = (
        select(Portfolio)
        .where(Portfolio.user_id == user_id, Portfolio.is_default == True)
        .options(selectinload(Portfolio.assets).selectinload(Asset.transactions))
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_user_portfolios(session: AsyncSession, user_id: int) -> Sequence[Portfolio]:
    stmt = (
        select(Portfolio)
        .where(Portfolio.user_id == user_id)
        .options(selectinload(Portfolio.assets))
    )
    result = await session.execute(stmt)
    return result.scalars().all()


async def get_asset(
    session: AsyncSession, portfolio_id: int, coin_id: str
) -> Optional[Asset]:
    stmt = select(Asset).where(
        Asset.portfolio_id == portfolio_id, Asset.coin_id == coin_id
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_portfolio_assets(
    session: AsyncSession, portfolio_id: int
) -> Sequence[Asset]:
    stmt = (
        select(Asset)
        .where(Asset.portfolio_id == portfolio_id)
        .options(selectinload(Asset.transactions))
        .order_by(Asset.total_invested.desc())
    )
    result = await session.execute(stmt)
    return result.scalars().all()


async def add_or_update_asset(
    session: AsyncSession,
    portfolio_id: int,
    coin_id: str,
    symbol: str,
    name: str,
    amount: float,
    price: float,
    tx_type: str = "buy",
    note: Optional[str] = None,
) -> Asset:
    asset = await get_asset(session, portfolio_id, coin_id)

    if asset is None:
        asset = Asset(
            portfolio_id=portfolio_id,
            coin_id=coin_id,
            symbol=symbol.upper(),
            name=name,
            amount=amount,
            avg_buy_price=price,
            total_invested=amount * price,
        )
        session.add(asset)
        await session.flush()
    else:
        if tx_type == "buy":
            total_cost = asset.total_invested + (amount * price)
            total_amount = asset.amount + amount
            asset.avg_buy_price = total_cost / total_amount if total_amount > 0 else 0
            asset.amount = total_amount
            asset.total_invested = total_cost
        else:
            asset.amount = max(0, asset.amount - amount)
            if asset.amount == 0:
                asset.total_invested = 0
                asset.avg_buy_price = 0
            else:
                sell_ratio = amount / (asset.amount + amount)
                asset.total_invested *= (1 - sell_ratio)

    tx = Transaction(
        asset_id=asset.id,
        type=tx_type,
        amount=amount,
        price=price,
        total=amount * price,
        note=note,
    )
    session.add(tx)
    await session.commit()

    return asset


async def remove_asset(session: AsyncSession, asset_id: int) -> None:
    stmt = delete(Asset).where(Asset.id == asset_id)
    await session.execute(stmt)
    await session.commit()


async def get_asset_transactions(
    session: AsyncSession, asset_id: int
) -> Sequence[Transaction]:
    stmt = (
        select(Transaction)
        .where(Transaction.asset_id == asset_id)
        .order_by(Transaction.created_at.desc())
    )
    result = await session.execute(stmt)
    return result.scalars().all()


async def get_recent_transactions(
    session: AsyncSession, portfolio_id: int, limit: int = 20
) -> Sequence[Transaction]:
    stmt = (
        select(Transaction)
        .join(Asset)
        .where(Asset.portfolio_id == portfolio_id)
        .order_by(Transaction.created_at.desc())
        .limit(limit)
    )
    result = await session.execute(stmt)
    return result.scalars().all()


async def create_alert(
    session: AsyncSession,
    user_id: int,
    coin_id: str,
    symbol: str,
    target_price: float,
    direction: str,
) -> Alert:
    alert = Alert(
        user_id=user_id,
        coin_id=coin_id,
        symbol=symbol.upper(),
        target_price=target_price,
        direction=direction,
    )
    session.add(alert)
    await session.commit()
    return alert


async def get_active_alerts(session: AsyncSession, user_id: Optional[int] = None) -> Sequence[Alert]:
    stmt = select(Alert).where(Alert.is_active == True)
    if user_id is not None:
        stmt = stmt.where(Alert.user_id == user_id)
    result = await session.execute(stmt)
    return result.scalars().all()


async def deactivate_alert(session: AsyncSession, alert_id: int) -> None:
    stmt = update(Alert).where(Alert.id == alert_id).values(is_active=False)
    await session.execute(stmt)
    await session.commit()


async def delete_alert(session: AsyncSession, alert_id: int) -> None:
    stmt = delete(Alert).where(Alert.id == alert_id)
    await session.execute(stmt)
    await session.commit()


async def add_to_watchlist(
    session: AsyncSession,
    user_id: int,
    coin_id: str,
    symbol: str,
    name: str,
) -> WatchlistItem:
    stmt = select(WatchlistItem).where(
        WatchlistItem.user_id == user_id, WatchlistItem.coin_id == coin_id
    )
    result = await session.execute(stmt)
    existing = result.scalar_one_or_none()
    if existing:
        return existing

    item = WatchlistItem(
        user_id=user_id,
        coin_id=coin_id,
        symbol=symbol.upper(),
        name=name,
    )
    session.add(item)
    await session.commit()
    return item


async def get_watchlist(session: AsyncSession, user_id: int) -> Sequence[WatchlistItem]:
    stmt = (
        select(WatchlistItem)
        .where(WatchlistItem.user_id == user_id)
        .order_by(WatchlistItem.created_at)
    )
    result = await session.execute(stmt)
    return result.scalars().all()


async def remove_from_watchlist(session: AsyncSession, item_id: int) -> None:
    stmt = delete(WatchlistItem).where(WatchlistItem.id == item_id)
    await session.execute(stmt)
    await session.commit()
