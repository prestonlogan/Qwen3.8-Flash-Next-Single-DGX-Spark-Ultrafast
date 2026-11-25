#!/usr/bin/env python3
import argparse, hashlib, json, statistics, sys, time, urllib.request
from concurrent.futures import ThreadPoolExecutor

def post(url, model, prompt, max_tokens, variant):
    body = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0,
        "max_tokens": max_tokens,
        "chat_template_kwargs": {"enable_thinking": False},
    }
    if variant:
        body["seed"] = variant
    req = urllib.request.Request(url + "/v1/chat/completions", json.dumps(body).encode(), {"Content-Type": "application/json"})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=1800) as r:
        d = json.load(r)
    ch = d["choices"][0]
    text = ch.get("message", {}).get("content") or ""
    return {
        "wall_s": time.time() - t0,
        "usage": d.get("usage", {}),
        "finish_reason": ch.get("finish_reason"),
        "content_len": len(text),
        "content_sha256": hashlib.sha256(text.encode()).hexdigest(),
        "content_prefix": text[:160],
        "text": text,
    }

def stats(url):
    with urllib.request.urlopen(url + "/describe", timeout=10) as r:
        d = json.load(r)
    s = d.get("spec_stats") or d.get("speculation") or d.get("spec") or d
    return {
        "rounds": s.get("rounds", 0),
        "proposed": s.get("proposed", 0),
        "accepted": s.get("accepted", 0),
        "emitted": s.get("emitted", 0),
        "round_ms": s.get("round_ms", 0.0),
        "accept_rate": s.get("accept_rate", 0.0),
        "tokens_per_round": s.get("tokens_per_round", 0.0),
        "relaxed_accepts": s.get("relaxed_accepts", 0),
        "verify_depth": s.get("verify_depth"),
    }

def prompt(rows, nonce):
    lines = [f"FIXED COPY BENCH {nonce}"]
    for i in range(rows):
        lines.append(
            f"field note {i}: operator {chr(65+i%26)}{(i*17)%100} logged voltage {(i*37)%991} "
            f"humidity {(i*29)%83} rotation {(i*11)%97} and ordinary maintenance telemetry."
        )
    lines.append(f"Continue the log at field note {rows}. Output only field notes {rows} through {rows+15}, one per line, in exactly the same format.")
    return "\n".join(lines)

def delta(before, after):
    rounds = after["rounds"] - before["rounds"]
    emitted = after["emitted"] - before["emitted"]
    proposed = after["proposed"] - before["proposed"]
    accepted = after["accepted"] - before["accepted"]
    round_s = (after["round_ms"] * after["rounds"] - before["round_ms"] * before["rounds"]) / 1000.0
    return {
        "rounds": rounds,
        "emitted": emitted,
        "proposed": proposed,
        "accepted": accepted,
        "accepted_per_proposed": accepted / proposed if proposed else 0.0,
        "emitted_per_round": emitted / rounds if rounds else 0.0,
        "round_ms": round_s * 1000.0 / rounds if rounds else 0.0,
        "round_effective_tps": emitted / round_s if round_s > 0 else 0.0,
    }

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://127.0.0.1:5806")
    ap.add_argument("--model", default="local-ai")
    ap.add_argument("--mode", choices=["single", "batch2"], required=True)
    ap.add_argument("--rows", type=int, default=4400)
    ap.add_argument("--max-tokens", type=int, default=512)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    nonce = f"{int(time.time())}-{args.mode}"
    if args.mode == "single":
        p = prompt(args.rows, nonce)
        before = stats(args.url)
        r = post(args.url, args.model, p, args.max_tokens, None)
        after = stats(args.url)
        out = {"mode": "single", "nonce": nonce, "rows": args.rows, "before": before, "after": after, "response": r, **delta(before, after)}
        out["response"].pop("text", None)
    else:
        ps = [prompt(args.rows, nonce + "-" + str(i)) for i in range(2)]
        before = stats(args.url)
        with ThreadPoolExecutor(max_workers=2) as ex:
            futs = [ex.submit(post, args.url, args.model, p, args.max_tokens, i) for i, p in enumerate(ps)]
            rs = [f.result() for f in futs]
        after = stats(args.url)
        out = {"mode": "batch2", "nonce": nonce, "rows": args.rows, "before": before, "after": after, "responses": rs, "batch_wall_s": max(r["wall_s"] for r in rs), **delta(before, after)}
        for r in out["responses"]:
            r.pop("text", None)
    with open(args.out, "w") as f:
        json.dump(out, f, indent=2)
        f.write("\n")
    print(json.dumps({k: v for k, v in out.items() if k not in ("responses", "response")}, indent=2))

if __name__ == "__main__":
    main()
