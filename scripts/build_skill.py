"""Build a portable skill ZIP, not an application package."""

import re
import zipfile
from pathlib import Path

from check_repository import inspect
from validate_skill import validate

ROOT = Path(__file__).resolve().parents[1]


def build(output=None):
    from hashlib import sha256

    folder = ROOT / "skills" / "applypilot-local"
    validate(folder)
    version = (ROOT / "VERSION").read_text().strip()
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        raise ValueError("VERSION must be a semantic release version.")
    output = Path(output) if output else ROOT / "dist"
    output.mkdir(parents=True, exist_ok=True)
    archive = output / f"applypilot-local-v{version}.zip"
    allowed = {".md", ".py", ".txt"}
    files = [
        path for path in folder.rglob("*") if path.is_file() and "__pycache__" not in path.parts
    ]
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as target:
        for path in sorted(files):
            if path.is_symlink() or (path.suffix not in allowed and path.name != "LICENSE"):
                raise ValueError(f"Unexpected skill resource: {path.name}")
            name = path.relative_to(folder.parent).as_posix()
            content = path.read_bytes()
            problems = inspect(name, content)
            if problems:
                raise ValueError("\n".join(problems))
            info = zipfile.ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            target.writestr(info, content)
    digest = sha256(archive.read_bytes()).hexdigest()
    (output / "SHA256SUMS.txt").write_text(f"{digest}  {archive.name}\n", encoding="utf-8")
    print(f"Built {archive.name} ({len(files)} skill resources).")
    return archive


if __name__ == "__main__":
    build()
