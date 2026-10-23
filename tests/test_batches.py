import copy
import json

import pytest
from batch_lib import canonical_url, pdf_quality, safe_file, validate
from conftest import SKILL
from fixture_batch import fixture, save
from publish_batch import publish
from render_resume import render
from validate_batch import check


def test_complete_batch_and_handoff(tmp_path):
    source = tmp_path / "staging with spaces"
    fixture(source, SKILL)
    (source / "private-extra.txt").write_text("Private extra file must not be copied.")
    result = publish(source, tmp_path / "batches")
    folder = tmp_path / "batches" / "2026-10-23" / "fixture-run"
    assert result["path"] == str(folder.resolve())
    assert result["status"] == "ready"
    assert result["summary"]["ready"] == 1
    assert check(folder)["published"] is True
    assert not (folder / "private-extra.txt").exists()
    handoff = json.loads((folder / "handoff.json").read_text())
    assert handoff["submission_authorized"] is False
    assert handoff["applications"][0]["application_status"] == "Pending"
    assert handoff["applications"][0]["files"]["resume_pdf"] == "jobs/design-01/resume.pdf"
    manifest = json.loads((folder / "manifest.json").read_text())
    assert manifest["verified_submissions"] == 0
    assert manifest["validation"]["pdf_quality"]["design-01"]["text_verified"]


def test_rerun_preserves_prior_batch(tmp_path):
    stage = tmp_path / "stage"
    data = fixture(stage, SKILL, ready=False)
    root = tmp_path / "batches"
    first = publish(stage, root)
    original = (root / data["date"] / data["run_id"] / "manifest.json").read_bytes()
    with pytest.raises(ValueError, match="already exists"):
        publish(stage, root)
    data["run_id"] = "second-run"
    save(stage, data)
    second = publish(stage, root)
    assert first["path"] != second["path"]
    assert (root / data["date"] / "fixture-run" / "manifest.json").read_bytes() == original
    assert json.loads((root / data["date"] / "latest.json").read_text())["run_id"] == "second-run"


def test_draft_and_zero_results_are_blocked(tmp_path):
    stage = tmp_path / "stage"
    data = fixture(stage, SKILL, ready=False)
    assert publish(stage, tmp_path / "batches")["status"] == "blocked"
    data["jobs"] = []
    data["run_id"] = "zero-run"
    save(stage, data)
    result = publish(stage, tmp_path / "batches")
    assert result["status"] == "blocked"
    assert result["summary"]["shortfall"] == 1


def test_shortfall_and_sources_are_separate(tmp_path):
    stage = tmp_path / "stage"
    data = fixture(stage, SKILL)
    data["requested_count"] = 2
    data["source_reports"][0]["outcome"] = "blocked"
    save(stage, data)
    result = publish(stage, tmp_path / "batches")
    manifest = json.loads(
        (tmp_path / "batches" / data["date"] / data["run_id"] / "manifest.json").read_text()
    )
    assert result["status"] == "partial"
    assert manifest["source_health"] == "degraded"
    assert result["summary"]["shortfall"] == 1


@pytest.mark.parametrize(
    "mutation",
    [
        lambda d: d.update(date="../escape"),
        lambda d: d.update(run_id="../escape"),
        lambda d: d.update(requested_count=0),
        lambda d: d.update(created_at="2026-10-23T09:00:00"),
        lambda d: d.update(date="2026-10-24"),
        lambda d: d["jobs"][0].update(application_status="Submitted"),
        lambda d: d["jobs"][0]["availability"].update(status="unknown"),
        lambda d: d["jobs"][0]["materials"]["review"].update(pdf_visual_checked=False),
        lambda d: d["jobs"][0]["materials"]["files"].update(resume_md="../private.txt"),
        lambda d: d["jobs"][0].update(url="https://user:secret@example.com/jobs/1"),
    ],
)
def test_invalid_ready_batch_rejected(tmp_path, mutation):
    data = fixture(tmp_path, SKILL)
    mutation(data)
    save(tmp_path, data)
    with pytest.raises((ValueError, OSError)):
        validate(tmp_path)


def test_duplicate_tracking_url_rejected(tmp_path):
    data = fixture(tmp_path, SKILL, ready=False)
    duplicate = copy.deepcopy(data["jobs"][0])
    duplicate["id"] = "another-id"
    duplicate["url"] += "?utm_source=duplicate"
    data["jobs"].append(duplicate)
    save(tmp_path, data)
    with pytest.raises(ValueError, match="Duplicate posting URL"):
        validate(tmp_path)
    assert (
        canonical_url("https://example.com/job?id=4&utm_source=x") == "https://example.com/job?id=4"
    )


def test_invalid_publish_keeps_latest_intact(tmp_path):
    stage = tmp_path / "stage"
    data = fixture(stage, SKILL, ready=False)
    root = tmp_path / "batches"
    publish(stage, root)
    pointer = root / data["date"] / "latest.json"
    before = pointer.read_bytes()
    data["run_id"] = "broken"
    data["jobs"][0]["materials"]["files"]["resume_md"] = "missing.md"
    save(stage, data)
    with pytest.raises(ValueError):
        publish(stage, root)
    assert pointer.read_bytes() == before
    assert not (root / data["date"] / "broken").exists()


def test_tampered_file_detected(tmp_path):
    stage = tmp_path / "stage"
    fixture(stage, SKILL, ready=False)
    result = publish(stage, tmp_path / "batches")
    from pathlib import Path

    folder = Path(result["path"])
    (folder / "HANDOFF.md").write_text("Changed after publication.")
    with pytest.raises(ValueError, match="Published file changed"):
        check(folder)


def test_symlink_rejected(tmp_path):
    target = tmp_path / "original.txt"
    target.write_text("Original")
    link = tmp_path / "linked.txt"
    try:
        link.symlink_to(target)
    except OSError:
        pytest.skip("Creating symlinks requires an additional Windows privilege.")
    with pytest.raises(ValueError, match="Symlink"):
        safe_file(tmp_path, "linked.txt")


def test_pdf_renderer_preserves_words_and_output(tmp_path):
    fixture(tmp_path, SKILL)
    pdf = tmp_path / "jobs/design-01/resume.pdf"
    source = tmp_path / "jobs/design-01/resume.md"
    quality = pdf_quality(pdf, source.read_text())
    assert quality["pages"] >= 1
    before = pdf.read_bytes()
    with pytest.raises(ValueError, match="already exists"):
        render(source, pdf)
    assert pdf.read_bytes() == before
    with pytest.raises(ValueError, match="lost words"):
        pdf_quality(pdf, source.read_text() + " Nonexistentword")


def test_failed_render_leaves_no_pdf(tmp_path):
    source = tmp_path / "resume.md"
    source.write_text("Too short")
    output = tmp_path / "resume.pdf"
    with pytest.raises(ValueError, match="substantive"):
        render(source, output)
    assert not output.exists()


def test_needs_user_excluded_from_handoff(tmp_path):
    data = fixture(tmp_path / "stage", SKILL, ready=False)
    data["jobs"][0].update(decision="needs_user", application_status="Needs user")
    data["pending_questions"] = ["Do you require sponsorship in the job's country?"]
    save(tmp_path / "stage", data)
    result = publish(tmp_path / "stage", tmp_path / "batches")
    from pathlib import Path

    handoff = json.loads((Path(result["path"]) / "handoff.json").read_text())
    assert handoff["applications"] == []
    assert len(handoff["pending_questions"]) == 1


def test_failed_index_generation_is_atomic(tmp_path, monkeypatch):
    import publish_batch

    stage = tmp_path / "stage"
    data = fixture(stage, SKILL, ready=False)
    root = tmp_path / "batches"
    publish(stage, root)
    day = root / data["date"]
    before = (day / "latest.json").read_bytes()
    data["run_id"] = "interrupted-run"
    save(stage, data)

    def fail(*args):
        raise OSError("Simulated disk failure before publication")

    monkeypatch.setattr(publish_batch, "indexes", fail)
    with pytest.raises(OSError, match="Simulated"):
        publish(stage, root)
    assert (day / "latest.json").read_bytes() == before
    assert not (day / "interrupted-run").exists()
    assert not (day / ".publish.lock").exists()
    assert not list(day.glob("staging-*"))


def test_existing_writer_lock_preserved(tmp_path):
    stage = tmp_path / "stage"
    data = fixture(stage, SKILL, ready=False)
    root = tmp_path / "batches"
    day = root / data["date"]
    day.mkdir(parents=True)
    lock = day / ".publish.lock"
    lock.write_text("another-writer")
    with pytest.raises(ValueError, match="publication holds"):
        publish(stage, root)
    assert lock.read_text() == "another-writer"


def test_unsupported_glyph_does_not_silently_disappear(tmp_path):
    from fixture_batch import RESUME

    source = tmp_path / "resume.md"
    source.write_text(RESUME + chr(0x1F680), encoding="utf-8")
    output = tmp_path / "resume.pdf"
    with pytest.raises(ValueError, match="Unsupported glyphs"):
        render(source, output)
    assert not output.exists()
