from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


StrategyName = Literal["buy_and_hold", "moving_average_crossover", "rsi_mean_reversion"]
Timeframe = Literal["1d"]
BrokerMode = Literal["sandbox", "alpaca_paper", "alpaca_live"]
OrderSide = Literal["buy", "sell"]
OrderType = Literal["market", "limit"]
TimeInForce = Literal["day", "gtc"]
RiskSeverity = Literal["info", "warning", "blocker"]


class HealthResponse(BaseModel):
    status: Literal["ok"]
    service: str


class Symbol(BaseModel):
    symbol: str
    name: str
    asset_class: Literal["us_equity", "us_etf"]


class Bar(BaseModel):
    symbol: str
    date: date
    open: float
    high: float
    low: float
    close: float
    volume: int


class BacktestRequest(BaseModel):
    symbols: list[str] = Field(min_length=1, max_length=5)
    start: date
    end: date
    timeframe: Timeframe = "1d"
    initial_cash: float = Field(default=100_000, gt=0)
    strategy: StrategyName
    params: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_dates(self) -> "BacktestRequest":
        if self.start > self.end:
            raise ValueError("start must be on or before end")
        return self


class Metrics(BaseModel):
    total_return: float
    cagr: float
    volatility: float
    sharpe: float
    max_drawdown: float
    win_rate: float
    trade_count: int


class EquityPoint(BaseModel):
    date: date
    equity: float


class Trade(BaseModel):
    symbol: str
    entry_date: date
    exit_date: date
    entry_price: float
    exit_price: float
    pnl_pct: float


class BacktestResult(BaseModel):
    id: str
    request: BacktestRequest
    symbol: str
    metrics: Metrics
    equity_curve: list[EquityPoint]
    trades: list[Trade]


class ResearchRequest(BaseModel):
    question: str = Field(min_length=3, max_length=2000)
    backtest_id: str | None = None


class ResearchResponse(BaseModel):
    answer: str
    suggested_experiments: list[str]
    used_mock: bool


class TradingStatusResponse(BaseModel):
    provider: str
    mode: BrokerMode
    broker_connected: bool
    trading_enabled: bool
    live_trading_enabled: bool
    requires_confirmation: bool
    allowed_symbols: list[str]
    max_order_notional: float
    max_order_quantity: float
    message: str


class AccountSnapshot(BaseModel):
    account_id: str
    currency: str = "USD"
    cash: float
    buying_power: float
    portfolio_value: float
    status: str


class PositionSnapshot(BaseModel):
    symbol: str
    quantity: float
    market_value: float
    average_entry_price: float
    last_price: float
    unrealized_pl: float
    unrealized_pl_pct: float


class RiskCheck(BaseModel):
    name: str
    passed: bool
    severity: RiskSeverity
    message: str


class OrderIntent(BaseModel):
    symbol: str = Field(min_length=1, max_length=12)
    side: OrderSide
    quantity: float = Field(gt=0)
    order_type: OrderType = "market"
    time_in_force: TimeInForce = "day"
    limit_price: float | None = Field(default=None, gt=0)
    rationale: str | None = Field(default=None, max_length=1000)
    confirmation_phrase: str | None = Field(default=None, max_length=120)

    @model_validator(mode="after")
    def validate_limit_price(self) -> "OrderIntent":
        if self.order_type == "limit" and self.limit_price is None:
            raise ValueError("limit_price is required for limit orders")
        return self


class OrderPreview(BaseModel):
    accepted: bool
    broker_provider: str
    broker_mode: BrokerMode
    symbol: str
    side: OrderSide
    quantity: float
    order_type: OrderType
    time_in_force: TimeInForce
    estimated_price: float
    estimated_notional: float
    risk_checks: list[RiskCheck]
    confirmation_required: bool
    confirmation_phrase: str
    message: str


class OrderReceipt(BaseModel):
    id: str
    status: str
    broker_provider: str
    broker_mode: BrokerMode
    symbol: str
    side: OrderSide
    quantity: float
    order_type: OrderType
    time_in_force: TimeInForce
    submitted_at: str
    estimated_notional: float
    broker_order_id: str | None = None
    message: str
