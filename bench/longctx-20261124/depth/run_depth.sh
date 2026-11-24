#!/usr/bin/env bash
# Decode speed with the context already filled, via tool-eval-bench's perf mode (pip install tool-eval-bench).
# BASE defaults to the recipe's port; the recipe has no key check, so the key is a placeholder.
BASE=${BASE:-http://127.0.0.1:8888}; MODEL=${MODEL:-local-ai}; KEY=${API_KEY:-none}
OPENAI_API_KEY=$KEY tool-eval-bench --base-url "$BASE" --api-key "$KEY" --model "$MODEL" \
  --perf-only --pp 2048 --tg 512 --depth 0,32768,65536,100000,150000,200000,250000 --concurrency 1 --benchy-runs 2 \
  --context-size 262144 --label "v1.1.0 default, decode at depth" --output-dir runs --no-live --json-file depth.json
