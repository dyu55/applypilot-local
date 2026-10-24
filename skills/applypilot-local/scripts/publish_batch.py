"""Agent helper: publish a complete immutable run inside a date-named folder."""

import argparse
import csv
import json
import shutil
import tempfile
from pathlib import Path

from batch_lib import (
    require,
    safe_file,
    sha256,
    validate,
    write_json,
)
from daily_report import build_report


def csv_safe(value):
    value = str(value)
    return "'" + value if value.lstrip().startswith(("=", "+", "-", "@")) else value


def indexes(stage, batch, summary, quality):
    report = build_report(stage, batch, summary, quality)
    write_json(stage / "daily_report.json", report)
    records = []
    lines = [
        f"# Application order: {batch['date']}",
        "",
        f"Ready: {summary['ready']}/{summary['requested']}. Shortfall: {summary['shortfall']}.",
        "",
        "Prepared materials do not mean an application was submitted.",
        f"Preparation report: {report['result']}. Read DAILY_REPORT.md before using this order.",
        "",
    ]
    ready = [job for job in batch["jobs"] if job["materials"]["status"] == "ready"]
    if report["result"] == "BLOCKED":
        ready = []
    if batch["schema_version"] == 2:
        ready.sort(key=lambda job: job["rank"])
    for number, job in enumerate(ready, 1):
        record = {
            "order": number,
            "job_id": job["id"],
            "company": job["company"],
            "title": job["title"],
            "url": job["url"],
            "files": job["materials"]["files"],
            "application_status": "Pending",
            "selection_rank": job.get("rank", number),
        }
        records.append(record)
        lines.extend(
            [
                f"{number}. {job['company']} - {job['title']}",
                f"   Posting: {job['url']}",
                f"   Resume: {job['materials']['files']['resume_pdf']}",
                "",
            ]
        )
    if not ready:
        lines.append(
            "No jobs are listed: the batch is blocked or no jobs are ready. Read the report."
        )
    lines.extend(["", "## Pending questions", ""])
    lines.extend(f"- {item}" for item in batch.get("pending_questions", []))
    if not batch.get("pending_questions"):
        lines.append("None recorded.")
    (stage / "APPLY_ORDER.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    with (stage / "applications.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "id",
                "company",
                "title",
                "url",
                "decision",
                "availability",
                "materials",
                "application_status",
            ]
        )
        for job in batch["jobs"]:
            writer.writerow(
                [
                    csv_safe(value)
                    for value in (
                        job["id"],
                        job["company"],
                        job["title"],
                        job["url"],
                        job["decision"],
                        job["availability"]["status"],
                        job["materials"]["status"],
                        job["application_status"],
                    )
                ]
            )
    write_json(
        stage / "handoff.json",
        {
            "schema_version": 1,
            "run_id": batch["run_id"],
            "date": batch["date"],
            "submission_authorized": False,
            "report_result": report["result"],
            "path_base": "this folder",
            "applications": records,
            "pending_questions": batch.get("pending_questions", []),
            "instructions": (
                "Review availability and materials. Obtain separate submission instructions. "
                "This preparation skill does not collect or write back application results."
            ),
        },
    )
    (stage / "HANDOFF.md").write_text(
        "# Manual application or Muse handoff\n\n"
        "Read DAILY_REPORT.md, APPLY_ORDER.md, and handoff.json. "
        "All file paths are relative to this folder. Resolve a BLOCKED report before use.\n\n"
        "This is a local file handoff, not a tested Muse API integration. "
        "Nothing was sent or submitted. Creating these files does not authorize applications. "
        "Follow the user's separate instructions, "
        "resolve pending questions, recheck posting availability, and review each upload. "
        "This skill finishes at preparation and does not request or write back Muse results.\n",
        encoding="utf-8",
    )
    manifest = {
        "schema_version": batch["schema_version"],
        "date": batch["date"],
        "run_id": batch["run_id"],
        "created_at": batch["created_at"],
        "time_zone": batch["time_zone"],
        "status": "ready"
        if not summary["shortfall"]
        else "partial"
        if summary["ready"]
        else "blocked",
        "summary": summary,
        "source_reports": batch["source_reports"],
        "report_result": report["result"],
        "strategy": batch.get("strategy"),
        "collection_execution": batch.get("collection_execution"),
        "source_health": "ok"
        if all(item["outcome"] == "ok" for item in batch["source_reports"])
        else "degraded",
        "jobs": batch["jobs"],
        "pending_questions": batch.get("pending_questions", []),
        "validation": {
            "method": "bundled_helper",
            "pdf_quality": quality,
            "fact_review": "agent_attestation",
            "visual_review": "agent_attestation",
        },
        "submission_authorized": False,
        "verified_submissions": 0,
        "file_hashes": {},
    }
    for file in sorted(stage.rglob("*")):
        if file.is_file():
            manifest["file_hashes"][file.relative_to(stage).as_posix()] = sha256(file)
    write_json(stage / "manifest.json", manifest)
    return manifest


def publish(source, output):
    source, output = Path(source).resolve(), Path(output).resolve()
    require(source.is_dir(), "Staging folder does not exist.")
    skill_root = Path(__file__).resolve().parents[1]
    require(not output.is_relative_to(skill_root), "Publish outside the installed skill folder.")
    require(
        not output.is_relative_to(source) and not source.is_relative_to(output),
        "Staging and output folders must be separate.",
    )
    batch, _, _ = validate(source)
    day = output / batch["date"]
    day.mkdir(parents=True, exist_ok=True)
    require(not day.is_symlink(), "Date folder must not be a symlink.")
    destination = day / batch["run_id"]
    lock = day / ".publish.lock"
    try:
        lock_handle = lock.open("x", encoding="utf-8")
    except FileExistsError as exc:
        raise ValueError(
            "Another publication holds the date lock. Inspect a stale lock before retrying."
        ) from exc
    try:
        with lock_handle:
            lock_handle.write(batch["run_id"])
        require(not destination.exists(), "Run already exists; preserve it and use a new run ID.")
        with tempfile.TemporaryDirectory(prefix="staging-", dir=day) as temp:
            stage = Path(temp) / "run"
            stage.mkdir()
            # Copy only declared materials. Private extra files never enter the batch accidentally.
            relatives = {"batch.json"}
            for job in batch["jobs"]:
                relatives.update(job["materials"].get("files", {}).values())
            for relative in sorted(relatives):
                target = stage / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(safe_file(source, relative), target)
            batch, summary, quality = validate(stage)
            manifest = indexes(stage, batch, summary, quality)
            stage.rename(destination)
        # A failed pointer update leaves the complete run recoverable and the old pointer intact.
        with tempfile.TemporaryDirectory(prefix="pointer-", dir=day) as temp:
            pointer = Path(temp) / "latest.json"
            write_json(
                pointer,
                {
                    "run_id": batch["run_id"],
                    "path": batch["run_id"],
                    "manifest_sha256": sha256(destination / "manifest.json"),
                },
            )
            pointer.replace(day / "latest.json")
        return {
            "path": str(destination),
            "status": manifest["status"],
            "summary": summary,
            "report_result": manifest["report_result"],
        }
    finally:
        lock.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("staging", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    try:
        print(json.dumps(publish(args.staging, args.output)))
    except (OSError, ValueError, TypeError, KeyError) as exc:
        parser.exit(1, f"Batch publication failed: {exc}\n")


if __name__ == "__main__":
    main()
