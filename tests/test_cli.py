"""Exercise CLI behavior through the same entry point used by installed commands."""

import json
import sys

import pytest

from applypilot.cli import main


def invoke(monkeypatch, capsys, root, *args):
    monkeypatch.setattr(sys, "argv", ["applypilot", "--data-dir", str(root), *args])
    main()
    return capsys.readouterr().out


def test_cli_demo_doctor_and_exports(monkeypatch, capsys, tmp_path):
    assert json.loads(invoke(monkeypatch, capsys, tmp_path, "init"))["initialized"]
    assert json.loads(invoke(monkeypatch, capsys, tmp_path, "demo"))["imported"] == 7
    assert not json.loads(invoke(monkeypatch, capsys, tmp_path, "doctor"))["network_contacted"]
    exported = json.loads(invoke(monkeypatch, capsys, tmp_path, "export"))
    assert len(exported["jobs"]) == 7
    assert "company" in invoke(monkeypatch, capsys, tmp_path, "export", "--format", "csv")


def test_cli_import_and_actionable_error(monkeypatch, capsys, tmp_path):
    source = tmp_path / "fictional.csv"
    source.write_text("title,company,url\nAnalyst,Example,https://example.com/role\n")
    assert json.loads(invoke(monkeypatch, capsys, tmp_path, "import", str(source)))["imported"] == 1
    with pytest.raises(SystemExit) as error:
        invoke(monkeypatch, capsys, tmp_path, "collect")
    assert error.value.code == 1
