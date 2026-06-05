# GitHub Trading System Research

This document records the reusable patterns reviewed before moving `ai-quant-lab` from a backtesting demo toward a live-ready AI quantitative trading platform.

## Reviewed Systems

| Project | What It Provides | Reuse Decision |
| --- | --- | --- |
| [QuantConnect LEAN](https://github.com/QuantConnect/Lean) | Event-driven algorithmic trading engine with live trading, alternative data, pluggable modules, and CLI live deployment. | Do not embed in v1. Borrow the event-driven broker/data separation and keep LEAN as a future engine option. |
| [Lumibot](https://github.com/Lumiwealth/lumibot) | Python strategy framework for stocks, options, crypto, futures, and forex; supports real brokers, Alpaca config, paper-first operation, and AI agent hooks. | Borrow the paper-first broker wrapper pattern and AI-as-agent boundary. Evaluate as a future Python strategy runtime. |
| [alpaca-py](https://github.com/alpacahq/alpaca-py) | Official Alpaca Python SDK for trading, broker, and market data clients with paper/sandbox credentials. | Use Alpaca-compatible REST/API semantics as the first real broker integration boundary. SDK adoption can follow once API surface stabilizes. |
| [vn.py / VeighNa](https://github.com/vnpy/vnpy) | Chinese open-source quant trading platform with many gateways and modules for portfolio strategy, algo trading, paper accounts, risk management, web trading, and AI/ML work. | Do not embed in this Next/FastAPI monorepo. Borrow gateway, paper account, risk manager, and web trader module boundaries. |
| [OpenAlgo](https://github.com/marketcalls/openalgo) | Self-hosted Flask/React trading platform with unified broker API, strategy host, sandbox engine, monitoring, and PnL tracking. | Borrow the unified broker API plus sandbox-before-live workflow. Keep frontend/API stack local instead of adopting the whole app. |
| [aat](https://github.com/AsyncAlgoTrading/aat) | Async event-driven trading framework with live/backtest engines plus risk and execution components. | Borrow the separation between trading, risk, execution, and backtest engines. Evaluate later for asynchronous execution. |

## Architecture Choice

The v1 repo should not import a full external trading platform. LEAN and vn.py are mature but too broad for this scaffold, and adopting them now would make the web/API product harder to review. Instead, the repo should implement a narrow adapter boundary:

- `internal_sandbox` remains the default provider and must work without credentials.
- `/trading/status`, `/trading/account`, `/trading/positions`, `/trading/orders/preview`, and `/trading/orders` form the broker-facing contract.
- Every order intent must pass risk precheck before submission.
- Manual confirmation is mandatory; AI-generated signals cannot directly submit orders.
- Alpaca paper/live is the first external broker boundary because its paper and live REST surfaces are simple and well documented.
- Future strategy runtimes can call the same order-intent API instead of touching broker credentials directly.

## Next Integration Stages

1. Keep internal sandbox as the CI/default path.
2. Add Alpaca paper account read/write tests with mocked HTTP responses.
3. Add broker error normalization for rejected orders, insufficient buying power, market closed, and auth failures.
4. Add persistent order ledger and audit trail before any live rollout.
5. Add pre-trade risk modules for max daily loss, position concentration, duplicate order detection, and market-hours checks.
6. Only after paper mode is validated, gate live mode behind `ENABLE_LIVE_TRADING=true`, protected credentials, operator review, and production monitoring.
