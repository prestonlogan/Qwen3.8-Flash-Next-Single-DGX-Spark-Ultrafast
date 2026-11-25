#!/usr/bin/env bash
set -euo pipefail
mode=${1:?default or exact}
label=${2:?label}
cd /home/plogan/experiments/hibana-flashnext-fast
out=/home/plogan/exp-hibana-goal20261125/v120-release-validation
mkdir -p "$out/$label"
if [ "$mode" = exact ]; then
  cat > speed-trial.yml <<'YAML'
services:
  hibana:
    image: hibana-flashnext-vision:d474b74d-v6
    environment:
      HIBANA_MTP_QSA_GUIDE: "0"
      HIBANA_QSA_PREFILL_BACKEND: original
      TUNING: v1.1-exact
      HIBANA_ACCEPT_DEFAULT: exact
      HIBANA_ACCEPT_SOFT: "0.0"
YAML
else
  cat > speed-trial.yml <<'YAML'
services:
  hibana:
    image: hibana-flashnext-vision:d474b74d-v6
    environment:
      HIBANA_MTP_QSA_GUIDE: "0"
      HIBANA_QSA_PREFILL_BACKEND: original
YAML
fi
docker rm -f hibana-flashnext >/dev/null 2>&1 || true
PROFILE=fast HOST=127.0.0.1 PORT=5806 RESTART=no docker compose -f compose.yaml -f vision-enabled.yml -f speed-trial.yml up -d --no-deps hibana > "$out/$label/compose.txt" 2>&1
health=000
for _ in $(seq 1 240); do
  health=$(curl -s -o /dev/null -w "%{http_code}" --max-time 2 http://127.0.0.1:5806/health 2>/dev/null || true)
  [ "$health" = 200 ] && break
  sleep 2
done
docker logs hibana-flashnext > "$out/$label/boot.log" 2>&1 || true
if [ "$health" != 200 ]; then
  echo "boot failed health=$health"
  exit 1
fi
grep -m1 "acceptance:" "$out/$label/boot.log" || true
echo "booted $label mode=$mode health=$health"
