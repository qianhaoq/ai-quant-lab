# ai-quant-lab

AI-native web platform for US stock and ETF quantitative trading. The v1 product path is a guarded trading console with broker gateway status, account and position snapshots, order intent drafting, risk precheck, manual confirmation, and an AI trading researcher. Backtesting remains available as a support API, but the primary surface is live-ready trading infrastructure.

The default runtime uses an internal sandbox and sample data. It never sends orders to a funded brokerage account unless broker variables are configured, `ENABLE_LIVE_TRADING=true` is explicitly set for live mode, and each order passes risk checks plus manual confirmation. This project does not provide investment advice.

## Stack

- Web: Next.js, TypeScript, Vitest, Playwright
- API: FastAPI, pandas, NumPy, pytest
- Data: built-in deterministic sample data by default, optional provider boundary for Alpaca or Polygon
- Trading: internal sandbox by default, Alpaca paper/live REST boundary for future broker integration
- AI: OpenAI when `OPENAI_API_KEY` is present, deterministic mock fallback otherwise
- Workflow: Dev Container, Docker Compose, GitHub Actions, PR/issue templates

## Quick Start

```bash
pnpm install
pnpm api:install
pnpm dev
```

Open:

- Web: http://localhost:3000
- API: http://localhost:8000/docs

The app works without API keys. Copy `.env.example` to `.env` only when you want to configure real providers.

## Local Development Without Docker

Terminal 1:

```bash
cd apps/api
python3 -m venv .venv
.venv/bin/python -m pip install -e ".[dev]"
.venv/bin/python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Terminal 2:

```bash
pnpm install
pnpm dev:web
```

## API

- `GET /health`
- `GET /symbols`
- `GET /data/bars?symbol=SPY&start=2024-01-01&end=2024-06-30&timeframe=1d`
- `GET /trading/status`
- `GET /trading/account`
- `GET /trading/positions`
- `POST /trading/orders/preview`
- `POST /trading/orders`
- `POST /backtests`
- `GET /backtests/{id}`
- `POST /research/chat`

Trading controls:

- `BROKER_PROVIDER=internal_sandbox` keeps all orders local.
- `BROKER_PROVIDER=alpaca` plus `BROKER_MODE=alpaca_paper` targets Alpaca paper trading when credentials are present.
- `BROKER_MODE=alpaca_live` requires `ENABLE_LIVE_TRADING=true`; otherwise live mode is locked.
- Every order must pass symbol, quantity, notional, gateway, and confirmation checks before submission.
- AI responses can create hypotheses and order-intent fields, but they cannot submit orders or bypass risk checks.

Backtest strategies:

- `buy_and_hold`
- `moving_average_crossover`
- `rsi_mean_reversion`

Metrics returned by every backtest:

- total return
- CAGR
- volatility
- Sharpe
- max drawdown
- win rate
- trade count

## Deployment Notes

### Vercel Web

Create a Vercel project from `apps/web`.

Required environment variable:

```bash
NEXT_PUBLIC_API_BASE_URL=https://<railway-api-domain>
```

### Railway API

Create a Railway service from `apps/api`.

Suggested environment variables:

```bash
APP_ENV=production
ALLOWED_ORIGINS=https://<vercel-domain>
MARKET_DATA_PROVIDER=sample
BROKER_PROVIDER=internal_sandbox
BROKER_MODE=sandbox
ENABLE_LIVE_TRADING=false
MAX_ORDER_NOTIONAL=25000
MAX_ORDER_QUANTITY=100
ALLOWED_TRADE_SYMBOLS=SPY,QQQ,AAPL
OPENAI_API_KEY=<optional>
ALPACA_API_KEY_ID=<optional>
ALPACA_API_SECRET_KEY=<optional>
```

The app is designed to remain usable when `OPENAI_API_KEY` and broker credentials are absent.

## AI-native Workflow

1. Create a Linear or GitHub issue with product intent, broker mode, safety boundary, acceptance criteria, and test expectations.
2. Let an agent implement in a Dev Container or isolated worktree.
3. Require backend pytest, frontend lint/typecheck/Vitest/build, and Playwright smoke before merge.
4. For broker work, require a risk note covering credentials, live toggle, order lifecycle, and failure modes.
5. Use AI review as the first pass, then human review as the final gate.

### Linear Queue Runner

This repo includes a local Linear queue runner for the AI-native workflow:

```bash
export LINEAR_API_KEY=<linear-api-key>
pnpm runner:dry-run
pnpm runner:once
```

The runner pulls issues from `待 Agent 处理`, moves the selected issue to `Agent 执行中`, creates an isolated git worktree, runs `codex exec`, reruns tests, opens a GitHub draft PR, and writes the result back to Linear. It never merges PRs automatically. Issues labeled `risk:trading` are blocked by default unless `RUNNER_ALLOW_TRADING_RISK=true` is set, and they still end in human review.

See `docs/ai-native-runner.md` for setup, safety policy, cron rollout, and webhook rollout.

Reference research for reusable trading systems is captured in `docs/research/github-trading-systems.md`.

## Safety

This repository is a trading-platform scaffold, not a broker, investment adviser, or compliance system. Defaults are sandbox-only. Real brokerage integration requires external credentials, explicit live enablement, risk precheck, manual confirmation, and operator review.
