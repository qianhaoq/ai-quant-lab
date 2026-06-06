#!/usr/bin/env bash
set -euo pipefail

node --version
python3 --version
if ! command -v pnpm >/dev/null 2>&1 || [ "$(pnpm --version)" != "10.12.1" ]; then
  sudo npm install -g pnpm@10.12.1
fi
pnpm --version
pnpm install --frozen-lockfile
pnpm api:install
pnpm api:test
pnpm typecheck
pnpm lint
pnpm runner:test
pnpm build
