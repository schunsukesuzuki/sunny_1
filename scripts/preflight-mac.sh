#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
printf '\n[1/5] macOS / native Ollama\n'
if [[ "$(uname -s)" != 'Darwin' ]]; then echo 'NOTE: Apple Metal check requires macOS.'; fi
if ! command -v ollama >/dev/null; then echo 'Ollama not installed'; exit 1; fi
if ! curl -fsS http://localhost:11434/api/tags >/dev/null; then
  echo 'Ollama cannot be reached: start native macOS Ollama app'; exit 1
fi
ollama list
printf '\n[2/5] GPU process\n'
echo 'The model must be loaded for ollama ps to show GPU usage.'
ollama ps
printf '\n[3/5] .env and Docker\n'
if [[ ! -f .env ]]; then echo 'Missing .env: cp .env.example .env'; exit 1; fi
if ! command -v docker >/dev/null; then echo 'Docker CLI missing'; exit 1; fi
if ! grep -qE '^E2B_API_KEY=[^[:space:]]{10}' .env; then
  echo 'WARNING: E2B_API_KEY may be missing. Do not paste the key in chat or logs.'
fi
printf '\n[4/5] containers / host published ports\n'
docker compose ps
printf '\n[5/5] health through Docker Vite proxy\n'
if curl -fsS http://127.0.0.1:5173/api/health >/dev/null; then
  echo 'Web proxy -> FastAPI health OK'
else
  echo 'WARNING: React/Vite proxy -> FastAPI health failed, inspect docker compose logs api web'
fi
printf '\nNote: default API host port is 18000, not 8000.\n'
