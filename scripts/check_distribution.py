"""Inspect release archives rather than relying on Git ignore rules."""

import re
import tarfile
import zipfile
from pathlib import Path


def inspect(name: str, content: bytes) -> None:
    if any(part in name.split("/") for part in (".env", ".venv", "runtime", "data")):
        raise ValueError(f"Private path in distribution: {name}")
    if Path(name).suffix in {".pdf", ".docx", ".sqlite3", ".db"}:
        raise ValueError(f"Private runtime file in distribution: {name}")
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        return
    if re.search(r"[\u3400-\u9fff\uf900-\ufaff]", text):
        raise ValueError(f"Non-English CJK text in distribution: {name}")
    if re.search(r"/(?:Users|home)/[A-Za-z][\w.-]+/", text):
        raise ValueError(f"Personal machine path in distribution: {name}")


def main() -> None:
    archives = list(Path("dist").glob("*"))
    if not archives:
        raise SystemExit("No distribution archives found.")
    for path in archives:
        if path.name == ".gitignore":
            continue
        if path.suffix == ".whl":
            with zipfile.ZipFile(path) as archive:
                for name in archive.namelist():
                    inspect(name, archive.read(name))
        elif path.name.endswith(".tar.gz"):
            with tarfile.open(path) as archive:
                for member in archive.getmembers():
                    if member.isfile():
                        inspect(member.name, archive.extractfile(member).read())
        else:
            raise ValueError(f"Unexpected build artifact: {path.name}")
    print(f"Distribution content check passed ({len(archives)} archives).")


if __name__ == "__main__":
    main()
