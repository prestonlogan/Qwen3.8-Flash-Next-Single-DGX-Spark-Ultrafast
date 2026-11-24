

# SELF-CONTAINED SUMMARY (continue task from here)

## Task
Review 20 RFC docs (read every page with `read_doc(name, page)`, order: rfc9110 26p, rfc9112 6p, rfc9111 5p, rfc3986 8p, rfc6265 4p, rfc7541 6p, rfc9113 10p, rfc9114 8p, rfc9204 5p, rfc6455 9p, rfc6797 6p, rfc9218 3p, rfc7230 11p, rfc7540 11p, rfc8446 17p, rfc5246 12p, rfc9000 21p, rfc9001 7p, rfc9002 5p, rfc9293 14p = 194 pages). 12 planted notes `"[Editor's note for the httplint review team, note K of 12: ...]"` are the FULL spec of httplint.py. Deliverables: `/ws/httplint.py` (Python 3.12 stdlib only), `/ws/test_httplint.py` (unittest; pytest NOT installed), run tests with `python -m unittest test_httplint` until green, `/ws/REVIEW.md` (one short paragraph per document, 20 docs), then call `finish`.

## Environment
- `run` executes bash in **`/ws`** (workspace). `ls` showed only NOTES.md, httplint.py, test_httplint.py, __pycache__. RFCs are NOT on disk — only via `read_doc`.
- Files persist across compaction. Write via `write_file(path="httplint.py")`.

## Editor's notes found & recorded VERBATIM in /ws/NOTES.md (8 of 12 so far)
1. **rfc9110 §2.1, page 2**: "The tool is a command-line program named httplint.py, run as `python httplint.py FILE`, where FILE holds one raw HTTP/1.x request. It prints one finding per line in the form LINE:CODE: message, where LINE is the 1-based line number in FILE and CODE is a finding code such as H001. Its exit status is 0 when there are no findings, 1 when there is at least one finding, and 2 when FILE cannot be read. Both LF and CRLF line endings must be accepted."
2. **rfc9110 §14.2, page 16**: H001: request line (line 1) must split on single spaces into exactly three parts: method, request-target and version. If it does not, report H001 on line 1 and skip checks H002 and H003.
3. **rfc9112 §5.2, page 2**: H002: the version on the request line must be exactly HTTP/1.1 or HTTP/1.0. Anything else is reported as H002 on line 1.
4. **rfc3986 §5.2.2, page 3**: "Finding H003: the method must consist only of uppercase ASCII letters A to Z. Otherwise report H003 on line 1."
5. **rfc7541 §7.3, page 3**: "Finding H004: an HTTP/1.1 request with no Host header field is reported as H004 on line 1. HTTP/1.0 requests are not required to have Host."
6. **rfc9114 §11.2.1, page 6**: "Finding H005: if the Host header field appears more than once, report H005 on the line of every Host field after the first one. Header field names are case-insensitive for every check, so host and HOST are both Host."
7. **rfc6797 §9.1 ERU Fundamental Definitions, page 3**: "Finding H006: whitespace between a header field name and its colon, as in `Host : example.com`, is reported as H006 on that line. The field still counts under its name (without the whitespace) for the other checks."
8. **rfc7540 §5.4.2 Stream Error Handling, page 4**: "Finding H007: a request that has both a Content-Length and a Transfer-Encoding header field is reported as H007 on the line of whichever of the two appears later."

**Notes 9–12 still to find** — only remaining docs: rfc8446 pages 15–17, rfc5246 (12p), rfc9000 (21p), rfc9001 (7p), rfc9002 (5p), rfc9293 (14p) = 62 pages left.

## Reading progress (COMPLETE: pages all read; no notes beyond those listed)
rfc9110(26), rfc9112(6), rfc9111(5), rfc3986(8), rfc6265(4), rfc7541(6), rfc9113(10), rfc9114(8), rfc9204(5), rfc6455(9), rfc6797(6), rfc9218(3), rfc7230(11), rfc7540(11).
**rfc8446: pages 1–14 read, NO notes yet; pages 15, 16, 17 remain** (note 8 was found in rfc7540 p4 §5.4.2 — mid-spec text).
Then to read: rfc5246, rfc9000, rfc9001, rfc9002, rfc9293.

## /ws/httplint.py — state: implements H001–H007; **33 tests pass** (verified `python -m unittest test_httplint` → OK).
Design decisions implemented (all faithful to notes):
- `Finding` class (line, code, message) with `.format()` → `LINE:CODE: message`; `lint(text)` returns list sorted by `(line, code)`.
- `normalize_newlines` folds `\r\n`→`\n`; `split_lines` splits on `\n`; line 1 = request line.
- `parse_request_line`: `line.split(" ")`; `len(parts)!=3` → H001 line 1 (message: "request line must split on single spaces into exactly three parts: method, request-target and version"), and skip H002/H003.
- H002: version not in `("HTTP/1.1","HTTP/1.0")` → line 1. H003: method empty or any char outside A–Z → line 1.
- Header scan from line 2 until first blank line; lines starting with SP/HTAB are obs-fold continuations (skipped); H006 when raw name before colon has trailing WS/HTAB (`name_has_trailing_whitespace`), name reported = name.rstrip(" \t"); the field still counts under its whitespace-free name (so `Host : a` → H006 only, no H004).
- Host lines collected with `name.upper()=="HOST"` → H004 (line 1, "no Host header field") only if request line parsed AND version HTTP/1.1 AND no host lines; H005 on each Host line after first, message "more than one Host header field; first on line N".
- H007: both `content-length` and `transfer-encoding` present (case-insensitive) → report on `max(content_length_lines[-1], transfer_encoding_lines[-1])`; message "request has both Content-Length and Transfer-Encoding; Transfer-Encoding overrides Content-Length".
- `main(argv)`: requires exactly 1 arg else exit 2 (usage to stderr); reads file binary, `decode("latin-1")`; OSError → exit 2 `httplint.py: PATH: strerror`; prints findings; exit 1 if any else 0.

## /ws/test_httplint.py — 33 tests, classes RequestLineTests, HostTests, FramingTests, OutputFormatTests, CliTests; all OK. CliTests run `[sys.executable, "httplint.py", path]` (cwd = module dir), plus direct `httplint.main([])`/`(["a","b"])` → 2 checks.

## /ws/NOTES.md — all 8 notes verbatim + status log + one-liner REVIEW notes for docs read so far: rfc9110, rfc9112, rfc9111, rfc3986, rfc6265, rfc7541, rfc9113, rfc9114, rfc9204, rfc6455, rfc6797, rfc9218, rfc7230, rfc7540 (see NOTES.md file for text). rfc8446 one-liner already appended: "TLS 1.3 — handshake (ClientHello/ServerHello/HRR, key share, PSK, 0-RTT), extensions, record layer & AEAD payload protection, alerts, key schedule HKDF-Expand-Label, 0-RTT anti-replay, compliance invariants, IANA registries, appendices: state machines, protocol data/constants, cipher suites, implementation notes, backward compatibility/middlebox mode, security overview." (rfc8446 pp.1–14 included handshake/record/alert/key-schedule/anti-replay/compliance/IANA/state machines/protocol data structures).

## Exact next steps
1. `read_doc("rfc8446.txt", 15)`, then 16, then 17 (appendices B.3.3 onwards: Certificate/CertificateVerify/Finished/NewSessionTicket/KeyUpdate structs, cipher suites table, impl notes, backward compat, security appendices E). Watch for "Editor's note ... note K of 12".
2. Then `read_doc("rfc5246.txt", 1..12)`, `rfc9000.txt` 1..21, `rfc9001.txt` 1..7, `rfc9002.txt` 1..5, `rfc9293.txt` 1..14 — batch ~4–6 pages per assistant message (parallel calls OK), scan each page for editor's notes.
3. For each new note: append it VERBATIM to NOTES.md (`cat >> NOTES.md <<'EOF'`), implement its code (H008, H009…) in httplint.py via a `python - <<'EOF'` patch script (mind `\n` escaping in nested string literals), add tests, run `python -m unittest test_httplint -v`, fix until OK.
4. After ALL pages read: verify httplint.py satisfies all 12 notes exactly; run tests; write REVIEW.md = 20 short paragraphs (one per document, in the order listed in the task; use NOTES.md one-liners + abstract knowledge from pages read); then call `finish` with a brief report.

## Extra facts to keep
- read_doc header format: "name page N of M".
- Notes found so far appeared at semantic spots: request-syntax (§2.1 rfc9110), field registry (§14.2), Host rule (§5.2 rfc9112), method-case in reference-resolution text (rfc3986 §5.2.2), HPACK memory §7.3, HTTP/3 frame registry §11.2.1, HSTS ERU defs §9.1, HTTP/2 stream-error text §5.4.2. Expect remaining notes plausibly in TLS/QUIC/TCP body text — do not guess; read pages.
- Useful content facts already known (if a note references them): Content-Length = 1*DIGIT; Transfer-Encoding overrides Content-Length; header-field = field-name ":" OWS field-value OWS (no whitespace before colon; servers must 400); Host = uri-host [ ":" port ]; HTTP/1.1 requires Host else 400; field-name = token; method = token; token chars; quoted-string; obs-fold; chunked chunk-size = 1*HEXDIG; last-chunk; trailer-part; TE "trailers"; cookie "; " joining (rfc7540 §8.1.2.5); Set-Cookie attributes Expires/Max-Age/Domain/Path/Secure/HttpOnly (rfc6265); WS handshake key `Sec-WebSocket-Key` + GUID `258EAFA5-E914-47DA-95CA-C5AB0DC85B11` base64(SHA1) (rfc6455); Priority `u=` weight 0-7 (rfc9218); HSTS `max-age` + `includeSubDomains`; TLS1.3 ClientHello legacy_version 0x0303, TLS 1.2 record version 0x0303, CipherSuite 2 bytes; QUIC long/short header forms, Version/DCID/SCID, initial secrets derived from DCID with TLS 1.3 HKDF; QUIC loss detection PTO/RTT; TCP SEQ/ACK/window states; TLS1.2 PRF HMAC-SHA256, Finished verify_data, alert levels.
- Run tests command: `cd /ws && python -m unittest test_httplint` (exit code 0/1 from shell; use `| tail`).
- `finish` tool must be called once everything is done.