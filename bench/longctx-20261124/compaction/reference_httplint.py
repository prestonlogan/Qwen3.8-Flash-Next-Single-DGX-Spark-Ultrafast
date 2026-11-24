# Reference solution, used only to validate checker.py (it must score 25/25). Never shown to the agent.
import json, re, sys
args = sys.argv[1:]
js = "--json" in args
args = [a for a in args if a != "--json"]
try:
    text = open(args[0], newline="").read()
except OSError:
    sys.exit(2)
lines = text.replace("\r\n", "\n").split("\n")
found = []
def add(line, code, msg): found.append((line, code, msg))
parts = lines[0].split(" ")
version = None
if len(parts) != 3:
    add(1, "H001", "request line must have exactly three parts")
else:
    method, _, version = parts
    if version not in ("HTTP/1.1", "HTTP/1.0"): add(1, "H002", "unsupported version")
    if not re.fullmatch(r"[A-Z]+", method): add(1, "H003", "method must be uppercase letters")
fields = []
for i, l in enumerate(lines[1:], start=2):
    if l == "": break
    if l[0] in " \t":
        add(i, "H009", "obsolete line folding"); continue
    name, sep, value = l.partition(":")
    if name != name.rstrip(" \t"):
        add(i, "H006", "whitespace before colon")
    fields.append((i, name.strip().lower(), value))
hosts = [i for i, n, _ in fields if n == "host"]
if version == "HTTP/1.1" and not hosts: add(1, "H004", "missing Host")
for i in hosts[1:]: add(i, "H005", "duplicate Host")
cl = [i for i, n, _ in fields if n == "content-length"]; te = [i for i, n, _ in fields if n == "transfer-encoding"]
if cl and te: add(max(cl[0], te[0]), "H007", "both Content-Length and Transfer-Encoding")
for i, n, v in fields:
    if n == "content-length" and not re.fullmatch(r"[0-9]+", v.strip()): add(i, "H008", "invalid Content-Length")
found.sort(key=lambda f: (f[0], f[1]))
if js: print(json.dumps([{"line": l, "code": c, "message": m} for l, c, m in found]))
else:
    for l, c, m in found: print(f"{l}:{c}: {m}")
sys.exit(1 if found else 0)
