# Compaction agent test: a doc-review and tool-building task far larger than the context window.
# The agent reads ~900K tokens of RFCs (docs/, only through read_doc) that hide 12 editor's notes with the
# requirements for httplint.py, then builds and tests the tool in its workspace. When a turn's prompt passes
# COMPACT_AT tokens, the history is replaced by the agent's own summary (files in the workspace persist).
# Commands run in python:3.12-slim with no network and only the workspace mounted.
# Stop rules: same tool call 4 times in a row (loop), 45 min without a new page read or file write (stall),
# 3 engine errors in a row, MAX_HOURS wall time, MAX_TURNS turns.
import json, os, subprocess, sys, time, urllib.request
URL = os.environ.get("URL", "http://127.0.0.1:8888/v1/chat/completions")
MODEL = os.environ.get("MODEL", "local-ai")
KEY = os.environ.get("API_KEY", "")  # the recipe has no key check; set this only behind a gateway
COMPACT_AT = int(os.environ.get("COMPACT_AT", "150000"))
MAX_HOURS, MAX_TURNS, PAGE_CHARS = float(os.environ.get("MAX_HOURS", "5")), 1500, 20000
RUN = os.path.abspath(sys.argv[1]); WS = RUN + "/workspace"; DOCS = os.path.abspath("docs")
os.makedirs(WS, exist_ok=True)
ORDER = [f"rfc{n}.txt" for n in "9110 9112 9111 3986 6265 7541 9113 9114 9204 6455 6797 9218 7230 7540 8446 5246 9000 9001 9002 9293".split()]
PAGES = {d: (len(open(f"{DOCS}/{d}").read()) + PAGE_CHARS - 1) // PAGE_CHARS for d in ORDER}
LOG = open(RUN + "/events.jsonl", "a")
def log(**k):
    k["t"] = round(time.time() - T0, 1); LOG.write(json.dumps(k) + "\n"); LOG.flush()
    print(time.strftime("%I:%M %p"), json.dumps(k)[:300], flush=True)
SYSTEM = f"""You are an autonomous software agent working alone; nobody will answer questions. Use the tools.

Task: review a documentation set and build a tool from it.
1. Read every document in full, in this order, page by page with read_doc: {", ".join(f"{d} ({PAGES[d]} pages)" for d in ORDER)}.
   Total {sum(PAGES.values())} pages. The team's editor planted 12 notes, "[Editor's note for the httplint review team, note K of 12: ...]",
   at various places inside these documents. Together they are the full specification of httplint.py. Nothing else defines it.
2. In the workspace, write httplint.py meeting every note exactly (Python 3.12 standard library only), and tests in
   test_httplint.py using unittest (pytest is not installed). Run the tests with run and fix failures.
3. Write REVIEW.md: one short paragraph per document on what it covers.
4. Call finish.

Your context window is limited. When it fills up, the conversation is replaced by a summary you write, so keep
important facts in your summaries; files you write in the workspace persist. The documents are only reachable
through read_doc; run executes bash in the workspace (python 3.12, no network)."""
TOOLS = [
    {"type": "function", "function": {"name": "read_doc", "description": "Read one page of a document.",
        "parameters": {"type": "object", "properties": {"name": {"type": "string"}, "page": {"type": "integer", "description": "1-based"}}, "required": ["name", "page"]}}},
    {"type": "function", "function": {"name": "write_file", "description": "Create or overwrite a file in the workspace.",
        "parameters": {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}}, "required": ["path", "content"]}}},
    {"type": "function", "function": {"name": "read_file", "description": "Read a file from the workspace.",
        "parameters": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}}},
    {"type": "function", "function": {"name": "run", "description": "Run a bash command in the workspace (120 s limit).",
        "parameters": {"type": "object", "properties": {"command": {"type": "string"}}, "required": ["command"]}}},
    {"type": "function", "function": {"name": "finish", "description": "Call when the whole task is done.",
        "parameters": {"type": "object", "properties": {"summary": {"type": "string"}}, "required": ["summary"]}}},
]
def chat(messages, tools=True, max_tokens=16384):
    body = {"model": MODEL, "messages": messages, "max_tokens": max_tokens}
    if tools: body["tools"] = TOOLS
    req = urllib.request.Request(URL, json.dumps(body).encode(), {"Content-Type": "application/json", **({"Authorization": "Bearer " + KEY} if KEY else {})})
    with urllib.request.urlopen(req, timeout=3600) as r: return json.load(r)
def safe(path):
    p = os.path.realpath(os.path.join(WS, path))
    if not p.startswith(os.path.realpath(WS) + os.sep): raise ValueError("path must be inside the workspace")
    return p
read_pages = set()
def tool(name, a):
    if name == "read_doc":
        d, p = a["name"], int(a["page"])
        if d not in PAGES: return f"Unknown document {d}. Documents: {', '.join(ORDER)}"
        if not 1 <= p <= PAGES[d]: return f"{d} has pages 1 to {PAGES[d]}."
        read_pages.add((d, p)); s = open(f"{DOCS}/{d}").read()
        return f"{d} page {p} of {PAGES[d]}\n\n" + s[(p - 1) * PAGE_CHARS:p * PAGE_CHARS]
    if name == "write_file":
        p = safe(a["path"]); os.makedirs(os.path.dirname(p), exist_ok=True); open(p, "w").write(a["content"])
        return f"wrote {len(a['content'])} chars to {a['path']}"
    if name == "read_file":
        return open(safe(a["path"])).read()[:40000]
    if name == "run":
        p = subprocess.run(["docker", "run", "--rm", "--network", "none", "-u", f"{os.getuid()}:{os.getgid()}", "-e", "HOME=/tmp",
                            "-v", f"{WS}:/ws", "-w", "/ws", "python:3.12-slim", "timeout", "120", "bash", "-c", a["command"]],
                           capture_output=True, text=True)
        out = (p.stdout + p.stderr)[-8000:]
        return f"exit {p.returncode}\n{out}"
    return f"unknown tool {name}"
COMPACT_PROMPT = ("Your context is about to be compacted: everything above will be replaced by what you write now. Write a "
    "complete summary that lets you continue with no other memory: every editor's note found so far with its exact details, "
    "which documents and pages you have finished, what files you have written and their state, and the exact next step. "
    "Reply with the summary only, no tool calls.")
T0 = time.time()
messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": "Begin."}]
compactions = 0; errors = 0; last_calls = []; last_progress = time.time(); outcome = None; turn = 0
while outcome is None:
    turn += 1
    if turn > MAX_TURNS: outcome = "max_turns"; break
    if time.time() - T0 > MAX_HOURS * 3600: outcome = "max_hours"; break
    if time.time() - last_progress > 45 * 60: outcome = "stall"; break
    try:
        r = chat(messages); errors = 0
    except Exception as e:
        errors += 1; log(ev="error", err=repr(e)[:300])
        if errors >= 3: outcome = "engine_errors"; break
        time.sleep(30); continue
    m = r["choices"][0]["message"]; u = r.get("usage", {})
    calls = m.get("tool_calls") or []
    log(ev="turn", turn=turn, prompt=u.get("prompt_tokens"), completion=u.get("completion_tokens"), calls=[c["function"]["name"] for c in calls],
        finish=r["choices"][0].get("finish_reason"), pages=len(read_pages), compactions=compactions)
    messages.append({"role": "assistant", "content": m.get("content") or "", **({"tool_calls": calls} if calls else {})})
    if not calls:
        messages.append({"role": "user", "content": "Continue with the task using the tools. Call finish when everything is done."})
    for c in calls:
        name = c["function"]["name"]
        try: a = json.loads(c["function"]["arguments"] or "{}")
        except Exception: a = None
        sig = name + json.dumps(a, sort_keys=True)
        last_calls = (last_calls + [sig])[-4:]
        if len(last_calls) == 4 and len(set(last_calls)) == 1: outcome = "loop"
        if a is None: res = "error: arguments were not valid JSON"
        elif name == "finish": outcome = "finished"; res = "ok"; log(ev="finish", summary=a.get("summary", "")[:2000])
        else:
            before = len(read_pages)
            try: res = tool(name, a)
            except Exception as e: res = f"error: {e}"
            if len(read_pages) > before or name == "write_file": last_progress = time.time()
        messages.append({"role": "tool", "tool_call_id": c.get("id", ""), "content": res})
    if outcome: break
    if (u.get("prompt_tokens") or 0) + (u.get("completion_tokens") or 0) > COMPACT_AT:
        try:
            s = chat(messages + [{"role": "user", "content": COMPACT_PROMPT}], tools=False, max_tokens=12000)
        except Exception as e:
            log(ev="error", err="compaction: " + repr(e)[:300]); outcome = "engine_errors"; break
        summary = s["choices"][0]["message"].get("content") or ""
        compactions += 1
        open(f"{RUN}/summary-{compactions}.md", "w").write(summary)
        log(ev="compaction", n=compactions, before=u.get("prompt_tokens"), summary_tokens=s.get("usage", {}).get("completion_tokens"), pages=len(read_pages))
        messages = [{"role": "system", "content": SYSTEM},
                    {"role": "user", "content": f"[The conversation was compacted ({compactions} so far). Your summary:]\n\n{summary}\n\nContinue the task."}]
log(ev="end", outcome=outcome, turns=turn, compactions=compactions, pages=len(read_pages), total_pages=sum(PAGES.values()),
    hours=round((time.time() - T0) / 3600, 2))
