"""Check portable frontmatter and local resources without a particular agent host."""

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "applypilot-local"


def validate(folder=SKILL):
    folder = Path(folder)
    entry = folder / "SKILL.md"
    raw = entry.read_text(encoding="utf-8")
    match = re.match(r"\A---\n(.*?)\n---\n(.+)\Z", raw, re.DOTALL)
    if not match:
        raise ValueError("SKILL.md requires YAML frontmatter and a body.")
    metadata = yaml.safe_load(match[1])
    if set(metadata) != {"name", "description"}:
        raise ValueError("Use portable name/description frontmatter only.")
    if metadata["name"] != folder.name or not re.fullmatch(r"[a-z0-9-]{1,64}", folder.name):
        raise ValueError("Skill name must match its folder.")
    if (
        not isinstance(metadata["description"], str)
        or not 20 <= len(metadata["description"]) <= 1024
    ):
        raise ValueError("A concise, descriptive trigger is required.")
    for file in folder.rglob("*.md"):
        content = file.read_text(encoding="utf-8")
        for target in re.findall(r"\]\(([^)]+)\)", content):
            if "://" in target or target.startswith("#"):
                continue
            path = (file.parent / target.split("#")[0]).resolve()
            if not path.is_relative_to(folder.resolve()) or not path.is_file():
                raise ValueError(f"Missing or external skill reference: {target}")
    for helper in (
        "batch_lib.py",
        "strategy.py",
        "daily_report.py",
        "render_resume.py",
        "publish_batch.py",
        "validate_batch.py",
        "requirements-pdf.txt",
    ):
        if not (folder / "scripts" / helper).is_file():
            raise ValueError(f"Missing helper resource: {helper}")
    print(f"Portable skill validation passed: {folder.name}")


if __name__ == "__main__":
    validate()
