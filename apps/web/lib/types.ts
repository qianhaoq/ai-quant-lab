export type SymbolInfo = {
  symbol: string;
  name: string;
  asset_class: "us_equity" | "us_etf";
};

export type StrategyName = "buy_and_hold" | "moving_average_crossover" | "rsi_mean_reversion";

export type BacktestRequest = {
  symbols: string[];
  start: string;
  end: string;
  timeframe: "1d";
  initial_cash: number;
  strategy: StrategyName;
  params: Record<string, number>;
};

export type Metrics = {
  total_return: number;
  cagr: number;
  volatility: number;
  sharpe: number;
  max_drawdown: number;
  win_rate: number;
  trade_count: number;
};

export type EquityPoint = {
  date: string;
  equity: number;
};

export type Trade = {
  symbol: string;
  entry_date: string;
  exit_date: string;
  entry_price: number;
  exit_price: number;
  pnl_pct: number;
};

export type BacktestResult = {
  id: string;
  request: BacktestRequest;
  symbol: string;
  metrics: Metrics;
  equity_curve: EquityPoint[];
  trades: Trade[];
};

export type ResearchResponse = {
  answer: string;
  suggested_experiments: string[];
  used_mock: boolean;
};
