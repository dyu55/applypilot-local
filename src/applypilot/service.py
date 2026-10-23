"""Shared application operations used by the CLI and local HTTP API."""

import csv
import io
import json
from typing import Any

from applypilot.domain import Job
from applypilot.screening import assess
from applypilot.sources import collect
from applypilot.storage import Workspace


def import_jobs(workspace: Workspace, jobs: list[Job]) -> dict[str, int]:
    profile = workspace.profile()
    imported = 0
    for job in jobs:
        _, added = workspace.add_job(job, assess(job, profile))
        imported += added
    return {"imported": imported, "duplicates": len(jobs) - imported}


def collect_jobs(workspace: Workspace) -> dict[str, Any]:
    profile = workspace.profile()
    if not any(source.enabled for source in profile.sources):
        raise ValueError("Add and enable a job source in Settings before collecting jobs.")
    result = collect(profile)
    counts = import_jobs(workspace, result["jobs"])
    summary = {**counts, "sources": result["sources"]}
    summary["run_id"] = workspace.record_run(summary)
    return summary


def export(workspace: Workspace, format: str) -> str:
    jobs = workspace.jobs()
    if format == "json":
        return json.dumps({"schema_version": 1, "jobs": jobs}, indent=2, ensure_ascii=False)
    output = io.StringIO(newline="")
    fields = ["id", "title", "company", "location", "url", "source", "status", "fit", "reasons"]
    writer = csv.DictWriter(output, fieldnames=fields)
    writer.writeheader()
    for job in jobs:
        record = {key: job.get(key, "") for key in fields}
        record["fit"] = job["assessment"]["fit"]
        record["reasons"] = "; ".join(job["assessment"]["reasons"])
        # Opening exported CSV in a spreadsheet must not execute job-supplied formulas.
        record = {
            key: "'" + str(value)
            if str(value).startswith(("=", "+", "-", "@", "\t", "\r"))
            else value
            for key, value in record.items()
        }
        writer.writerow(record)
    return output.getvalue()
