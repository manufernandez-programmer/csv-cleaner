"""Clean small UTF-8 CSV files without overwriting existing output."""

import argparse
import csv
from dataclasses import dataclass, field
from pathlib import Path
import sys


class CleanerError(Exception):
    """An actionable input or output error suitable for the command line."""


@dataclass
class CleanResult:
    headers: list[str]
    rows: list[list[str]] = field(default_factory=list)
    total: int = 0
    duplicates: int = 0
    missing_emails: int = 0
    invalid_emails: int = 0
    warnings: list[str] = field(default_factory=list)


def email_issue(value: str) -> str | None:
    """Preserve the original, deliberately basic email heuristic."""
    if not value:
        return "missing"
    local, separator, domain = value.partition("@")
    if not separator or not local or "." not in domain:
        return "invalid"
    return None


def clean_rows(stream) -> CleanResult:
    """Parse and validate before writing; preserve first occurrence and order."""
    reader = csv.reader(stream, strict=True)
    try:
        headers = next(reader, None)
        if not headers:
            raise CleanerError("CSV is empty or has no header.")
        if len(set(headers)) != len(headers):
            raise CleanerError("CSV contains duplicate headers.")
        if any(not name.strip() for name in headers):
            raise CleanerError("CSV contains an empty header.")
        if "email" not in headers:
            raise CleanerError("CSV must contain the exact header 'email'.")
        email_index = headers.index("email")
        result = CleanResult(headers)
        seen = set()
        for row in reader:
            if not row:  # Match DictReader's handling of completely blank lines.
                continue
            result.total += 1
            if len(row) != len(headers):
                raise CleanerError(
                    f"Row {result.total}: expected {len(headers)} columns, got {len(row)}."
                )
            cleaned = [value.strip() for value in row]
            issue = email_issue(cleaned[email_index])
            if issue == "missing":
                result.missing_emails += 1
                result.warnings.append(f"Warning: missing email in row {result.total}.")
            elif issue == "invalid":
                result.invalid_emails += 1
                result.warnings.append(f"Warning: basic email check failed in row {result.total}.")
            key = tuple(cleaned)
            if key in seen:
                result.duplicates += 1
            else:
                seen.add(key)
                result.rows.append(cleaned)
        return result
    except csv.Error as exc:
        raise CleanerError(f"Invalid CSV near physical line {reader.line_num}: {exc}.") from exc


def clean_file(input_path: Path) -> tuple[Path, CleanResult]:
    """Read UTF-8 input, then exclusively create its sibling *_limpios.csv."""
    input_path = Path(input_path)
    if input_path.suffix.lower() != ".csv":
        raise CleanerError("Input file must have a '.csv' extension.")
    output_path = input_path.with_name(input_path.stem + "_limpios.csv")
    try:
        with input_path.open("r", newline="", encoding="utf-8-sig") as stream:
            result = clean_rows(stream)
    except UnicodeError as exc:
        raise CleanerError("Cannot decode input as UTF-8. Convert the file to UTF-8 first.") from exc
    except OSError as exc:
        raise CleanerError(f"Cannot read input '{input_path}': {exc.strerror or str(exc)}.") from exc

    created = False
    try:
        # Exclusive creation also protects against a file appearing after validation.
        with output_path.open("x", newline="", encoding="utf-8") as stream:
            created = True
            writer = csv.writer(stream)
            writer.writerow(result.headers)
            writer.writerows(result.rows)
    except FileExistsError as exc:
        raise CleanerError(
            f"Output already exists: '{output_path}'. Move or rename it before retrying."
        ) from exc
    except (OSError, UnicodeError, csv.Error) as exc:
        detail = exc.strerror if isinstance(exc, OSError) and exc.strerror else str(exc)
        partial = " A partial output may remain; inspect it before removing or renaming it." if created else ""
        raise CleanerError(f"Cannot write output '{output_path}': {detail}.{partial}") from exc
    return output_path, result


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="MARS CSV Cleaner: trim fields, remove duplicate rows, and flag basic email issues."
    )
    parser.add_argument("input", type=Path, help="UTF-8, comma-separated .csv file with an exact 'email' header")
    args = parser.parse_args(argv)
    try:
        output_path, result = clean_file(args.input)
    except CleanerError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    for warning in result.warnings:
        print(warning)
    print(f"Cleaned file created: {output_path}")
    print("\nMARS CSV Cleaner\n")
    print(f"Rows received:       {result.total}")
    print(f"Duplicates removed:  {result.duplicates}")
    print(f"Missing emails:      {result.missing_emails}")
    print(f"Invalid emails:      {result.invalid_emails}")
    print(f"Rows exported:       {len(result.rows)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
