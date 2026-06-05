from datetime import date

import numpy as np
import pandas as pd

from app.models import Bar, Symbol


class DataProviderError(ValueError):
    pass


SUPPORTED_SYMBOLS = [
    Symbol(symbol="SPY", name="SPDR S&P 500 ETF Trust", asset_class="us_etf"),
    Symbol(symbol="QQQ", name="Invesco QQQ Trust", asset_class="us_etf"),
    Symbol(symbol="AAPL", name="Apple Inc.", asset_class="us_equity"),
]


def list_symbols() -> list[Symbol]:
    return SUPPORTED_SYMBOLS


def symbol_exists(symbol: str) -> bool:
    normalized = symbol.upper()
    return any(item.symbol == normalized for item in SUPPORTED_SYMBOLS)


def get_sample_bars(symbol: str, start: date, end: date, timeframe: str = "1d") -> pd.DataFrame:
    normalized = symbol.upper()
    if timeframe != "1d":
        raise DataProviderError("Only 1d timeframe is supported in v1")
    if not symbol_exists(normalized):
        raise DataProviderError(f"Unsupported symbol: {symbol}")
    if start > end:
        raise DataProviderError("start must be on or before end")

    all_dates = pd.date_range("2023-01-03", "2024-12-31", freq="B")
    idx = np.arange(len(all_dates))
    base = {"SPY": 390.0, "QQQ": 280.0, "AAPL": 145.0}[normalized]
    trend = np.linspace(0, base * 0.28, len(all_dates))
    seasonal = np.sin(idx / 8.0) * base * 0.018
    drawdown = np.where((idx >= 130) & (idx <= 160), -base * 0.055, 0)
    close = base + trend + seasonal + drawdown
    open_ = close * (1 + np.cos(idx / 5.0) * 0.002)
    high = np.maximum(open_, close) * 1.006
    low = np.minimum(open_, close) * 0.994
    volume = (2_000_000 + idx * 3750 + (np.sin(idx / 3.0) + 1) * 150_000).astype(int)

    frame = pd.DataFrame(
        {
            "symbol": normalized,
            "date": all_dates,
            "open": open_.round(2),
            "high": high.round(2),
            "low": low.round(2),
            "close": close.round(2),
            "volume": volume,
        }
    )
    selected = frame[(frame["date"].dt.date >= start) & (frame["date"].dt.date <= end)].copy()
    if selected.empty:
        raise DataProviderError("No sample bars found for the requested range")
    return selected.reset_index(drop=True)


def bars_to_models(frame: pd.DataFrame) -> list[Bar]:
    return [
        Bar(
            symbol=str(row.symbol),
            date=row.date.date(),
            open=float(row.open),
            high=float(row.high),
            low=float(row.low),
            close=float(row.close),
            volume=int(row.volume),
        )
        for row in frame.itertuples(index=False)
    ]
