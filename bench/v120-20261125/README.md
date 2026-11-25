# v1.2.0 release validation (2026-11-25)

All runs were on one DGX Spark on 2026-11-25 with image `hibana-flashnext-vision:d474b74d-v6`, the image this
branch builds.

- **candidate** is v1.2.0 as shipped: `TUNING=v1.1` (default) or `TUNING=v1.1-exact` (exact), with patch 0005's guide
  on and `QSA_PREFILL_BACKEND=auto`.
- **baseline** is the same image with `MTP_QSA_GUIDE=0` and `QSA_PREFILL_BACKEND=original`, which is v1.1.1 behavior
  plus the HyperConnection startup fix. The released v1.1.1 image was not used as the baseline because it can freeze
  during batch 4 verify capture.

`summary.json` holds every median and individual run quoted in [RELEASE-NOTES-v1.2.0.md](../../RELEASE-NOTES-v1.2.0.md).

## Files

| Path | What it is |
|---|---|
| `{baseline,candidate}/{default,exact}/bench.json` | `bench/bench.py` short-context decode: 3 runs at temperature 0 and for 4 requests, 5 runs for single sampled requests |
| `{baseline,candidate}/default/depth*/` | tool-eval-bench throughput at 100K (four runs) and 250K (two runs) |
| `{baseline,candidate}/exact/fixed100k*.json` | Fixed exact 100K copy prompt, batch 1 and batch 2 (`scripts/v120_fixed.py`) |
| `{baseline,candidate}/exact/bytecheck.json` | Exact-mode output hashes for the short code prompt and the 133K archive prompt (`scripts/v120_bytecheck.py`) |
| `{baseline,candidate}/default/ruler/results.jsonl` | RULER subset at 131K: four tasks with 3 samples, variable tracking with 10 |
| `{baseline,candidate}/default/prefill*.json` | Prefill at 2K, 32K and 63K (`scripts/v120_prefill.py`) |
| `candidate/default-crash/` | v1.1.1 crash regression with `HIBANA_DRAFT_VOCAB=98304` (`scripts/v120_crash.py`) and `tools/check.py --needle 70000` |
| `coldboots/boot{1..5}.log` | Five consecutive cold boots of the candidate, each through warmup and batch 4 verify capture |

The scripts use paths and a local gateway port from the test Spark. Change those before running them elsewhere.
