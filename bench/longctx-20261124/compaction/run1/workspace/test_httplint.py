"""unittest tests for httplint.py.

The whole specification comes from the twelve editor's notes planted in the RFCs
(recorded in NOTES.md): note 1 = the CLI contract, notes 2-11 = findings
H001-H010, note 12 = the --json option.

Note 11 is the one that interacts with the others: "a header line that contains
no colon at all, or whose name part before the colon is empty, is reported as
H010 on that line.  A line with no colon is never treated as obsolete line
folding, even if it begins with whitespace."  So a colon-less line is H010 even
when it starts with SP/HTAB, and it is H010 instead of H009 in that case.
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest

import httplint


def run_lint(text: str) -> list[str]:
    return [f.format() for f in httplint.lint(text)]


def codes(text: str) -> list[str]:
    return [f.code for f in httplint.lint(text)]


def lines(text: str) -> list[int]:
    return [f.line for f in httplint.lint(text)]


def text_lines(text: str) -> list[str]:
    """The line numbers of the plain-text output, as rendered strings."""
    return [line.split(":", 1)[0] for line in text.splitlines()]


def text_codes(text: str) -> list[str]:
    return [line.split(":", 2)[1] for line in text.splitlines()]


def text_messages(text: str) -> list[str]:
    return [line.split(": ", 1)[1] for line in text.splitlines()]


# ---------------------------------------------------------------------------
# note 1: the CLI contract
# ---------------------------------------------------------------------------


class CliTests(unittest.TestCase):
    def _write(self, text: str) -> str:
        handle = tempfile.NamedTemporaryFile("w", delete=False, newline="")
        handle.write(text)
        handle.close()
        self.addCleanup(os.unlink, handle.name)
        return handle.name

    def _run(self, *args: str):
        proc = subprocess.run(
            [sys.executable, "httplint.py", *args],
            cwd=os.path.dirname(os.path.abspath(httplint.__file__)),
            capture_output=True,
            text=True,
        )
        return proc.returncode, proc.stdout, proc.stderr

    def test_exit_0_when_no_findings(self):
        path = self._write("GET / HTTP/1.1\nHost: example.com\n\n")
        self.assertEqual(self._run(path), (0, "", ""))

    def test_exit_1_when_at_least_one_finding(self):
        path = self._write("GET / HTTP/1.1\n\n")
        code, out, err = self._run(path)
        self.assertEqual(code, 1)
        self.assertEqual(out, "1:H004: HTTP/1.1 request has no Host header field\n")

    def test_exit_2_when_file_cannot_be_read(self):
        code, out, err = self._run("no-such-file.txt")
        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        self.assertIn("no-such-file.txt", err)

    def test_exit_2_for_a_missing_argument(self):
        self.assertEqual(httplint.main([]), 2)

    def test_exit_2_for_extra_arguments(self):
        self.assertEqual(httplint.main(["a", "b"]), 2)

    def test_both_lf_and_crlf_endings_accepted(self):
        lf = "GET /index.html HTTP/1.1\nHost: example.com\n\n"
        self.assertEqual(run_lint(lf), [])
        self.assertEqual(run_lint(lf.replace("\n", "\r\n")), [])
        path = self._write(lf.replace("\n", "\r\n"))
        self.assertEqual(self._run(path), (0, "", ""))

    def test_crlf_line_numbers_are_lines_not_bytes(self):
        crlf = "GET / HTTP/1.1\r\nHost: a\r\nbogus line\r\n\r\n"
        self.assertEqual(codes(crlf), ["H010"])
        self.assertEqual(lines(crlf), [3])

    def test_finding_line_format(self):
        self.assertEqual(httplint.Finding(3, "H005", "x").format(), "3:H005: x")


# ---------------------------------------------------------------------------
# notes 2, 3, 4: the request line (H001, H002, H003)
# ---------------------------------------------------------------------------


class RequestLineTests(unittest.TestCase):
    def test_clean_request_has_no_findings(self):
        self.assertEqual(run_lint("GET /index.html HTTP/1.1\nHost: a\n\n"), [])

    def test_double_space_is_h001(self):
        self.assertEqual(codes("GET  / HTTP/1.1\nHost: a\n\n"), ["H001"])

    def test_more_than_three_parts_is_h001(self):
        self.assertEqual(codes("GET / HTTP/1.1 1\nHost: a\n\n"), ["H001"])

    def test_two_parts_is_h001(self):
        self.assertEqual(codes("GET /\n\n"), ["H001"])

    def test_one_part_is_h001(self):
        self.assertEqual(codes("CONNECT\r\n\n"), ["H001"])

    def test_h001_reports_on_line_1(self):
        self.assertEqual(lines("GET /\n\n"), [1])

    def test_h001_skips_h002_and_h003(self):
        # bad method and bad version, but four space-separated parts: only H001
        self.assertEqual(codes("gety / HTTP/2.0 1\n\n"), ["H001"])

    def test_tab_in_the_request_line_is_h001(self):
        # tabs are not single spaces, so this does not split into three parts
        self.assertEqual(codes("GET\t/ HTTP/1.1\nHost: a\n\n"), ["H001"])

    def test_bad_version_is_h002_on_line_1(self):
        self.assertEqual(codes("GET / HTTP/2\nHost: a\n\n"), ["H002"])
        self.assertEqual(lines("GET / HTTP/2\nHost: a\n\n"), [1])

    def test_lowercase_version_is_h002(self):
        self.assertEqual(codes("GET / http/1.1\nHost: a\n\n"), ["H002"])

    def test_http_10_and_http_11_are_accepted(self):
        self.assertEqual(run_lint("GET / HTTP/1.0\n\n"), [])
        self.assertEqual(run_lint("HEAD / HTTP/1.1\nHost: a\n\n"), [])

    def test_lowercase_method_is_h003(self):
        self.assertEqual(codes("get / HTTP/1.1\nHost: a\n\n"), ["H003"])

    def test_methods_are_not_limited_to_token_characters(self):
        # note 4 asks for *only* uppercase ASCII letters A-Z
        for method in ("GET2", "GET_", "GET-X", "GeT", "GET.", "GET2".lower()):
            with self.subTest(method=method):
                self.assertEqual(codes(f"{method} / HTTP/1.1\nHost: a\n\n"), ["H003"])

    def test_a_pure_uppercase_method_is_accepted(self):
        self.assertEqual(run_lint("FOOBAR / HTTP/1.1\nHost: a\n\n"), [])

    def test_empty_method_is_h003(self):
        self.assertEqual(codes(" / HTTP/1.1\nHost: a\n\n"), ["H003"])

    def test_method_and_version_both_bad(self):
        self.assertEqual(codes("get / HTTP/1.5\nHost: a\n\n"), ["H002", "H003"])
        self.assertEqual(lines("get / HTTP/1.5\nHost: a\n\n"), [1, 1])


# ---------------------------------------------------------------------------
# notes 5 and 6: Host (H004, H005)
# ---------------------------------------------------------------------------


class HostTests(unittest.TestCase):
    def test_missing_host_on_http11_is_h004_on_line_1(self):
        self.assertEqual(codes("GET / HTTP/1.1\nUser-Agent: x\n\n"), ["H004"])
        self.assertEqual(lines("GET / HTTP/1.1\nUser-Agent: x\n\n"), [1])

    def test_http10_is_not_required_to_have_a_host(self):
        self.assertEqual(run_lint("GET / HTTP/1.0\nUser-Agent: x\n\n"), [])

    def test_h004_needs_a_parsable_request_line(self):
        # version unknown -> the version part of H004 cannot be established
        self.assertEqual(codes("GET / HTTP/1.1 extra\n\n"), ["H001"])

    def test_field_names_are_case_insensitive_everywhere(self):
        for name in ("Host", "host", "HOST", "HoSt"):
            with self.subTest(name=name):
                self.assertEqual(
                    run_lint(f"GET / HTTP/1.1\n{name}: example.com\n\n"), []
                )

    def test_duplicate_host_reports_every_one_after_the_first(self):
        text = "GET / HTTP/1.1\nHost: a.com\nAccept: */*\nhost: b.com\n\n"
        self.assertEqual(codes(text), ["H005"])
        self.assertEqual(lines(text), [4])

    def test_three_hosts_produce_two_findings(self):
        text = "GET / HTTP/1.1\nHost: a\nHOST: b\nhost: c\n\n"
        self.assertEqual(codes(text), ["H005", "H005"])
        self.assertEqual(lines(text), [3, 4])

    def test_h005_line_numbers_are_1_based_with_crlf(self):
        text = "GET / HTTP/1.1\r\nA: 1\r\nB: 2\r\nHost: x\r\nHost: y\r\n\r\n"
        self.assertEqual(lines(text), [5])

    def test_a_folded_host_line_is_not_a_host(self):
        text = "GET / HTTP/1.1\nHost: a\n host: b\n\n"
        self.assertEqual(codes(text), ["H009"])

    def test_a_host_line_without_a_colon_is_h010(self):
        text = "GET / HTTP/1.1\nHost a.com\n\n"
        self.assertEqual(codes(text), ["H004", "H010"])
        self.assertEqual(lines(text), [1, 2])


# ---------------------------------------------------------------------------
# note 7: H006 - whitespace between a name and its colon
# ---------------------------------------------------------------------------


class NameColonWhitespaceTests(unittest.TestCase):
    def test_space_before_colon_is_h006_on_that_line(self):
        text = "GET / HTTP/1.1\nHost : example.com\n\n"
        self.assertEqual(codes(text), ["H006"])
        self.assertEqual(lines(text), [2])

    def test_tab_before_colon_is_h006(self):
        text = "GET / HTTP/1.1\nHost\t: example.com\n\n"
        self.assertEqual(codes(text), ["H006"])

    def test_several_spaces_before_colon(self):
        text = "GET / HTTP/1.1\nHost   : a\n\n"
        self.assertEqual(codes(text), ["H006"])

    def test_the_field_still_counts_under_its_name(self):
        # Host : x is a Host field for the other checks: no H004, no H005
        self.assertEqual(codes("GET / HTTP/1.1\nHost : example.com\n\n"), ["H006"])
        text = "GET / HTTP/1.1\nHost: a\nX : y\n\n"
        self.assertEqual(codes(text), ["H006"])

    def test_h006_and_h005_together(self):
        text = "GET / HTTP/1.1\nHost: a\nhost : b\n\n"
        self.assertEqual(codes(text), ["H005", "H006"])
        self.assertEqual(lines(text), [3, 3])

    def test_h006_on_a_non_host_field(self):
        text = "GET / HTTP/1.1\nHost: a\nUser-Agent : x\n\n"
        self.assertEqual(codes(text), ["H006"])
        self.assertEqual(lines(text), [3])

    def test_no_whitespace_after_the_colon_is_fine(self):
        self.assertEqual(run_lint("GET / HTTP/1.1\nHost:a\n\n"), [])

    def test_whitespace_before_the_colon_makes_the_name_itself(self):
        # "Host " and "Host" are the same field name, so a duplicate appears
        text = "GET / HTTP/1.1\nHost: a\nHost : b\n\n"
        self.assertEqual(codes(text), ["H005", "H006"])
        self.assertEqual(lines(text), [3, 3])

    def test_h006_and_h009_are_distinct(self):
        text = "GET / HTTP/1.1\nHost : a\n X: y\n\n"
        self.assertEqual(codes(text), ["H006", "H009"])
        self.assertEqual(lines(text), [2, 3])


# ---------------------------------------------------------------------------
# notes 8 and 9: message framing (H007, H008)
# ---------------------------------------------------------------------------


class FramingTests(unittest.TestCase):
    def test_both_codings_report_on_the_later_line(self):
        text = "POST / HTTP/1.1\nHost: a\nContent-Length: 3\nTransfer-Encoding: chunked\n\n"
        self.assertEqual(codes(text), ["H007"])
        self.assertEqual(lines(text), [4])

    def test_the_later_line_wins_when_transfer_encoding_comes_first(self):
        text = "POST / HTTP/1.1\nHost: a\nTransfer-Encoding: chunked\nX: y\ncontent-length: 3\n\n"
        self.assertEqual(codes(text), ["H007"])
        self.assertEqual(lines(text), [5])

    def test_only_one_of_the_two_is_fine(self):
        self.assertEqual(
            run_lint("POST / HTTP/1.1\nHost: a\nContent-Length: 0\n\n"), []
        )
        self.assertEqual(
            run_lint("POST / HTTP/1.1\nHost: a\nTransfer-Encoding: chunked\n\n"), []
        )

    def test_framing_field_names_are_case_insensitive(self):
        text = "POST / HTTP/1.1\nHost: a\ncontent-length: 2\nTRANSFER-ENCODING: chunked\n\n"
        self.assertEqual(codes(text), ["H007"])
        self.assertEqual(lines(text), [4])

    def test_h007_and_h005_are_independent(self):
        text = (
            "POST / HTTP/1.1\nHost: a\nContent-Length: 2\nhost: b\n"
            "Transfer-Encoding: chunked\n\n"
        )
        self.assertEqual(codes(text), ["H005", "H007"])
        self.assertEqual(lines(text), [4, 5])

    def test_fields_after_the_blank_line_are_not_scanned(self):
        text = "POST / HTTP/1.1\nHost: a\n\nContent-Length: 1\nTransfer-Encoding: chunked\n"
        self.assertEqual(run_lint(text), [])

    def test_the_request_line_is_not_scanned_as_a_header_field(self):
        # this request line happens to split into three parts, so line 1 is
        # read as a method/version pair and never as a header field: no H007
        # and no H008 can come from it.
        text = "Content-Length: 3 HTTP/1.1\nTransfer-Encoding: chunked\n\n"
        self.assertEqual(codes(text), ["H003", "H004"])
        self.assertEqual(lines(text), [1, 1])


class ContentLengthTests(unittest.TestCase):
    def test_non_digit_value_is_h008_on_that_line(self):
        text = "POST / HTTP/1.1\nHost: a\nContent-Length: twelve\n\n"
        self.assertEqual(codes(text), ["H008"])
        self.assertEqual(lines(text), [3])

    def test_empty_value_is_h008(self):
        self.assertEqual(codes("POST / HTTP/1.1\nHost: a\nContent-Length:\n\n"), ["H008"])

    def test_negative_value_is_h008(self):
        self.assertEqual(codes("POST / HTTP/1.1\nHost: a\nContent-Length: -1\n\n"), ["H008"])

    def test_hexadecimal_value_is_h008(self):
        self.assertEqual(codes("POST / HTTP/1.1\nHost: a\nContent-Length: 1f\n\n"), ["H008"])

    def test_comma_separated_values_are_h008(self):
        self.assertEqual(codes("POST / HTTP/1.1\nHost: a\nContent-Length: 4,4\n\n"), ["H008"])

    def test_surrounding_whitespace_is_trimmed_first(self):
        self.assertEqual(
            run_lint("POST / HTTP/1.1\nHost: a\nContent-Length:   42   \n\n"), []
        )
        self.assertEqual(
            run_lint("POST / HTTP/1.1\nHost: a\nContent-Length:\t5\t\n\n"), []
        )

    def test_zero_is_valid(self):
        self.assertEqual(
            run_lint("POST / HTTP/1.1\nHost: a\nContent-Length: 0\n\n"), []
        )

    def test_field_name_is_case_insensitive(self):
        self.assertEqual(
            codes("POST / HTTP/1.1\nHost: a\nCONTENT-LENGTH: 12a\n\n"), ["H008"]
        )

    def test_each_bad_content_length_line_is_reported(self):
        text = "POST / HTTP/1.1\nHost: a\nContent-Length: x\nContent-Length: y\n\n"
        self.assertEqual(codes(text), ["H008", "H008"])
        self.assertEqual(lines(text), [3, 4])

    def test_h008_and_h007_together(self):
        text = "POST / HTTP/1.1\nHost: a\nContent-Length: x\nTransfer-Encoding: chunked\n\n"
        self.assertEqual(codes(text), ["H008", "H007"])
        self.assertEqual(lines(text), [3, 4])

    def test_a_folded_continuation_is_h009_and_not_an_h008(self):
        # a fold line with a colon is H009 and is not checked for anything else
        text = "POST / HTTP/1.1\nHost: a\nContent-Length: 12\n x: 34\n\n"
        self.assertEqual(codes(text), ["H009"])
        self.assertEqual(lines(text), [4])

    def test_a_digit_continuation_without_a_colon_is_h010(self):
        # note 11: a colon-less line is H010 even when it starts with whitespace
        text = "POST / HTTP/1.1\nHost: a\nContent-Length: 12\n 34\n\n"
        self.assertEqual(codes(text), ["H010"])
        self.assertEqual(lines(text), [4])


# ---------------------------------------------------------------------------
# note 10: H009 - obsolete line folding
# ---------------------------------------------------------------------------


class ObsoleteLineFoldingTests(unittest.TestCase):
    def test_leading_space_is_h009_on_that_line(self):
        text = "GET / HTTP/1.1\nHost: a\nX: y\n continued: value\n\n"
        self.assertEqual(codes(text), ["H009"])
        self.assertEqual(lines(text), [4])

    def test_leading_tab_is_h009(self):
        text = "GET / HTTP/1.1\nHost: a\n\tcontinued: value\n\n"
        self.assertEqual(codes(text), ["H009"])
        self.assertEqual(lines(text), [3])

    def test_a_fold_line_is_not_checked_for_anything_else(self):
        # looks like a bad Content-Length, but it is a fold line: only H009
        text = "GET / HTTP/1.1\nHost: a\n content-length: twelve\n\n"
        self.assertEqual(codes(text), ["H009"])

    def test_a_fold_line_is_not_a_field(self):
        # folded framing fields do not count, so nothing else fires either
        text = "GET / HTTP/1.1\n transfer-encoding: chunked\n content-length: 1\n\n"
        self.assertEqual(codes(text), ["H004", "H009", "H009"])
        self.assertEqual(lines(text), [1, 2, 3])

    def test_multiple_folded_lines(self):
        text = "GET / HTTP/1.1\nHost: a\n x: 1\n\ty: 2\n\n"
        self.assertEqual(codes(text), ["H009", "H009"])
        self.assertEqual(lines(text), [3, 4])

    def test_the_request_line_is_never_a_fold_line(self):
        # line 1 is not a header line, so a leading space there is H001 only
        self.assertEqual(codes(" GET / HTTP/1.1\nHost: a\n\n"), ["H001"])

    def test_folding_after_the_blank_line_is_not_scanned(self):
        self.assertEqual(run_lint("GET / HTTP/1.1\nHost: a\n\n folded in body\n"), [])

    def test_a_whitespace_only_line_is_not_a_blank_line(self):
        # "   " is not empty, so the header section does not end there; the
        # line has no colon at all, so it is H010 (note 11 takes precedence)
        text = "GET / HTTP/1.1\nHost: a\n   \nbogus line\n\n"
        self.assertEqual(codes(text), ["H010", "H010"])
        self.assertEqual(lines(text), [3, 4])

    def test_fold_line_is_not_checked_for_an_empty_name(self):
        # a fold line is not a field of its own: no H010 either
        text = "GET / HTTP/1.1\nHost: a\n : x\n\n"
        self.assertEqual(codes(text), ["H009"])
        self.assertEqual(lines(text), [3])


# ---------------------------------------------------------------------------
# note 11: H010 - no colon, or an empty name
# ---------------------------------------------------------------------------


class MissingNameOrColonTests(unittest.TestCase):
    def test_line_without_a_colon_is_h010_on_that_line(self):
        text = "GET / HTTP/1.1\nHost: a\nbogus garbage line\n\n"
        self.assertEqual(codes(text), ["H010"])
        self.assertEqual(lines(text), [3])

    def test_empty_name_before_the_colon_is_h010(self):
        text = "GET / HTTP/1.1\nHost: a\n: value\n\n"
        self.assertEqual(codes(text), ["H010"])
        self.assertEqual(lines(text), [3])

    def test_a_whitespace_starting_line_without_a_colon_is_h010_not_h009(self):
        # note 11: "never treated as obsolete line folding, even if it begins
        # with whitespace"
        text = "GET / HTTP/1.1\nHost: a\n   no colon here\n\n"
        self.assertEqual(codes(text), ["H010"])
        self.assertEqual(lines(text), [3])

    def test_a_tab_starting_line_without_a_colon_is_h010(self):
        text = "GET / HTTP/1.1\nHost: a\n\tnope\n\n"
        self.assertEqual(codes(text), ["H010"])
        self.assertEqual(lines(text), [3])

    def test_several_colon_less_lines(self):
        text = "GET / HTTP/1.1\nHost: a\nno colon\n: empty name\n\n"
        self.assertEqual(codes(text), ["H010", "H010"])
        self.assertEqual(lines(text), [3, 4])

    def test_a_h010_line_is_not_a_field(self):
        # neither Host nor Content-Length may be satisfied by such a line
        text = "GET / HTTP/1.1\nHost: a\nContent-Length 5\n\n"
        self.assertEqual(codes(text), ["H010"])

    def test_a_colon_less_request_line_is_h001_not_h010(self):
        text = "GET / HTTP/1.1\nHost: a\nGET / HTTP/1.1\n\n"
        self.assertEqual(codes(text), ["H010"])
        self.assertEqual(lines(text), [3])

    def test_colon_less_line_after_the_blank_line_is_not_scanned(self):
        self.assertEqual(run_lint("GET / HTTP/1.1\nHost: a\n\nno colon in body\n"), [])

    def test_h009_and_h010_on_the_same_request(self):
        text = "GET / HTTP/1.1\nHost: a\n X: y\n not folded\n\n"
        self.assertEqual(codes(text), ["H009", "H010"])
        self.assertEqual(lines(text), [3, 4])


# ---------------------------------------------------------------------------
# note 12: --json
# ---------------------------------------------------------------------------


class JsonOutputTests(unittest.TestCase):
    def _write(self, text: str) -> str:
        handle = tempfile.NamedTemporaryFile("w", delete=False, newline="")
        handle.write(text)
        handle.close()
        self.addCleanup(os.unlink, handle.name)
        return handle.name

    def _run(self, *args: str):
        proc = subprocess.run(
            [sys.executable, "httplint.py", *args],
            cwd=os.path.dirname(os.path.abspath(httplint.__file__)),
            capture_output=True,
            text=True,
        )
        return proc.returncode, proc.stdout, proc.stderr

    def test_json_is_one_array_of_objects(self):
        path = self._write(
            "POST / HTTP/1.1\nHost: a\nContent-Length: x\nTransfer-Encoding: chunked\n\n"
        )
        code, out, err = self._run("--json", path)
        self.assertEqual(code, 1)
        self.assertEqual(err, "")
        data = json.loads(out)
        self.assertIsInstance(data, list)
        self.assertEqual([item["code"] for item in data], ["H008", "H007"])
        self.assertEqual([item["line"] for item in data], [3, 4])
        for item in data:
            self.assertEqual(sorted(item), ["code", "line", "message"])
            self.assertIsInstance(item["line"], int)
            self.assertIsInstance(item["code"], str)
            self.assertIsInstance(item["message"], str)

    def test_json_order_matches_the_text_order(self):
        path = self._write(
            "get / HTTP/9\nHost: a\nbogus line\nHost: b\nContent-Length: zz\n\n"
        )
        _, text_out, _ = self._run(path)
        _, json_out, _ = self._run("--json", path)
        data = json.loads(json_out)
        self.assertEqual([item["line"] for item in data], [int(x) for x in text_lines(text_out)])
        self.assertEqual([item["code"] for item in data], text_codes(text_out))
        self.assertEqual([item["message"] for item in data], text_messages(text_out))

    def test_exit_0_with_json_and_an_empty_array_when_no_findings(self):
        path = self._write("GET / HTTP/1.1\nHost: a\n\n")
        self.assertEqual(self._run("--json", path), (0, "[]\n", ""))

    def test_exit_2_with_json_when_the_file_cannot_be_read(self):
        code, out, err = self._run("--json", "no-such-file.txt")
        self.assertEqual(code, 2)
        self.assertEqual(out, "")

    def test_exit_2_with_json_for_a_wrong_argument_count(self):
        self.assertEqual(httplint.main(["--json"]), 2)
        self.assertEqual(httplint.main(["--json", "a", "b"]), 2)

    def test_the_option_may_come_after_the_file(self):
        path = self._write("GET / HTTP/1.1\n\n")
        code, out, err = self._run(path, "--json")
        self.assertEqual(code, 1)
        self.assertEqual(json.loads(out)[0]["code"], "H004")

    def test_render_helpers(self):
        findings = httplint.lint("GET / HTTP/1.1\nbogus\n\n")
        self.assertEqual(
            httplint.render_text(findings),
            "1:H004: HTTP/1.1 request has no Host header field\n"
            "2:H010: header line has no colon; not a field of its own\n",
        )
        self.assertEqual(
            json.loads(httplint.render_json(findings)),
            [
                {"line": 1, "code": "H004", "message": findings[0].message},
                {"line": 2, "code": "H010", "message": findings[1].message},
            ],
        )


# ---------------------------------------------------------------------------
# output ordering for the text form
# ---------------------------------------------------------------------------


class OutputOrderTests(unittest.TestCase):
    def test_findings_are_sorted_by_line_then_code(self):
        text = "get / HTTP/9\nHost: a\nbogus line\nHost: b\n: ouch\n\n"
        findings = httplint.lint(text)
        self.assertEqual([(f.line, f.code) for f in findings], [
            (1, "H002"),
            (1, "H003"),
            (3, "H010"),
            (4, "H005"),
            (5, "H010"),
        ])

    def test_two_findings_on_one_line_are_ordered_by_code(self):
        text = "GET / HTTP/1.1\nHost: a\nHost : b\n\n"
        self.assertEqual([(f.line, f.code) for f in httplint.lint(text)], [
            (3, "H005"),
            (3, "H006"),
        ])

    def test_the_text_output_ends_every_line_with_a_newline(self):
        self.assertEqual(
            httplint.render_text([httplint.Finding(1, "H001", "x")]), "1:H001: x\n"
        )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
