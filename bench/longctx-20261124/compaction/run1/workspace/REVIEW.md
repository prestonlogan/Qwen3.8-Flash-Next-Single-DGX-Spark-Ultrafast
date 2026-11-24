# REVIEW — documentation set behind `httplint.py`

The twenty documents were read page by page (194 pages, in the order below). The
twelve planted editor's notes are the complete specification of `httplint.py`;
their verbatim text and verified locations are in `NOTES.md`, the implementation
is `httplint.py` and the 89 unit tests in `test_httplint.py` all pass.

Every note location was confirmed by reading the page that contains it, so the
"Where each note sits" table at the end is authoritative; the paragraph for each
document names only the note(s) that actually sit in it.

## rfc9110.txt — HTTP Semantics (STD 97, 26 pages)
The version-independent core of HTTP: architecture and terminology (resources,
representations, user agents, origin servers, intermediaries, gateways,
proxies), universal syntax (ABNF conventions, character encoding, the
`#rule` list extension, field-line and field-value syntax and combination
rules), the method definitions (GET, HEAD, POST, PUT, DELETE, CONNECT,
OPTIONS, TRACE) and their idempotency/safe properties, the status-code classes
and codes, content handling (media types, content codings, content
negotiation), conditional requests and ETags, range requests (byte ranges,
206/416), the cookie/set-cookie cross-references, the authentication framework
(challenges, credentials, realms), the IANA registries for methods, status
codes and fields, and the long security-considerations section on authority
establishment, ambient authority, cross-origin requests, request smuggling,
fragment-privacy and field-name confusion.
Notes: 1 (the CLI contract — `python httplint.py FILE`, `LINE:CODE: message`
output, exit 0/1/2, LF and CRLF both accepted) in §2.1 on page 2; 2 (H001: the
request line must split on single spaces into exactly three parts, and on
failure H002/H003 are skipped) in §14.2 on page 16.

## rfc9112.txt — HTTP/1.1 (6 pages)
The message syntax and connection management of HTTP/1.x: request-line and
request-target forms (origin, absolute, authority, asterisk) and target-URI
reconstruction, the status line, field-line syntax with OWS and the explicit
prohibition on whitespace between a field name and its colon, obsolete line
folding (`obs-fold`) and the MUST-level requirements for rejecting or
unfolding it, message-body framing by `Content-Length` versus
`Transfer-Encoding`/`chunked` (including `Trailer` and the rule that
`Transfer-Encoding` overrides `Content-Length`), connection management
(persistent connections, pipelining, `Connection`, `Keep-Alive`, `Upgrade`),
TLS origin channels, the `message/http` and `application/http` media types,
and the request-smuggling/response-splitting security analysis of
inconsistent framing.
Note: 3 (H002: the version must be exactly `HTTP/1.1` or `HTTP/1.0`) in §5.2
on page 2.

## rfc9111.txt — HTTP Caching (STD 98, 5 pages)
How caches store, reuse, invalidate and validate responses: cache
architecture and the age model (Apparent-Age calculation, `Age`, freshness
lifetime with `max-age`/`Expires`/heuristic freshness, staleness), the
`Cache-Control` response and request directives (`no-cache`, `no-store`,
`max-age`, `must-revalidate`, `public`/`private`, `no-transform`,
`immutable`, `stale-while-revalidate`), serving stale and `Warning`,
invalidation and store invalidation, the construction of cache keys and the
`Vary` header, validation with `ETag`/`Last-Modified`/`If-None-Match`/
`If-Modified-Since` producing 304 or 200, stale responses, the
`Cache-Control` interaction with cookies and authorization, and the security
considerations for shared caches, cache-key poisoning and side channels.
No editor's note.

## rfc3986.txt — URI Generic Syntax (8 pages)
The generic syntax shared by URIs and relative references: scheme, authority
(userinfo, host as IP-literal/IPv4/registered name, port), path, query and
fragment components; reserved versus unreserved characters and
percent-encoding; the forms of URI-reference, absolute-URI and
same-document/suffix references; the base-URI establishment rules; the
step-by-step reference-resolution algorithm (pre-parse base, transform
references, remove dot-segments, recompose); syntax-based normalization and
URI comparison; and the security considerations on fragment/confusion attacks,
insufficient entropy, malicious/look-alike URIs and cross-site scripting.
Note: 4 (H003: the method must consist only of uppercase ASCII letters A–Z,
otherwise report it on line 1) inside §5.2.2 on page 3.

## rfc6265.txt — HTTP State Management Mechanism (4 pages)
The cookie protocol: `Set-Cookie` and `Cookie` syntax and semantics, the
well-behaved-server profile versus the liberal user-agent parsing profile,
the `Expires`, `Max-Age`, `Domain`, `Path`, `Secure` and `HttpOnly`
attributes, the cookie store and canonical-vhost rules, the domain-match and
path-match algorithms used to decide which cookies to send and in what order,
the per-domain/per-path limits and eviction, the `Cookie2`/`Set-Cookie2`
obsolescence, and the security analysis of ambient authority (CSRF), session
fixation, clear-text transmission, weak confidentiality and integrity,
cross-domain access and DNS reliance.
No editor's note.

## rfc7541.txt — HPACK: Field Compression for HTTP/2 (6 pages)
Header compression for HTTP/2 and its reuse by other protocols: the index
address space spanning the dynamic table and the static table of Appendix A,
the four field representations (indexed, literal with incremental indexing,
literal never indexed, literal without indexing), the prefixed-integer and
string-literal encodings with the Huffman code table of Appendix B, dynamic
table size changes and eviction, the decoding algorithms and the
encoder/decoder context requirements, the security considerations around
compression of secret data (CRIME/PETAL-style probing) and their mitigations
(never-indexed literals, high-entropy values, penalty of insertion), and the
`Content-Length`/`Host` handling rules for intermediaries.
Note: 5 (H004: an HTTP/1.1 request with no `Host` field is reported on line 1;
HTTP/1.0 is exempt) in §7.3 on page 3.

## rfc9113.txt — HTTP/2 (10 pages)
The binary framing layer: the client connection preface and the
SETTINGS/`SETTINGS_NO_RFC7540_PRIORITIES` parameters, the nine-octet frame
header and frame sizes, stream identifiers and the stream state machine,
connection- and stream-level flow control with `WINDOW_UPDATE`, the
deprecated priority tree and the PRIORITY frame, the frames DATA, HEADERS,
PRIORITY, RST_STREAM, SETTINGS, PUSH_PROMISE, PING, GOAWAY, WINDOW_UPDATE and
CONTINUATION, the error codes (PROTOCOL_ERROR, INTERNAL_ERROR, ENHANCE_YOUR_CALM,
...), the HTTP mapping with pseudo-headers (`:method`, `:path`, `:scheme`,
`:authority`), the requirement that field names be lower case, that no
connection-specific or uppercase field appear, that `TE` only be `trailers`
and that `:authority` replace `Host`, `Cookie` splitting, `MAX_CONCURRENT_STREAMS`,
`MAX_FRAME_SIZE`, server push and `PUSH_PROMISE`/`CANCEL_PUSH`, CONNECT and
extended CONNECT, HTTP/1.1 intermediation, `421 Misdirected Request`, and the
TLS requirements inherited from RFC 7540.
No editor's note.

## rfc9114.txt — HTTP/3 (8 pages)
HTTP semantics over QUIC: one request per client-initiated bidirectional
stream, the unidirectional control, push and QPACK encoder/decoder streams,
the control stream frames (SETTINGS with `MAX_FIELD_SECTION_SIZE`, PING,
GOAWAY with the push-ID range, MAX_PUSH_ID, reserved types), the DATA, HEADERS
and PUSH_PROMISE frames with their QPACK-encoded field sections, `CANCEL_PUSH`
and `RESET_STREAM`/`STOP_SENDING`, the `H3_*` error-code registry, the QPACK
usage requirements and stream ordering, priority handling via RFC 9218, the
`Alt-Svc`/`h3` advertisement, connection reuse and connection migration, the
mapping from HTTP/2 and HTTP/1.1, and the security considerations on padding,
compression (BREACH), early data/replay, migration and privacy.
Note: 6 (H005: every `Host` field after the first is reported on its own line;
names are case-insensitive for every check) in §11.2.1 on page 6.

## rfc9204.txt — QPACK: Field Compression for HTTP/3 (5 pages)
Field compression for HTTP/3: a dedicated encoder stream and decoder stream
per connection plus the client-initiated streams, the static table of 99
entries, the field-line representations (indexed with a base index and
post-base indexing, literal with name reference, name-only, and full literal),
the prefixed integers and string literals that HPACK uses, the insertion count
and delta-base encodings with modulo arithmetic and wrap-bit handling, the
encoder instructions (Insert With Name Literal, Insert With Name Reference,
Duplicate, Section Ack, Stream Section Insert Count Increment, Stream Section
Delta Base) and decoder instructions (Section Ack, Increment, Duplicate),
dynamic table capacity updates and eviction, blocked streams with the
field-section prefix carrying Required Insert Count and Delta Base, the
`SETTINGS_QPACK_MAX_TABLE_CAPACITY` and `SETTINGS_QPACK_BLOCKED_STREAMS`
settings, the per-stream blocking behaviour, and the security/efficiency
differences from HPACK (encoder-stream dependency and latency).
No editor's note.

## rfc6455.txt — The WebSocket Protocol (9 pages)
Long-lived bidirectional messaging over a single TCP connection opened by an
HTTP/1.1 upgrade: the opening handshake with `Upgrade: websocket`,
`Connection: Upgrade`, `Sec-WebSocket-Key` (base64 of a 16-byte nonce),
`Sec-WebSocket-Version: 13`, optional `Sec-WebSocket-Protocol` and
`Sec-WebSocket-Extensions` and `Origin`, and the server's `101 Switching
Protocols` with `Sec-WebSocket-Accept` computed as base64(SHA-1(key +
258EAFA5-E914-47DA-95CA-C5AB0DC85B11)); the request and response processing
model and its `WebSocket` interface; the framing of messages with FIN/RSV
bits and opcodes (continuation, text, binary, close, ping, pong) and the 7-,
16- and 64-bit extended payload lengths; mandatory client-to-server masking
and its unmasking procedure and rationale; control-frame rules (payload limit,
no fragmentation, must not be reserved opcodes); the close handshake with
status codes 1000–1015 and the reserved ranges; UTF-8 validation of text
messages; extension negotiation with `permessage-deflate`-style framing; and
the security considerations (masking as defence against cache poisoning and
non-HTTP tunnels, `Sec-WebSocket-Location`, SHA-1 in the handshake,
cross-origin and `Origin` checks, Denial of Service from `Sec-WebSocket-Protocol`).
No editor's note.

## rfc6797.txt — HTTP Strict Transport Security (6 pages)
The `Strict-Transport-Security` response header field: the `max-age` directive
in seconds as the expiry delta, `includeSubDomains`, the host-only policy and
the "known HSTS host" model (an explicit host name plus its subdomains), the
effective request URI and the upgrade of an `http` request URI to `https` and
of the default port to `443`, the requirements on servers (send the field on
`https` responses with a long `max-age`, include it in `http` responses, do
not add it as a request header), user-agent behaviour (no redirect-following
over `http`, no mixed-content downgrade, error handling on certificate
failure, interaction with caching and cookie `Secure` scope, no user bypass)
and the preload/registration considerations, and the security analysis of
downgrade, stripping and passive MITM attacks versus the residual risks of
first-connection and trust-anchor compromise.
Note: 7 (H006: whitespace between a field name and its colon is reported on
that line, while the field still counts under its name stripped of that
whitespace) in §9.1 on page 3.

## rfc9218.txt — Extensible Prioritization Scheme for HTTP (3 pages)
A replacement for the RFC 7540 priority tree: the `Priority` header field as a
Structured-Fields Dictionary of parameters, with `u` (urgency, integer 0–7,
default 3) and `i` (incremental, boolean, default false), unknown parameters
ignored, per message and per request-connection; the end-to-end semantics of
the header versus the hop-by-hop `PRIORITY_UPDATE` frame (HTTP/2 frame type
`0x10`, HTTP/3 frame type `0xF0700` carried on the control stream, with the
Target Stream ID and the Field Section); the `SETTINGS_NO_RFC7540_PRIORITIES`
setting for disabling the legacy tree; merging rules (a response value
overrides the request's, omission means "use the default" in a request and
"no change" in a response), retransmission and 100-Continue handling; client
and server scheduling guidance (non-incremental streams share a scheduler,
incremental ones follow their predecessors, order by stream ID, CONNECT and
push considerations, intermediaries and coalescing, back-end proxies); and the
IANA registrations for the header field, the setting and the frame type.
No editor's note.

## rfc7230.txt — HTTP/1.1 Message Syntax and Routing (11 pages; obsoleted by RFC 9110/9112)
The historic specification of the same message layer: the core ABNF (CR, LF,
SP, HTAB, VCHAR, obs-text, OCTET, `rule-list`/`#rule` list extension), the
message format and its parsing algorithm (no sentinel, `obs-fold` handling),
the generic grammar for methods and status codes, field syntax with the
historical `RFC 2616` whitespace allowance, transfer codings and `chunked`
with the `TE`/`Transfer-Encoding` rules and trailers, message-body length
determination and its `Content-Length` pitfalls, request-target forms and
`Host` and the effective request URI, `Via` and message transformations,
connection management (persistent connections, pipelining and its ordering
requirements, `Connection`, `Upgrade`), the IANA registries for header fields
and transfer codings, the security considerations on response splitting and
request smuggling, and the appendices with the collected ABNF and an index.
No editor's note.

## rfc7540.txt — HTTP/2 (the original, 11 pages; obsoleted by RFC 9113)
The first Standards Track HTTP/2: the connection preface `PRI * HTTP/2.0\r\n\r\nSM\r\n\r\n`,
the nine-octet frame header and frame size limits, stream identifiers and the
idle/reserved/open/half-closed/closed state machine, connection and stream
flow control with `WINDOW_UPDATE` and the 65535 initial window, the priority
tree with dependency, weight and exclusive bit and its reprioritization and
state-management rules, error handling split into connection and stream errors
with `GOAWAY`/`RST_STREAM` and the full error-code list, the frames DATA,
HEADERS, PRIORITY, RST_STREAM, SETTINGS, PUSH_PROMISE, PING, GOAWAY,
WINDOW_UPDATE and CONTINUATION with their flags, HPACK use and header-block
fragmentation, the HTTP mapping with pseudo-headers, lower-case field names,
forbidden connection-specific fields, `TE: trailers`, `Cookie` splitting,
server push and its authorization checks, `CONNECT`, `421`-style
connection reuse concerns, TLS 1.2 deployment constraints and the Appendix A
cipher-suite black list (RC4, 3DES, export, NULL, CBC-mode-only, `*_ECDSA_NULL_ECDHE`
etc.) and Appendix B backward-compatibility notes.
Note: 8 (H007: a request with both `Content-Length` and `Transfer-Encoding` is
reported on the line of whichever of the two appears later) in §5.4.2 on
page 4.

## rfc8446.txt — TLS 1.3 (17 pages)
The current TLS: the 1-RTT full handshake and 0-RTT, the ClientHello/ServerHello
exchange with `supported_versions`, `signature_algorithms`, `key_share`,
`pre_shared_key`, `cookie`/HelloRetryRequest and the PSK modes, `early_data`,
`psk_key_exchange_modes`, `supported_groups` and the rest of the extension
registry; the key schedule built from HKDF-Expand-Label/Derive-Secret with
early, handshake and application traffic secrets and `exporter`; AEAD-only
record protection with per-record nonces, `KeyUpdate`, `EncryptedExtensions`,
`Certificate`/`CertificateRequest`/`CertificateVerify` over the transcript and
`Finished` verified over the transcript hash; the alert protocol and
`error: alert(133)`-style mappings; session tickets and the anti-replay
rules (single-use tickets, freshness via `ticket_age_add`, `max_early_data_size`,
`end_of_early_data`); the five cipher suites
(TLS_AES_128_GCM_SHA256, TLS_AES_256_GCM_SHA384, TLS_CHACHA20_POLY1305_SHA256,
TLS_AES_128_CCM, TLS_AES_128_CCM_8); the compliance invariants and "must not"
list; the IANA registries; the client/server state machines, protocol data
and constants, cipher-suite and handshake transcript tables in the appendices;
the TLS 1.2 compatibility/middlebox mode with the downgrade sentinel; and the
security-properties and implementation-considerations appendices (forward
secrecy, 0-RTT replay, PSK binding, `KeyUpdate` limits, cookie/privacy,
downgrade and middlebox risks, denial-of-service via handshake amplification).
No editor's note.

## rfc5246.txt — TLS 1.2 (12 pages)
The previous TLS version: the TLS presentation language (integers, opaque
vectors, `select`/`case`, `digitally-signed` structs, the cipher-suite
identifiers), the PRF with `P_HASH` over MD5 and SHA-1 and the master-secret
expansion; the record layer with `TLSCompressed`/`TLSCiphertext` and the
compression/DONE state, stream ciphers (RC4), CBC padding with the explicit
IV and the `bad_record_mac`/Lucky-Thirteen timing mitigations, and AEAD with
`additional_data` and the implicit/explicit nonce split; the alert protocol
with `warning`/`fatal` levels and the `unexpected_message`, `bad_record_mac`,
`record_overflow`, `decompression_failure`, `handshake_failure`,
`bad_certificate`, `certificate_expired`, `handshake_failure`,
`illegal_parameter`, `unknown_ca`, `decode_error`, `protocol_version`,
`insufficient_security`, `no_renegotiation` and `fallback_scsv` codes; the
handshake protocol with `ClientHello` (client random, session ID, cipher
suites, compression methods, extensions), `ServerHello`, `Certificate`,
`ServerKeyExchange` for `DHE`/`ECDHE`/`PSK`, `CertificateRequest`,
`ServerHelloDone`, `ClientKeyExchange` with the `RSA` pre-master-secret or
the `ECDHE`/`DHE` key exchange and the Bleichenbacher-tolerant error handling,
`ChangeCipherSpec` and `Finished` with `verify_data` computed by the PRF over
the handshake hash with the `client finished`/`server finished` labels;
session resumption and `session_id`, secure renegotiation via
`renegotiation_info`, mandatory cipher suite `TLS_RSA_WITH_AES_128_CBC_SHA`,
TLS 1.0/1.1 back-compatibility notes, the SSL 2.0 compatible `ClientHello`,
the cipher-suite parameter tables (bulk cipher, MAC, IV and key sizes) and the
security analysis of modes, padding, downgrade, `FIPS` and `session resumption`.
Note: 9 (H008: a `Content-Length` value that, after trimming surrounding
whitespace, is not a string of one or more ASCII digits) in §7.4.9 on page 7.

## rfc9000.txt — QUIC: A UDP-Based Multiplexed and Secure Transport (21 pages)
The transport protocol: 62-bit variable-length integer encoding, long and
short header forms and the fixed bits, connection IDs and their retirement,
version negotiation and `Retry` (with the integrity tag and `Version`-specific
salt), packet-number spaces and the Initial/0-RTT/Handshake/Application data
types, packet protection and header protection abstraction, the frame set
(PADDING, PING, ACK with ACK ranges and ECN counts, RESET_STREAM,
STOP_SENDING, CRYPTO, NEW_TOKEN, STREAM and its off/length bits,
MAX_DATA, MAX_STREAM_DATA, MAX_STREAMS and the BLOCKED variants,
STREAM_DATA_BLOCKED, STREAM_ID_BLOCKED, NEW_CONNECTION_ID, RETIRE_CONNECTION_ID,
PATH_CHALLENGE/PATH_RESPONSE, CONNECTION_CLOSE with application and transport
error codes, APPLICATION_CLOSE and HANDSHAKE_DONE), stream states and
flow-control limits with final sizes and sending/receiving offsets, the
connection-wide and per-stream credit model, congestion-control and
loss-detection hooks, connection migration and path validation, the
`0-RTT` data rules and `RETRY`, idle timeouts and keep-alives, `Version`
handling and the `0x?a?a?a?a` Grease versions, the transport parameters
(acknowledged on `ClientHello`/`EncryptedExtensions` and `Retry`, with
`initial_max_data`, `max_stream_*`, `active_connection_id_limit`,
`initial_source_connection_id`, `stateless_reset_token`, `max_datagram_frame_size`,
`disable_active_migration`, `max_idle_timeout`, `max_ack_delay`), `ECN`
validation and `PMTUD`/`DPLPMTUD`, the `0-RTT` and `RETRY` anti-replay
guidance, and the security considerations (integrity of transmitted data,
confidentiality and traffic analysis, amplification, denial of service via
handshake, stream and `0-RTT` manipulation, request forgery, `Stateless
Reset` oracle, `Version` downgrade, connection ID entropy, `ACK`/loss and
`Slowloris` concerns).
Note: 10 (H009: a header line beginning with a space or tab is obsolete line
folding, reported on that line, and is not a field of its own nor checked for
anything else) in §10.3 on page 9.

## rfc9001.txt — Using TLS to Secure QUIC (7 pages)
The TLS 1.3 mapping onto QUIC: the use of TLS 1.3 semantics with QUIC's own
record-layer-equivalent (packets) and the requirement for TLS 1.3 only; the
Initial secrets derived from the destination connection ID and a
version-specific salt, the `tls13 quic initial`, `tls13 quic handshake`,
`tls13 quic application` and `tls13 quic exporter` labels and the key-schedule
chain to early/handshake/application traffic secrets; header protection with
the AEAD-derived mask, sample offsets and the packet-number and length
masking, and its interaction with loss recovery; the AEAD limits, `KeyUpdate`
and the `KEY_UPDATE` frame, `0-RTT` keys with `early_secret` and
`max_early_data_size` and the `Resumption Master Secret` and `resumption
secret` derivation, `Session Resumption` tickets, `Retry` integrity protection
with a key derived from the initial secret or a configured secret, and the
`EXPORTER_` exporters used for `exporter_for QUIC` and for `QPACK` or other
signals; the `CRYPTO_ERROR` alert mapping with the `0x0100`-style code
`0x0100 + alert description`, the `tls_error` transport parameter; and the
security considerations of the `Initial` secret (no confidentiality against
an off-path attacker who can see the `ClientHello`), header protection,
`Retry` integrity, traffic analysis and `0-RTT` replay.
No editor's note.

## rfc9002.txt — QUIC Loss Detection and Congestion Control (5 pages)
The sender-side recovery algorithm: RTT measurement with `latest_rtt`,
`smoothed_rtt` and `rtt_variance` (RFC 6291-style averaging, the `Karn`
retransmission rule and the `min_rtt`/`smoothed_rtt` correction), the loss
detection threshold (`packet_threshold` 3 and `time_threshold` 9/8 of the
smoothed RTT plus variance), the detection of spurious retransmission and the
response to it, the PTO (probe timeout) computation with `idle_timeout` and
`max_ack_delay` and the `PING`/probe-packet rules, the `on_packet_lost`,
`on_new_ack`, `on_rtt_measurement` and `on_congestion_event` callbacks, the
congestion controller interface (`in_flight`, `bytes_in_flight`,
`max_datagram_frame_size`, `on_packet_acked` and `on_packet_lost`, `on_rtt`),
the loss-based increase phase (`congestion_window` growth by `kMaxDatagramSize`
per ack, `slow_start` and the avoidance phase), `ssthresh` reduction on loss
(`kLossReductionFactor` 1/2), the persistent-congestion detection with the
`congestion_window` floor and `kMinimumWindow` and `kInitialWindow` (10 * MSS,
bounded by 14720/12000), the pacing and `pacing_rate` guidance, the
`cwnd`/`bytes_in_flight` accounting rules and `Application Limited` sending,
and the guidance on `Congestion Control` alternatives and `ECN`; the
`RFC 9000` hooks for `Max_datagram_frame_size` and `DPLPMTUD`.
No editor's note.

## rfc9293.txt — Transmission Control Protocol (14 pages)
The current TCP specification that obsoletes RFC 793 and collects RFCs 879,
2873, 6093, 6429, 6528 and 6691: the TCP header (source and destination ports,
sequence and acknowledgment numbers, data offset, reserved bits, the CWR/ECE/
URG/ACK/PSH/RST/SYN/FIN flags, window, checksum over the pseudo-header, urgent
pointer, options), the options (`EOL`, `NOP`, MSS, window scale, SACK
permitted and SACK blocks, timestamp, echo and echo reply, MD5 and TCP-AO),
the state variables and the three-way handshake with its `SYN`-state
handling and `SYN`-cookies, sequence-number arithmetic and the four
segment-acceptability tests with `SACK`-state updates, the reset generation
and processing rules (including the RFC 5961 challenge-ACK behaviour),
half-open and simultaneous-open, `TIME-WAIT` and `PAWS` and the 2*MSL
`SEGMENT_Lifetime`, the `FIN`/`LAST-ACK`/`CLOSING` close sequence with
`TIME-WAIT` and `TIME-WAIT` state, `RST` and `FIN` on abort, `URG` and
`PSH` semantics, the `SEND`/`RECEIVE`/`OPEN`/`CLOSE`/`ABORT`/`STATUS`/
`FLUSH`/`ATTACH`/`DETACH`/`RECEIVE`/`SEND`/`VARIANCE` interface and the
asynchronous reports, the `TCP/Lower-Level Interface` with `ICMP`
soft/hard error handling and the `TCP` options `TCP_PCB`, `TCP_MSS`,
`TCP_TTL`, `TCP_TOS` and `TCP_DEBUG`, the `TCP` parameters
(`TCP_MSS`, `TCP_TTL`, `TCP_IGH`, `TCP_RTT`, `TCP_PMTU`, `TCP_SLOW_INC`,
`TCP_RETR_THRESH`, `TCP_URP` and the `TCP` timer list), the `TCP` state
table with its event/action lists and the `TCP` processing of events in each
state, the `MIB`-style statistics, `TCP-AO`/`MD5` and `IPsec` security, the
`TCP Header Flags` and `TCP Option Numbers` registries, the security analysis
(no cryptographic integrity in TCP, `TCP-AO` and `IPsec` as the defences,
`tcpcrypt`, `SYN` flooding and `ACK` storms, `ICMP`-based attacks, source
address validation, the `wire image` and `fingerprinting` of the header and
`options`, the `RST`-injection problem and the `challenge ACK`, the
`TIME-WAIT` and `PAWS` risks, `MD5` key-distribution, and the
`fingerprinting` and `telemetry` concerns), and the `TCP` glossary with a
list of changes from RFC 793.
Notes: 11 (H010: a header line with no colon at all, or whose name part before
the colon is empty, is reported on that line; a colon-less line is never
obsolete line folding even when it starts with whitespace) in §5.2 on page 2,
and 12 (the `--json` option: a single JSON array of objects with the keys
`line` (integer), `code` and `message` in the same order as the text output,
with unchanged exit statuses) in §8.1 on page 10.

## Where each note sits (verified against the page that contains it)
| # | document | page | section | governs |
|---|----------|------|---------|---------|
| 1 | rfc9110 | 2 | §2.1 | CLI, `LINE:CODE: message` format, exit 0/1/2, LF+CRLF |
| 2 | rfc9110 | 16 | §14.2 | H001 request-line three-part split; skip H002/H003 |
| 3 | rfc9112 | 2 | §5.2 | H002 version `HTTP/1.1`/`HTTP/1.0` |
| 4 | rfc3986 | 3 | §5.2.2 | H003 method = uppercase A–Z only |
| 5 | rfc7541 | 3 | §7.3 | H004 missing `Host` in HTTP/1.1 |
| 6 | rfc9114 | 6 | §11.2.1 | H005 duplicate `Host`; case-insensitive names |
| 7 | rfc6797 | 3 | §9.1 | H006 whitespace before the colon |
| 8 | rfc7540 | 4 | §5.4.2 | H007 `Content-Length` + `Transfer-Encoding` |
| 9 | rfc5246 | 7 | §7.4.9 | H008 `Content-Length` not all digits |
| 10 | rfc9000 | 9 | §10.3 | H009 obsolete line folding |
| 11 | rfc9293 | 2 | §5.2 | H010 no colon / empty field name |
| 12 | rfc9293 | 10 | §8.1 | `--json` output mode |
