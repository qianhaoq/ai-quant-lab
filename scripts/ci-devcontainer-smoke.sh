#!/usr/bin/env bash
set -euo pipefail

node --version
python3 --version
corepack enable
pnpm --version
pnpm install --frozen-lockfile
pnpm api:install
pnpm api:test
pnpm typecheck
pnpm lint
pnpm runner:test
pnpm build
