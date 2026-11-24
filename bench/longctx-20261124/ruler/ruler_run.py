# RULER (NVIDIA/RULER synthetic tasks, data from its prepare.py) against an OpenAI-compatible server.
# Chat API, thinking off, temperature 0, 128 output tokens. Scoring as RULER: string_match_all, string_match_part for qa.
# Usage: ruler_run.py LENGTHS N [MAX_TOKENS] [RESULTS]   (resumes from RESULTS, default results.jsonl; MAX_TOKENS default 128)
# The cwe rows in results_cwe1024.jsonl came from: TASKS=cwe ruler_run.py 32768 5 1024 results_cwe1024.jsonl (then 65536,131072 3)
import json, os, re, sys, time, urllib.request
URL = os.environ.get("URL", "http://127.0.0.1:8888/v1/chat/completions"); MODEL = os.environ.get("MODEL", "local-ai")
KEY = os.environ.get("API_KEY", "")  # the recipe has no key check; set this only behind a gateway
TASKS = "niah_single_1 niah_single_2 niah_single_3 niah_multikey_1 niah_multikey_2 niah_multikey_3 niah_multivalue niah_multiquery vt cwe fwe qa_1 qa_2".split()
lengths = [int(x) for x in sys.argv[1].split(",")]; N = int(sys.argv[2])
MAX_TOKENS = int(sys.argv[3]) if len(sys.argv) > 3 else 128; RESULTS = sys.argv[4] if len(sys.argv) > 4 else "results.jsonl"
if os.environ.get("TASKS"): TASKS = os.environ["TASKS"].split(",")
done = set()
if os.path.exists(RESULTS):
    for l in open(RESULTS): r = json.loads(l); done.add((r["len"], r["task"], r["index"]))
def ask(text):
    body = {"model": MODEL, "messages": [{"role": "user", "content": text}], "max_tokens": MAX_TOKENS, "temperature": 0,
            "chat_template_kwargs": {"enable_thinking": False}}
    req = urllib.request.Request(URL, json.dumps(body).encode(), {"Content-Type": "application/json", **({"Authorization": "Bearer " + KEY} if KEY else {})})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=1800) as r: d = json.load(r)
            return d["choices"][0]["message"].get("content") or "", d.get("usage", {})
        except Exception as e:
            print("retry", attempt, repr(e)[:200], flush=True); time.sleep(30)
    return None, {}
def score(task, pred, refs):
    p = pred.lower()
    if task.startswith("qa"): return 100.0 * max(1.0 if r.lower() in p else 0.0 for r in refs)
    return 100.0 * sum(1.0 if r.lower() in p else 0.0 for r in refs) / len(refs)
out = open(RESULTS, "a")
for L in lengths:
    data = {t: [json.loads(l) for l in open(f"data/{L}/{t}/validation.jsonl")][:N] for t in TASKS}
    for i in range(N):
        for t in TASKS:
            if (L, t, i) in done or i >= len(data[t]): continue
            s = data[t][i]; t0 = time.time(); pred, usage = ask(s["input"])
            if pred is None: print("FAILED", L, t, i, flush=True); continue
            r = {"len": L, "task": t, "index": i, "score": score(t, pred, s["outputs"]), "pred": pred[:300], "refs": s["outputs"],
                 "prompt_tokens": usage.get("prompt_tokens"), "secs": round(time.time() - t0, 1)}
            out.write(json.dumps(r) + "\n"); out.flush()
            print(time.strftime("%I:%M %p"), L, t, i, r["score"], r["prompt_tokens"], r["secs"], flush=True)
