from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    allowed_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    market_data_provider: str = "sample"
    openai_api_key: str | None = None
    openai_model: str = "gpt-4.1-mini"
    broker_provider: str = "internal_sandbox"
    broker_mode: str = "sandbox"
    enable_live_trading: bool = False
    max_order_notional: float = 25_000
    max_order_quantity: float = 100
    allowed_trade_symbols: str = "SPY,QQQ,AAPL"
    alpaca_api_key_id: str | None = None
    alpaca_api_secret_key: str | None = None

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]

    @property
    def trade_symbols(self) -> list[str]:
        return [symbol.strip().upper() for symbol in self.allowed_trade_symbols.split(",") if symbol.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
