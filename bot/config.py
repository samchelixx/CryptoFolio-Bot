import os
from dataclasses import dataclass, field
from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    bot_token: str = field(default_factory=lambda: os.getenv("BOT_TOKEN", ""))
    db_url: str = field(
        default_factory=lambda: os.getenv(
            "DB_URL", "sqlite+aiosqlite:///data/cryptofolio.db"
        )
    )
    coingecko_base_url: str = field(
        default_factory=lambda: os.getenv(
            "COINGECKO_BASE_URL", "https://api.coingecko.com/api/v3"
        )
    )
    cache_ttl: int = field(
        default_factory=lambda: int(os.getenv("CACHE_TTL", "300"))
    )
    default_currency: str = field(
        default_factory=lambda: os.getenv("DEFAULT_CURRENCY", "usd")
    )
    alert_check_interval: int = field(
        default_factory=lambda: int(os.getenv("ALERT_CHECK_INTERVAL", "60"))
    )

    def __post_init__(self) -> None:
        if not self.bot_token:
            raise ValueError("BOT_TOKEN is required. Set it in .env file.")


settings = Settings()
