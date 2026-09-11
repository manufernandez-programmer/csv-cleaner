"""Run the real CLI in a temporary directory and verify the public demo."""

import argparse
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="also check README and captured transcript")
    args = parser.parse_args()
    with tempfile.TemporaryDirectory() as directory:
        work = Path(directory)
        shutil.copyfile(ROOT / "cleaner.py", work / "cleaner.py")
        shutil.copyfile(ROOT / "examples/sample.csv", work / "sample.csv")
        run = subprocess.run([sys.executable, "cleaner.py", "sample.csv"], cwd=work, capture_output=True, text=True, encoding="utf-8", check=True)
        if run.stderr:
            raise RuntimeError(run.stderr)
        output = (work / "sample_limpios.csv").read_bytes()
        if output != (ROOT / "examples/expected.csv").read_bytes():
            raise RuntimeError("Generated CSV differs from examples/expected.csv")
        transcript = "$ python cleaner.py sample.csv\n" + run.stdout
        transcript += "\n$ cat sample_limpios.csv\n" + output.decode("utf-8").replace("\r\n", "\n")
        if args.check:
            if transcript != (ROOT / "docs/demo.txt").read_text(encoding="utf-8"):
                raise RuntimeError("Captured demo differs from the real CLI output")
            if "```text\n" + run.stdout + "```" not in (ROOT / "README.md").read_text(encoding="utf-8"):
                raise RuntimeError("README output differs from the real CLI output")
        print(transcript, end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
