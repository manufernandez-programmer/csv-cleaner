import contextlib
import csv
import errno
import io
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import cleaner

ROOT = Path(__file__).resolve().parents[1]


class CleaningTests(unittest.TestCase):
    def clean(self, text):
        return cleaner.clean_rows(io.StringIO(text, newline=""))

    def test_trims_every_field_and_deduplicates_after_cleaning(self):
        result = self.clean("name,email\n Alice , alice@example.com \nAlice,alice@example.com\nBob,bob@example.com\n")
        self.assertEqual(result.rows, [["Alice", "alice@example.com"], ["Bob", "bob@example.com"]])
        self.assertEqual((result.total, result.duplicates), (3, 1))

    def test_email_counts_include_duplicates_and_keep_problematic_rows(self):
        result = self.clean("name,email\nA, \nA,\nB,bad\nC,c@example.com\n")
        self.assertEqual((result.missing_emails, result.invalid_emails), (2, 1))
        self.assertEqual(len(result.rows), 3)
        self.assertEqual(result.warnings, [
            "Warning: missing email in row 1.",
            "Warning: missing email in row 2.",
            "Warning: basic email check failed in row 3.",
        ])

    def test_email_heuristic_is_explicitly_basic(self):
        for value in ["bad", "@example.com", "a@example"]:
            with self.subTest(value=value):
                self.assertEqual(cleaner.email_issue(value), "invalid")
        for value in ["a@example.com", "a@@example.com", "a@.", "a b@example.com"]:
            with self.subTest(value=value):
                self.assertIsNone(cleaner.email_issue(value))
        self.assertEqual(cleaner.email_issue(""), "missing")

    def test_rejects_wrong_width_and_headers(self):
        cases = [
            ("name,email\nA\n", "expected 2 columns, got 1"),
            ("name,email\nA,a@example.com,extra\n", "expected 2 columns, got 3"),
            ("email,email\na@example.com,b@example.com\n", "duplicate headers"),
            ("name,name,email\nA,B,a@example.com\n", "duplicate headers"),
            ("name,Email\n", "exact header 'email'"),
            ("name, email\n", "exact header 'email'"),
            ("name, ,email\n", "empty header"),
            ("", "empty or has no header"),
            ("\n", "empty or has no header"),
            ('name,email\n"unterminated,a@example.com\n', "Invalid CSV"),
            ('name,email\n"A"oops,a@example.com\n', "Invalid CSV"),
        ]
        for text, message in cases:
            with self.subTest(text=text):
                with self.assertRaisesRegex(cleaner.CleanerError, message):
                    self.clean(text)

    def test_quotes_commas_multiline_unicode_and_blank_lines(self):
        result = self.clean('name,email\r\n\r\n" Demo, Ñ\nItem ",a@example.com\r\n')
        self.assertEqual(result.rows, [["Demo, Ñ\nItem", "a@example.com"]])
        self.assertEqual(result.total, 1)

    def test_header_only_is_valid(self):
        result = self.clean("name,email\n")
        self.assertEqual(result.rows, [])
        self.assertEqual(result.total, 0)

    def test_headers_and_case_are_preserved(self):
        result = self.clean(" Name ,email\nA,a@example.com\na,a@example.com\n")
        self.assertEqual(result.headers, [" Name ", "email"])
        self.assertEqual(len(result.rows), 2)


class FileTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.source = Path(self.temp.name) / "sample.csv"
        self.output = self.source.with_name("sample_limpios.csv")
        self.source.write_text("name,email\n A , a@example.com \n", encoding="utf-8")

    def test_roundtrip_preserves_original_and_output_format(self):
        original = self.source.read_bytes()
        output, result = cleaner.clean_file(self.source)
        self.assertEqual(output, self.output)
        self.assertEqual(self.source.read_bytes(), original)
        self.assertEqual(output.read_bytes(), b"name,email\r\nA,a@example.com\r\n")
        self.assertEqual(result.total, 1)

    def test_existing_output_is_untouched(self):
        self.output.write_bytes(b"do not overwrite")
        with self.assertRaisesRegex(cleaner.CleanerError, "Output already exists"):
            cleaner.clean_file(self.source)
        self.assertEqual(self.output.read_bytes(), b"do not overwrite")

    def test_output_created_during_read_is_untouched(self):
        original_clean = cleaner.clean_rows
        def concurrent_creation(stream):
            result = original_clean(stream)
            self.output.write_bytes(b"another writer")
            return result
        with patch.object(cleaner, "clean_rows", side_effect=concurrent_creation):
            with self.assertRaisesRegex(cleaner.CleanerError, "Output already exists"):
                cleaner.clean_file(self.source)
        self.assertEqual(self.output.read_bytes(), b"another writer")

    def test_symlink_output_is_not_followed(self):
        try:
            self.output.symlink_to(self.source)
        except (OSError, NotImplementedError):
            self.skipTest("Symlinks unavailable")
        original = self.source.read_bytes()
        with self.assertRaisesRegex(cleaner.CleanerError, "Output already exists"):
            cleaner.clean_file(self.source)
        self.assertEqual(self.source.read_bytes(), original)

    def test_invalid_input_never_creates_output(self):
        for data, message in [
            (b"name,email\n\xff,a@example.com", "decode input as UTF-8"),
            (b"email,email\n", "duplicate headers"),
            (b'name,email\nA,a@example.com\n"oops', "Invalid CSV"),
            (b"name,email\nA,a@example.com\nB\n", "expected 2 columns"),
        ]:
            with self.subTest(data=data):
                self.source.write_bytes(data)
                with self.assertRaisesRegex(cleaner.CleanerError, message):
                    cleaner.clean_file(self.source)
                self.assertFalse(self.output.exists())
                self.assertEqual(self.source.read_bytes(), data)

    def test_utf8_bom_and_uppercase_extension(self):
        path = self.source.with_name("bom.CSV")
        path.write_bytes(b"\xef\xbb\xbfname,email\nA,a@example.com\n")
        output, result = cleaner.clean_file(path)
        self.assertEqual(output.name, "bom_limpios.csv")
        self.assertEqual(result.headers, ["name", "email"])
        self.assertFalse(output.read_bytes().startswith(b"\xef\xbb\xbf"))

    def test_missing_input_and_wrong_extension(self):
        for path, message in [
            (self.source.with_name("absent.csv"), "Cannot read input"),
            (self.source.with_suffix(".txt"), "extension"),
        ]:
            with self.subTest(path=path):
                with self.assertRaisesRegex(cleaner.CleanerError, message):
                    cleaner.clean_file(path)

    def test_directory_input(self):
        directory = self.source.with_name("directory.csv")
        directory.mkdir()
        with self.assertRaisesRegex(cleaner.CleanerError, "Cannot read input"):
            cleaner.clean_file(directory)

    def test_read_permission_and_io_errors(self):
        for error in [PermissionError(errno.EACCES, "Permission denied"), OSError(errno.EIO, "Input/output error")]:
            with self.subTest(error=error):
                with patch.object(Path, "open", side_effect=error):
                    with self.assertRaisesRegex(cleaner.CleanerError, "Cannot read input"):
                        cleaner.clean_file(self.source)
                self.assertFalse(self.output.exists())

    def test_output_permission_error(self):
        real_open = Path.open
        def denied(path, mode="r", **kwargs):
            if mode == "x":
                raise PermissionError(errno.EACCES, "Permission denied")
            return real_open(path, mode, **kwargs)
        with patch.object(Path, "open", denied):
            with self.assertRaisesRegex(cleaner.CleanerError, "Cannot write output.*Permission denied"):
                cleaner.clean_file(self.source)
        self.assertFalse(self.output.exists())

    def test_write_failure_warns_about_partial_file(self):
        with patch.object(csv, "writer", side_effect=OSError(errno.ENOSPC, "No space left on device")):
            with self.assertRaisesRegex(cleaner.CleanerError, "Cannot write output.*partial output may remain"):
                cleaner.clean_file(self.source)
        self.assertTrue(self.output.exists())

    def test_flush_failure_is_reported(self):
        real_open = Path.open
        @contextlib.contextmanager
        def failing_close(path, mode="r", **kwargs):
            with real_open(path, mode, **kwargs) as stream:
                yield stream
                if mode == "x":
                    raise OSError(errno.EIO, "flush failed")
        with patch.object(Path, "open", failing_close):
            with self.assertRaisesRegex(cleaner.CleanerError, "flush failed.*partial output may remain"):
                cleaner.clean_file(self.source)

    def test_cli_success_error_and_help(self):
        def run(*args):
            return subprocess.run([sys.executable, str(ROOT / "cleaner.py"), *map(str, args)], capture_output=True, text=True)
        success = run(self.source)
        self.assertEqual(success.returncode, 0, success.stderr)
        self.assertIn("Rows exported:       1", success.stdout)
        self.assertEqual(success.stderr, "")
        existing = run(self.source)
        self.assertEqual(existing.returncode, 1)
        self.assertEqual(existing.stdout, "")
        self.assertIn("Output already exists", existing.stderr)
        self.assertNotIn("Traceback", existing.stderr)
        self.assertEqual(run("--help").returncode, 0)
        self.assertEqual(run().returncode, 2)
        self.assertEqual(run(self.source, "extra").returncode, 2)

    def test_import_has_no_cli_side_effects(self):
        result = subprocess.run([sys.executable, "-c", "import cleaner"], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual((result.returncode, result.stdout, result.stderr), (0, "", ""))


if __name__ == "__main__":
    unittest.main()
