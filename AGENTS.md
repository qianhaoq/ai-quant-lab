# ai-quant-lab Agent Rules

用中文和用户对话。

This repository is an AI-native quantitative research lab for US stocks and ETFs.

## Product Boundaries

- v1 is research-only: backtesting, paper-style simulation, and AI-assisted analysis.
- Do not add live trading, broker OAuth, real order placement, account funding, portfolio custody, or automated execution.
- Do not present AI output as investment advice. Keep AI responses framed as research hypotheses and validation suggestions.
- The app must run without paid data, broker credentials, or an LLM key by using sample data and mock AI fallback.

## Engineering Rules

- Keep the monorepo split: `apps/web` owns Next.js UI, `apps/api` owns FastAPI/data/backtesting/AI APIs.
- Backend behavior changes require pytest coverage.
- Frontend behavior changes require Vitest coverage; user-critical flows should also keep the Playwright smoke test working.
- Do not commit secrets or real API keys. Use `.env.example` for configuration shape only.
- Prefer small, reversible PRs with a linked issue, test evidence, preview URL, and risk notes.
