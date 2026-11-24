# Speed bench behind the README's numbers (run 2026-11-20): `python3 bench/bench.py results.json` against a running
# server. Greedy cells send Hibana's stock acceptance rule explicitly (accept_top_k 3, accept_margin 2.0); sampled
# cells send no temperature (1.0, the generation config). Thinking on (server default).
# Decode tok/s = (completion_tokens - 1) / (last chunk - first chunk). Results: bench/results.json.
# BENCH_ACCEPT=server leaves the acceptance rule to the server (v1.1.0's exact acceptance) instead of sending the stock one.
import json, os, time, base64, sys, statistics, threading, urllib.request
URL = os.environ.get("HIBANA_URL", "http://127.0.0.1:8888") + "/v1/chat/completions"
KEY = os.environ.get("API_KEY", "")
MODEL = os.environ.get("HIBANA_MODEL", "local-ai")
STOCK_ACCEPT = os.environ.get("BENCH_ACCEPT", "stock") != "server"
IMG = os.path.dirname(os.path.abspath(__file__)) + "/"
PROSE = "Write a 700-word short story about a lighthouse keeper who finds a message in a bottle. Use vivid detail."
CODE = "Write a Python LRU cache class with get and put, full type hints, docstrings, and pytest unit tests."
def img_msg(name, text):
    b = base64.b64encode(open(IMG + name, "rb").read()).decode()
    return [{"role": "user", "content": [{"type": "image_url", "image_url": {"url": "data:image/png;base64," + b}},
                                         {"type": "text", "text": text}]}]
def one(messages, greedy, max_tokens):
    body = {"model": MODEL, "messages": messages, "max_tokens": max_tokens, "stream": True,
            "stream_options": {"include_usage": True}}
    if greedy: body.update(temperature=0, **(dict(accept_top_k=3, accept_margin=2.0) if STOCK_ACCEPT else {}))
    req = urllib.request.Request(URL, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json", **({"Authorization": "Bearer " + KEY} if KEY else {})})
    t0 = time.time(); first = last = None; n = None
    with urllib.request.urlopen(req, timeout=900) as r:
        for raw in r:
            line = raw.decode().strip()
            if not line.startswith("data:") or line == "data: [DONE]": continue
            d = json.loads(line[5:])
            if d.get("usage"): n = d["usage"]["completion_tokens"]
            for c in d.get("choices") or []:
                delta = c.get("delta") or {}
                if delta.get("content") or delta.get("reasoning_content") or delta.get("reasoning"):
                    now = time.time(); first = first or now; last = now
    return {"tokens": n, "ttft": first - t0, "decode": (n - 1) / (last - first), "start": t0, "first": first, "last": last}
CELLS = [("prose T0", [{"role": "user", "content": PROSE}], True, 512, 3),
         ("code T0", [{"role": "user", "content": CODE}], True, 512, 3),
         ("image prose T0", img_msg("shapes.png", "Describe this image in detail, then write a short poem about it."), True, 512, 3),
         ("prose T1.0", [{"role": "user", "content": PROSE}], False, 1024, 5),
         ("code T1.0", [{"role": "user", "content": CODE}], False, 1024, 5),
         ("image prose T1.0", img_msg("shapes.png", "Describe this image in detail, then write a short poem about it."), False, 1024, 5)]
out = {}
one([{"role": "user", "content": "Say hi."}], True, 16)  # warm up
for name, msgs, greedy, mt, reps in CELLS:
    rs = [one(msgs, greedy, mt) for _ in range(reps)]
    med = statistics.median(r["decode"] for r in rs)
    out[name] = {"median": round(med, 1), "runs": [round(r["decode"], 1) for r in rs], "tokens": [r["tokens"] for r in rs]}
    print(time.strftime("%I:%M %p"), name, out[name], flush=True)
for label, greedy in (("4 requests T1.0", False), ("4 requests T0", True)):
    aggs = []
    for _ in range(3):
        res = [None] * 4
        def go(i): res[i] = one([{"role": "user", "content": PROSE}], greedy, 1024 if not greedy else 512)
        th = [threading.Thread(target=go, args=(i,)) for i in range(4)]; [t.start() for t in th]; [t.join() for t in th]
        aggs.append(sum(r["tokens"] - 1 for r in res) / (max(r["last"] for r in res) - min(r["first"] for r in res)))
    out[label] = {"median": round(statistics.median(aggs), 1), "runs": [round(a, 1) for a in aggs]}
    print(time.strftime("%I:%M %p"), label, out[label], flush=True)
json.dump(out, open(sys.argv[1], "w"), indent=1)
