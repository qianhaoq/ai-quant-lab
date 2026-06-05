"use client";

import { FormEvent, useState } from "react";
import { Play } from "lucide-react";
import type { BacktestRequest, StrategyName, SymbolInfo } from "@/lib/types";

type Props = {
  symbols: SymbolInfo[];
  loading: boolean;
  onSubmit: (payload: BacktestRequest) => void;
};

const STRATEGIES: Array<{ value: StrategyName; label: string }> = [
  { value: "buy_and_hold", label: "Buy and hold" },
  { value: "moving_average_crossover", label: "Moving average crossover" },
  { value: "rsi_mean_reversion", label: "RSI mean reversion" }
];

export function StrategyForm({ symbols, loading, onSubmit }: Props) {
  const [symbol, setSymbol] = useState("SPY");
  const [strategy, setStrategy] = useState<StrategyName>("moving_average_crossover");
  const [start, setStart] = useState("2023-01-03");
  const [end, setEnd] = useState("2024-12-31");
  const [initialCash, setInitialCash] = useState(100000);
  const [shortWindow, setShortWindow] = useState(20);
  const [longWindow, setLongWindow] = useState(50);
  const [rsiEntry, setRsiEntry] = useState(35);
  const [rsiExit, setRsiExit] = useState(55);

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    onSubmit({
      symbols: [symbol],
      start,
      end,
      timeframe: "1d",
      initial_cash: initialCash,
      strategy,
      params: strategyParams()
    });
  }

  function strategyParams(): Record<string, number> {
    if (strategy === "moving_average_crossover") {
      return { short_window: shortWindow, long_window: longWindow };
    }
    if (strategy === "rsi_mean_reversion") {
      return { period: 14, entry: rsiEntry, exit: rsiExit };
    }
    return {};
  }

  return (
    <form className="strategy-form" onSubmit={submit}>
      <label>
        Symbol
        <select value={symbol} onChange={(event) => setSymbol(event.target.value)}>
          {(symbols.length ? symbols : [{ symbol: "SPY", name: "SPDR S&P 500 ETF Trust", asset_class: "us_etf" }]).map(
            (item) => (
              <option key={item.symbol} value={item.symbol}>
                {item.symbol} - {item.name}
              </option>
            )
          )}
        </select>
      </label>

      <label>
        Strategy
        <select value={strategy} onChange={(event) => setStrategy(event.target.value as StrategyName)}>
          {STRATEGIES.map((item) => (
            <option key={item.value} value={item.value}>
              {item.label}
            </option>
          ))}
        </select>
      </label>

      <div className="form-row">
        <label>
          Start date
          <input type="date" value={start} onChange={(event) => setStart(event.target.value)} />
        </label>
        <label>
          End date
          <input type="date" value={end} onChange={(event) => setEnd(event.target.value)} />
        </label>
      </div>

      <label>
        Initial cash
        <input
          min={1000}
          step={1000}
          type="number"
          value={initialCash}
          onChange={(event) => setInitialCash(Number(event.target.value))}
        />
      </label>

      {strategy === "moving_average_crossover" ? (
        <div className="form-row">
          <label>
            Short window
            <input
              min={2}
              type="number"
              value={shortWindow}
              onChange={(event) => setShortWindow(Number(event.target.value))}
            />
          </label>
          <label>
            Long window
            <input
              min={3}
              type="number"
              value={longWindow}
              onChange={(event) => setLongWindow(Number(event.target.value))}
            />
          </label>
        </div>
      ) : null}

      {strategy === "rsi_mean_reversion" ? (
        <div className="form-row">
          <label>
            Entry RSI
            <input
              min={1}
              max={99}
              type="number"
              value={rsiEntry}
              onChange={(event) => setRsiEntry(Number(event.target.value))}
            />
          </label>
          <label>
            Exit RSI
            <input
              min={1}
              max={99}
              type="number"
              value={rsiExit}
              onChange={(event) => setRsiExit(Number(event.target.value))}
            />
          </label>
        </div>
      ) : null}

      <button className="secondary-button" type="submit" disabled={loading}>
        <Play size={16} />
        {loading ? "Running" : "Run backtest"}
      </button>
    </form>
  );
}
