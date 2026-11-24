---
license: other
license_name: qwen-community-1.0
license_link: LICENSE
base_model:
- Qwen/Qwen3.8-Flash-Next
tags:
- speculative-decoding
- mtp
- hibana
- dgx-spark
---

# Qwen3.8-Flash-Next MTP draft head (distilled, 3-bit experts)

A replacement multi-token-prediction (MTP) draft head for Qwen3.8-Flash-Next, used by the
[Qwen3.8-Flash-Next Single DGX Spark Ultrafast](https://github.com/prestonlogan/Qwen3.8-Flash-Next-Single-DGX-Spark-Ultrafast)
recipe (v1.1.0 and later) on [Hibana](https://github.com/sharar-project/hibana). The draft head only proposes tokens.
The target model verifies every proposal. With exact acceptance (the recipe's `TUNING=v1.1-exact`) the served
distribution is the target's own, so a better draft head changes speed, not answers. The recipe's default relaxes
acceptance slightly (`accept_soft` 0.35 when sampling, Hibana's top-3 rule at temperature 0).

| File | Size | SHA-256 | Contents |
|---|---:|---|---|
| `mtp-t35-overlap-body.pt` | 177,868,149 B | `964a0756170bd3c7ef8b7b785d761b8dbe0706939ed4ff3d7286108d9dcde0f6` | MTP body (attention, norms, projections) |
| `mtp-t35-overlap-w3exp.pt` | 1,030,229,181 B | `b2db323c741517b3d4d244801c20af4a90cd909a09d72d3d550e4b34d5396c50` | The head's 512 routed experts in Hibana's 3-bit format |

Both are plain PyTorch state dicts, loaded with `torch.load(..., weights_only=True)`.

## Training

Warm-started from the checkpoint's own MTP head, then distilled against Qwen3.8-Flash-Next's output distributions on
858 text and image traces. The loss targets speculative acceptance directly: KL divergence plus an overlap term
(1 - sum min(p, q)) over four rollout steps, with a rank-32 LoRA on all 512 experts merged into the 3-bit weights.
Serving the experts in 3-bit form frees about 1.5 GiB of memory against the stock head.

## Use

The recipe's `download` service fetches and checks both files. By hand, place them in Hibana's results folder and set:

```bash
HIBANA_MTP_WEIGHTS=/data/w3-checkpoints/mtp-t35-overlap-body.pt
HIBANA_MTP_W3_EXPERTS=1
HIBANA_MTP_W3_EXPERTS_PATH=/data/w3-checkpoints/mtp-t35-overlap-w3exp.pt
```

These variables need the recipe's `patches/0004`; upstream Hibana v0.1.0 does not read them.

## License

Derived from Qwen3.8-Flash-Next and distributed under the Qwen Community License 1.0 (see `LICENSE`, copyright 2026
Qwen), including its conditions for large commercial deployments and for Model-as-a-Service and AI Work Assistant
businesses.
