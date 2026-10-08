#!/usr/bin/env bash
# Start local Ollama and ensure the FLOODTAIL primary model is present.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export HOME="${FLOODTAIL_OLLAMA_HOME:-$ROOT/.ollama-home}"
export OLLAMA_MODELS="${OLLAMA_MODELS:-$ROOT/.ollama-models}"
MODEL="${OLLAMA_PRIMARY_MODEL:-qwen2.5:3b-instruct}"
HOST="${OLLAMA_HOST:-http://127.0.0.1:11434}"

mkdir -p "$HOME/.ollama" "$OLLAMA_MODELS"

if ! curl -sf "${HOST}/api/tags" >/dev/null 2>&1; then
  echo "Starting ollama serve (HOME=$HOME OLLAMA_MODELS=$OLLAMA_MODELS)..."
  nohup ollama serve >"${TMPDIR:-/tmp}/ollama-serve.log" 2>&1 &
  for _ in $(seq 1 30); do
    if curl -sf "${HOST}/api/tags" >/dev/null 2>&1; then
      break
    fi
    sleep 1
  done
fi

if ! curl -sf "${HOST}/api/tags" >/dev/null 2>&1; then
  echo "ERROR: Ollama did not become ready at ${HOST}" >&2
  exit 1
fi

if ! ollama list 2>/dev/null | grep -q "${MODEL%%:*}"; then
  echo "Pulling ${MODEL}..."
  ollama pull "$MODEL"
fi

echo "Ollama ready at ${HOST}; model ${MODEL}"
ollama list
