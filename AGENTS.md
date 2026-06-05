# ai-quant-lab Agent Rules

用中文和用户对话。

This repository is an AI-native quantitative trading platform for US stocks and ETFs.

## Product Boundaries

- The default runtime must remain safe without broker credentials: internal sandbox, sample data, and mock AI fallback must keep working.
- Live-capable broker work is allowed only behind explicit configuration, risk precheck, and human confirmation. Never add unguarded real order submission.
- AI may generate signal hypotheses, risk analysis, and order intent drafts. AI must not bypass risk checks, confirmation phrases, broker safety switches, or human review.
- Do not present AI output as investment advice. Keep AI responses framed as hypotheses, risk checks, and validation suggestions.
- Do not add account funding, custody movement, credential collection UI, or broker OAuth flows without a separate security and compliance review.

## Engineering Rules

- Keep the monorepo split: `apps/web` owns Next.js UI, `apps/api` owns FastAPI/data/trading/backtesting/AI APIs.
- Backend behavior changes require pytest coverage.
- Frontend behavior changes require Vitest coverage; user-critical flows should also keep the Playwright smoke test working.
- Do not commit secrets or real API keys. Use `.env.example` for configuration shape only.
- Prefer small, reversible PRs with a linked issue, test evidence, preview URL, and risk notes.
