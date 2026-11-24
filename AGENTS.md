# AGENTS.md

Serve Qwen3.8-Flash-Next (125B MoE, RadixArk NVFP4 checkpoint, 135 GB, plus Hibana's calibrated 3-bit copies, 51 GB)
with image input on one DGX Spark with [Hibana](https://github.com/sharar-project/hibana) via Docker Compose. Based on
[dedene/Hibana-Qwen3.8-Flash-Next-DGX-Spark](https://github.com/dedene/Hibana-Qwen3.8-Flash-Next-DGX-Spark) (6948e9b);
this recipe adds patches 0002 and 0003 (image input), patch 0004 (v1.1.0 speed and repetition stack), and ships
Hibana's `fast` profile with `TUNING=v1.1` as the default.

## Layout

- `compose.yaml`: `download` (one-shot, Hibana's own pinned fetch) -> `hibana` (the server on :8888). Both use the
  image built from `Dockerfile`.
- `tools/download.sh`: runs Hibana's `preflight.ensure_snapshots` + `ensure_w3` for the `fast` profile, so every profile
  can start without a new download, then (TUNING=v1.1) the distilled draft head from `DRAFT_HEAD_REPO`, SHA-256
  checked, into `DATA_DIR/w3-checkpoints`. `exit 0` last.
- `tools/serve.sh`: maps this recipe's settings to `hibana serve flashnext` flags and `HIBANA_*`.
- `tools/check.py`: stdlib-only functional checks against a running server, including image input.
- Knobs are `${VAR:-default}` in compose and serve.sh; `.env.example` documents each one.
- `patches/`: applied in order by the Dockerfile after `uv sync`, each followed by a `grep -q` or test.
  - 0001 (dedene): tool arguments cast by anyOf/oneOf/type lists.
  - 0002: Flash-Next image input: Qwen vision tower and projector (`model/flashnext/vision.py`), image placeholder
    expansion, multimodal M-RoPE positions in attention and the sparse indexer. `HIBANA_VISION=1` loads it.
  - 0003: image requests keep MTP speculation (`HIBANA_VISION_SPEC`, default on) and the captured CUDA graphs with
    M-RoPE rotary inputs (`HIBANA_VISION_GRAPHS`, default on). Text requests take the same paths as before.
  - 0004 (v1.1.0): repetition guard and late `</think>` ramp (`engine/think_guard.py`), distilled MTP draft head with
    3-bit experts (`HIBANA_MTP_WEIGHTS`, `HIBANA_MTP_W3_EXPERTS*`), GB10 kernels (HyperConnection mix, split-K sparse
    attention, 3-bit GEMM geometry), route renormalization, prefill warmup. The patch header lists which parts are
    opt-in; `tools/serve.sh` turns them on when `TUNING=v1.1` (default) and `PROFILE=fast`.
- `TUNING=stock` reproduces v1.0.0 behavior (Hibana `fast`, `accept_soft` 0.5, stock MTP head, DRAFT_VOCAB 131072).

## Verify

```bash
docker compose config --quiet
shellcheck tools/*.sh
python3 -m py_compile tools/*.py
docker compose up -d --wait      # on the Spark, with :8888 free
tools/check.py                   # all ok, including "image input"
```

## Pins

- Hibana `d474b74d5a892b2cd1cc8fc50cb17946e2a539bb` (tag v0.1.0, 2026-11-13). Its `uv.lock` pins the Python stack
  (torch 2.13.0+cu130, flashinfer 0.6.17, triton 3.7.1, b12x 1.5.0). Patches 0002-0004 apply to this commit only, in order.
- Base image `nvidia/cuda:13.0.0-devel-ubuntu24.04@sha256:1e8ac7a54c184a1af8ef2167f28fa98281892a835c981ebcddb1fad04bdd452d`,
  uv `ghcr.io/astral-sh/uv:0.13.6@sha256:af22a52f5eafef3d78e551599d405c02df61919d18028f0cea8eda93bc9986d0`.
- Image tag `hibana-flashnext-vision:d474b74d-v2`: bump `-vN` with every Dockerfile or patch change.
- Weights, pinned in Hibana's source (`hibana/model/flashnext/config.py`), not here:
  `RadixArk/Qwen3.8-Flash-Next-NVFP4@7b719225242aacd3dbd3f9407468c2ee9a9d2594` (includes the vision tower weights),
  `yemara/Qwen3.8-Flash-Next-NVFP4-sharar-w3-qad@5c4c62a62853caebea8cedda7fbed952efa1effe`,
  this recipe's distilled MTP draft head (SHA-256 pinned in `tools/download.sh`),
  DFlash2 `incoai/Qwen3.8-Flash-Next-DFlash2@a22a1744e85c17364dcc54a6a420af7135d4c7f6`.

## Model facts

- Qwen3.8-Flash-Next: 48 layers (36 Gated DeltaNet, 12 attention with a sparse indexer), 512 experts, top 10, MTP head,
  262K context, and a vision tower that upstream Hibana does not load.
- Hibana loads the trunk as FP8 in every profile. `fast` (default here and in Hibana) serves 3-bit experts and trunk
  copies and relaxed sampled acceptance (`accept_soft` 0.5); `TUNING=v1.1` switches `fast` to exact acceptance with
  the distilled draft head. `exact` keeps NVFP4 experts and exact acceptance.
- Do not raise `HIBANA_ACCEPT_SOFT` above 0.5: at 1.0-3.0 long thinking runs fell into repetition loops and ended with
  no answer (1 in 5 to 1 in 3 replays of one agent task). Hibana's authors cap Flash-Next at 0.5 too.
- `HIBANA_DRAFT_VOCAB` (98304 with TUNING=v1.1, 131072 with stock): the MTP drafter reads only the first N rows of the vocabulary head.
  Verification uses the full vocabulary. Hibana leaves it off because it lowers draft acceptance on non-English text,
  and it is not supported across two Sparks.
- Images: inline only (OpenAI `image_url` with a base64 `data:` URL, or an Anthropic base64 `image` block); the server
  fetches no URLs. At most 32 MiB encoded and 100 images per request. Each is resized to between 65,536 and 1,048,576
  pixels (Qwen's smart_resize). No video. One Spark only. The vision tower adds 0.84 GiB of weights.
- Thinking is on unless a request sends `chat_template_kwargs.enable_thinking: false`. Reasoning comes back in
  `reasoning_content`. Any `model` id is accepted. No API key check.
- Omitted `temperature` is 1.0 with top_p 0.95, top_k 20 (the generation config).

## Constraints

- Hibana at a pinned commit plus `patches/`. Keep each patch applying cleanly with `git apply` from `/opt/hibana`.
- Never `hf cache prune` on the Spark (it deletes every revision-pinned snapshot).
- Speed claims in the README come from measured runs only; record the date, settings and method next to each number.
