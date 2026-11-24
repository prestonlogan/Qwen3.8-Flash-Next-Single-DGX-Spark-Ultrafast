#!/usr/bin/env bash
# Docker healthcheck for the hibana service. Healthy when /health answers 200.
#
# Hibana answers 503 only after its engine thread has failed (for example a CUDA error), or while it drains on
# shutdown; the web server itself stays up. Docker restart policies act only when the container exits, so a failed
# engine would stay unavailable until someone restarted it by hand. On a 503 this script stops the server so the
# container exits and RESTART=unless-stopped can bring it back: SIGTERM to PID 1 (tini forwards it, and Hibana drains),
# then SIGKILL if it is still answering 503 a minute later (the same as compose's stop_grace_period).
# Timeouts and refused connections (busy, or still starting) only count as unhealthy.
set -u
mark=/tmp/hibana-unavailable
code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 4 "http://127.0.0.1:${PORT:-8888}/health")
if [[ $code == 200 ]]; then
  rm -f "$mark"
  exit 0
fi
if [[ $code == 503 ]]; then
  say() { echo "$(date -u +%FT%TZ) health: $*" > /proc/1/fd/1; }
  if [[ ! -e $mark ]]; then
    touch "$mark"
    say "engine unavailable (HTTP 503); stopping the server so the container exits and the restart policy can act"
    kill -TERM 1
  elif (( $(date +%s) - $(stat -c %Y "$mark") >= 60 )); then
    say "engine still unavailable 60 s after SIGTERM; killing"
    kill -KILL -1
  fi
fi
exit 1
