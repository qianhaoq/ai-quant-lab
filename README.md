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

### 本地 API 安全配置

账户、持仓、订单、研究和回测 API 要求 `Authorization: Bearer <token>`。
在服务端用 `API_TOKENS` 配置随机长令牌到稳定主体的 JSON 映射；没有配置时拒绝访问。
只有 `BROKER_OWNER_SUBJECT` 可访问该实例唯一的 `BROKER_ACCOUNT_ID`，其他主体无权访问；
多账户请使用独立实例、凭据和账本，不接受客户端选择其他券商账户。
不要将令牌提交到仓库或放入 NEXT_PUBLIC 环境变量。浏览器本地调试可在开发控制台执行
`sessionStorage.setItem('aql-api-token', '<operator-provisioned-token>')` 后刷新；关闭会话后清除。
这只是本地开发认证方式，远程使用必须另配 TLS 与可靠身份管理。

订单先调用 preview，再由人工复核并将返回的 `approval_token` 和确认短语一起提交；
审批绑定主体、账户、券商模式和全部订单字段，5 分钟过期，仅一次有效，每个主体的新预检替换旧审批。
Alpaca 买单必须使用限价，卖单预算至少按单笔安全金额上限预留。

开发/安全默认累计限制：每账户 10 次提交、预留名义金额 50,000 美元；
研究全实例 20 次调用、340,000 个保守预留 token，每次预留 16,000 输入加最多 1,000 输出，最多 2 个并发。
**这些不是用户的真实投资授权额度，也不是实际美元模型账单估计。**
失败或不确定结果仍消耗预算，不自动重试；额度不按时间自动重置。
SQLite `.local/safety.sqlite3` 在重启和多 worker 间共享，必须保留；不要通过删除账本恢复额度。
多副本必须共享同一本地 SQLite 文件或另行实现统一预算服务，不支持分离账本的分布式部署。
容器挂载保留此文件。默认不启用付费模型，即使有 key 也走 mock；需显式
`ENABLE_PAID_MODELS=true` 才允许调用。实盘仍要求原有显式开关、风控和人工确认。
Compose 发布端口及直接 API 开发命令默认仅回环监听。
