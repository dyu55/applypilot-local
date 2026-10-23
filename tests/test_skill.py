import zipfile

import pytest
from build_skill import build
from check_repository import inspect
from conftest import SKILL
from smoke_skill import smoke
from validate_skill import validate


def test_skill_and_release_archive(tmp_path):
    validate(SKILL)
    archive = build(tmp_path)
    with zipfile.ZipFile(archive) as content:
        names = content.namelist()
        assert "applypilot-local/SKILL.md" in names
        assert "applypilot-local/scripts/batch_lib.py" in names
        assert "applypilot-local/references/output-contract.md" in names
        assert not any("tests/" in name or "__pycache__" in name for name in names)
    smoke(archive)


def test_repository_scan_rejects_private_files_and_cjk():
    assert inspect("candidate.pdf", b"private")
    assert inspect("SKILL.md", chr(0x4E00).encode())
    assert inspect("state/profile.json", b"{}")
    assert not inspect("SKILL.md", b"English skill instructions.")


def test_missing_reference_is_reported(tmp_path):
    folder = tmp_path / "example-skill"
    folder.mkdir()
    (folder / "SKILL.md").write_text(
        "---\nname: example-skill\ndescription: A meaningful skill description for tests.\n"
        "---\nRead [missing](missing.md).\n"
    )
    with pytest.raises(ValueError, match="Missing or external"):
        validate(folder)
