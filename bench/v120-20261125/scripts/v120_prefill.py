#!/usr/bin/env python3
import argparse, json, os, random, time, urllib.request

def make_prompt(words, nonce):
    rng = random.Random(20261125 + words)
    vocab = ["amber", "basalt", "cedar", "delta", "ember", "fjord", "garnet", "harbor", "indigo", "juniper", "kelp", "lumen", "maple", "nectar", "onyx", "prairie"]
    body = " ".join(rng.choice(vocab) for _ in range(words))
    return f"Unique prefill marker {nonce}.\n{body}\nReply with only the marker.", nonce

def ask(url, model, prompt, max_tokens=8):
    body = {"model": model, "messages": [{"role": "user", "content": prompt}], "temperature": 0,
            "max_tokens": max_tokens, "stream": True, "stream_options": {"include_usage": True},
            "chat_template_kwargs": {"enable_thinking": False}}
    req = urllib.request.Request(url + "/v1/chat/completions", json.dumps(body).encode(), {"Content-Type": "application/json"})
    t0 = time.time(); first = None; usage = {}
    with urllib.request.urlopen(req, timeout=1800) as r:
        for raw in r:
            line = raw.decode().strip()
            if not line.startswith("data:") or line == "data: [DONE]":
                continue
            d = json.loads(line[5:])
            if d.get("usage"):
                usage = d["usage"]
            for c in d.get("choices") or []:
                delta = c.get("delta") or {}
                if first is None and (delta.get("content") or delta.get("reasoning_content") or delta.get("reasoning")):
                    first = time.time()
    total = time.time() - t0
    pt = usage.get("prompt_tokens") or 0
    return {"ttft_ms": (first - t0) * 1000 if first else None, "total_ms": total * 1000,
            "usage": usage, "prefill_tps": pt / (first - t0) if first and pt else None}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://127.0.0.1:5806")
    ap.add_argument("--model", default="local-ai")
    ap.add_argument("--out", required=True)
    ap.add_argument("--nonce", default=str(int(time.time())))
    args = ap.parse_args()
    cases = [("pp2048", 1200), ("long32k", 19000), ("long_cold", 39000), ("long_warm", 39000)]
    if os.environ.get("CASES"):
        wanted = set(os.environ["CASES"].split(","))
        cases = [c for c in cases if c[0] in wanted]
    results = []
    for name, words in cases:
        p, nonce = make_prompt(words, args.nonce + "-" + name)
        r = ask(args.url, args.model, p)
        r.update({"name": name, "requested_words": words, "nonce": nonce})
        results.append(r)
        print(name, r, flush=True)
    with open(args.out, "w") as f:
        json.dump({"results": results}, f, indent=2)
        f.write("\n")

if __name__ == "__main__":
    main()
