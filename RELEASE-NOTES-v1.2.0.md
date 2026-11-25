# v1.2.0

Validated on one DGX Spark on 2026-11-25. This release adds target-guided long-context draft attention, automatic QSA prefill, and the HyperConnection startup fix. It is based on v1.1.1, so it includes the host-path acceptance fix.

## What changed

- Patch 0005 guides MTP draft attention after 65,536 tokens. The draft keeps 14,336 recent KV pages plus up to 2,048 distant pages selected by the target model's verify-time sparse attention at layer 43.
- `TUNING=v1.1` and `TUNING=v1.1-exact` enable the guide by default. Image requests and budget speculation are excluded.
- `HIBANA_QSA_PREFILL_BACKEND=auto` is set in the v1.1 serve settings.
- The HyperConnection tensor-core kernel no longer contains programmatic dependent launch instructions that the host never launched correctly. This fixes the intermittent batch 4 verify capture freeze.
- Patch 0004 includes the v1.1.1 `think_bias` fix and the Dockerfile guard against `if batch.eager:`.
- Patch 0006 fixes issue #10: inside thinking, the engine masks the `</think>` token unless the previous token ends in a newline, and the parser ends reasoning on the token id instead of the text, so quoting or explaining the tag no longer ends the turn.

## Measured results

All numbers below are from the v1.2.0 validation on one DGX Spark on 2026-11-25. The comparison baseline is the same image with `HIBANA_MTP_QSA_GUIDE=0` and `HIBANA_QSA_PREFILL_BACKEND=original`. The released v1.1.1 image cannot reliably complete batch 4 verify capture because it still has the old PDL instructions.

### Startup, crash, and smoke

- Five consecutive cold boots passed. Each reached warmup, health 200, and repeated batch 4 verify capture.
- The crash regression passed with `HIBANA_DRAFT_VOCAB=98304`: no temperature, then 0.3, then four concurrent requests produced zero NameError or Traceback entries.
- `tools/check.py --needle 70000` passed model listing, alias, thinking off, thinking on, tool call, tool round trip, streaming, Dutch, image input, speed, image speed, and the 70K needle.

### Short context

Decode tok/s, median of 3 runs (temperature 0 and 4 requests) or 5 runs (single sampled requests), from `bench/bench.py`. Raw runs: [bench/v120-20261125](bench/v120-20261125/README.md).

| Cell | v1.1.1 equivalent | v1.2.0 | Run range, v1.1.1 eq. | Run range, v1.2.0 |
|---|---:|---:|---|---|
| Default prose T0 | 122.1 | 123.0 | 120.8 to 127.5 | 120.8 to 126.7 |
| Default code T0 | 166.8 | 166.3 | 163.5 to 171.6 | 163.0 to 171.8 |
| Default image prose T0 | 116.2 | 116.3 | 103.5 to 119.3 | 103.2 to 119.9 |
| Default prose T1.0 | 115.2 | 125.7 | 94.8 to 137.1 | 111.2 to 141.8 |
| Default code T1.0 | 131.8 | 131.4 | 122.5 to 140.9 | 127.2 to 135.1 |
| Default image prose T1.0 | 92.4 | 93.2 | 88.9 to 95.1 | 83.4 to 96.7 |
| Default 4 requests T0 | 298.4 | 288.6 | 283.6 to 308.4 | 282.4 to 302.1 |
| Default 4 requests T1.0 | 231.4 | 209.1 | 208.9 to 242.7 | 190.6 to 222.7 |
| Exact prose T0 | 102.1 | 102.7 | 82.7 to 105.3 | 82.9 to 106.4 |
| Exact code T0 | 102.3 | 101.9 | 98.7 to 104.2 | 99.5 to 104.9 |
| Exact image prose T0 | 87.1 | 87.6 | 85.2 to 96.9 | 84.7 to 95.6 |
| Exact prose T1.0 | 92.5 | 97.1 | 85.6 to 108.6 | 79.8 to 103.4 |
| Exact code T1.0 | 108.1 | 97.0 | 92.2 to 123.0 | 94.1 to 109.8 |
| Exact image prose T1.0 | 84.7 | 80.6 | 77.9 to 85.4 | 77.1 to 84.9 |
| Exact 4 requests T0 | 226.5 | 225.8 | 221.1 to 284.9 | 221.0 to 283.8 |
| Exact 4 requests T1.0 | 199.3 | 187.9 | 174.5 to 204.5 | 172.3 to 206.6 |

At temperature 0, every cell is within 3.3 percent and the run ranges overlap. Patch 0005 is inactive below 65,536 tokens, so short prompts run the same draft path as before. Sampled cells move more in both directions (default prose +9 percent, exact code -10 percent), and every sampled range overlaps. The 4-request sampled medians were lower in both modes (-9.6 percent default, -5.7 percent exact). We count that as noise at 3 runs, but it is the one consistent direction in the table, so it is listed under known caveats.

### Long context

| Test | v1.1.1 equivalent | v1.2.0 |
|---|---:|---:|
| Realistic decode at 100K | 89.9 | 101.0 |
| Realistic decode at 250K | 74.4 | 100.4 |
| Fixed exact 100K copy | 149.0 | 179.3 |
| Batch 2 fixed live, warm | 202.1 | 229.3 to 244.3 |
| Batch 2 fixed live, first request after boot | 202.1 | 187.8 |

The 100K comparison used four runs each. The 250K comparison used two runs each. The fixed copy prompt was 99,964 tokens. Batch 2 used two 99,968-token prompts and 320 output tokens. The first batch 2 request after boot paid a one-time guide warmup cost; later runs were 14 to 21 percent faster.

### Quality

- Exact fixed prompts were byte-identical. The short code prompt hash was `9b423bbd358845b6c12a4bf8e836bec5041641d55004374c3d3947a912d31a55`; the 133K archive prompt hash was `1981371a29c2ed1cb2706189ae471d91dec1e17ac73e420cc1d0e1ebf81dfbb0`.
- The 131K RULER five-task subset averaged 90.5 for v1.2.0 and 90.1 for the baseline.
- Variable tracking at 131K, 10 samples, averaged 86.0 for v1.2.0 and 84.0 for the baseline.
- Retrieval, frequent-word, and QA task scores were unchanged.

### Prefill

| Test | v1.1.1 equivalent | v1.2.0 |
|---|---:|---:|
| 2,048-token prompt | 2,985 | 3,004 |
| Unique 32K prompt | 3,151 | 3,435 |
| Unique 63K prompt, first after boot | 3,225 | 3,147 |
| Unique 63K prompt, warm | 3,245 | 3,129 |

Medians of 3 runs. The 32K prefill was 9.0 percent faster. The 2K result was flat. At 63K, prefill was 2.4 percent slower on the first request and 3.6 percent slower warm.

## Upgrade

```bash
git pull && docker compose up -d --build --wait
```

The image is `hibana-flashnext-vision:d474b74d-v7`.

## Rollback

Return to the v1.1.1 release:

```bash
git checkout v1.1.1
docker compose up -d --build --wait
```

v1.1.1 still has the old HyperConnection PDL instructions. It can freeze during batch 4 verify capture on some boots. If it does, use the v1.2.0 image with `MTP_QSA_GUIDE=0` and `QSA_PREFILL_BACKEND=original` as the v1.1.1-equivalent fallback.

## Known caveats

- Short context is not faster. The gain starts after 65,536 tokens.
- The first batch 2 long-context request after boot can be slower while the guide warms up.
- Prefill at 63K was 2 to 4 percent slower in this sample, while 32K was 9 percent faster.
- The 4-request sampled cells had lower medians in both modes (209.1 against 231.4 default, 187.9 against 199.3 exact). The run ranges overlap, and a 3-run median cannot separate this from noise. Patch 0005 is not active at these prompt lengths.
- The released v1.1.1 image itself cannot reliably complete batch 4 verify capture. The baseline used for these numbers is v1.1.1 behavior on the v1.2.0 image with the two v1.2.0 features disabled.
