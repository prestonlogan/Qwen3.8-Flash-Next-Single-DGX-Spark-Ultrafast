#!/usr/bin/env python3
import argparse, json, time, urllib.request
from concurrent.futures import ThreadPoolExecutor

def ask(url, model, prompt, max_tokens, temperature=None, seed=None):
    body = {"model": model, "messages": [{"role": "user", "content": prompt}], "max_tokens": max_tokens}
    if temperature is not None:
        body["temperature"] = temperature
    if seed is not None:
        body["seed"] = seed
    req = urllib.request.Request(url + "/v1/chat/completions", json.dumps(body).encode(), {"Content-Type": "application/json"})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=1800) as r:
        d = json.load(r)
    ch = d["choices"][0]
    return {"wall_s": time.time() - t0, "content": (ch.get("message", {}).get("content") or "")[:200],
            "reasoning_len": len(ch.get("message", {}).get("reasoning_content") or ""),
            "finish_reason": ch.get("finish_reason"), "usage": d.get("usage", {})}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://127.0.0.1:5806")
    ap.add_argument("--model", default="local-ai")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    prompt = "A notebook costs 4 euros and a pen costs 1.50 euros. How much do 3 notebooks and 2 pens cost? Answer with the number only."
    out = {"first_no_temperature": ask(args.url, args.model, prompt, 128),
           "second_temperature_0_3": ask(args.url, args.model, prompt, 128, temperature=0.3, seed=2)}
    with ThreadPoolExecutor(max_workers=4) as ex:
        futs = [ex.submit(ask, args.url, args.model, prompt + f" Variant {i}.", 128, 0.3, 10 + i) for i in range(4)]
        out["four_concurrent"] = [f.result() for f in futs]
    with open(args.out, "w") as f:
        json.dump(out, f, indent=2)
        f.write("\n")
    print(json.dumps(out, indent=2))

if __name__ == "__main__":
    main()
