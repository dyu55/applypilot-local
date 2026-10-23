"""Exercise an extracted portable skill outside its source checkout."""

import json
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))
from fixture_batch import fixture  # noqa: E402


def smoke(archive=None):
    version = (ROOT / "VERSION").read_text().strip()
    archive = Path(archive) if archive else ROOT / "dist" / f"applypilot-local-v{version}.zip"
    with tempfile.TemporaryDirectory(prefix="skill smoke ") as temp:
        root = Path(temp)
        with zipfile.ZipFile(archive) as content:
            content.extractall(root)
        skill = root / "applypilot-local"
        stage = root / "private workspace" / "staging"
        fixture(stage, skill)
        output = root / "private workspace" / "batches"
        result = subprocess.run(
            [sys.executable, str(skill / "scripts/publish_batch.py"), str(stage), str(output)],
            check=True,
            text=True,
            capture_output=True,
            cwd=root,
        )
        published = json.loads(result.stdout)
        assert published["status"] == "ready"
        result = subprocess.run(
            [sys.executable, str(skill / "scripts/validate_batch.py"), published["path"]],
            check=True,
            text=True,
            capture_output=True,
            cwd=root,
        )
        assert json.loads(result.stdout)["published"] is True
    print(
        "Extracted skill smoke passed: fictional PDF, dated batch, handoff, and hash verification."
    )


if __name__ == "__main__":
    smoke()
