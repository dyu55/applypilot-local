"""Reject CJK text, private runtime files, machine paths, and obvious secrets."""

import re
import subprocess
from pathlib import Path


def inspect(name, content):
    problems = []
    if Path(name).suffix.lower() in {".pdf", ".docx", ".db", ".sqlite", ".sqlite3"}:
        problems.append(f"Private runtime file: {name}")
    if any(part in name.split("/") for part in (".env", "state", "batches", "runtime")):
        problems.append(f"Private runtime path: {name}")
    try:
        value = content.decode("utf-8")
    except UnicodeDecodeError:
        return problems
    if re.search(r"[\u3400-\u9fff\uf900-\ufaff]", value):
        problems.append(f"Non-English CJK text: {name}")
    if re.search(r"/(?:Users|home)/[A-Za-z][\w.-]+/", value):
        problems.append(f"Personal machine path: {name}")
    if re.search(r"(?:gh[pousr]_[A-Za-z0-9]{20,}|sk-[A-Za-z0-9]{24,})", value):
        problems.append(f"Possible credential: {name}")
    return problems


def main():
    root = Path(__file__).resolve().parents[1]
    paths = (
        subprocess.check_output(
            ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"], cwd=root
        )
        .decode()
        .split("\0")
    )
    problems = []
    count = 0
    for name in sorted(set(filter(None, paths))):
        path = root / name
        if path.is_file():
            count += 1
            problems.extend(inspect(name, path.read_bytes()))
    if problems:
        raise SystemExit("\n".join(problems))
    print(f"Repository content check passed ({count} files).")


if __name__ == "__main__":
    main()
