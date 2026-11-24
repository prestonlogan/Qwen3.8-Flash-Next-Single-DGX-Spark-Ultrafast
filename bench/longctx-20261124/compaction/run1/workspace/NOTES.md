# httplint spec notes — VERBATIM from editor's notes planted in RFCs

## Note 1 (rfc9110.txt §2.1, file page 2) — VERIFIED
"The tool is a command-line program named httplint.py, run as `python httplint.py FILE`, where FILE
holds one raw HTTP/1.x request. It prints one finding per line in the form LINE:CODE: message, where
LINE is the 1-based line number in FILE and CODE is a finding code such as H001. Its exit status is
0 when there are no findings, 1 when there is at least one finding, and 2 when FILE cannot be read.
Both LF and CRLF line endings must be accepted."

## Note 2 (rfc9110.txt §14.2, file page 16) — VERIFIED
H001: the request line (line 1) must split on single spaces into exactly three parts: method,
request-target and version. If it does not, report H001 on line 1 and skip checks H002 and H003.

## Note 3 (rfc9112.txt §5.2, file page 2) — VERIFIED
H002: the version on the request line must be exactly HTTP/1.1 or HTTP/1.0. Anything else is
reported as H002 on line 1.

## Note 4 (rfc3986.txt §5.2.2 Transform References, file page 3) — VERIFIED VERBATIM
"Finding H003: the method must consist only of uppercase ASCII letters A to Z. Otherwise report
H003 on line 1."

## Note 5 (rfc7541.txt §7.3 Memory Consumption, file page 3) — VERIFIED VERBATIM
"Finding H004: an HTTP/1.1 request with no Host header field is reported as H004 on line 1.
HTTP/1.0 requests are not required to have Host."

=> Findings so far: H001 (request-line split into exactly 3 single-space parts, line 1; if fail skip
   H002 & H003), H002 (version == HTTP/1.1 or HTTP/1.0, line 1), H003 (method only uppercase A-Z,
   line 1), H004 (HTTP/1.1 requires a Host header field; missing -> report on line 1; HTTP/1.0 exempt).

## Notes 6-12: NOT YET READ (to be recorded verbatim)
Remaining docs: rfc9113(10), rfc9114(8), rfc9204(5), rfc6455(9), rfc6797(6), rfc9218(3),
rfc7230(11), rfc7540(11), rfc8446(17), rfc5246(12), rfc9000(21), rfc9001(7), rfc9002(5), rfc9293(14).

## One-liners so far (for REVIEW.md)
- rfc9110 HTTP Semantics: architecture, terminology, universal syntax/methods/status codes, content
  negotiation, conditionals, range requests, auth framework, field registries, security.
- rfc9112 HTTP/1.1: message syntax/parsing, request & status lines, field syntax, obs-fold, body
  framing (Content-Length/chunked/trailers), connection management & persistence, TLS origin channels,
  media types message/http & application/http, request smuggling/response splitting.
- rfc9111 HTTP Caching: stores/reuses responses, Vary, freshness & age, serving stale, validation
  (304), invalidation, Age/Cache-Control/Expires/Pragma/Warning.
- rfc3986 URI Generic Syntax: scheme/authority/path/query/fragment, percent-encoding, reserved vs
  unreserved, relative references + resolution algorithm (dot-segment removal), normalization/comparison.
- rfc6265 HTTP State Management Mechanism: Cookie & Set-Cookie syntax/semantics, well-behaved server
  profile vs liberal UA parsing, attributes (Expires/Max-Age/Domain/Path/Secure/HttpOnly), storage
  model, cookie matching/发送 order, limits, security (ambient authority, weak integrity).
- rfc7541 HPACK: header compression for HTTP/2 — static & dynamic tables, index address space,
  indexed/literal (with/without indexing, never-indexed) representations, integer & string literal
  encodings, Huffman table, dynamic table size updates, eviction, CRIME-style probing security.

---

### Note 6 (rfc9114.txt, §11.2.1 Frame Types registry, page 6) — VERBATIM
"Finding H005: if the Host header field appears more than once, report H005 on the line of every Host field after the first one. Header field names are case-insensitive for every check, so host and HOST are both Host."

## REVIEW notes so far
- rfc9110 HTTP Semantics: architecture, message syntax, methods, status codes, content handling, conditionals, range, auth, caching/cookies cross-refs, field registry.
- rfc9112 HTTP/1.1: message syntax, parsing, connection management, Content-Length/Transfer-Encoding framing, request smuggling.
- rfc9111 HTTP Caching: freshness, age calculation, validation, Cache-Control/Age/Expires/Vary.
- rfc3986 URI Generic Syntax: components, scheme/authority/path/query/fragment, percent-encoding, reference resolution, dot-segment removal, normalization.
- rfc6265 HTTP State Management Mechanism: Set-Cookie/Cookie, attribute parsing, domain/path matching, security (HttpOnly/Secure/SameSite-ish).
- rfc7541 HPACK: header compression, integer & string encodings, static/dynamic tables, indexing modes, Huffman, CRIME/BREACH mitigations.
- rfc9113 HTTP/2: binary framing, streams, flow control, HPACK usage, pseudo-headers, field validity (lowercase names), push, CONNECT, TLS constraints.
- rfc9114 HTTP/3: mapping over QUIC, streams, frames (DATA/HEADERS/SETTINGS/GOAWAY/PUSH_PROMISE/MAX_PUSH_ID/CANCEL_PUSH), QPACK, error codes, HTTP/2->HTTP/3 mapping appendix.
- rfc9204 QPACK: field compression for HTTP/3; static/dynamic tables, prefixed integers, string literals, encoder/decoder streams & instructions, field line representations, blocked streams, error codes.
- rfc6455 WebSocket Protocol: HTTP Upgrade handshake (Sec-WebSocket-Key/Accept/Version), client & server requirements, data framing, masking, fragmentation, control frames, close codes, registries.

### Note 7 (rfc6797.txt, §9.1 ERU Fundamental Definitions, page 3 of 6) — VERBATIM
"Finding H006: whitespace between a header field name and its colon, as in `Host : example.com`, is reported as H006 on that line. The field still counts under its name (without the whitespace) for the other checks."

## REVIEW notes so far
- rfc6797 HSTS: Strict-Transport-Security header field syntax (max-age, includeSubDomains), server & UA processing models, known-HSTS-host domain matching, effective request URI, security considerations.

## Status check (after reading rfc6797 p6 and rfc7230 p7-11)
- rfc6797 COMPLETE (6 pages; only note 7 = H006 on p3).
- rfc7230 COMPLETE (11 pages; NO note found in p7-p11: routing 5.7, connection mgmt 6,
  upgrade 6.7, #rule 7, IANA 8, security 9, acks/refs/appendices ABNF/index).
- rfc7230 one-liner for REVIEW.md: RFC 7230 HTTP/1.1 Message Syntax and Routing (obsoleted
  by RFC 9110/9112): core ABNF (CR/LF/SP/HTAB/obs-text), message format, parsing rules,
  methods/status codes cross-ref, field syntax, transfer codings & chunked, message body
  length, request-target forms, Host, effective request URI, Via/transformations, connection
  management (persistent connections, pipelining, tear-down, Upgrade), #rule list extension,
  IANA registries, security (response splitting, request smuggling), full collected ABNF.
- Implementation: httplint.py + test_httplint.py written in /ws; 28 tests pass (python -m
  unittest test_httplint). Working dir for run is /ws.
- Remaining notes 8-12 live in: rfc7540(11), rfc8446(17), rfc5246(12), rfc9000(21),
  rfc9001(7), rfc9002(5), rfc9293(14) = 87 pages to read. Expect codes H007+.

## rfc7540 read so far: pages 1-8 (no note yet). Pages 9-11 remain.
- rfc7540 one-liner for REVIEW.md: HTTP/2 — connection preface, frame format/size, streams &
  state machine, flow control (WINDOW_UPDATE), priority dependency tree, frame types DATA/HEADERS/
  PRIORITY/RST_STREAM/SETTINGS/PUSH_PROMISE/PING/GOAWAY/WINDOW_UPDATE/CONTINUATION, error codes,
  HTTP mapping (pseudo-headers, lowercase names, malformed messages, Cookie splitting, CONNECT,
  server push), connection reuse / 421, TLS 1.2 constraints, cipher-suite black list appendix.

## rfc7540 COMPLETE (11 pages; note 8 on page 4 = §5.4.2). No notes in pages 1-3, 5-11.

### Note 8 (rfc7540.txt, §5.4.2 Stream Error Handling, page 4 of 11) — VERBATIM
"Finding H007: a request that has both a Content-Length and a Transfer-Encoding header field is reported as H007 on the line of whichever of the two appears later."

## Notes 9-12: NOT YET READ
Remaining docs: rfc8446(17), rfc5246(12), rfc9000(21), rfc9001(7), rfc9002(5), rfc9293(14) = 76 pages.

## rfc8446 (TLS 1.3) read pages 1-13, NO notes yet. Pages 14-17 remain.
- rfc8446 one-liner for REVIEW.md: TLS 1.3 — handshake (ClientHello/ServerHello/HRR, key share,
  PSK, 0-RTT), extensions (supported_versions, cookie, sigalgs, key_share, pre_shared_key,
  early_data...), record layer & AEAD payload protection, alerts, key schedule HKDF-Expand-Label,
  0-RTT anti-replay (single-use tickets, CHR, freshness), compliance invariants, IANA registries,
  appendices: state machines, protocol data/constants, cipher suites, implementation notes,
  backward compatibility/middlebox mode, security-properties overview.

## Note 9 of 12 — found in rfc5246.txt page 7 (§7.4.9 Finished):
"[Editor's note for the httplint review team, note 9 of 12: Finding
   H008: a Content-Length value that, after trimming surrounding
   whitespace, is not a string of one or more ASCII digits is reported
   as H008 on that line.]"

## Note 10 of 12 — found in rfc9000.txt page 9 (§10.3 Stateless Reset):
"[Editor's note for the httplint review team, note 10 of 12: Finding
   H009: a header line that begins with a space or a tab (obsolete line
   folding) is reported as H009 on that line. Such a line is not a field
   of its own and is not checked for anything else.]"

## Note 11 of 12 — found in rfc9293.txt page 2 (TCP, §5.2 Sequence Number Arithmetic):
"[Editor's note for the httplint review team, note 11 of 12: Finding
   H010: a header line that contains no colon at all, or whose name part
   before the colon is empty, is reported as H010 on that line. A line
   with no colon is never treated as obsolete line folding, even if it
   begins with whitespace.]"

Status: notes 1-11 found (H001..H010). Note 12 (H011?) NOT yet found.
Docs fully read this session with no note: rfc6797(6), rfc7540(11), rfc5246(12).
Docs read earlier but claims UNRELIABLE: rfc9001, rfc9002, rfc9293(rest), rfc9113, rfc9114, rfc9204, rfc6455, rfc9218, rfc7230, rfc8446, rfc9110, rfc9112, rfc9111, rfc3986, rfc6265, rfc7541.

## Notes 9 and 10 (recovered from earlier context; verbatim wording as captured)
Note 9 (rfc5246.txt, §7.4.9 Finished, page 7):
"H008: a Content-Length value that, after trimming surrounding whitespace, is not a string of one or more ASCII digits is reported as H008 on that line."
Note 10 (rfc9000.txt, §10.3 Stateless Reset, page 9):
"H009: a header line that begins with a space or a tab (obsolete line folding) is reported as H009 on that line. Such a line is not a field of its own and is not checked for anything else."

## Code map so far (H001..H010)
H001 request line must split on single spaces into exactly 3 parts (line 1; if fired, skip H002+H003)
H002 version exactly HTTP/1.1 or HTTP/1.0 (line 1)
H003 method only uppercase ASCII A-Z (line 1)
H004 HTTP/1.1 request with no Host header field (line 1; HTTP/1.0 exempt)
H005 Host appears more than once -> on the line of every Host after the first
H006 whitespace between a field name and its colon -> on that line (field still counts by its name)
H007 both Content-Length and Transfer-Encoding -> on the line of whichever appears later
H008 Content-Length value, after trimming surrounding whitespace, not [0-9]+ -> on that line
H009 header line beginning with SP or HTAB (obsolete line folding) -> on that line; not a field, not checked for anything else
H010 header line with no colon at all, or empty name part before the colon -> on that line;
     a line with no colon is NEVER treated as obsolete line folding, even if it begins with whitespace

## Note 12 of 12 — found in rfc9293.txt page 10 (in §8.1 Normative References):
"[Editor's note for the httplint review team, note 12 of 12: With the option --json, as in
 `python httplint.py --json FILE`, the tool prints instead a single JSON array of objects with the
 keys line (an integer), code and message, in the same order as the text output. Exit statuses are
 the same as without --json.]"

## NOTE COUNT: all 12 notes now located!
Mapping: note 1 = CLI/output-format/exit codes; notes 2..11 = findings H001..H010; note 12 = --json.

## FINAL VERBATIM LOCATION TABLE (all 12 confirmed by reading the page itself)
| # | doc | page | section | content |
|---|-----|------|---------|---------|
| 1 | rfc9110 | 2 | 2.1 HTTP Layering area (prose after "HTTP/1.1 message syntax") | CLI `python httplint.py FILE`, output `LINE:CODE: message`, exit 0/1/2, LF and CRLF both accepted |
| 2 | rfc9110 | 16 | 14.2 Range | H001 request line splits on single spaces into exactly 3 parts; else H001 on line 1, skip H002/H003 |
| 3 | rfc9112 | 2 | 5.2 Obsolete Line Folding | H002 version exactly HTTP/1.1 or HTTP/1.0, else H002 on line 1 |
| 4 | rfc3986 | 3 | 5.2.2 Transform References | H003 method only uppercase ASCII A-Z, else H003 on line 1 |
| 5 | rfc7541 | 3 | 7.3 Memory Consumption | H004 HTTP/1.1 request with no Host -> H004 on line 1; HTTP/1.0 exempt |
| 6 | rfc9114 | 6 | 11.2.1 Frame Types | H005 Host more than once -> H005 on every Host line after the first; names case-insensitive |
| 7 | rfc6797 | 3 | 9.1 Fundamental Definitions | H006 whitespace between name and colon -> H006 on that line; field still counted by name w/o whitespace |
| 8 | rfc7540 | 4 | 5.4.2 Stream Error Handling | H007 both Content-Length and Transfer-Encoding -> H007 on the later of the two lines |
| 9 | rfc5246 | 7 | 7.4.9 Finished | H008 Content-Length value not 1+ ASCII digits after trimming whitespace -> H008 on that line |
| 10 | rfc9000 | 9 | 10.3 Stateless Reset | H009 line begins SP/HTAB (obs-fold) -> H009 on that line; not a field, not checked for anything else |
| 11 | rfc9293 | 2 | 5.2 Sequence Number Arithmetic | H010 line has no colon, or empty name before colon -> H010 on that line; no-colon line never obs-fold even with leading whitespace |
| 12 | rfc9293 | 10 | 8.1 Normative References | --json prints single JSON array of objects keys line (integer), code, message, same order; exit statuses unchanged |
