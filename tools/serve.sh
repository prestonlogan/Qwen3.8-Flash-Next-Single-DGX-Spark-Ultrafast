#!/usr/bin/env bash
# `hibana serve flashnext` with this recipe's settings. Every engine flag lives here; extra arguments from compose are
# appended. The download service already fetched the pinned files, so this serve never downloads (--no-fetch).
set -euo pipefail

profile=${PROFILE:-fast}
case $profile in
  exact | fast | throughput) ;;
  *) echo "PROFILE must be exact, fast or throughput (got $profile)" >&2; exit 2 ;;
esac
proposer=${PROPOSER:-mtp}
case $proposer in
  mtp | dflash2) ;;
  *) echo "PROPOSER must be mtp or dflash2 (got $proposer)" >&2; exit 2 ;;
esac
case ${SSD:-on} in
  on) export HIBANA_SSD=1 HIBANA_SSD_GIB=${SSD_GIB:-100} ;;
  off) export HIBANA_SSD=0 ;;
  *) echo "SSD must be on or off (got $SSD)" >&2; exit 2 ;;
esac
export HIBANA_HOST_FLOOR_GIB=${HOST_FLOOR_GIB:-12}

# TUNING=v1.1 (default, PROFILE=fast only): exact speculative acceptance, the distilled MTP draft head, the repetition
# guard with its late </think> ramp, and the GB10 kernel and routing settings from patch 0004. TUNING=stock serves
# Hibana's own `fast` settings, the v1.0.0 behavior. Values already set in the environment win.
tuning=${TUNING:-v1.1}
case $tuning in
  v1.1 | stock) ;;
  *) echo "TUNING must be v1.1 or stock (got $tuning)" >&2; exit 2 ;;
esac
if [[ $profile == fast && $tuning == v1.1 ]]; then
  head_dir=${HIBANA_RESULTS:-/data}/w3-checkpoints
  for f in mtp-t35-overlap-body.pt mtp-t35-overlap-w3exp.pt; do
    [[ -s $head_dir/$f ]] || { echo "TUNING=v1.1 needs $head_dir/$f (the download service fetches it)" >&2; exit 2; }
  done
  v11=(
    # Speculation: lossless acceptance, the distilled draft head, a measured draft-step cost.
    HIBANA_ACCEPT_DEFAULT=exact HIBANA_ACCEPT_SOFT=0.0 HIBANA_SPEC_STEP_COST=0.055 HIBANA_VISION_SPEC=1
    HIBANA_MTP_WEIGHTS=$head_dir/mtp-t35-overlap-body.pt HIBANA_MTP_W3_EXPERTS=1
    HIBANA_MTP_W3_EXPERTS_PATH=$head_dir/mtp-t35-overlap-w3exp.pt
    # Precision and routing.
    'HIBANA_W3_SKIP_REGEX=\.ple\.' HIBANA_SSM_STATE=int8 HIBANA_SSM_COMPENSATORS=8 HIBANA_KV_FORMAT=fp8
    HIBANA_MOE_KEEP=4 HIBANA_MOE_BUDGET=18:64 HIBANA_ROUTE_PARSEVAL=1 HIBANA_ROUTE_CANDIDATES=20 HIBANA_ROUTE_BETA=-0.25
    # GB10 kernels and startup.
    HIBANA_HYPER_MIX_CUDA=16 HIBANA_WARMUP_PREFILL_TOKENS=4096
    # Repetition guard and the late </think> ramp (no bias before 40% of max_tokens or 4,096 thinking tokens).
    HIBANA_THINK_GUARD=1 HIBANA_THINK_SOFT_BIAS=5.5 HIBANA_THINK_SOFT_FIRM_BIAS=16.0 HIBANA_THINK_SOFT_START=4096
    HIBANA_THINK_SOFT_END=8192 HIBANA_THINK_SOFT_FIRM_END=12288 HIBANA_THINK_SOFT_START_FRAC=0.40
    HIBANA_THINK_SOFT_END_FRAC=0.58 HIBANA_THINK_SOFT_FIRM_FRAC=0.70
  )
  for kv in "${v11[@]}"; do
    name=${kv%%=*}
    [[ -n ${!name:-} ]] || export "$kv"
  done
fi
# Draft vocabulary shortlist: 98,304 rows for the distilled head (v1.1), 131,072 for the stock head (v1.0.0).
if [[ -z ${HIBANA_DRAFT_VOCAB:-} ]]; then
  [[ $tuning == v1.1 ]] && export HIBANA_DRAFT_VOCAB=98304 || export HIBANA_DRAFT_VOCAB=131072
fi

args=(
  flashnext "--$profile"
  --host "${HOST:-0.0.0.0}"
  --port "${PORT:-8888}"
  --context-length "${CONTEXT:-262144}"
  --proposer "$proposer"
  --no-fetch
)
# Empty: the profile's own value (exact: 4 drafts, fast: adaptive up to 8; batch 4 in both).
[[ -n ${SPEC:-} ]] && args+=(--spec "$SPEC")
[[ -n ${PARALLEL:-} ]] && args+=(--max-batch "$PARALLEL")

echo "serve: profile $profile, tuning $tuning, proposer $proposer, spec ${SPEC:-profile}, batch ${PARALLEL:-profile}," \
  "context ${CONTEXT:-262144}, SSD tier ${SSD:-on}, host floor ${HIBANA_HOST_FLOOR_GIB} GiB," \
  "vision ${HIBANA_VISION:-0}, draft vocab ${HIBANA_DRAFT_VOCAB:-0}"
exec hibana serve "${args[@]}" "$@"
