import json, collections
# Prints the RULER table. cwe rows come from results_cwe1024.jsonl (1,024 output tokens) when it exists.
import os
rs = [json.loads(l) for l in open("results.jsonl")]
if os.path.exists("results_cwe1024.jsonl"):
    rs = [r for r in rs if r["task"] != "cwe"] + [json.loads(l) for l in open("results_cwe1024.jsonl")]
by = collections.defaultdict(list)
for r in rs: by[(r["len"], r["task"])].append(r["score"])
lens = sorted({r["len"] for r in rs}); tasks = list(dict.fromkeys(r["task"] for r in rs))
print("task".ljust(16) + "".join(f"{l//1024}K".rjust(8) for l in lens))
for t in tasks: print(t.ljust(16) + "".join((f"{sum(by[(l,t)])/len(by[(l,t)]):.0f}" if by[(l,t)] else "-").rjust(8) for l in lens))
print("average".ljust(16) + "".join(f"{sum(sum(by[(l,t)])/len(by[(l,t)]) for t in tasks if by[(l,t)])/max(1,sum(1 for t in tasks if by[(l,t)])):.1f}".rjust(8) for l in lens))
print("n/task".ljust(16) + "".join(str(min(len(by[(l,t)]) for t in tasks)).rjust(8) for l in lens))
