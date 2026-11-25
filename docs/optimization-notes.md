# Optimization notes: what we tried, what worked, what didn't

These notes cover five days of work (2026-11-16 to 2026-11-20) on one DGX Spark, running Qwen3.8-Flash-Next on
[Hibana](https://github.com/sharar-project/hibana) `d474b74` (v0.1.0) from
[dedene's recipe](https://github.com/dedene/Hibana-Qwen3.8-Flash-Next-DGX-Spark). They record every change we measured,
including the ones we threw away, so you don't have to repeat them.

> **v1.1.0 (2026-11-24).** These notes describe v1.0.0. v1.1.0 adds a distilled draft head, a repetition guard and
> GB10 kernels (patch 0004). With that stack, the top-3 greedy rule from section 5 is now the default at temperature
> 0, and sampled acceptance returns at `accept_soft` 0.35, below the 0.5 that section 6 reverted. The guard stops the
> loops section 6 describes: the default had 0 looping runs of 30 in the agent replay. `TUNING=v1.1-exact` keeps
> exact acceptance. Results: [bench/ab-20261124](../bench/ab-20261124/README.md).


> **v1.2.0 (2026-11-25).** Patch 0005 guides long-context MTP draft attention with the target
> model's verify-time sparse attention page selection. It keeps 14,336 recent pages plus 2,048 selected distant
> pages after 65,536 tokens. Same-day controlled results: fixed exact 100K copy effective throughput 179.3 versus
> 149.0 tok/s, realistic 100K decode 101.0 versus 89.9, and 250K decode 100.4 versus 74.4. Exact fixed prompts stayed
> byte-identical. The 131K RULER five-task subset averaged 90.5 versus 90.1, and variable tracking over 10 samples
> averaged 86.0 versus 84.0. A simpler fixed 16K draft window was rejected because lower draft time did not make up
> for lower acceptance.

Back to the [README](../README.md).

## Contents

1. [Summary](#1-summary)
2. [Where decode time goes](#2-where-decode-time-goes)
3. [How we measured](#3-how-we-measured)
4. [What we shipped](#4-what-we-shipped)
5. [Worked, but not the default: looser greedy acceptance](#5-worked-but-not-the-default-looser-greedy-acceptance)
6. [Shipped, then reverted: looser sampled acceptance](#6-shipped-then-reverted-looser-sampled-acceptance)
7. [Measured and rejected](#7-measured-and-rejected)
8. [The 8-hour speed run, start to end](#8-the-8-hour-speed-run-start-to-end)
9. [Quality checks](#9-quality-checks)
10. [Not tested, and ideas not started](#10-not-tested-and-ideas-not-started)
11. [Method lessons](#11-method-lessons)
12. [Sources](#12-sources)

---

## 1. Summary

- **Most of the text speed is Hibana's `fast` profile, not this repo.** dedene measured `exact` at 45.2 tok/s and `fast`
  at 102.0 on English prose. This repo makes `fast` the default.
- **Image requests went from ~36 to ~101 tok/s in three steps:** load the vision tower (patch 0002, ~36 tok/s), let
  image requests use speculative decoding (~71), then let them use CUDA graphs (~91, then ~101 with later changes).
  Patch 0003 holds the last two steps.
- **The draft-vocabulary shortlist (`DRAFT_VOCAB=131072`) gave +3% to +10%** on our bench, and about +8% on code in the
  README bench. It doesn't help non-English text.
- **Acceptance looseness is the biggest speed lever.** It decides how many drafted tokens the model keeps per round. It
  is also where quality breaks:
  - Looser **greedy** acceptance (`5:4.0`) gave +15% and passed our short quality screen. It is not the default. See
    [section 5](#5-worked-but-not-the-default-looser-greedy-acceptance).
  - Looser **sampled** acceptance (`accept_soft` 3.0) gave +30% to +55% and passed the same screen. In real use, long
    thinking runs looped and ended with no answer. We reverted to 0.5. See
    [section 6](#6-shipped-then-reverted-looser-sampled-acceptance).
- **Restricting how many experts each round may read (an expert budget) was the biggest raw speed gain we found, up to
  +31%.** It failed the code quality screen at every setting we tried.
- **16 other settings changed nothing, cost speed, or cost quality.** They are listed in
  [section 7](#7-measured-and-rejected).
- **Config tuning is used up.** What's left needs changes to Hibana's kernels. See
  [section 10](#10-not-tested-and-ideas-not-started).

---

## 2. Where decode time goes

### The Spark is memory-bound at batch 1

The GB10 has 273 GB/s of LPDDR5X bandwidth, about 250 GB/s usable. One request at a time, decode speed is set by how
many bytes of weights each generated token needs, not by compute. Every lever below either reads fewer bytes per round
or keeps more tokens per round.

### Bytes per round (reconstructed from Hibana's source and the checkpoint manifest)

| Component | GB |
|---|---:|
| Trunk, shared experts and per-layer embeddings, in 3-bit (W3) form | ~2.295 |
| One ordinary pass with 10 routed experts per layer (no speculation) | **~3.26** |
| Verify pass, routed-expert union of 16 per layer | ~3.84 |
| Verify pass, routed-expert union of 27 per layer | ~4.90 |
| One MTP draft step (FP8 body, 10 experts, 2-bit shortlist head, FP8 rescore) | ~0.323 |
| Full cycle: 8 drafts + 1 verify | **6.42–7.48** |

How we got these:

- Each routed expert is three 2560 × 640 matrices: 2,012,160 bytes in W3 form with scales. Across 48 layers, 10
  experts per layer cost 0.97 GB, 16 cost 1.55 GB and 27 cost 2.61 GB.
- Hibana's verify pass doesn't read every expert that any row picks. It caps the union at about 16 per layer, but it
  always keeps 3 guaranteed experts per row. With 9 rows (8 drafts + 1), the union can reach 27. A free union would be
  about 83.
- **Context adds almost no bytes.** NVFP4 KV and BF16 index keys cost about 0.8 KB per token over the 12 attention
  layers: about 21 MB at 25K tokens. The sparse indexer caps attended positions near 2K, and the 36 Gated DeltaNet
  layers have fixed-size state. When long-context decode is slower, the cause is acceptance or per-round overhead, not
  bytes.

**Hibana's startup log overstates bytes per token.** It prints `fp8 trunk, 5.38 GB per decode token`. In
`model/flashnext/model.py`, `self.stream_bytes` is computed before `attach_calibrated` swaps in the smaller 3-bit
matrices, so it counts the FP8 trunk. The 231 trunk and head matrices save 2.12 GB in W3 form, which brings an ordinary
pass to about 3.26 GB.

| Trunk matrices | FP8 bytes | W3 bytes |
|---|---:|---:|
| Attention and GDN projections | 2,673,868,800 | 1,089,748,992 |
| Vocabulary head | 635,699,200 | 259,246,080 |
| Shared experts | 235,929,600 | 96,583,680 |
| Per-layer embedding projections | 32,768,000 | 13,363,200 |

These are counts of selected weights. Physical DRAM traffic was not measured with counters.

### Speed ceilings that follow

At 250 GB/s, with emitted tokens = accepted drafts + 1 per round:

| Scenario | GB per round | Tokens per round | Ceiling, tok/s |
|---|---:|---:|---:|
| No speculation, 10 experts per layer | ~3.26 | 1 | ~77 |
| 8 drafts, 2 accepted | ~6.95 | 3 | ~108 |
| 8 drafts, 3 accepted | ~6.95 | 4 | ~144 |
| 8 drafts, 4 accepted | ~6.95 | 5 | ~180 |
| Adaptive ~3.6 drafts, union ~15, 2 accepted | ~4.9 | 3 | ~152 |

At the start, short prose ran at 91–97 tok/s with about 3 tokens per round. That's 165–220 GB/s effective, 66–88% of
usable bandwidth. Removing overhead alone could not reach much more. Only three things move the ceiling:

1. **Keep more drafted tokens per round** (acceptance).
2. **Read fewer bytes per round** (smaller expert union, cheaper drafts).
3. **Waste less time per round** (CUDA graphs instead of eager launches).

### What a round looks like (profiled)

| Phase | Time per round |
|---|---:|
| Draft (MTP head) | ~9–10 ms |
| Verify (full model over all drafted rows) | ~26–30 ms |
| Accept or reject | ~1.6 ms |

Verify dominates, and it is limited by reading the selected experts. The timer build adds about 15% sync overhead, so
treat the milliseconds as relative.

Acceptance by draft position at the start, stock settings:

| Draft position | 1 | 2 | 3 | 4 | 5 | 6 |
|---|---:|---:|---:|---:|---:|---:|
| Accepted | 80% | 57% | 39% | 28% | 26% | 24% |

Hibana's adaptive policy mostly proposes 3–4 drafts, rarely 8. Drafting deeper wouldn't pay. Keeping more of drafts 2–4
would.

---

## 3. How we measured

Three benchmarks appear in these notes. **Numbers from different benchmarks are not comparable.** Each table says which
one it uses.

### README bench (`bench/bench.py`)

The README numbers. Thinking on (the server default). Greedy cells send Hibana's stock acceptance rule explicitly
(`accept_top_k` 3, `accept_margin` 2.0) at temperature 0 with 512 output tokens, median of 3. Sampled cells send no
temperature (1.0 from the generation config) with 1,024 output tokens, median of 5. Decode tok/s =
`(completion_tokens − 1) / (last chunk − first chunk)`. Results are in `bench/results.json`.

### Speed-run bench (frozen for the 8-hour run, sha256 `3789be32…`)

- **Quick:** a 512-token story, temperature 0, thinking **off**, n=6.
- **Realistic:** thinking on, temperature 1.0 / top-p 0.95 / top-k 20, at least 1,200 output tokens:
  - `prose25` and `reason25`: a long document plus a question. Labelled "25K", but the filler measured 15,944 prompt
    tokens. We froze it as-is and report the real size.
  - `prose2` and `code2`: ~1.1K-token prompts.
- **Image:** `imgprose` (512 × 512 red square + story prompt, temperature 0, 512 tokens) and `imgreal` (thinking on,
  temperature 1.0, 700 tokens).

Speculation counters came from the server's `/describe` endpoint, diffed per run.

### Image speculation bench (2026-11-16)

A 512 × 512 red square plus "Write a 400-word story inspired by this image", 512 tokens, temperature 0, thinking off,
n=3, sent directly to the server port.

### Quality gates

| Gate | What it is | Pass rule |
|---|---|---|
| Greedy screen | 20 GSM8K + 20 MBPP questions, fixed seed (`Random(20261116)`), temperature 0, thinking off, 1,024-token cap. MBPP code runs in a network-off container against all 3 tests | No more than 1 point below baseline (18/20 GSM8K, 19/20 MBPP) on either |
| Sampled screen | The same questions at temperature 0.7, 3 passes | Within noise of the 0.5 control (which itself swings 18–20/20 between passes) |
| Image suite | 22 expected-answer checks (OCR, shapes, two images, follow-ups, cache isolation, 6,746-token context) + 7 extra checks (a 10,376-token prompt with the image after a prefill chunk boundary) | All pass |
| Tool smoke | Tool call with arguments, streaming, thinking on | Pass |
| Long-thinking replay | Added after the failure in [section 6](#6-shipped-then-reverted-looser-sampled-acceptance): one real agent request replayed with up to 32,768 output tokens | No run ends without an answer or tool call |

Rules for the speed run:

- A change had to gain **more than 3%** on the deciding cells to be kept.
- Kept changes were re-measured after a cold restart.

---

## 4. What we shipped

### 4.1 `fast` profile as the default

Hibana's `fast` profile combines several techniques. The Hibana authors' single-request ablation on Flash-Next (their
paper, their test, cumulative in this order):

| Added | Tok/s gain |
|---|---:|
| No speculation (baseline: 27.9 tok/s) | — |
| MTP speculative decoding | +97% |
| 3-bit calibrated weights (about 3.25 bits per weight with scales, vs 4.5 for NVFP4) | +43% |
| Expert sharing (drafts reuse one expert set during verify) | +32% |
| Adaptive draft length | +5% |
| 2-bit draft head shortlist, rescored at higher precision | +3% |
| Relaxed verification | +1% |
| Final cache optimization | +5% |
| **Total: 27.9 → 119.6 tok/s** | |

These gains depend on the order and on their test. dedene's numbers on the Spark (thinking on, 512 tokens): `exact`
45.2 tok/s, `fast` 102.0 on English prose.

`fast` is lossy. The README's [Quality and limits](../README.md#quality-and-limits) section has the GPQA-Diamond and
agent benchmark numbers. `PROFILE=exact` turns it off.

### 4.2 Image input (patch 0002)

Upstream Hibana doesn't load Flash-Next's vision tower, although the checkpoint ships one. Patch 0002 adds:

- **The Qwen vision tower and projector**: 333 weight names, all matched to the checkpoint. BF16, 897,862,112 bytes
  (0.84 GiB), plus 1 GiB of encode workspace.
- **Image placeholder expansion** in the chat template.
- **Multimodal rotary positions (M-RoPE)** in eager attention and in the sparse indexer (QSA). Qwen's merged spatial
  positions are kept separate from the physical KV page index.
- **Cache safety:** each image placeholder's identity includes a digest of the image and its preprocessing, so cached
  prefixes never cross images.
- **Image-safe per-layer embedding history.**

A bug worth knowing about: the first build removed Qwen's visual added tokens from a reconstructed tokenizer. That
shifted the thinking token IDs, and every response came back empty. A regression test now checks that the text-only
special-token IDs stay unchanged.

Checks:

- The tower forward matched an independent Qwen4-style reference exactly on one fixture.
- 100 randomized single- and multi-image position layouts matched Transformers.
- The existing image, indexer, QSA and per-layer-embedding unit suites passed (101 tests).
- Gateway tests: colors, shapes, two images, follow-ups, OCR, 1,024 × 1,024 input, a 8,382-token prompt with the image
  near the end, and concurrent image and text requests.

Text speed did not change (thinking off, greedy, 3 runs each, medians):

| Prompt | Before | With vision | After removing it again |
|---|---:|---:|---:|
| Story | 88.83 | 86.94 | 88.56 |
| Explanation | 113.74 | 113.21 | 113.14 |
| Code | 144.59 | 143.41 | 143.31 |

**But image requests decoded at only ~36 tok/s.** Hibana's speculative path and CUDA graphs assumed text positions, so
any request with an image fell back to one eager pass per token.

### 4.3 Speculation for image requests (first half of patch 0003)

This let image requests use MTP drafting and verification. It changed 5 files: `attention.py`, `engine/spec.py`,
`proposers/mtp.py`, `engine/executor.py`, `engine/config.py`. Image prose bench, n=3:

| Build | Decode tok/s, mean (range) | End-to-end |
|---|---:|---:|
| Eager image decode | 36.2 (35.5–37.5) | 14.48 s |
| **Image speculation on** | **71.2 (65.3–75.7)** | **7.44 s** |
| Image speculation built in, switched off | 36.4 (35.5–38.0) | 14.22 s |

Image acceptance was 54.6%, 3.03 tokens per round, in line with text. Text output stayed identical, and the unit suite
was unchanged (1,198 passed).

For text that follows the image, M-RoPE positions equal `p + delta` on all axes, so drafter positions are exact. Inside
the image span they are approximate. That only affects acceptance, not output.

### 4.4 CUDA graphs for image requests (second half of patch 0003)

The remaining gap had a clear cause. Image rounds took about 46 ms against 37–41 ms for text, with the same acceptance
(0.548 vs 0.528). The gap was per-round launch overhead from eager execution, not acceptance. The fix gives image rows
their own rotary and compress position buffers, so image batches can replay the captured graphs. That took 11 files
and 646 lines.

**We first rejected it, then kept it.** At n=3 graphs-on measured 77.7 tok/s against 73.0 graphs-off, with overlapping
ranges, and its image output differed from graphs-off at characters 44–50. Three runs with overlapping ranges don't
show a win, and they don't show a loss either. We retested at n=6 during the speed run:

| Cell (speed-run bench) | Before | With graphs | Change |
|---|---:|---:|---:|
| `imgprose` | 71.9 | 90.7 | **+26%** |
| `imgreal` | 71.8 | 80.6 | +12% |

It passed all 22 + 7 image checks, text was unchanged, and the gain reproduced after a cold restart. With the other
kept changes, image prose ended at 95% of text speed on the speed-run bench. On the README bench, image prose (101.8)
matches text prose (101.3).

### 4.5 Draft-vocabulary shortlist (`DRAFT_VOCAB=131072`)

The MTP drafter's vocabulary head normally scores all ~250K tokens. With this setting it reads only the 131,072 most
common rows, which is cheaper per draft. Verification still uses the full vocabulary, so the model can still emit any
token. A rare token is just never proposed as a draft.

Speed-run bench, n=12, every cell:

| Shortlist size | Quick | `prose25` | `reason25` | `prose2` | `code2` | Verdict |
|---|---:|---:|---:|---:|---:|---|
| Off (full vocabulary) | baseline | | | | | |
| **131,072** | +4.5% | +9.9% | +3.7% | +4.5% | +3.2% | **kept** |
| 65,536 | +12.9% vs 131K | −3% vs 131K | +6% | −2% vs 131K | +5% | rejected: prose is the main target, and rare story words fall outside 65K |
| 196,608 | −4% vs 131K | ~same | −14% vs 131K | ~same | ~same | rejected (n=1–4): more rows cost draft time without raising acceptance |

The 131,072 gains are relative to the configuration live at the time, with the looser acceptance settings of sections 5
and 6. The greedy screen held at 18/20 and 18/20, and the sampled screen at 17/18 (noise).

On the README bench, with stock acceptance: code 133.3 tok/s against dedene's 123.2 for `fast` without the shortlist
(+8%), and prose 101.3 against 102.0 (no change). **It helps code more than prose under stock acceptance.**

It lowers acceptance on scripts outside the common tokens. Set `DRAFT_VOCAB=0` if most of your traffic is not English
or code. Hibana leaves it off for that reason, and it isn't supported across two Sparks.

---

## 5. Worked, but not the default: looser greedy acceptance

At temperature 0, Hibana accepts a drafted token when it's within the model's top `accept_top_k` choices and within
`accept_margin` of the top logit. The stock rule is `3:2.0`.

Per-request probe ladder with MTP:

| Rule | 3:2.0 (stock) | 4:3.0 | 6:6.0 | 8:10.0 |
|---|---:|---:|---:|---:|
| Quick, tok/s | ~88 | 102 | 117 | 127 |

Each rung through the greedy screen:

| Rule | GSM8K | MBPP | Result |
|---|---:|---:|---|
| Baseline | 18/20 | 19/20 | |
| 4:3.0 | 18 | 18 | pass |
| **5:4.0** | **18** | **18** | **pass (loosest)** |
| 5:5.0 | 18 | 17 | fail |
| 6:4.0 | — | 16 | fail |
| 6:6.0 | 15 | 16 | fail |

`5:4.0` gave **+14.7%** on the quick cell (87.7 → 100.6 tok/s), and image prose rose too. It ran on our own server for
the rest of the week.

**Why it isn't this repo's default:** the only evidence for it is the short-answer screen. That is the same kind of
screen that passed `accept_soft` 3.0 before 3.0 broke long thinking ([section 6](#6-shipped-then-reverted-looser-sampled-acceptance)).
`5:4.0` hasn't had a long-thinking replay. To try it, send it per request:

```json
{"temperature": 0, "accept_top_k": 5, "accept_margin": 4.0}
```

---

## 6. Shipped, then reverted: looser sampled acceptance

**This is the most useful result in these notes.** Anyone tuning Hibana for speed will find this setting, and it looks
free.

### How it works

MTP drafts are point guesses. At temperature > 0, Hibana accepts a drafted token `y` when `u < e^s · p(y)`, where `u`
is uniform on [0, 1) and `p(y)` is the model's probability for that token. `s` is `accept_soft`:

| `accept_soft` | Boost (e^s) | Always accepted when the model gives the draft at least |
|---|---:|---:|
| 0 (exact sampling) | 1× | 100% (otherwise accepted with probability p) |
| **0.5 (Hibana default)** | **1.65×** | **61%** |
| 1.0 | 2.7× | 37% |
| 2.0 | 7.4× | 14% |
| 3.0 | 20× | 5% |

### It looked like a clean win

Probe ladder at temperature 0.7:

| `accept_soft` | 1 | 2 | 3 | 5 | 8 | 20 |
|---|---:|---:|---:|---:|---:|---:|
| tok/s | 78 | 87 | **95** | 95 | 90 | 89 |

At 3.0, tokens per round rose from about 3.0 to 5.2–6.3. Every realistic cell gained 30–55% (speed-run bench, n=6):

| Cell | 0.5 | 3.0 |
|---|---:|---:|
| `prose25` | ~84 | 129.2 |
| `reason25` | ~96 | 131.3 |
| `prose2` | ~87 | 135.3 |
| `code2` | ~105 | 147.7 |

It passed every gate we had:

- Sampled screen: math 54/60 and code 55/60, against 56/60 and 57/60 for 0.5. That's within the control's own swing.
- No loops in 48 benchmark rows.
- Tool smoke passed.

We shipped it on our server.

### It broke in real use

Hours later, a long agentic coding session thought for 25,573 tokens at about 169 tok/s, then
ended with **no answer and no tool call**. From about 20% of the way in, it repeated one sentence with small changes
more than 150 times.

The likely cause: the drafter often proposes "repeat recent text". The 20× boost lets those tokens through, and each
repeat makes the next one more likely.

### Replay study

We replayed that exact request: same system prompt, 5 user messages, 44 tools, `reasoning_effort: xhigh`, 32,768-token
cap, the model's default sampling. We set `accept_soft` per request so the server didn't need to restart. A run
**failed** when it ended with no answer and no tool call.

| `accept_soft` | Runs | Failed | How they failed | Decode tok/s |
|---|---:|---:|---|---:|
| 0 (exact) | 5 | 1 | coherent over-planning until the token limit (no repetition) | 65–77 |
| **0.5** | **5** | **0** | — | **90–102** |
| 1.0 | 10 | 2 | paraphrased dithering ("Let me do it" / "Let's do it"); over-planning to the limit | 109–131 |
| 2.0 | 2 | 1 | dithering loop (the set was stopped by the kill rule) | 97–157 |
| 3.0 | 6 | 2 | literal loops, including "OK, let's do it." 1,582 times | 128–167 |

Failure modes seen above 0.5:

1. **Literal loops:** the same line, over and over.
2. **Paraphrased dithering:** "Let me stop and do it." / "I need to stop." in rotating forms.
3. **Degenerate text:** "The plan is to implement the plan", runs of zeros.
4. **Over-planning:** the model writes the whole program inside its thinking and runs out of tokens. This also happened
   once at exact, so not every failure is caused by acceptance.

### A repetition guard didn't fix it

We built a host-side guard, `HIBANA_REPEAT_GUARD="n:k:cool[:soft]"`. It counts repeated n-token spans in each sampled
request's output. On the k-th repeat, it drops that request to stricter acceptance, either for a cooldown or for the rest
of the request. It hooks the accept paths in `engine/accept_graphs.py` and `engine/spec.py`.

| Setting | Runs | Failed | How |
|---|---:|---:|---|
| 3.0 + guard, 256-token cooldown to exact | 7 | 2 | degenerate ending; paraphrased loop |
| 3.0 + guard, latched to 0.5 for the rest of the request | 5 | 2 | degenerate text, no tool call |

Why it can't work:

- Exact n-gram matching only catches literal loops. It misses paraphrased dithering and degenerate text.
- Dropping to strict acceptance after the guard fires is too late. The run has already drifted, and strict sampling
  doesn't steer it back to a tool call.

### What Hibana documents

Hibana's `docs/operations.md` reports only exact and 0.5 for sampled requests:

- 216 tok/s at 0.5 vs 183 exact (sampled, thinking on, 4 requests).
- GPQA-Diamond at 0.5 scored 81.8% vs 84.8% exact, with answers 18% longer.

Their conclusion: "on long reasoning the faster decode buys little." Nothing between 0.5 and 1.0 is documented. In our
replay, mean output at 0.5 was about 17K tokens against about 15K at exact, so part of 0.5's speed goes into longer
thinking.

### Outcome

- `accept_soft` stays at **0.5**. The README tells users not to raise it.
- Values between 0.5 and 1.0, such as 0.75, aren't worth testing. They would buy about +10%. Telling a 1-in-10 failure
  rate apart from 0.5 would need 20+ long replays per value.

---

## 7. Measured and rejected

Speed-run bench unless noted. Trials after 2:45 AM ran with `accept_soft` 3.0 and `5:4.0` live, so their realistic
numbers are higher than this repo's defaults. The comparisons within each trial still hold.

| Change | Result | Why rejected |
|---|---|---|
| **Expert budget: keep 1 guaranteed, budget 12** (`HIBANA_MOE_KEEP=1`, `MOE_BUDGET=12`) | Quick 137.8 (**+31%**), realistic ~155–168 | Greedy screen failed twice: GSM8K 15/20 and 15/20, MBPP 18 and 16 (baseline 18/19) |
| Expert budget: keep 1, budget 12 per request capped at 64 (`12:64`) | Quick 125.8 (+20%), 4.09 tokens per round | Greedy screen failed twice: MBPP 16/20 both times (−3) |
| Expert budget: keep 2, budget `8:48` | Quick +0.5%, every cell within noise | No gain. At stock acceptance, expert bytes weren't the live bottleneck |
| DFlash2 drafter (`PROPOSER=dflash2`, 9 drafts, its default accept rule `2:1.0`) | Quick 76.2 (**−13%**), acceptance fell to 16% | Probes showed MTP and DFlash2 are equal at matched acceptance settings. The gain lives in the acceptance rule, not the drafter |
| DFlash2 at depth 15 | Not run | At 57–67% acceptance, 7 more verify rows (~30 ms) return about 0.4 tokens per round. Depth only pays above ~95% acceptance |
| `HIBANA_SPEC=10` | Crashed | MTP depth is capped at 8 |
| `HIBANA_SPEC_STEP_COST=0.14` (adaptive depth) | Mixed ±6% | Noise. Under looser acceptance the policy stays near 8 drafts anyway |
| `HIBANA_MTP_SAMPLE=1` (draft from the MTP distribution, not argmax) | −1% to +2% | No gain in tokens per round |
| `HIBANA_DRAFT_HEAD_RESCORE` 16 → 32 | ±3% | Noise. More rescored candidates didn't raise acceptance |
| `HIBANA_VERIFY_STATE=snapshots` | −6% to −16% everywhere | Restoring snapshots is slower than rebuilding state |
| `HIBANA_SSM_STATE=int8` (DeltaNet recurrent state, 4× smaller than FP32) | Quick +4.7%, realistic +0.9% to +3.7% | Under the 3% bar on the deciding cells. The state pool is ~11.6 GiB, but it's a small share of bytes per round |
| `HIBANA_SSM_STATE=int4` | Quick +7.7%, realistic <3% | Greedy screen failed: MBPP 16/20 (−3) |
| `HIBANA_BOLT_EXPERTS=fp8` (grouped kernel instead of fused b12x) | −3.5% on two cells | The fused b12x kernel is faster |
| `HIBANA_KV_FORMAT=fp8` (instead of NVFP4) | Quick +8.6%, realistic −2.4% to +0.2% | A win only at 36-token context. At 16K the larger KV cancels the saved dequantization, and it halves long-context capacity |
| `HIBANA_DEVICE_ACCEPT=1` (accept step on the GPU) | Mixed ±5% | Noise. Accept is ~1.6 ms of a ~40 ms round |
| `DRAFT_VOCAB=65536` and `196608` | See [4.5](#45-draft-vocabulary-shortlist-draft_vocab131072) | 131,072 is best on both sides |

`fast`'s other precision settings were already the best choice: `w3_decode`, `draft_head=w2`, `rescore=16`,
`flashnext_experts=w3`, `bolt_experts=b12x`.

**Earlier informal test, no conclusion:** on 2026-11-16 we compared expert budgets 16 and 12 with one agentic coding
task each (92.1 vs 96.6 tok/s). The two sessions took different steps, tools and lengths, so this says nothing about
speed or quality. The controlled expert-budget trials above replace it.

---

## 8. The 8-hour speed run, start to end

From 11:10 PM ET on 2026-11-19 to 5:20 AM ET on 2026-11-20. Speed-run bench, medians, n=6:

| Cell | Start | End | Change |
|---|---:|---:|---:|
| Quick prose (temperature 0, thinking off) | 88.5 | 104.8 | +18% |
| `prose25` (~16K-token prompt, thinking on, temperature 1.0) | 83.5 | 138.6 | +66% |
| `reason25` | 96.2 | 140.7 | +46% |
| `prose2` | 88.1 | 134.9 | +53% |
| `code2` | 107.5 | 160.7 | +49% |
| `imgprose` | 71.9 | 99.8 | +39% |
| `imgreal` (thinking on, temperature 1.0) | 71.8 | 136.2 | +90% |

A real ~25K-token cached prompt (25,165 tokens, thinking on, sampled, n=3) measured 137.1 tok/s.

**These end numbers include `accept_soft` 3.0, which we later reverted.** The temperature-1.0 cells would be lower at
0.5. We didn't re-run this bench after the revert. In the long-thinking replay, 0.5 decoded at 90–102 tok/s against
128–167 at 3.0.

What the run kept, in order:

1. CUDA graphs for image requests ([4.4](#44-cuda-graphs-for-image-requests-second-half-of-patch-0003)): kept, shipped
   in this repo.
2. Greedy `5:4.0` ([section 5](#5-worked-but-not-the-default-looser-greedy-acceptance)): kept on our server, not this
   repo's default.
3. `accept_soft` 3.0 ([section 6](#6-shipped-then-reverted-looser-sampled-acceptance)): reverted.
4. `DRAFT_VOCAB=131072` ([4.5](#45-draft-vocabulary-shortlist-draft_vocab131072)): kept, shipped in this repo.

Targets set before the run:

| Target | Result |
|---|---|
| Realistic 25K prose 100+ tok/s | Met (138.6), but only with 3.0 |
| Short prose 120+ tok/s | **Missed** (104.8). Every greedy rule looser than `5:4.0` failed MBPP |
| Image within 5% of text | Met (95.2%) |

Before the run we surveyed the public stacks. vLLM, SGLang, Flare, TensorFold and llama.cpp all report about 67 tok/s
or less single-stream for Flash-Next on GB10. No public stack was 1.3× faster than Hibana `fast`, so we tuned it
instead of switching.

---

## 9. Quality checks

### Paired screen against FP4-Local (2026-11-16)

Before any tuning, we compared stock Hibana `fast` with an FP4-Local (vLLM, NVFP4 + MTP) setup. The same 20 GSM8K and
20 MBPP questions, temperature 0, thinking off, 1,024-token cap:

| | Hibana `fast` | FP4-Local |
|---|---:|---:|
| GSM8K correct | 18/20 | 18/20 |
| GSM8K incomplete (hit the cap) | 1 | 2 |
| MBPP passes all 3 tests | 19/20 | 20/20 |

The one MBPP difference (`mbpp-016`): Hibana searched for a matching substring. The hidden tests wanted the whole
string to match. The task says "contains", so both readings are plausible. These public questions may also be in the
model's training data.

Twenty questions per category can't rule out real differences on hard reasoning, tool use or long-context work. For
those, see the GPQA-Diamond and agent benchmark numbers in the README, measured by Hibana's authors and dedene.

### Image outputs

- Speculation for image requests changed image answers in a few characters at temperature 0 (characters 4–8 in the
  story case). Turning speculation off also changed them, compared with the first vision build, and a cold vs warm cache
  alone changed output. So the drift is not caused by speculation alone.
- CUDA graphs changed image prose from character 44–50 on. Text output stayed identical.
- All factual image checks (OCR, counts, colors, follow-ups) gave the same answers in every build.

---

## 10. Not tested, and ideas not started

### Not tested

- **Image prefixes restored from the SSD cache tier:** after a container restart the follow-up answer was correct, but
  `cached_tokens` was 0 and no restore event appeared.
- **Behaviour under memory pressure** (request retraction) with images.
- **Standard image benchmarks** (MMMU, ChartQA): only our own checks.
- **Concurrent image and text requests with CUDA graphs:** before graphs, an image in the batch forced the whole batch
  eager, and text requests sharing it ran at about 53–55 tok/s. Not re-measured with patch 0003.
- **Greedy `5:4.0` on long thinking.**

### Ideas not started

- **Plausibility floor for sampled acceptance.** Accept a boosted draft only when the model ranks it close to its own
  top choice (Medusa-style typical acceptance). That would keep 0.5's safety and might buy some of 1.0–3.0's speed.
  It needs changes in `engine/rejection.py` and the fused kernel `kernels/sampled_verify.py`. Pass rule: no failures on
  the long-thinking replay, quality screens held, and sampled speed at least +25% over 0.5.
- **Cheaper verify.** Verify is 26–30 ms of a ~40 ms round and is bound by reading selected experts. Expert budgets cut
  those bytes but failed quality. A smarter union policy would need kernel and scheduler work.
- **Faster prefill:** `HIBANA_QSA_PREFILL_BACKEND=optimized` exists (SM121, up to 32K). It affects time to first token,
  not decode, and we haven't measured it.

---

## 11. Method lessons

1. **Short-answer quality screens can't see long-thinking failures.** GSM8K and MBPP at 1,024 tokens passed
   `accept_soft` 3.0. A 20K-token agent run did not. Any acceptance change needs a long replay.
2. **"No answer" means no answer and no tool call.** Our first kill rule only checked for empty content, and it missed a
   run that wrote one sentence and then hit the token limit.
3. **Three runs with overlapping ranges decide nothing.** CUDA graphs for images looked like noise at n=3 and turned out
   to be +26% at n=6.
4. **Tracing costs about 11% decode speed.** `HIBANA_TRACES` + `HIBANA_TRACE_CONFIDENCE` took quick prose from 88.5 to
   79.0. Run speed trials without tracing and read counters from `/describe`.
5. **Set the keep threshold before measuring.** A 3% bar, with a cold-restart re-test, threw out several changes that
   were real but too small to matter (SSM int8 at +0.9–3.7%).
6. **Look for per-request settings first.** `accept_soft`, `accept_top_k` and `accept_margin` can be set per request, so
   whole probe ladders ran without restarting the 186 GB model.
7. **Report the real prompt size.** Our "25K" cells measured 15,944 tokens. We kept the label so results stayed
   comparable, and we always state the real size.
8. **Don't trust logged byte counts.** Hibana's "5.38 GB per decode token" counts the FP8 trunk that `fast` doesn't use.
   Work it out from the manifest.
9. **Find the lever with the cheapest probe.** DFlash2 lost 13%, but its per-request probes showed that the drafter
   didn't matter and the acceptance rule did. That led to the two biggest gains of the run, and to the biggest failure.

---

## 12. Sources

- [Hibana](https://github.com/sharar-project/hibana) at
  [`d474b74`](https://github.com/sharar-project/hibana/tree/d474b74d5a892b2cd1cc8fc50cb17946e2a539bb), including
  `docs/operations.md`.
- [Hibana paper](https://arxiv.org/abs/2611.10469): method and the Flash-Next speed ablation.
- [dedene/Hibana-Qwen3.8-Flash-Next-DGX-Spark](https://github.com/dedene/Hibana-Qwen3.8-Flash-Next-DGX-Spark): the
  recipe this repo is built from, and the `exact`, `fast`, TensorFold and agent benchmark numbers.
- Checkpoints: RadixArk/Qwen3.8-Flash-Next-NVFP4 and Hibana's calibrated 3-bit copies, at the revisions Hibana pins in
  `hibana/launch/preflight.py`.
- [GSM8K](https://github.com/openai/grade-school-math) and
  [MBPP](https://github.com/google-research/google-research/tree/master/mbpp) (sanitized) for the quality screens.
