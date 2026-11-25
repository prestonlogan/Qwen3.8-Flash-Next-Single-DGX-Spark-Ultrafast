# v1.2.0

Released 2026-11-25. This release adds target-guided long-context draft attention, automatic QSA prefill, and the HyperConnection startup fix. It is based on v1.1.1, so it includes the host-path acceptance fix.

## What changed

- Patch 0005 guides MTP draft attention after 65,536 tokens. The draft keeps 14,336 recent KV pages plus up to 2,048 distant pages selected by the target model's verify-time sparse attention at layer 43.
- `TUNING=v1.1` and `TUNING=v1.1-exact` enable the guide by default. Image requests and budget speculation are excluded.
- `HIBANA_QSA_PREFILL_BACKEND=auto` is set in the v1.1 serve settings.
- The HyperConnection tensor-core kernel no longer contains programmatic dependent launch instructions that the host never launched correctly. This fixes the intermittent batch 4 verify capture freeze.
- Patch 0004 includes the v1.1.1 `think_bias` fix and the Dockerfile guard against `if batch.eager:`.

## Measured results

All numbers below are from the v1.2.0 validation on one DGX Spark on 2026-11-25. The comparison baseline is the same image with `HIBANA_MTP_QSA_GUIDE=0` and `HIBANA_QSA_PREFILL_BACKEND=original`. The released v1.1.1 image cannot reliably complete batch 4 verify capture because it still has the old PDL instructions.

### Startup, crash, and smoke

- Five consecutive cold boots passed. Each reached warmup, health 200, and repeated batch 4 verify capture.
- The crash regression passed with `HIBANA_DRAFT_VOCAB=98304`: no temperature, then 0.3, then four concurrent requests produced zero NameError or Traceback entries.
- `tools/check.py --needle 70000` passed model listing, alias, thinking off, thinking on, tool call, tool round trip, streaming, Dutch, image input, speed, image speed, and the 70K needle.

### Short context

Decode tok/s, median. Run spread was up to 17 percent on the noisiest cells.

| Cell | v1.1.1 equivalent | v1.2.0 |
|---|---:|---:|
| Default prose T0 | 122.1 | 123.0 |
| Default code T0 | 166.8 | 166.3 |
| Default image prose T0 | 116.2 | 116.3 |
| Default 4 requests T0 | 298.4 | 288.6 |
| Default 4 requests T1.0 | 231.4 | 209.1 |
| Exact prose T0 | 102.1 | 102.7 |
| Exact code T0 | 101.9 | 102.3 |
| Exact image prose T0 | 87.1 | 87.6 |
| Exact 4 requests T0 | 226.5 | 225.8 |
| Exact 4 requests T1.0 | 199.3 | 187.9 |

Short-context results are unchanged within the measured run spread. The 4-request sampled cells were the noisiest.

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
| Unique 63K prompt | 3,225 | 3,147 |

The 32K prefill was 9.0 percent faster. The 2K result was flat. The 63K result was 2.4 percent slower in this sample.

## Upgrade

```bash
git pull && docker compose up -d --build --wait
```

The image is `hibana-flashnext-vision:d474b74d-v6`.

## Rollback

Return to the v1.1.1-equivalent configuration:

```bash
cd /home/plogan/experiments/hibana-flashnext-fast
cp -p vision-enabled.yml.t94-rc-clean-20261123 vision-enabled.yml
rm -f speed-trial.yml
curl -s http://127.0.0.1:30002/unload
```

## Known caveats

- Short context is not faster. The gain starts after 65,536 tokens.
- The first batch 2 long-context request after boot can be slower while the guide warms up.
- Prefill at 63K was slightly slower in this sample, while 32K was faster.
- The released v1.1.1 image itself cannot reliably complete batch 4 verify capture. The baseline used for these numbers is v1.1.1 behavior on the v1.2.0 image with the two v1.2.0 features disabled.
