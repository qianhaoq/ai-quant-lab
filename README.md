# ai-quant-lab

AI-native web platform for US stock and ETF quantitative research. The v1 scope is backtesting, paper-style simulation, and an AI research copilot. It does not support live trading and does not provide investment advice.

## Stack

- Web: Next.js, TypeScript, Vitest, Playwright
- API: FastAPI, pandas, NumPy, pytest
- Data: built-in deterministic sample data by default, optional provider boundary for Alpaca or Polygon
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
- `POST /backtests`
- `GET /backtests/{id}`
- `POST /research/chat`

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
OPENAI_API_KEY=<optional>
```

The app is designed to remain usable when `OPENAI_API_KEY` is absent.

## AI-native Workflow

1. Create a Linear or GitHub issue with context, acceptance criteria, and test expectations.
2. Let an agent implement in a Dev Container or isolated worktree.
3. Run backend pytest, frontend lint/typecheck/Vitest, and the Playwright smoke test.
4. Open a PR with the preview URL and risk notes.
5. Use AI review as the first pass, then human review as the final gate.

## Safety

This repository is for research and educational workflows only. It does not place orders, connect funded brokerage accounts, or recommend securities.
