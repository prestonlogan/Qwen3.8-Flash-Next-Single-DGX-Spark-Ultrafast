# Needle in a Haystack Benchmark — RadixArk/Qwen3.8-Flash-Next-NVFP4

- **Run ID**: `2026-11-24T06-16-54.492554Z_39c5b91b`
- **Date**: `2026-11-24T06:16:54.493284+00:00`
- **Mode**: needle
- **tool-eval-bench**: `v3.1.1.dev4+ga53ff61de`
- **Label**: <code>hibana v1.0.0 fast profile, DGX Spark</code>
- **Retrieval Accuracy**: **100.0%**
- **Effective Context**: ~260,096 tokens (estimated)
- **Completion**: 100.0%
- **Rating**: ★★★★★ Excellent

## Inference Engine

| Property | Value |
|---|---|
| Quantization | NVFP4 |
| Host | `spark-9535` |
| Platform | `Linux-7.0.0-1025-nvidia-aarch64-with-glibc2.39` |
| Python | 3.12.14 |

## Needle in a Haystack — Retrieval

**Retrieval Accuracy:** 100.0% (20/20)
**Rating:** ★★★★★ Excellent
**Context Window:** 262,144 tokens
**Effective Context:** ~260,096 tokens (estimated; largest fully retrieved length)
*Haystack sizes are estimated at 4 characters per token. Common tokenizers pack more characters into each token, so the real prompts run 10-17% smaller than labelled.*
**Duration:** 710.1s
**Tokens:** 2,299,526

### Retrieval Grid

Rows are needle depth, columns are haystack size.

| Depth | ~1K | ~85K | ~169K | ~254K |
|---|---|---|---|---|
| 0% | ✅ | ✅ | ✅ | ✅ |
| 25% | ✅ | ✅ | ✅ | ✅ |
| 50% | ✅ | ✅ | ✅ | ✅ |
| 75% | ✅ | ✅ | ✅ | ✅ |
| 100% | ✅ | ✅ | ✅ | ✅ |

### Accuracy by Haystack Size

| Context (estimated tokens) | Accuracy |
|---|---:|
| ~1,024 | 100.0% |
| ~87,381 | 100.0% |
| ~173,738 | 100.0% |
| ~260,096 | 100.0% |
