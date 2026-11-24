# v1.0.0 vs v1.1.0, same Spark, same day (2026-11-24)

Both versions ran back to back on one DGX Spark between 1:56 AM and 3:02 AM ET, each from a fresh boot, with the
same benchmark scripts. v1.0.0 is the published image (`20261120-specvis2`, Hibana `fast`, `accept_soft` 0.5, stock
MTP head). v1.1.0 is the image this branch builds (`d474b74d-v2`; a clean build from a fresh clone has a source tree
identical to the tested image, 238 files) with `TUNING=v1.1`. Both had `VISION=1`.

## Speed: `bench/bench.py`

Decode tok/s, median (3 runs at temperature 0 and for 4 requests, 5 runs for single sampled requests). The spread
between runs is large on sampled prose (77-128 tok/s on both versions), so treat sampled differences under ~10% as noise.

| Cell | v1.0.0 | v1.1.0 default (exact acceptance) | v1.1.0, same relaxed temperature-0 rule as v1.0.0 |
|---|---:|---:|---:|
| Prose, temperature 0 | 103.5 | 107.4 | **121.8** |
| Code, temperature 0 | 124.6 | 92.6 | **144.9** |
| Prose about an image, temperature 0 | 106.1 | 81.6 | **121.5** |
| 4 requests, temperature 0, total | 255.6 | 222.1 | **306.5** |
| Prose, temperature 1.0 | 114.5 | 98.2 | 85.9 |
| Code, temperature 1.0 | 106.1 | 106.6 | 101.7 |
| Prose about an image, temperature 1.0 | 87.6 | 79.2 | 81.8 |
| 4 requests, temperature 1.0, total | 195.8 | 197.1 | 204.4 |

- **Temperature 0.** `bench.py` sends Hibana's relaxed greedy rule (`accept_top_k=3`, `accept_margin=2.0`) with
  every temperature-0 request. That rule keeps a drafted token when it is within the model's top 3 and close in
  score, so output can differ from plain greedy decoding. v1.1.0 accepts only exact matches by default
  (`BENCH_ACCEPT=server` leaves the rule to the server). With the same relaxed rule, v1.1.0 is 15-20% faster than
  v1.0.0 on single requests and 20% faster on 4 requests. With its exact default it is slower on code and images.
- **Temperature 1.0.** v1.0.0 uses relaxed sampled acceptance (`accept_soft` 0.5), which shifts the output
  distribution. v1.1.0 samples exactly from the model's distribution (`accept_soft` 0.0) at about the same speed,
  within the run-to-run spread. The third column sends the relaxed rule only on temperature-0 requests, so its
  sampled rows are a second run of the v1.1.0 default.

## Time to first token: 17,906-token prompt, nothing cached

One request per row, from `diag_cold_ttft_exact.py`.

| | v1.0.0 | v1.1.0 |
|---|---:|---:|
| First request after boot | 6,395 ms | 7,922 ms |
| Second request, new prompt | 8,944 ms | 11,985 ms |
| With a short title request alongside | 5,615 ms | 6,144 ms |
| Prompt fully in the prefix cache | 174 ms | 177 ms |

tool-eval-bench's prefill column agrees: 2,907 vs 3,786 tok/s at 2,048 tokens with an empty context. **v1.1.0
prefills more slowly**, about 10-35% more time to first token on long uncached prompts.

## Quality

| | v1.0.0 | v1.1.0 |
|---|---:|---:|
| tool-eval-bench 3.1.1 (seed 42, hard mode on), score / 100 | 89 | **93** |
| Hard mode | 62/70 | **65/70** |
| Deployability / responsiveness | 85 / 76 | 86 / 71 |
| Needle in a haystack, ~1K to ~254K tokens | 20/20 | 20/20 |
| GSM8K (20, temperature 0) | 18 | 18 |
| MBPP (20) | 20 | 19 |
| Tool calls (20) | 19 | 20 |
| AIME (20) | 20 | 20 |

From the development runs on 2026-11-23 (same Spark, frozen harness; not rerun today):

| | v1.0.0 | v1.1.0 |
|---|---:|---:|
| 30-run agent-session replay at temperature 1.0: runs that fell into a repetition loop | 2/30 | **0/30** |
| Forward KL to an exact BF16-trunk reference, 200 prompts at temperature 1.0 (lower is closer) | 0.908 | **0.728** (T92, an earlier build of the same stack) |
| One long reasoning prompt (UT-01): thinking tokens before the answer | 26,112 | **7,626** |

The v1.0.0 tool-eval-bench run is from 1:30 AM the same night, before the A/B, on the same image and settings.

## Files

`bench_v1.0.json`, `bench_v1.1.json`, `bench_v1.1_relaxed-greedy.json`: `bench.py` output. `ttft_*.json`: time to
first token. `suites_*.json`: GSM8K/MBPP (`mbpp.math`, `mbpp.code`), tool calls, AIME. `tool-eval-*.md`,
`needle-*.md`: tool-eval-bench reports.
