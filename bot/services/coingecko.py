import time
import asyncio
import logging
from typing import Any, Optional

import aiohttp

from bot.config import settings

logger = logging.getLogger(__name__)


class _Cache:
    def __init__(self, ttl: int = 300):
        self._ttl = ttl
        self._store: dict[str, tuple[float, Any]] = {}

    def get(self, key: str) -> Optional[Any]:
        if key in self._store:
            ts, value = self._store[key]
            if time.time() - ts < self._ttl:
                return value
            del self._store[key]
        return None

    def set(self, key: str, value: Any) -> None:
        self._store[key] = (time.time(), value)

    def clear(self) -> None:
        self._store.clear()


class CoinGeckoService:
    BASE = settings.coingecko_base_url

    def __init__(self) -> None:
        self._cache = _Cache(ttl=settings.cache_ttl)
        self._session: Optional[aiohttp.ClientSession] = None
        self._semaphore = asyncio.Semaphore(5)

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                headers={"Accept": "application/json"},
                timeout=aiohttp.ClientTimeout(total=15),
            )
        return self._session

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()

    async def _request(self, endpoint: str, params: Optional[dict] = None) -> Any:
        cache_key = f"{endpoint}:{params}"
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        async with self._semaphore:
            session = await self._get_session()
            url = f"{self.BASE}{endpoint}"
            try:
                async with session.get(url, params=params) as resp:
                    if resp.status == 429:
                        logger.warning("Rate limit hit, waiting 60s...")
                        await asyncio.sleep(60)
                        return await self._request(endpoint, params)
                    resp.raise_for_status()
                    data = await resp.json()
                    self._cache.set(cache_key, data)
                    return data
            except aiohttp.ClientError as e:
                logger.error("API error: %s", e)
                raise

    async def get_price(
        self,
        coin_ids: list[str],
        vs_currency: str = "usd",
        include_change: bool = True,
    ) -> dict[str, dict]:
        params = {
            "ids": ",".join(coin_ids),
            "vs_currencies": vs_currency,
            "include_24hr_change": str(include_change).lower(),
            "include_market_cap": "true",
            "include_24hr_vol": "true",
        }
        return await self._request("/simple/price", params)

    async def search_coins(self, query: str) -> list[dict]:
        data = await self._request("/search", {"query": query})
        return data.get("coins", [])[:10]

    async def get_coin_info(self, coin_id: str) -> dict:
        params = {
            "localization": "false",
            "tickers": "false",
            "community_data": "false",
            "developer_data": "false",
        }
        return await self._request(f"/coins/{coin_id}", params)

    async def get_market_chart(
        self, coin_id: str, vs_currency: str = "usd", days: int = 30
    ) -> dict:
        params = {"vs_currency": vs_currency, "days": str(days)}
        return await self._request(f"/coins/{coin_id}/market-chart", params)

    async def get_ohlc(
        self, coin_id: str, vs_currency: str = "usd", days: int = 30
    ) -> list[list]:
        params = {"vs_currency": vs_currency, "days": str(days)}
        return await self._request(f"/coins/{coin_id}/ohlc", params)

    async def get_trending(self) -> list[dict]:
        data = await self._request("/search/trending")
        return [item["item"] for item in data.get("coins", [])]

    async def get_markets(
        self,
        vs_currency: str = "usd",
        per_page: int = 25,
        page: int = 1,
        order: str = "market_cap_desc",
    ) -> list[dict]:
        params = {
            "vs_currency": vs_currency,
            "order": order,
            "per_page": str(per_page),
            "page": str(page),
            "sparkline": "false",
            "price_change_percentage": "1h,24h,7d",
        }
        return await self._request("/coins/markets", params)


coingecko = CoinGeckoService()
