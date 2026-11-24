# Throughput Benchmark — qwen3.8-flash-next-hibana-fast

- **Run ID**: `2026-11-24T20-21-13.869317Z_b5d7b549`
- **Date**: `2026-11-24T20:21:13.869370+00:00`
- **Mode**: throughput-only
- **tool-eval-bench**: `v3.1.1.dev4+ga53ff61de`
- **Label**: <code>v1.1.0 default, decode at depth</code>
- **Backend**: unknown
- **Server**: http://***:30002
- **Model (API)**: `qwen3.8-flash-next-hibana-fast`

## Environment

| Property | Value |
|---|---|
| Host | `spark-9535` |
| Platform | `Linux-7.0.0-1025-nvidia-aarch64-with-glibc2.39` |
| Python | 3.12.14 |

## Results

| Test | pp t/s | tg t/s | TTFT (ms) | Total (ms) | Tokens |
|---|---:|---:|---:|---:|---:|
| pp2048 tg512 @ d0 | 2,272 | 124.2 | 1,003 | 5,116 | 2048+512 |
| pp2048 tg512 @ d32768 | 2,883 | 104.2 | 11,128 | 15,695 | 2048+477 |
| pp2048 tg512 @ d65536 | 2,740 | 101.4 | 22,514 | 27,554 | 2048+512 |
| pp2048 tg512 @ d100000 | 2,643 | 94.1 | 35,189 | 39,967 | 2048+450.5 |
| pp2048 tg512 @ d150000 | 2,584 | 86.0 | 53,489 | 59,430 | 2048+512 |
| pp2048 tg512 @ d200000 | 2,462 | 72.1 | 74,721 | 80,720 | 2048+433.5 |
| pp2048 tg512 @ d250000 | 2,644 | 69.4 | 86,609 | 93,974 | 2048+512 |