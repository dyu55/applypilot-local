"""Reject CJK text, private runtime files, machine paths, and obvious secrets."""

import re
import subprocess
from pathlib import Path


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    paths = subprocess.check_output(["git", "ls-files", "-z"], cwd=root).decode().split("\0")
    problems = []
    for name in filter(None, paths):
        path = root / name
        if path.suffix.lower() in {".pdf", ".docx", ".db", ".sqlite", ".sqlite3"}:
            problems.append(f"Private runtime file: {name}")
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if re.search(r"[\u3400-\u9fff\uf900-\ufaff]", content):
            problems.append(f"Non-English CJK text: {name}")
        if re.search(r"/(?:Users|home)/[A-Za-z][\w.-]+/", content):
            problems.append(f"Personal machine path: {name}")
        if re.search(r"(?:gh[pousr]_[A-Za-z0-9]{20,}|sk-[A-Za-z0-9]{24,})", content):
            problems.append(f"Possible credential: {name}")
    if problems:
        raise SystemExit("\n".join(problems))
    print(f"Repository content check passed ({len(paths) - 1} files).")


if __name__ == "__main__":
    main()
