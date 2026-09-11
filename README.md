# MARS CSV Cleaner

A focused Python CLI for cleaning small CSV exports: trim whitespace, remove duplicate rows, and flag basic email issues while keeping the original file intact.

**Python 3.10+ · Standard library only · Automated tests · Reproducible demo**

## Overview

CSV Cleaner turns a repetitive spreadsheet cleanup task into a repeatable local command. It is a small portfolio project demonstrating file handling, explicit validation, testable Python functions, and automation with GitHub Actions.

## Problem

Contact and product exports often contain padded fields, repeated records, and missing or suspicious email addresses. Manual cleanup is easy to repeat inconsistently, and silently overwriting an earlier result can lose work.

## Solution

Read and validate the input, trim each field, keep the first occurrence of each distinct cleaned row, and create a separate CSV. Email warnings identify records for review without discarding them. Existing output files are never overwritten.

## Features

- Trim leading and trailing whitespace from every data field.
- Remove identical rows **after trimming**, preserving the first occurrence and input order.
- Report missing emails and failures of a deliberately basic email check.
- Reject duplicate or empty headers, missing `email`, and rows with missing or extra columns.
- Report parsing errors detected by Python's strict CSV reader.
- Explain UTF-8 decoding, input/output, permission, and existing-output errors.
- Work locally with no third-party Python dependencies or network calls.

## Requirements

- Python **3.10 or newer**.
- Git to clone the repository.

No package installation or `requirements.txt` is needed. Commands below use `python`; use `python3` if that is how Python 3 is available on your system. The CLI works in a terminal on Arch/CachyOS and other systems with a supported Python interpreter.

## Supported input assumptions

| Input | Contract |
| --- | --- |
| Filename | `.csv` extension, case-insensitive |
| Encoding | UTF-8; an optional leading UTF-8 BOM is accepted |
| Delimiter | Comma; no delimiter detection |
| Header | First record; unique, nonblank column names and the exact, case-sensitive `email` header |
| Header normalization | Headers are preserved, not trimmed or renamed; `Email` and ` email` do not satisfy `email` |
| Records | Same number of fields as the header; quoted commas, doubled quotes, and quoted multiline fields are supported |
| Empty content | An empty file or empty first record is rejected; a valid header with zero data rows is accepted |
| Blank lines | Completely blank records after the header are skipped |

## Quick start

```bash
git clone https://github.com/manufernandez-programmer/csv-cleaner.git
cd csv-cleaner
python cleaner.py --help
python cleaner.py examples/sample.csv
```

The last command creates `examples/sample_limpios.csv`. Running it again fails safely until you move or rename that output. The checked-in reference is named `examples/expected.csv`, so a fresh clone can run the example immediately.

## Usage

```bash
python cleaner.py path/to/input.csv
```

There is one positional input argument and no overwrite option. The output is always a sibling of the input: `input.csv` becomes `input_limpios.csv`.

| Exit code | Meaning |
| --- | --- |
| `0` | Success, including files with email warnings; also `--help` |
| `1` | Input validation, decoding, reading, or writing failed |
| `2` | Command-line usage error, such as a missing or extra argument |

Success summaries and email warnings go to standard output. Errors go to standard error without a traceback for handled failures. Warnings identify row numbers without printing email values.

## Reproducible example

All sample products, places, and email values are fictitious. Valid sample addresses use `example.com`; `not-an-email` and `adapter@example` are intentionally malformed.

[Input CSV](examples/sample.csv) → [expected cleaned CSV](examples/expected.csv)

Run the demo from the repository root:

```bash
python scripts/demo.py
```

It copies the script and sample into a temporary directory, executes the real CLI, verifies the output against `examples/expected.csv`, and prints the captured session. It can be rerun without colliding with existing example output. The CLI produces:

```text
Warning: missing email in row 4.
Warning: basic email check failed in row 5.
Warning: basic email check failed in row 6.
Cleaned file created: sample_limpios.csv

MARS CSV Cleaner

Rows received:       6
Duplicates removed:  1
Missing emails:      1
Invalid emails:      2
Rows exported:       5
```

The sample demonstrates padded fields, a duplicate that becomes identical after trimming, a missing email, and two basic format failures. The [captured text demo](docs/demo.txt) includes both the actual console output and cleaned CSV; it is a recorded execution, not a mock screenshot.

## Output behavior

- The input is opened read-only. All parsing and structural checks finish before the output is created.
- Output uses exclusive creation (`x` mode), so an existing path is rejected even if it appears during processing. The tool also refuses an existing output symlink.
- Output is UTF-8 without a BOM, with comma-separated fields, standard CSV quoting, and CRLF record endings from Python's CSV writer. Original quoting and line endings are not preserved.
- On a write or flush failure, a partial output **may remain**. The error explicitly asks you to inspect it before removing or renaming it. There is no automatic deletion or retry.
- Warnings and the success summary appear only after output is written successfully.
- Row numbers and `Rows received` count nonblank data records, excluding the header. Quoted multiline records count as one row. Parser errors instead report a physical line number.
- Email counts include **all input records before deduplication**, including duplicate records. `Rows exported` equals `Rows received` minus `Duplicates removed`.

## Design decisions

- **Standard library:** `csv`, `argparse`, `pathlib`, and `unittest` keep setup small and the code approachable.
- **Small functions:** `email_issue()` implements the heuristic, `clean_rows()` parses and cleans, `clean_file()` handles files, and `main()` handles the CLI. Importing the module does not run the program.
- **Stable, whole-row deduplication:** every trimmed field participates; matching emails alone do not make two rows duplicates. Comparisons remain case-sensitive.
- **Review rather than delete:** missing or suspicious emails stay in the output so a person can decide what to fix.
- **Compatibility:** the original cleaning rules and `_limpios.csv` suffix remain; CLI messages are now consistently in English.
- **Private working data:** `.env` files, virtual environments, caches, generated `*_limpios.csv` files, and `/private-data/` are ignored by Git. Public fixtures stay tracked. Ignore rules do not remove files already committed.

## Limitations

This is **not full email validation**. The preserved heuristic only checks that a nonempty value has an `@`, a nonempty part before its first `@`, and a dot somewhere after it. It may accept `a@@example.com`, `a@.`, or addresses containing spaces. It does not implement RFC validation, DNS checks, mailbox existence, or deliverability verification.

CSV parsing uses `csv.reader(..., strict=True)`, not a complete CSV specification validator. Some unusual quote patterns can still be accepted by Python; field sizes are subject to its default CSV parser limit. Semicolon-separated files, other encodings, schema inference, and data-type validation are outside the supported contract.

Unique rows, deduplication keys, and warnings are held in memory. This utility targets small exports, not files of arbitrary size. It does not sanitize spreadsheet formulas or interpret cell contents beyond trimming and the email heuristic. Output creation prevents overwrites but is not a transactional or crash-durable storage system.

## Testing

From the repository root:

```bash
python -m unittest discover -s tests -v
python scripts/demo.py --check
```

The suite covers trimming, duplicate handling, email counts, field counts, duplicate and invalid headers, quoted and multiline CSV, Unicode/BOM input, existing output, concurrent output creation, symlinks, CLI exit codes, and import behavior. Permission and I/O failures are simulated for deterministic tests, including environments that run with elevated permissions.

The demo check compares the actual output bytes to the expected fixture and verifies both the saved transcript and README output. GitHub Actions runs the tests and demo check on Python 3.10–3.14 using a hosted Linux runner.

## Project status

A focused portfolio utility under active improvement. The repository includes executable examples and tests; it does not claim production-scale performance or external customer results. No new release is being published as part of this polish.

**License decision pending:** no license has been selected or added. The owner will decide reuse terms before the project is described as permissively licensed.
