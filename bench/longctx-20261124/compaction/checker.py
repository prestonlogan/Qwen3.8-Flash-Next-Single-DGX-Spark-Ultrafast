# Hidden checker for the agent's httplint.py. Each case names the editor's note (requirement) it tests.
# Usage: checker.py WORKSPACE_DIR  -> prints per-case results and a JSON summary on the last line.
# Runs the tool inside python:3.12-slim with no network, like the agent's own commands.
import json, os, subprocess, sys, tempfile
ws = os.path.abspath(sys.argv[1])
CR = "\r\n"
def req(*lines, crlf=False):
    return (CR if crlf else "\n").join(lines) + (CR if crlf else "\n")
OK11 = ["GET /a HTTP/1.1", "Host: example.com", "Accept: */*", ""]
CASES = [  # (name, note, file content or None for missing file, args, expected findings [(line, code)], exit)
    ("clean 1.1", 1, req(*OK11), [], [], 0),
    ("clean 1.1 CRLF", 1, req(*OK11, crlf=True), [], [], 0),
    ("missing file", 1, None, [], [], 2),
    ("finding format and exit 1", 1, req("GET /a HTTP/1.1", "Accept: */*", ""), [], [(1, "H004")], 1),
    ("request line two parts", 2, req("GET /a", "Host: x", ""), [], [(1, "H001")], 1),
    ("request line double space skips H002/H003", 2, req("get  /a HTTP/2", "Host: x", ""), [], [(1, "H001")], 1),
    ("version HTTP/2", 3, req("GET /a HTTP/2", "Host: x", ""), [], [(1, "H002")], 1),
    ("version lowercase", 3, req("GET /a http/1.1", "Host: x", ""), [], [(1, "H002")], 1),
    ("method lowercase", 4, req("get /a HTTP/1.1", "Host: x", ""), [], [(1, "H003")], 1),
    ("method with digit", 4, req("G3T /a HTTP/1.1", "Host: x", ""), [], [(1, "H003")], 1),
    ("1.0 without Host is fine", 5, req("GET /a HTTP/1.0", "Accept: */*", ""), [], [], 0),
    ("lowercase host counts", 6, req("GET /a HTTP/1.1", "host: x", ""), [], [], 0),
    ("duplicate Host, mixed case", 6, req("GET /a HTTP/1.1", "Host: x", "Accept: */*", "HOST: y", "host: z", ""),
     [], [(4, "H005"), (5, "H005")], 1),
    ("space before colon", 7, req("GET /a HTTP/1.1", "Host : x", ""), [], [(2, "H006")], 1),
    ("space before colon still counts as Host", 7, req("GET /a HTTP/1.1", "Host : x", "Host: y", ""), [],
     [(2, "H006"), (3, "H005")], 1),
    ("CL and TE", 8, req("POST /a HTTP/1.1", "Host: x", "Transfer-Encoding: chunked", "Accept: */*",
                         "Content-Length: 5", "", "hello"), [], [(5, "H007")], 1),
    ("CL invalid", 9, req("POST /a HTTP/1.1", "Host: x", "Content-Length: 12a", "", "body"), [], [(3, "H008")], 1),
    ("CL with spaces is valid", 9, req("POST /a HTTP/1.1", "Host: x", "Content-Length:  42 ", ""), [], [], 0),
    ("CL negative", 9, req("POST /a HTTP/1.1", "Host: x", "content-length: -1", ""), [], [(3, "H008")], 1),
    ("obs-fold", 10, req("GET /a HTTP/1.1", "Host: x", "X-Long: a", "\tcontinued", ""), [], [(4, "H009")], 1),
    ("obs-fold not checked further", 10, req("GET /a HTTP/1.1", "Host: x", " Host : y", ""), [], [(3, "H009")], 1),
    ("body not checked", 11, req("POST /a HTTP/1.1", "Host: x", "Content-Length: 3", "", "Host : y", " z"), [], [], 0),
    ("sorted by line then code", 11, req("get /a HTTP/1.1", "Accept: */*", "Content-Length: x", ""), [],
     [(1, "H003"), (1, "H004"), (3, "H008")], 1),
    ("json clean", 12, req(*OK11), ["--json"], [], 0),
    ("json findings", 12, req("get /a HTTP/1.1", "Host: x", "Host: y", ""), ["--json"], [(1, "H003"), (3, "H005")], 1),
]
def run(content, args):
    with tempfile.TemporaryDirectory(dir=ws) as d:
        name = os.path.basename(d) + "/case.http"
        if content is not None:
            open(os.path.join(d, "case.http"), "w", newline="").write(content)
        p = subprocess.run(["docker", "run", "--rm", "--network", "none", "-u", f"{os.getuid()}:{os.getgid()}",
                            "-v", f"{ws}:/ws:ro", "-w", "/ws", "python:3.12-slim", "timeout", "30",
                            "python", "httplint.py", *args, name], capture_output=True, text=True)
        return p.returncode, p.stdout
def parse(out, js):
    if js:
        return [(int(o["line"]), str(o["code"])) for o in json.loads(out)]
    got = []
    for l in out.splitlines():
        parts = l.split(":", 2)
        if len(parts) >= 2 and parts[0].strip().isdigit():
            got.append((int(parts[0]), parts[1].strip()))
    return got
results = []
for name, note, content, args, want, code in CASES:
    try:
        rc, out = run(content, args)
        got = parse(out, "--json" in args) if code != 2 else []
        ok = rc == code and got == want
    except Exception as e:
        rc, got, ok = None, repr(e)[:80], False
    results.append({"case": name, "note": note, "ok": ok})
    print(("PASS " if ok else "FAIL ") + f"[note {note}] {name}" + ("" if ok else f"  want {want} exit {code}, got {got} exit {rc}"))
notes = {}
for r in results:
    notes.setdefault(r["note"], []).append(r["ok"])
summary = {"passed": sum(r["ok"] for r in results), "total": len(results),
           "notes_fully_passed": sorted(n for n, v in notes.items() if all(v)),
           "notes_failed": sorted(n for n, v in notes.items() if not all(v))}
print(json.dumps(summary))
