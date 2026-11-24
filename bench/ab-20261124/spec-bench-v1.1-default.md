# Speculative Decoding Benchmark — RadixArk/Qwen3.8-Flash-Next-NVFP4

- **Run ID**: `2026-11-24T15-46-31.521994Z_1b2b9a02`
- **Date**: `2026-11-24T15:46:31.522031+00:00`
- **Mode**: spec-bench
- **tool-eval-bench**: `v3.1.1.dev4+ga53ff61de`
- **Label**: <code>hibana v1.1.0 (T94 + accept_soft 0.35), DGX Spark</code>
- **Spec Method**: unknown
- **Runs per cell**: 3 (counters pooled, α range shown per row)
- **Temperature**: 0 (greedy: a ceiling for sampled workloads)

> [!NOTE]
> Acceptance rate metrics were not available from the server.
> Effective t/s (wall-clock based) still captures the real benefit
> of MTP / speculative decoding.

## Inference Engine

| Property | Value |
|---|---|
| Quantization | NVFP4 |
| Host | `spark-9535` |
| Platform | `Linux-7.0.0-1025-nvidia-aarch64-with-glibc2.39` |
| Python | 3.12.14 |

## Results

| Prompt | Depth | Eff t/s | Stream t/s | Speedup | TTFT (ms) | Total (ms) | Tokens |
|---|---:|---:|---:|---:|---:|---:|---:|
| filler | 0 | 169.9 | 179.9 | — | 292 | 1,040 | 128 |
| code | 0 | 154.2 | 156.7 | — | 148 | 972 | 128 |
| structured | 0 | 192.0 | 192.2 | — | 167 | 829 | 128 |
| filler | 4096 | 157.3 | 157.5 | — | 156 | 964 | 128 |
| code | 4096 | 107.5 | 107.7 | — | 96 | 1,278 | 128 |
| structured | 4096 | 188.6 | 188.7 | — | 73 | 747 | 128 |
| filler | 8192 | 125.0 | 125.1 | — | 172 | 1,188 | 128 |
| code | 8192 | 129.9 | 130.8 | — | 108 | 1,085 | 128 |
| structured | 8192 | 168.6 | 170.6 | — | 82 | 835 | 128 |

## Per-Prompt-Type Summary

| Prompt Type | Avg Eff t/s | Avg Stream t/s | Avg α | Avg Waste |
|---|---:|---:|---:|---:|
| code | 130.5 | 131.8 | — | — |
| filler | 150.7 | 154.1 | — | — |
| structured | 183.1 | 183.8 | — | — |

## Interpretation Guide

- **Eff t/s** (Effective t/s): Tokens after the first ÷ wall-clock time after the first token, the same window a throughput baseline uses. This is what users experience. Higher is better.
- **Stream t/s**: Token generation rate measured from SSE stream timing. For standard decoding, this matches Eff t/s. For spec decode, Eff t/s is typically higher.
- **α (accept)**: Acceptance rate — % of draft tokens accepted by the verifier. Higher means the draft model/MTP heads predict well for this workload.
- **Waste**: Fraction of drafted tokens rejected (1 − α). Lower is better. High waste means the draft model is poorly aligned with the target.
- **τ (length)**: Average acceptance length, the tokens produced per speculative step, counting the verifier's own bonus token. Higher means more tokens generated per verification pass.
- **Window**: Average tokens drafted per speculative step (the configured draft window). Window utilization is (τ − 1) ÷ Window, the share of drafted positions accepted.
- **Draft t/s**: Rate at which draft tokens are generated, regardless of acceptance. Compare with Eff t/s to see draft overhead.
- **Steps/s**: Target-model verification passes per second. Without speculation each pass yields one token, and a verification pass costs at least a plain decode pass, so this is a lower bound on the no-spec decode rate and Eff t/s ÷ Steps/s (≈ τ) is a ceiling on the speedup. `--baseline-tgs` gives the measured figure.
- **Speedup**: Effective t/s ÷ baseline t/s. Values > 1.0x indicate spec decode is providing a benefit.

> [!TIP]
> Acceptance rates vary significantly by prompt type. Code and structured tasks
> typically show higher acceptance rates than creative/open-ended generation
> because future tokens are more predictable.
