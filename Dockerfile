# Hibana at a pinned commit plus this recipe's patches (patches/0001-0004), with its locked GB10 environment (uv.lock: torch 2.13 cu130, FlashInfer 0.6.17, Triton).
# Hibana runs on the host with uv by default; this puts the same `uv sync` in an image. The CUDA 13 devel base gives
# the /usr/local/cuda/bin/nvcc that Hibana's preflight wants and its first-use kernel builds need.
FROM nvidia/cuda:13.0.0-devel-ubuntu24.04@sha256:1e8ac7a54c184a1af8ef2167f28fa98281892a835c981ebcddb1fad04bdd452d

COPY --from=ghcr.io/astral-sh/uv:0.13.6@sha256:af22a52f5eafef3d78e551599d405c02df61919d18028f0cea8eda93bc9986d0 /uv /usr/local/bin/uv

ARG HIBANA_REPO=https://github.com/sharar-project/hibana.git
ARG HIBANA_COMMIT=d474b74d5a892b2cd1cc8fc50cb17946e2a539bb

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential ca-certificates curl git \
    && rm -rf /var/lib/apt/lists/*

# A uv-managed Python 3.12 (pyproject: python-preference only-managed), kept in the image, not in a cache volume.
ENV UV_PYTHON_INSTALL_DIR=/opt/uv-python UV_LINK_MODE=copy UV_COMPILE_BYTECODE=1 UV_NO_CACHE=1

WORKDIR /opt/hibana
RUN git init -q . \
    && git remote add origin "$HIBANA_REPO" \
    && git fetch -q --depth 1 origin "$HIBANA_COMMIT" \
    && git checkout -q FETCH_HEAD \
    && test "$(git rev-parse HEAD)" = "$HIBANA_COMMIT"
RUN uv sync --frozen
# Patches go on after the sync (the project is installed editable), so a patch change keeps the cached environment.
# 0001: cast tool arguments by anyOf/oneOf and type lists too, so an Optional[list] arrives as a list, not a string.
COPY patches/ /opt/patches/
RUN git apply /opt/patches/0001-tool-args-anyof.patch \
    && grep -q 'def _types(schema: dict)' hibana/api/parsers/tools.py
# 0002: image input for Flash-Next (Qwen vision tower and projector, image placeholders, multimodal M-RoPE positions in
#       attention and the sparse indexer). Upstream Hibana loads images only for Nemotron and Bolt.
# 0003: image requests keep speculative MTP decoding and run the captured CUDA graphs (M-RoPE rotary inputs), instead of
#       plain eager decoding.
RUN git apply /opt/patches/0002-flashnext-vision.patch \
    && git apply /opt/patches/0003-vision-speculation-graphs.patch \
    && grep -q 'class QwenVision' hibana/model/flashnext/vision.py \
    && grep -q 'HIBANA_VISION_GRAPHS' hibana/engine/config.py
# 0004 (v1.1.0, fixed in v1.1.1): repetition guard and late </think> ramp, distilled MTP draft head with 3-bit experts, GB10 kernels
#       (HyperConnection mix, split-K sparse attention, 3-bit GEMM geometry), route renormalization, prefill warmup.
#       The opt-in parts are switched on by compose.yaml; see the patch header.
RUN git apply /opt/patches/0004-v1.1-exact-speed-stack.patch \
    && ! grep -q 'if batch.eager:' hibana/engine/spec.py \
    && grep -q '_tail_periodic' hibana/engine/think_guard.py \
    && grep -q 'HIBANA_MTP_W3_EXPERTS_PATH' hibana/model/flashnext/mtp.py \
    && grep -q '_sparse_gqa_splitk_kernel' hibana/kernels/qsa/attention.py \
    && .venv/bin/python -m compileall -q hibana

ENV PATH=/opt/hibana/.venv/bin:/usr/local/cuda/bin:$PATH CUDA_HOME=/usr/local/cuda TRITON_CACHE_DIR=/root/.cache/triton
# No GPU at build time: the launcher is torch-free, so check that it and the locked torch build are there.
RUN hibana --help >/dev/null \
    && python /opt/patches/test_0001_tool_args_anyof.py \
    && python -c "import importlib.metadata as m; v = m.version('torch'); assert v.startswith('2.13.0') and 'cu130' in v, v; print('torch', v)"
