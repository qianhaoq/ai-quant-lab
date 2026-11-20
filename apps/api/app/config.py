from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    api_tokens: dict[str, str] = Field(default_factory=dict, repr=False)
    broker_owner_subject: str = "local-operator"
    broker_account_id: str = "internal-sandbox"
    safety_db_path: str = ".local/safety.sqlite3"
    safety_max_orders: int = Field(default=10, gt=0)
    safety_max_notional: float = Field(default=50000, gt=0, allow_inf_nan=False)
    enable_paid_models: bool = False
    safety_model_calls: int = Field(default=20, gt=0)
    safety_model_total_tokens: int = Field(default=340000, gt=0)
    safety_model_output_tokens: int = Field(default=1000, gt=0, le=2000)
    safety_model_concurrency: int = Field(default=2, gt=0, le=4)
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
