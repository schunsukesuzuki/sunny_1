#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if [[ -e .env ]]; then
  echo '.env is already present; leaving it untouched.'
else
  cp .env.example .env
  echo 'Created .env from .env.example. Open it and set E2B_API_KEY.'
fi
