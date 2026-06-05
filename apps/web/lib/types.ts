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

export type BrokerMode = "sandbox" | "alpaca_paper" | "alpaca_live";
export type OrderSide = "buy" | "sell";
export type OrderType = "market" | "limit";
export type TimeInForce = "day" | "gtc";

export type TradingStatus = {
  provider: string;
  mode: BrokerMode;
  broker_connected: boolean;
  trading_enabled: boolean;
  live_trading_enabled: boolean;
  requires_confirmation: boolean;
  allowed_symbols: string[];
  max_order_notional: number;
  max_order_quantity: number;
  message: string;
};

export type AccountSnapshot = {
  account_id: string;
  currency: "USD";
  cash: number;
  buying_power: number;
  portfolio_value: number;
  status: string;
};

export type PositionSnapshot = {
  symbol: string;
  quantity: number;
  market_value: number;
  average_entry_price: number;
  last_price: number;
  unrealized_pl: number;
  unrealized_pl_pct: number;
};

export type RiskCheck = {
  name: string;
  passed: boolean;
  severity: "info" | "warning" | "blocker";
  message: string;
};

export type OrderIntent = {
  symbol: string;
  side: OrderSide;
  quantity: number;
  order_type: OrderType;
  time_in_force: TimeInForce;
  limit_price?: number;
  rationale?: string;
  confirmation_phrase?: string;
};

export type OrderPreview = {
  accepted: boolean;
  broker_provider: string;
  broker_mode: BrokerMode;
  symbol: string;
  side: OrderSide;
  quantity: number;
  order_type: OrderType;
  time_in_force: TimeInForce;
  estimated_price: number;
  estimated_notional: number;
  risk_checks: RiskCheck[];
  confirmation_required: boolean;
  confirmation_phrase: string;
  message: string;
};

export type OrderReceipt = {
  id: string;
  status: string;
  broker_provider: string;
  broker_mode: BrokerMode;
  symbol: string;
  side: OrderSide;
  quantity: number;
  order_type: OrderType;
  time_in_force: TimeInForce;
  submitted_at: string;
  estimated_notional: number;
  broker_order_id?: string | null;
  message: string;
};
