import copy
import json
import shutil
from pathlib import Path

import pytest
from batch_lib import validate
from conftest import SKILL
from fixture_batch import fixture, save
from publish_batch import publish
from validate_batch import check


def report_for(stage, output):
    result = publish(stage, output)
    return result, json.loads((Path(result["path"]) / "daily_report.json").read_text())


def add_second_job(stage, data, ready=True):
    original = stage / "jobs/design-01"
    shutil.copytree(original, stage / "jobs/design-02")
    job = copy.deepcopy(data["jobs"][0])
    job.update(
        id="design-02", url="https://example.com/jobs/design-02", requisition_id="design-02", rank=2
    )
    job["materials"]["files"] = {
        key: value.replace("design-01", "design-02")
        for key, value in job["materials"]["files"].items()
    }
    if not ready:
        job["materials"].update(status="draft", reason="Rendered-page review is not complete.")
    data["jobs"].append(job)
    data["requested_count"] = data["strategy"]["target_count"] = 2
    return job


def test_daily_report_pass_has_counts_and_section_evidence(tmp_path):
    stage = tmp_path / "stage"
    fixture(stage, SKILL)
    result, report = report_for(stage, tmp_path / "batches")
    assert result["report_result"] == report["result"] == "PASS"
    assert report["counts"]["jobs_selected"] == report["counts"]["jobs_ready"] == 1
    assert report["counts"]["resume_pdfs_prepared"] == 1
    assert report["issues"] == []
    assert {item["basis"] for item in report["sections"]} >= {
        "bundled_helper",
        "agent_attestation",
        "computed_counts",
    }
    folder = Path(result["path"])
    assert "Result: **PASS**" in (folder / "DAILY_REPORT.md").read_text()
    assert check(folder)["published"] is True


def test_generated_pdf_is_not_automatically_ready(tmp_path):
    stage = tmp_path / "stage"
    data = fixture(stage, SKILL)
    add_second_job(stage, data, ready=False)
    save(stage, data)
    _, report = report_for(stage, tmp_path / "batches")
    assert report["result"] == "WARN"
    assert report["counts"]["resume_pdfs_prepared"] == 2
    assert report["counts"]["resume_pdfs_validated"] == 1
    assert report["counts"]["jobs_ready"] == 1


@pytest.mark.parametrize(
    "change",
    [
        lambda data: data["source_reports"][0].update(outcome="blocked"),
        lambda data: data["pending_questions"].append("Confirm an unresolved preference."),
        lambda data: data["workflow_checks"]["deduplication"].update(status="not_run"),
        lambda data: data["strategy"]["role_quotas"].update({"Another role": 1}),
        lambda data: data["strategy"]["collection"]["sources"].append("Second source"),
    ],
)
def test_unresolved_limitations_never_report_pass(tmp_path, change):
    stage = tmp_path / "stage"
    data = fixture(stage, SKILL)
    change(data)
    save(stage, data)
    result, report = report_for(stage, tmp_path / "batches")
    assert result["report_result"] == report["result"] == "WARN"
    assert report["issues"]


def test_failed_workflow_is_blocked_even_with_valid_pdf(tmp_path):
    stage = tmp_path / "stage"
    data = fixture(stage, SKILL)
    data["workflow_checks"]["screening"].update(
        status="failed", detail="A hard rule is unresolved."
    )
    save(stage, data)
    result, report = report_for(stage, tmp_path / "batches")
    assert report["counts"]["resume_pdfs_validated"] == 1
    assert result["report_result"] == "BLOCKED"
    handoff = json.loads((Path(result["path"]) / "handoff.json").read_text())
    assert handoff["applications"] == []


@pytest.mark.parametrize(
    "change",
    [
        lambda d: d["strategy"]["preferences"].pop("employers"),
        lambda d: d["strategy"].update(setup_complete=False),
        lambda d: d["strategy"]["fallback"].pop("enabled"),
        lambda d: d["strategy"].update(target_count=30),
        lambda d: d["strategy"].update(target_count=True),
        lambda d: d["strategy"].pop("role_quotas"),
        lambda d: d["collection_execution"].update(max_in_flight=4),
        lambda d: d["jobs"][0].update(selection_tier="fallback", fallback_rules_used=["wider age"]),
    ],
)
def test_missing_setup_and_unapproved_fallback_are_rejected(tmp_path, change):
    data = fixture(tmp_path, SKILL)
    change(data)
    save(tmp_path, data)
    with pytest.raises(ValueError):
        validate(tmp_path)


def test_enabled_fallback_is_explicit_and_reported(tmp_path):
    stage = tmp_path / "stage"
    data = fixture(stage, SKILL)
    data["strategy"]["fallback"] = {
        "enabled": True,
        "allowed_relaxations": ["Wider posting-age window"],
    }
    data["jobs"][0].update(
        selection_tier="fallback", fallback_rules_used=["Wider posting-age window"]
    )
    save(stage, data)
    _, report = report_for(stage, tmp_path / "batches")
    assert report["fallback"] == {"enabled": True, "jobs_used": 1}


def test_frozen_rank_controls_order_independently_of_input(tmp_path):
    stage = tmp_path / "stage"
    data = fixture(stage, SKILL)
    add_second_job(stage, data)
    data["jobs"].reverse()
    save(stage, data)
    result, _ = report_for(stage, tmp_path / "batches")
    handoff = json.loads((Path(result["path"]) / "handoff.json").read_text())
    assert [job["job_id"] for job in handoff["applications"]] == ["design-01", "design-02"]
    assert [job["selection_rank"] for job in handoff["applications"]] == [1, 2]
    assert "write back" in handoff["instructions"]


def test_actual_parallel_mode_recorded_without_claiming_helper_observation(tmp_path):
    stage = tmp_path / "stage"
    data = fixture(stage, SKILL)
    data["strategy"]["collection"]["sources"].append("Second source")
    data["source_reports"].append({**data["source_reports"][0], "source": "Second source"})
    data["collection_execution"] = {
        "mode": "parallel",
        "max_in_flight": 2,
        "detail": "Simulated two-source host concurrency for this fixture.",
    }
    save(stage, data)
    _, report = report_for(stage, tmp_path / "batches")
    parallel = next(item for item in report["sections"] if item["name"] == "parallel_execution")
    assert report["result"] == "PASS"
    assert parallel["basis"] == "agent_attestation"
    assert report["collection_execution"]["max_in_flight"] == 2


def test_legacy_input_is_readable_but_not_a_clean_v02_pass(tmp_path):
    stage = tmp_path / "stage"
    data = fixture(stage, SKILL)
    data["schema_version"] = 1
    for name in ("strategy", "workflow_checks", "collection_execution"):
        data.pop(name)
    save(stage, data)
    _, report = report_for(stage, tmp_path / "batches")
    assert report["result"] == "WARN"
    assert any("Legacy input" in item["detail"] for item in report["issues"])
