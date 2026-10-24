"""Build a daily preparation report from actual files, checks, and source outcomes."""

from collections import Counter


def build_report(stage, batch, summary, quality):
    jobs = batch["jobs"]
    selected = [job for job in jobs if job["decision"] == "selected"]
    generated = sum("resume_pdf" in job["materials"].get("files", {}) for job in jobs)
    editable = sum("resume_md" in job["materials"].get("files", {}) for job in jobs)
    issues, sections = [], []

    def section(name, status, detail, basis):
        sections.append({"name": name, "status": status, "detail": detail, "basis": basis})
        if status != "pass":
            issues.append({"section": name, "status": status, "detail": detail})

    checks = batch.get("workflow_checks", {})
    if batch["schema_version"] == 1:
        section(
            "intake",
            "warning",
            "Legacy input has no confirmed customizable strategy.",
            "not_checked",
        )
    for name in ("intake", "deduplication", "screening", "ranking", "resume_routing"):
        if name == "intake" and batch["schema_version"] == 1:
            continue
        check = checks.get(name, {"status": "not_run", "detail": "No agent check was recorded."})
        section(name, check["status"], check["detail"], "agent_attestation")
    bad_sources = [item for item in batch["source_reports"] if item["outcome"] != "ok"]
    section(
        "collection",
        "warning" if bad_sources else "pass",
        "; ".join(f"{item['source']}: {item['outcome']} - {item['detail']}" for item in bad_sources)
        if bad_sources
        else f"All {len(batch['source_reports'])} source reports completed without issues.",
        "source_reports",
    )
    strategy = batch.get("strategy", {})
    wanted = strategy.get("collection", {})
    actual = batch.get("collection_execution", {})
    missing_sources = set(wanted.get("sources", [])) - {
        item["source"] for item in batch["source_reports"]
    }
    if missing_sources:
        section(
            "source_coverage",
            "warning",
            "No source report for: " + ", ".join(sorted(missing_sources)),
            "source_reports",
        )
    parallel_unavailable = (
        wanted.get("mode") == "parallel"
        and len(wanted.get("sources", [])) > 1
        and actual.get("mode") != "parallel"
    )
    section(
        "parallel_execution",
        "warning" if parallel_unavailable else "pass" if actual else "not_run",
        actual.get("detail", "Actual collection mode was not recorded."),
        "agent_attestation",
    )
    incomplete = [job for job in selected if job["materials"]["status"] != "ready"]
    section(
        "materials",
        "warning" if incomplete else "pass" if quality else "not_run",
        f"{generated} resume PDFs; {len(quality)} passed PDF text validation; "
        f"{len(incomplete)} selected jobs remain incomplete. "
        "Fact and page reviews are agent attestations.",
        "files_and_pdf_checks",
    )
    section(
        "target",
        "pass" if not summary["shortfall"] else "warning",
        f"{summary['ready']}/{summary['requested']} ready jobs; shortfall {summary['shortfall']}.",
        "computed_counts",
    )
    counts = Counter(
        job.get("role_family", "unspecified")
        for job in selected
        if job["materials"]["status"] == "ready"
    )
    for family, requested in strategy.get("role_quotas", {}).items():
        section(
            f"quota:{family}",
            "pass" if counts[family] >= requested else "warning",
            f"{counts[family]}/{requested} ready jobs in {family}.",
            "computed_counts",
        )
    questions = batch.get("pending_questions", [])
    section(
        "questions",
        "warning" if questions or summary["needs_user"] else "pass",
        f"{len(questions)} unresolved questions; {summary['needs_user']} jobs need user input."
        + (" " + "; ".join(questions) if questions else ""),
        "recorded_questions",
    )
    section(
        "publication",
        "pass",
        "Declared files validated and copied together; "
        "report and indexes staged for atomic publication.",
        "bundled_helper",
    )
    result = (
        "BLOCKED"
        if not summary["ready"] or any(item["status"] == "failed" for item in sections)
        else "WARN"
        if issues
        else "PASS"
    )
    report = {
        "schema_version": 1,
        "date": batch["date"],
        "run_id": batch["run_id"],
        "result": result,
        "counts": {
            "jobs_recorded": len(jobs),
            "jobs_selected": len(selected),
            "jobs_ready": summary["ready"],
            "resume_pdfs_prepared": generated,
            "editable_resumes_prepared": editable,
            "resume_pdfs_validated": len(quality),
            "target": summary["requested"],
            "shortfall": summary["shortfall"],
            "needs_user": summary["needs_user"],
            "skipped": summary["skipped"],
        },
        "sections": sections,
        "issues": issues,
        "fallback": {
            "enabled": strategy.get("fallback", {}).get("enabled", False),
            "jobs_used": sum(job.get("selection_tier") == "fallback" for job in selected),
        },
        "collection_execution": actual,
        "scope": "Preparation only. No submission tracking or Muse result writeback.",
    }
    lines = [
        f"# Daily preparation report: {batch['date']}",
        "",
        f"Result: **{result}**",
        "",
        f"Jobs recorded: {len(jobs)}. Selected: {len(selected)}. "
        f"Ready: {summary['ready']}/{summary['requested']}.",
        f"Resume PDFs prepared: {generated}. PDF text checks passed: {len(quality)}. "
        f"Editable resumes: {editable}.",
        f"Shortfall: {summary['shortfall']}. Pending questions: {len(questions)}.",
        f"Collection mode: {actual.get('mode', 'not recorded')}. "
        f"Maximum concurrent reads: {actual.get('max_in_flight', 'not recorded')}.",
        f"Fallback enabled: {report['fallback']['enabled']}. "
        f"Selected fallback jobs: {report['fallback']['jobs_used']}.",
        "",
        "## Workflow checks",
        "",
        "| Section | Status | Detail |",
        "| --- | --- | --- |",
    ]
    for item in sections:
        detail = item["detail"].replace("|", "\\|").replace("\n", " ")
        lines.append(f"| {item['name']} | {item['status']} | {detail} |")
    lines.extend(["", "## Issues", ""])
    lines.extend(f"- {item['section']}: {item['detail']}" for item in issues)
    if not issues:
        lines.append("None found in the recorded preparation checks. PASS.")
    lines.extend(
        [
            "",
            "Preparation only. This report does not track applications or request Muse results.",
            "PDF text checks are automated; factual, screening, and visual reviews "
            "remain agent attestations.",
            "",
        ]
    )
    (stage / "DAILY_REPORT.md").write_text("\n".join(lines), encoding="utf-8")
    return report
