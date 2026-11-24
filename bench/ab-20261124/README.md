# v1.0.0 vs v1.1.0, same Spark, same day (2026-11-24)

All builds ran on one DGX Spark, each from a fresh boot, with the same benchmark scripts. v1.0.0 and v1.1.0 exact ran
back to back between 1:56 AM and 3:02 AM ET; the v1.1.0 default ran later that morning, finishing at 11:00 AM ET.

- **v1.0.0** is the published image (`20261120-specvis2`, Hibana `fast`, `accept_soft` 0.5, stock MTP head).
- **v1.1.0** is the image this branch builds (`d474b74d-v2`; a clean build from a fresh clone has a source tree
  identical to the tested image, 238 files). It ran in both modes:
  - **default** (`TUNING=v1.1`): top-3 acceptance at temperature 0 (`accept_top_k=3`, `accept_margin=2.0`) and
    `accept_soft` 0.35 for sampled requests.
  - **exact** (`TUNING=v1.1-exact`): only exact matches are accepted (`accept_soft` 0.0).

All runs had `VISION=1`.

## Speed: `bench/bench.py`

Decode tok/s, median (3 runs at temperature 0 and for 4 requests, 5 runs for single sampled requests). The spread
between runs is large on sampled prose (77-130 tok/s across builds), so treat sampled differences under ~10% as noise.

| Cell | v1.0.0 | v1.1.0 default | v1.1.0 exact |
|---|---:|---:|---:|
| Prose, temperature 0 | 103.5 | **132.4** | 107.4 |
| Code, temperature 0 | 124.6 | **153.6** | 92.6 |
| Prose about an image, temperature 0 | 106.1 | **114.0** | 81.6 |
| 4 requests, temperature 0, total | 255.6 | **296.3** | 222.1 |
| Prose, temperature 1.0 | **114.5** | 110.7 | 98.2 |
| Code, temperature 1.0 | 106.1 | **122.7** | 106.6 |
| Prose about an image, temperature 1.0 | 87.6 | **90.1** | 79.2 |
| 4 requests, temperature 1.0, total | 195.8 | **205.0** | 197.1 |

- **Temperature 0.** `bench.py` sends the top-3 rule with every temperature-0 request unless `BENCH_ACCEPT=server`.
  The exact column used `BENCH_ACCEPT=server`, so the server's exact rule applied. v1.0.0 and the v1.1.0 default use
  the same top-3 rule, so their temperature-0 rows compare the engines directly. With that rule the v1.1.0 engine is
  7-28% faster on single requests and 16% faster on 4 requests. A second exact-mode run, with the client sending the
  top-3 rule (`bench_v1.1-exact_relaxed-greedy.json`), gave 121.8 / 144.9 / 121.5 / 306.5.
- **Temperature 1.0.** v1.0.0 accepts near-misses with `accept_soft` 0.5, the v1.1.0 default with 0.35, and exact
  with 0.0 (samples exactly from the served model's distribution).

## 30-run agent-session replay, temperature 1.0

A frozen DeepSeek Harness session replayed 30 times (`run_dsh_sampled_gate_30.py`), counting runs that fell into a
repetition loop.

| | v1.0.0 | v1.1.0 default | v1.1.0 exact |
|---|---:|---:|---:|
| Mean decode tok/s | 97.2 | **109.2** (median 115.3) | 99.8 |
| Runs that looped | 2/30 | **0/30** | **0/30** |
| Repetition-guard stops | none (no guard) | 2, in one run | 0 |

In the default's one guarded run (req56), the guard stopped repeated thinking at 5,459 tokens and then repeated
visible text at 7,505 tokens. The run ended early instead of looping to `max_tokens`. The harness counts any guard stop
as a failure, so this run fails its strict gate; the exact mode passes it. v1.0.0 and exact are from the development
runs on 2026-11-23 (same Spark, same frozen harness); the default ran on 2026-11-24
(`gate30_v1.1-default.log`).

## Time to first token: 17,906-token prompt, nothing cached

One request per row, from `diag_cold_ttft_exact.py` (v1.0.0 and v1.1.0 exact; acceptance does not affect prefill).

| | v1.0.0 | v1.1.0 |
|---|---:|---:|
| First request after boot | 6,395 ms | 7,922 ms |
| Second request, new prompt | 8,944 ms | 11,985 ms |
| With a short title request alongside | 5,615 ms | 6,144 ms |
| Prompt fully in the prefix cache | 174 ms | 177 ms |

tool-eval-bench's prefill column agrees: 2,048 tokens with an empty context prefilled at 3,786 tok/s on v1.0.0, 3,434
on the v1.1.0 default and 2,907 on v1.1.0 exact. **v1.1.0 prefills more slowly**, about 10-35% more time to first
token on long uncached prompts.

## Quality

| | v1.0.0 | v1.1.0 default | v1.1.0 exact |
|---|---:|---:|---:|
| tool-eval-bench 3.1.1 (seed 42, hard mode on), score / 100 | 89 | 89 | **93** |
| Hard mode | 62/70 | 59/70 | **65/70** |
| Deployability / responsiveness | 85 / 76 | 85 / 77 | 86 / 71 |
| Safety warnings | TC-51, TC-85 | TC-51, TC-74, TC-98 | TC-51 |
| Needle in a haystack, ~1K to ~254K tokens | 20/20 | | 20/20 |
| GSM8K (20, temperature 0) | 18 | 19 | 18 |
| MBPP (20) | 20 | 19 | 19 |
| Tool calls (20) | 19 | 20 | 20 |
| AIME (20) | 20 | 20 | 20 |
| AIME mean tokens per answer | 1,441 | 1,525 | 1,874 |

tool-eval-bench runs at temperature 0, so the default's lower hard-mode score comes from the top-3 rule, not from
`accept_soft`. TC-98 is the default disclosing a recovery token under a multi-hop prompt injection.

From the development runs on 2026-11-23 (same Spark, frozen harness; exact mode, not rerun today):

| | v1.0.0 | v1.1.0 exact |
|---|---:|---:|
| Forward KL to an exact BF16-trunk reference, 200 prompts at temperature 1.0 (lower is closer) | 0.908 | **0.728** (T92, an earlier build of the same stack) |
| One long reasoning prompt (UT-01): thinking tokens before the answer | 26,112 | **7,626** |

The v1.0.0 tool-eval-bench run is from 1:30 AM the same night, before the A/B, on the same image and settings.

## Files

`bench_v1.0.json`, `bench_v1.1-default.json`, `bench_v1.1-exact.json`, `bench_v1.1-exact_relaxed-greedy.json`:
`bench.py` output. `ttft_*.json`: time to first token. `suites_*.json`: GSM8K/MBPP (`mbpp.math`, `mbpp.code`), tool
calls, AIME. `tool-eval-*.md`, `needle-*.md`: tool-eval-bench reports. `spec-bench-v1.1-default.md`: tool-eval-bench's
speed and prefill table for the default. `gate30_v1.1-default.log`: the default's 30-run replay.
