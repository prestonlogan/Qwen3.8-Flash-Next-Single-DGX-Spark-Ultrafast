#!/usr/bin/env bash
# Fetch what `hibana serve flashnext` will serve, with Hibana's own pinned revisions and checks (hibana/launch/preflight.py):
# the RadixArk NVFP4 checkpoint (135 GB) into the shared HF cache, the calibrated 3-bit copies (51 GB) into
# $HIBANA_RESULTS/w3-checkpoints, and the DFlash2 drafter (1.2 GB) when PROPOSER=dflash2. Resumable; a no-op once
# everything is present. The 3-bit copies are fetched for every profile, so switching PROFILE needs no new download.
# With TUNING=v1.1 (the default) it also fetches this recipe's distilled MTP draft head (1.2 GB) into the same folder
# and checks its SHA-256.
set -euo pipefail

proposer=${PROPOSER:-mtp}
case $proposer in
  mtp | dflash2) ;;
  *) echo "PROPOSER must be mtp or dflash2 (got $proposer)" >&2; exit 2 ;;
esac

HIBANA_PROPOSER=$proposer python - <<'PY'
import sys
from hibana.launch import preflight
from hibana.launch.settings import resolve

s = resolve("flashnext", "fast")
try:
    preflight.ensure_snapshots(s)
    w3 = preflight.ensure_w3(s)
except preflight.PreflightError as exc:
    sys.exit(f"download: {exc}")
if w3 is None:
    sys.exit("download: the 3-bit copies did not arrive (see above); PROFILE=exact still serves without them")
print(f"present: RadixArk/Qwen3.8-Flash-Next-NVFP4, 3-bit copies in {w3}")
PY

[[ ${TUNING:-v1.1} == v1.1* ]] || exit 0
DRAFT_HEAD_REPO=${DRAFT_HEAD_REPO:-prestonlogan/Qwen3.8-Flash-Next-MTP-Draft-Head} python - <<'PY'
import hashlib, os, shutil, sys
from pathlib import Path
from huggingface_hub import hf_hub_download

repo = os.environ["DRAFT_HEAD_REPO"]
dest = Path(os.environ.get("HIBANA_RESULTS", "/data")) / "w3-checkpoints"
files = {  # file: SHA-256
    "mtp-t35-overlap-body.pt": "964a0756170bd3c7ef8b7b785d761b8dbe0706939ed4ff3d7286108d9dcde0f6",
    "mtp-t35-overlap-w3exp.pt": "b2db323c741517b3d4d244801c20af4a90cd909a09d72d3d550e4b34d5396c50",
}

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 24), b""):
            h.update(chunk)
    return h.hexdigest()

dest.mkdir(parents=True, exist_ok=True)
for name, want in files.items():
    out = dest / name
    if out.is_file() and sha256(out) == want:
        continue
    try:
        got = Path(hf_hub_download(repo, name))
    except Exception as exc:  # network, missing repo, rate limit
        sys.exit(f"download: draft head {repo}/{name}: {exc} (TUNING=stock serves without it)")
    if sha256(got) != want:
        sys.exit(f"download: {repo}/{name} has the wrong SHA-256")
    shutil.copyfile(got, out)
print(f"present: distilled MTP draft head from {repo} in {dest}")
PY
exit 0
