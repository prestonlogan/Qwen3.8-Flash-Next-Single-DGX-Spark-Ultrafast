#!/usr/bin/env python3
"""httplint.py - lint a raw HTTP/1.x request.

Usage:  python httplint.py [--json] FILE

FILE holds one raw HTTP/1.x request.  Output: one finding per line in the form
    LINE:CODE: message
where LINE is the 1-based line number in FILE and CODE is a finding code such as
H001.  Exit status: 0 = no findings, 1 = at least one finding, 2 = FILE cannot be
read (or the command line is wrong).  Both LF and CRLF line endings are accepted.

With --json the tool prints instead a single JSON array of objects with the keys
line (an integer), code and message, in the same order as the text output; the
exit statuses are the same as without --json.

The checks implemented here are exactly the ones defined by the twelve editor's
notes planted in the RFCs (see NOTES.md).  Finding codes:

  H001  request line must split on single spaces into exactly three parts
        (method, request-target, version); on failure report on line 1 and skip
        H002 and H003.
  H002  request-line version must be exactly HTTP/1.1 or HTTP/1.0 (line 1).
  H003  method must consist only of uppercase ASCII letters A-Z (line 1).
  H004  an HTTP/1.1 request with no Host header field; HTTP/1.0 is exempt
        (reported on line 1).
  H005  more than one Host header field: report on the line of every Host field
        after the first one.
  H006  whitespace between a header field name and its colon, reported on that
        line; the field still counts under its name without the whitespace.
  H007  a request with both Content-Length and Transfer-Encoding: report on the
        line of whichever of the two appears later.
  H008  a Content-Length value that, after trimming surrounding whitespace, is
        not a string of one or more ASCII digits; report on that line.
  H009  a header line that begins with a space or a tab (obsolete line folding),
        reported on that line; such a line is not a field of its own and is not
        checked for anything else.
  H010  a header line that contains no colon at all, or whose name part before the
        colon is empty, reported on that line.  A line with no colon is *never*
        treated as obsolete line folding, even when it begins with whitespace.

Header field names are case-insensitive for every check (host, Host and HOST are
all Host).
"""

from __future__ import annotations

import json
import sys

__all__ = [
    "Finding",
    "lint",
    "render_text",
    "render_json",
    "parse_args",
    "main",
]

EX_OK = 0
EX_FINDINGS = 1
EX_ERROR = 2

PROGRAM = "httplint.py"
USAGE = f"usage: {PROGRAM} [--json] FILE"

VERSIONS = ("HTTP/1.1", "HTTP/1.0")

#: whitespace treated as "surrounding" / "between name and colon" (OWS)
WS = " \t"


class Finding:
    """A single lint finding: 1-based line number, code and message."""

    __slots__ = ("line", "code", "message")

    def __init__(self, line: int, code: str, message: str) -> None:
        self.line = int(line)
        self.code = code
        self.message = message

    def __iter__(self):
        return iter((self.line, self.code, self.message))

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"Finding({self.line!r}, {self.code!r}, {self.message!r})"

    def __eq__(self, other) -> bool:
        return isinstance(other, Finding) and tuple(self) == tuple(other)

    def __hash__(self):
        return hash(tuple(self))

    def as_dict(self) -> dict:
        """The JSON object form: keys line (int), code, message."""
        return {"line": self.line, "code": self.code, "message": self.message}

    def format(self) -> str:
        """The text form: LINE:CODE: message."""
        return f"{self.line}:{self.code}: {self.message}"


# ---------------------------------------------------------------------------
# small helpers
# ---------------------------------------------------------------------------


def normalize_newlines(text: str) -> str:
    """Accept both LF and CRLF line endings by folding CRLF to LF."""
    return text.replace("\r\n", "\n")


def split_lines(text: str) -> list[str]:
    """Split request text into lines (1-based numbering follows the file)."""
    return normalize_newlines(text).split("\n")


def parse_request_line(line: str) -> tuple[str, str, str] | None:
    """Return (method, request-target, version) or None when malformed.

    The request line must split on single spaces into exactly three parts.
    """
    parts = line.split(" ")
    if len(parts) != 3:
        return None
    return parts[0], parts[1], parts[2]


def is_uppercase_method(method: str) -> bool:
    """True when the method is one or more uppercase ASCII letters A-Z."""
    return bool(method) and all("A" <= ch <= "Z" for ch in method)


def is_ascii_digits(value: str) -> bool:
    """True when value is one or more ASCII digits (1*DIGIT)."""
    return bool(value) and all("0" <= ch <= "9" for ch in value)


def is_host(name: str) -> bool:
    return name.upper() == "HOST"


def field_name(line: str) -> str | None:
    """The name part of a header line, or None when it has no colon.

    Whitespace immediately before the colon is *not* part of the name, so
    "Host : x" yields "Host" (the caller reports H006 itself).
    """
    colon = line.find(":")
    if colon == -1:
        return None
    return line[:colon].rstrip(WS)


def field_value(line: str) -> str | None:
    """The value part of a header line, or None when it has no colon."""
    colon = line.find(":")
    if colon == -1:
        return None
    return line[colon + 1 :]


def name_has_trailing_whitespace(line: str) -> bool:
    """True when a field line has whitespace between its name and its colon."""
    colon = line.find(":")
    if colon == -1:
        return False
    raw_name = line[:colon]
    return raw_name != raw_name.rstrip(WS)


# ---------------------------------------------------------------------------
# the lint itself
# ---------------------------------------------------------------------------


def lint(text: str) -> list[Finding]:
    """Check one raw HTTP/1.x request, returning findings in output order."""
    findings: list[Finding] = []
    lines = split_lines(text)

    # ---- the request line: line 1 -------------------------------------------
    request_line = lines[0] if lines else ""
    parsed = parse_request_line(request_line)
    version = None
    if parsed is None:
        findings.append(
            Finding(
                1,
                "H001",
                "request line must split on single spaces into exactly three "
                "parts: method, request-target and version",
            )
        )
        # H002 and H003 are skipped for this request line.
    else:
        method, _target, version = parsed
        if version not in VERSIONS:
            findings.append(
                Finding(
                    1,
                    "H002",
                    f"request-line version {version!r} is not exactly "
                    f"{' or '.join(repr(v) for v in VERSIONS)}",
                )
            )
        if not is_uppercase_method(method):
            findings.append(
                Finding(
                    1,
                    "H003",
                    f"method {method!r} does not consist only of uppercase "
                    "ASCII letters A-Z",
                )
            )

    # ---- header fields: lines 2.. up to the first empty line ---------------
    host_lines: list[int] = []
    content_length_lines: list[int] = []
    transfer_encoding_lines: list[int] = []
    for number, line in enumerate(lines[1:], start=2):
        if line == "":  # the empty line ends the header section
            break
        if ":" not in line:
            # Note 11: a line with no colon is never treated as obsolete line
            # folding, not even when it begins with whitespace, and it is not
            # a field of its own.
            findings.append(
                Finding(
                    number,
                    "H010",
                    "header line has no colon; not a field of its own",
                )
            )
            continue
        if line[0] in WS:
            # Note 10: obsolete line folding.  Such a line is not a field of
            # its own and is not checked for anything else.
            findings.append(
                Finding(
                    number,
                    "H009",
                    "obsolete line folding: a header line begins with a space "
                    "or a tab; not a field of its own",
                )
            )
            continue
        name = field_name(line)
        if name == "":
            findings.append(
                Finding(
                    number,
                    "H010",
                    "header line has an empty field name before the colon; "
                    "not a field of its own",
                )
            )
            continue
        if name_has_trailing_whitespace(line):
            findings.append(
                Finding(
                    number,
                    "H006",
                    f"whitespace between field name {name!r} and its colon",
                )
            )
        if is_host(name):
            host_lines.append(number)
        elif name.upper() == "CONTENT-LENGTH":
            content_length_lines.append(number)
            value = field_value(line).strip(WS)
            if not is_ascii_digits(value):
                findings.append(
                    Finding(
                        number,
                        "H008",
                        f"Content-Length value {value!r} is not a string of "
                        "one or more ASCII digits",
                    )
                )
        elif name.upper() == "TRANSFER-ENCODING":
            transfer_encoding_lines.append(number)

    # ---- checks over the whole header section ------------------------------
    if parsed is not None and version == "HTTP/1.1" and not host_lines:
        findings.append(
            Finding(1, "H004", "HTTP/1.1 request has no Host header field")
        )
    if content_length_lines and transfer_encoding_lines:
        later = max(content_length_lines[-1], transfer_encoding_lines[-1])
        findings.append(
            Finding(
                later,
                "H007",
                "request has both Content-Length and Transfer-Encoding "
                "header fields",
            )
        )
    for duplicate in host_lines[1:]:
        findings.append(
            Finding(
                duplicate,
                "H005",
                f"more than one Host header field; the first is on line "
                f"{host_lines[0]}",
            )
        )

    return sorted(findings, key=lambda f: (f.line, f.code))


# ---------------------------------------------------------------------------
# output rendering
# ---------------------------------------------------------------------------


def render_text(findings: list[Finding]) -> str:
    """One finding per line: LINE:CODE: message."""
    return "".join(f"{finding.format()}\n" for finding in findings)


def render_json(findings: list[Finding]) -> str:
    """A single JSON array of {line, code, message} objects, in text order."""
    return json.dumps(
        [finding.as_dict() for finding in findings], separators=(",", ":")
    )


# ---------------------------------------------------------------------------
# command line
# ---------------------------------------------------------------------------


def parse_args(argv: list[str]) -> tuple[bool, str] | None:
    """Return (json_mode, path); None when the command line is not valid."""
    json_mode = False
    positional: list[str] = []
    for arg in argv:
        if arg == "--json":
            json_mode = True
        else:
            positional.append(arg)
    if len(positional) != 1:
        return None
    return json_mode, positional[0]


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    parsed = parse_args(args)
    if parsed is None:
        print(f"{PROGRAM}: wrong number of arguments", file=sys.stderr)
        print(USAGE, file=sys.stderr)
        return EX_ERROR
    json_mode, path = parsed

    try:
        with open(path, "rb") as handle:
            data = handle.read()
    except OSError as exc:
        print(f"{PROGRAM}: {path}: {exc.strerror or exc}", file=sys.stderr)
        return EX_ERROR

    findings = lint(data.decode("latin-1"))
    if json_mode:
        print(render_json(findings))
    else:
        sys.stdout.write(render_text(findings))
    return EX_FINDINGS if findings else EX_OK


if __name__ == "__main__":
    raise SystemExit(main())
