from uuid import uuid4

import numpy as np
import pandas as pd

from app.models import BacktestRequest, BacktestResult, EquityPoint, Metrics, Trade


class BacktestError(ValueError):
    pass


def run_backtest(request: BacktestRequest, bars: pd.DataFrame) -> BacktestResult:
    if len(request.symbols) != 1:
        raise BacktestError("v1 supports exactly one symbol per backtest")
    if bars.empty:
        raise BacktestError("Cannot backtest an empty bar set")

    symbol = request.symbols[0].upper()
    frame = bars.sort_values("date").reset_index(drop=True).copy()
    close = frame["close"].astype(float)
    position = _build_position(close, request.strategy, request.params)
    strategy_returns = close.pct_change().fillna(0) * position.shift(1).fillna(0)
    equity = request.initial_cash * (1 + strategy_returns).cumprod()
    trades = _extract_trades(symbol, frame, position)
    metrics = _compute_metrics(equity, strategy_returns, trades, frame)

    return BacktestResult(
        id=str(uuid4()),
        request=request,
        symbol=symbol,
        metrics=metrics,
        equity_curve=[
            EquityPoint(date=row.date.date(), equity=round(float(value), 2))
            for row, value in zip(frame.itertuples(index=False), equity, strict=True)
        ],
        trades=trades,
    )


def _build_position(close: pd.Series, strategy: str, params: dict) -> pd.Series:
    if strategy == "buy_and_hold":
        return pd.Series(1, index=close.index, dtype=float)
    if strategy == "moving_average_crossover":
        short_window = int(params.get("short_window", 20))
        long_window = int(params.get("long_window", 50))
        if short_window <= 1 or long_window <= 1 or short_window >= long_window:
            raise BacktestError("moving_average_crossover requires 1 < short_window < long_window")
        short_ma = close.rolling(short_window, min_periods=short_window).mean()
        long_ma = close.rolling(long_window, min_periods=long_window).mean()
        return (short_ma > long_ma).astype(float).fillna(0)
    if strategy == "rsi_mean_reversion":
        period = int(params.get("period", 14))
        entry = float(params.get("entry", 35))
        exit_ = float(params.get("exit", 55))
        if period <= 1 or entry >= exit_:
            raise BacktestError("rsi_mean_reversion requires period > 1 and entry < exit")
        rsi = _rsi(close, period)
        position = []
        current = 0.0
        for value in rsi:
            if np.isnan(value):
                position.append(current)
                continue
            if current == 0 and value < entry:
                current = 1.0
            elif current == 1 and value > exit_:
                current = 0.0
            position.append(current)
        return pd.Series(position, index=close.index, dtype=float)
    raise BacktestError(f"Unknown strategy: {strategy}")


def _rsi(close: pd.Series, period: int) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(period, min_periods=period).mean()
    loss = (-delta.clip(upper=0)).rolling(period, min_periods=period).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def _extract_trades(symbol: str, frame: pd.DataFrame, position: pd.Series) -> list[Trade]:
    trades: list[Trade] = []
    in_trade = False
    entry_idx = 0
    previous = 0.0

    for idx, current in enumerate(position):
        if current == 1 and previous == 0:
            in_trade = True
            entry_idx = idx
        if current == 0 and previous == 1 and in_trade:
            trades.append(_make_trade(symbol, frame, entry_idx, idx))
            in_trade = False
        previous = current

    if in_trade:
        trades.append(_make_trade(symbol, frame, entry_idx, len(frame) - 1))
    return trades


def _make_trade(symbol: str, frame: pd.DataFrame, entry_idx: int, exit_idx: int) -> Trade:
    entry = frame.iloc[entry_idx]
    exit_ = frame.iloc[exit_idx]
    entry_price = float(entry.close)
    exit_price = float(exit_.close)
    pnl_pct = (exit_price / entry_price) - 1
    return Trade(
        symbol=symbol,
        entry_date=entry.date.date(),
        exit_date=exit_.date.date(),
        entry_price=round(entry_price, 2),
        exit_price=round(exit_price, 2),
        pnl_pct=round(float(pnl_pct), 6),
    )


def _compute_metrics(
    equity: pd.Series, returns: pd.Series, trades: list[Trade], frame: pd.DataFrame
) -> Metrics:
    initial = float(equity.iloc[0])
    final = float(equity.iloc[-1])
    total_return = final / initial - 1
    days = max((frame.iloc[-1].date.date() - frame.iloc[0].date.date()).days, 1)
    cagr = (final / initial) ** (365 / days) - 1
    volatility = float(returns.std(ddof=0) * np.sqrt(252))
    sharpe = 0.0 if volatility == 0 else float(returns.mean() / returns.std(ddof=0) * np.sqrt(252))
    drawdown = equity / equity.cummax() - 1
    wins = [trade for trade in trades if trade.pnl_pct > 0]
    win_rate = 0.0 if not trades else len(wins) / len(trades)

    return Metrics(
        total_return=round(float(total_return), 6),
        cagr=round(float(cagr), 6),
        volatility=round(float(volatility), 6),
        sharpe=round(float(sharpe), 6),
        max_drawdown=round(float(drawdown.min()), 6),
        win_rate=round(float(win_rate), 6),
        trade_count=len(trades),
    )
