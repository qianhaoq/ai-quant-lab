from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


StrategyName = Literal["buy_and_hold", "moving_average_crossover", "rsi_mean_reversion"]
Timeframe = Literal["1d"]


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
