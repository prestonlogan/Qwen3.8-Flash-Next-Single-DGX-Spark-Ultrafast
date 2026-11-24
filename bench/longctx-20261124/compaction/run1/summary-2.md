

## SUMMARY — compacted state, keep everything needed to continue

### Task
Review 20 RFC documents (194 pages total) via `read_doc(name, page)`, build `httplint.py` in workspace `/ws` (Python 3.12 stdlib only) exactly per 12 planted "[Editor's note for the httplint review team, note K of 12: ...]" notes, write `test_httplint.py` (unittest; pytest NOT installed), run tests via `run` (bash, no network, cwd=/ws), fix failures, write `REVIEW.md` (one short paragraph per document), call `finish`. Tools: `read_doc(name, page)`, `run(command)`, `write_file(path, content)` (paths relative to /ws), `finish()`. Multiple parallel read_doc calls per message is allowed and efficient (issued up to 6 per message so far). Context fills → keep ALL important facts in summaries. Files persist.

### Editor's notes — VERIFIED VERBATIM (5 of 12 found)
- **Note 1** (rfc9110.txt §2.1, page 2): "The tool is a command-line program named httplint.py, run as `python httplint.py FILE`, where FILE holds one raw HTTP/1.x request. It prints one finding per line in the form LINE:CODE: message, where LINE is the 1-based line number in FILE and CODE is a finding code such as H001. Its exit status is 0 when there are no findings, 1 when there is at least one finding, and 2 when FILE cannot be read. Both LF and CRLF line endings must be accepted."
- **Note 2** (rfc9110.txt §14.2, page 16): "H001: the request line (line 1) must split on single spaces into exactly three parts: method, request-target and version. If it does not, report H001 on line 1 and skip checks H002 and H003."
- **Note 3** (rfc9112.txt §5.2, page 2): "H002: the version on the request line must be exactly HTTP/1.1 or HTTP/1.0. Anything else is reported as H002 on line 1."
- **Note 4** (rfc3986.txt §5.2.2 Transform References, page 3): "Finding H003: the method must consist only of uppercase ASCII letters A to Z. Otherwise report H003 on line 1."
- **Note 5** (rfc7541.txt §7.3 Memory Consumption, page 3): "Finding H004: an HTTP/1.1 request with no Host header field is reported as H004 on line 1. HTTP/1.0 requests are not required to have Host."

### Notes 6–12: NOT FOUND YET (7 remaining). Old guessed entries were deleted; trust only actual reads.
Likely future codes: H005… (header syntax, request-target, Host dupes, Content-Length/Transfer-Encoding, etc.) — must be taken verbatim from notes.

### Reading progress (pages read / total)
- rfc9110.txt **26/26 done** (notes 1, 2)
- rfc9112.txt **6/6 done** (note 3 on p2)
- rfc9111.txt **5/5 done** (no notes)
- rfc3986.txt **8/8 done** (note 4 on p3)
- rfc6265.txt **4/4 done** (no notes)
- rfc7541.txt **6/6 done** (note 5 on p3)
- rfc9113.txt **10/10 done** (no notes anywhere)
- **REMAINING, in order: rfc9114(8 pp), rfc9204(5), rfc6455(9), rfc6797(6), rfc9218(3), rfc7230(11), rfc7540(11), rfc8446(17), rfc5246(12), rfc9000(21), rfc9001(7), rfc9002(5), rfc9293(14) = 133 pages.** Next message: read rfc9114 pages 1–8 in parallel, then rfc9204 1–5, rfc6455 1–9 (3 pages/call batches), etc.

### Files in /ws
- `NOTES.md` — contains verified notes 1–5 + one-liners for rfc9110, rfc9112, rfc9111, rfc3986, rfc6265, rfc7541 (HPACK). Keep appending new notes verbatim + one-liners as they are read.
- Not yet written: `httplint.py`, `test_httplint.py`, `REVIEW.md`.

### httplint.py spec (assembled so far; implement exactly)
- CLI: `python httplint.py FILE`. FILE = one raw HTTP/1.x request. Print one finding per line as `LINE:CODE: message` (LINE = 1-based line number in FILE). Exit 0 = no findings; 1 = ≥1 finding; 2 = FILE cannot be read (missing/unreadable). Accept both LF and CRLF endings (a lone CR must not create a phony line; handle \r\n by stripping trailing \r; also count lines by LF, with CR-only not a terminator — note both LF and CRLF accepted).
- H001 (line 1): request line must split on single spaces (`line.split(' ')`) into exactly 3 parts (method, request-target, version) — no leading/trailing/double spaces. Report on line 1; if H001 fires, **skip H002 and H003**.
- H002 (line 1): version must be exactly `HTTP/1.1` or `HTTP/1.0` (case-sensitive).
- H003 (line 1): method must be non-empty and consist only of ASCII letters A–Z (uppercase).
- H004 (line 1): if version is HTTP/1.1 and no `Host` header field present in the header section (case-insensitive name), report on line 1. HTTP/1.0 exempt. Multiple Host values / duplicate Host likely a separate note (rfc9110 §7.2 says server must 400 on >1 Host or invalid Host value — plausible source of a future note).
- Likely later checks (from rfc9112 §5): field-line syntax `field-name ":" OWS field-value OWS`; field-name must be a token (tchar = `!#$%&'()*+-.^_`|~` DIGIT ALPHA; no whitespace before colon); field value must not contain CR/LF/NUL; obs-fold (line starting with SP/HTAB) deprecated; Content-Length = 1*DIGIT; Transfer-Encoding overrides Content-Length. Do NOT invent codes — only implement exactly what notes say.

### Useful reference facts (for REVIEW.md + cross-checks)
- rfc9112 ABNF: `request-line = method SP request-target SP HTTP-version`; `HTTP-version = HTTP-name "/" DIGIT "." DIGIT`; `field-line = field-name ":" OWS field-value OWS`; `obs-fold = OWS CRLF RWS`; `HTTP-message = start-line CRLF *(field-line CRLF) CRLF [message-body]`; chunked-body `chunk-size = 1*HEXDIG`, `last-chunk = 1*("0") [chunk-ext] CRLF`. §2.2: recipient MAY accept bare LF; sender MUST NOT generate bare CR; server SHOULD ignore at least one leading empty CRLF before request-line; sender MUST NOT send whitespace between start-line and first header field. §6.1 Content-Length/Transfer-Encoding ambiguity → smuggling risk.
- rfc9110: field-name=token; OWS/RWS = SP/HTAB; no whitespace allowed in request-target; CR/LF/NUL in field value invalid; Content-Length = 1*DIGIT; Transfer-Encoding overrides Content-Length; Host requirements (400 if missing/duplicate/invalid for HTTP/1.1).
- Review one-liners collected: rfc9110=HTTP Semantics (architecture, syntax, methods, status codes, content negotiation, conditionals, ranges, auth, registries); rfc9112=HTTP/1.1 messaging syntax/parsing/framing/connection mgmt/smuggling; rfc9111=caching (freshness, age, validation, Vary, Age/Cache-Control/Expires); rfc3986=URI generic syntax (components, percent-encoding, resolution, dot-segments, normalization); rfc6265=Cookie/Set-Cookie state management; rfc7541=HPACK (static/dynamic tables, indexed/literal/never-indexed representations, integer/string encodings, Huffman, CRIME mitigation); rfc9113=HTTP/2 (frames, streams, flow control, HPACK use, pseudo-headers, field validity lowercase rule, push, CONNECT, TLS constraints).

### Exact next step
1. `read_doc("rfc9114.txt", 1..8)` (8 parallel calls ok), then rfc9204 1–5, rfc6455 1–9, rfc6797 1–6, rfc9218 1–3, rfc7230 1–11, rfc7540 1–11, rfc8446 1–17, rfc5246 1–12, rfc9000 1–21, rfc9001 1–7, rfc9002 1–5, rfc9293 1–14. Check every page for `[Editor's note for the httplint review team, note K of 12:` and record VERBATIM into NOTES.md (append) as found; also append a short REVIEW.md one-liner per doc.
2. After all notes found (should be 12 by the end of rfc9293): write `/ws/httplint.py` (stdlib only: sys, os; parse lines by splitting on '\n' preserving '\r'; header/body split at first empty line; implement H001–H00x exactly per notes, in the order/dedup logic notes specify), `/ws/test_httplint.py` with unittest (subprocess to run CLI, tmp files, exit codes 0/1/2, LF & CRLF, each code trigger + skip logic), run `python3 -m unittest test_httplint -v` in /ws, fix until green, write `/ws/REVIEW.md` (one paragraph per each of the 20 documents), then `finish`.