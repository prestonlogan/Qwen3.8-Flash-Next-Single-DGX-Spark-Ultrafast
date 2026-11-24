# Builds the doc-review corpus: real RFCs (rfc/) with 12 editor's notes planted at fixed points. The notes are the
# requirements for the tool the agent must build. Output: docs/ (read only through the agent's read_doc tool).
import os, textwrap
ORDER = "9110 9112 9111 3986 6265 7541 9113 9114 9204 6455 6797 9218 7230 7540 8446 5246 9000 9001 9002 9293".split()
NOTES = [  # (rfc, fraction of the document, text)
    ("9110", 0.05, "The tool is a command-line program named httplint.py, run as `python httplint.py FILE`, where FILE "
     "holds one raw HTTP/1.x request. It prints one finding per line in the form LINE:CODE: message, where LINE is the "
     "1-based line number in FILE and CODE is a finding code such as H001. Its exit status is 0 when there are no "
     "findings, 1 when there is at least one finding, and 2 when FILE cannot be read. Both LF and CRLF line endings "
     "must be accepted."),
    ("9110", 0.60, "Finding H001: the request line (line 1) must split on single spaces into exactly three parts: "
     "method, request-target and version. If it does not, report H001 on line 1 and skip checks H002 and H003."),
    ("9112", 0.30, "Finding H002: the version on the request line must be exactly HTTP/1.1 or HTTP/1.0. Anything else "
     "is reported as H002 on line 1."),
    ("3986", 0.50, "Finding H003: the method must consist only of uppercase ASCII letters A to Z. Otherwise report H003 "
     "on line 1."),
    ("7541", 0.40, "Finding H004: an HTTP/1.1 request with no Host header field is reported as H004 on line 1. "
     "HTTP/1.0 requests are not required to have Host."),
    ("9114", 0.70, "Finding H005: if the Host header field appears more than once, report H005 on the line of every "
     "Host field after the first one. Header field names are case-insensitive for every check, so host and HOST are "
     "both Host."),
    ("6797", 0.50, "Finding H006: whitespace between a header field name and its colon, as in `Host : example.com`, is "
     "reported as H006 on that line. The field still counts under its name (without the whitespace) for the other "
     "checks."),
    ("7540", 0.30, "Finding H007: a request that has both a Content-Length and a Transfer-Encoding header field is "
     "reported as H007 on the line of whichever of the two appears later."),
    ("5246", 0.60, "Finding H008: a Content-Length value that, after trimming surrounding whitespace, is not a string of "
     "one or more ASCII digits is reported as H008 on that line."),
    ("9000", 0.40, "Finding H009: a header line that begins with a space or a tab (obsolete line folding) is reported "
     "as H009 on that line. Such a line is not a field of its own and is not checked for anything else."),
    ("9002", 0.50, "The header section ends at the first empty line; lines after it are the body and are never checked. "
     "Findings are printed sorted by line number, and by code within the same line."),
    ("9293", 0.80, "With the option --json, as in `python httplint.py --json FILE`, the tool prints instead a single "
     "JSON array of objects with the keys line (an integer), code and message, in the same order as the text output. "
     "Exit statuses are the same as without --json."),
]
os.makedirs("docs", exist_ok=True)
for rfc in ORDER:
    lines = open(f"rfc/rfc{rfc}.txt", encoding="utf-8", errors="replace").read().splitlines()
    inserts = sorted(((frac, text) for r, frac, text in NOTES if r == rfc), reverse=True)
    for frac, text in inserts:
        k = NOTES.index(next(n for n in NOTES if n[0] == rfc and n[1] == frac)) + 1
        at = int(len(lines) * frac)
        while at < len(lines) and lines[at].strip():  # put the note between paragraphs
            at += 1
        note = textwrap.wrap(f"[Editor's note for the httplint review team, note {k} of {len(NOTES)}: {text}]", 69)
        lines[at:at] = [""] + ["   " + l for l in note] + [""]
    open(f"docs/rfc{rfc}.txt", "w").write("\n".join(lines) + "\n")
print(len(ORDER), "docs")
