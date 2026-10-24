"""Validate prepared batches and publish derived indexes without network access."""

import hashlib
import json
import re
from collections import Counter
from datetime import date, datetime
from pathlib import Path, PurePosixPath
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

REQUIRED_FILES = {"resume_pdf", "resume_md", "job_description", "notes", "fact_map"}
BASE_GENERATED_FILES = {
    "manifest.json",
    "APPLY_ORDER.md",
    "applications.csv",
    "handoff.json",
    "HANDOFF.md",
}
GENERATED_FILES = BASE_GENERATED_FILES | {"DAILY_REPORT.md", "daily_report.json"}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def text(value, label):
    require(isinstance(value, str) and bool(value.strip()), f"{label} must be nonempty text.")
    return value


def timestamp(value):
    parsed = datetime.fromisoformat(text(value, "Timestamp").replace("Z", "+00:00"))
    require(parsed.tzinfo is not None, "Timestamps must include a UTC offset.")
    return parsed


def canonical_url(value):
    parsed = urlsplit(text(value, "Posting URL"))
    require(
        parsed.scheme in {"http", "https"}
        and bool(parsed.hostname)
        and not parsed.username
        and not parsed.password
        and not re.search(r"[\s\x00-\x1f\x7f]", value),
        "Posting URL must be an HTTP(S) URL without credentials or whitespace.",
    )
    tracking = {"ref", "referrer", "source", "trk", "trackingid"}
    query = sorted(
        (key, val)
        for key, val in parse_qsl(parsed.query, keep_blank_values=True)
        if not key.casefold().startswith("utm_") and key.casefold() not in tracking
    )
    return urlunsplit((parsed.scheme, parsed.netloc.lower(), parsed.path, urlencode(query), ""))


def safe_file(root, value):
    text(value, "File path")
    parts = PurePosixPath(value)
    require(
        not parts.is_absolute()
        and parts.as_posix() == value
        and ".." not in parts.parts
        and "\\" not in value
        and ":" not in value
        and parts.parts
        and not any(part.startswith(".") for part in parts.parts),
        "File paths must be relative, visible paths without traversal.",
    )
    root = Path(root).resolve()
    candidate = root.joinpath(*parts.parts)
    current = root
    for part in parts.parts:
        current = current / part
        require(not current.is_symlink(), "Symlinked batch files are not allowed.")
    require(candidate.resolve().is_relative_to(root), "File escapes the staging folder.")
    require(candidate.is_file() and candidate.stat().st_size > 0, f"Missing/empty file: {value}")
    require(candidate.stat().st_size <= 20_000_000, f"File exceeds 20 MB: {value}")
    return candidate


def pdf_quality(pdf, source):
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise ValueError("Install the PDF helper requirements to verify ready materials.") from exc
    reader = PdfReader(pdf)
    require(not reader.is_encrypted, "Resume PDF must not be encrypted.")
    require(0 < len(reader.pages) <= 20, "Resume PDF must contain between 1 and 20 pages.")
    extracted = "\n".join(page.extract_text() or "" for page in reader.pages)
    require(len(extracted.split()) >= 40, "Resume PDF has too little substantive text.")

    def words(value):
        return Counter(re.findall(r"\w+", value.casefold(), re.UNICODE))

    # Markdown heading and bullet markers do not enter the word comparison.
    missing = words(source) - words(extracted)
    require(not missing, "Resume PDF lost words from the editable source.")
    return {"pages": len(reader.pages), "words": len(extracted.split()), "text_verified": True}


def validate(root):
    root = Path(root).resolve()
    batch = read_json(root / "batch.json")
    require(
        isinstance(batch, dict) and batch.get("schema_version") in {1, 2},
        "Unsupported batch schema.",
    )
    day = text(batch.get("date"), "Date")
    require(re.fullmatch(r"\d{4}-\d{2}-\d{2}", day) is not None, "Use a YYYY-MM-DD date.")
    date.fromisoformat(day)
    run_id = text(batch.get("run_id"), "Run ID")
    require(re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_-]{0,79}", run_id), "Invalid run ID.")
    created = timestamp(batch.get("created_at"))
    require(
        created.date().isoformat() == day, "Batch date must match the local creation timestamp."
    )
    text(batch.get("time_zone"), "Time zone")
    target = batch.get("requested_count")
    require(type(target) is int and target > 0, "Requested count must be a positive integer.")
    sources = batch.get("source_reports")
    require(isinstance(sources, list) and sources, "Include at least one source report.")
    for report in sources:
        require(isinstance(report, dict), "Source reports must be objects.")
        text(report.get("source"), "Source")
        text(report.get("detail"), "Source detail")
        timestamp(report.get("checked_at"))
        require(
            report.get("outcome") in {"ok", "partial", "blocked", "not_checked"},
            "Invalid source outcome.",
        )
    jobs = batch.get("jobs")
    require(isinstance(jobs, list), "Jobs must be a list, including for zero-result runs.")
    ids, urls, requisitions, used_files = set(), set(), set(), set()
    summary = {"ready": 0, "draft": 0, "missing": 0, "selected": 0, "needs_user": 0, "skipped": 0}
    quality = {}
    for job in jobs:
        require(isinstance(job, dict), "Job records must be objects.")
        job_id = text(job.get("id"), "Job ID")
        require(re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_-]{0,79}", job_id), "Invalid job ID.")
        require(job_id not in ids, "Duplicate job ID.")
        ids.add(job_id)
        for key in ("title", "company", "location"):
            text(job.get(key), key)
        url = canonical_url(job.get("url"))
        require(url not in urls, "Duplicate posting URL after removing tracking parameters.")
        urls.add(url)
        if job.get("requisition_id"):
            key = (job["company"].casefold(), text(job["requisition_id"], "Requisition ID"))
            require(key not in requisitions, "Duplicate employer requisition.")
            requisitions.add(key)
        availability = job.get("availability", {})
        require(isinstance(availability, dict), "Availability must be an object.")
        require(
            availability.get("status") in {"open", "unknown", "expired"}, "Invalid availability."
        )
        text(availability.get("evidence"), "Availability evidence")
        timestamp(availability.get("checked_at"))
        decision = job.get("decision")
        require(decision in {"selected", "needs_user", "skipped"}, "Invalid screening decision.")
        reasons = job.get("reasons")
        require(isinstance(reasons, list) and reasons, "Include screening reasons.")
        for reason in reasons:
            text(reason, "Screening reason")
        expected_status = {"selected": "Pending", "needs_user": "Needs user", "skipped": "Skipped"}
        require(
            job.get("application_status") == expected_status[decision],
            "Preparation cannot record a submission or conflicting application status.",
        )
        materials = job.get("materials")
        require(isinstance(materials, dict), "Materials must be an object.")
        status = materials.get("status")
        require(status in {"ready", "draft", "missing"}, "Invalid material status.")
        files = materials.get("files", {})
        require(isinstance(files, dict), "Material files must be an object.")
        for kind, relative in files.items():
            text(kind, "File kind")
            text(relative, "File path")
            require(
                relative.casefold() not in used_files,
                "Each job must have its own portable material paths.",
            )
            require(
                PurePosixPath(relative).name not in GENERATED_FILES | {"batch.json"},
                "Reserved output filename.",
            )
            safe_file(root, relative)
            used_files.add(relative.casefold())
        if status == "ready":
            require(
                decision == "selected" and availability["status"] == "open",
                "Ready jobs must be selected with verified open availability.",
            )
            require(
                files.keys() >= REQUIRED_FILES,
                "Ready materials require PDF, editable resume, description, notes, and fact map.",
            )
            text(materials.get("source_resume_id"), "Source resume ID")
            review = materials.get("review", {})
            require(
                isinstance(review, dict)
                and all(review.get(key) is True for key in ("facts_checked", "pdf_visual_checked")),
                "Ready materials require fact and rendered-page review attestations.",
            )
            fact_map = read_json(safe_file(root, files["fact_map"]))
            require(
                isinstance(fact_map, dict) and fact_map.get("reviewed") is True,
                "Fact map must be reviewed.",
            )
            claims = fact_map.get("claims")
            require(isinstance(claims, list) and claims, "Fact map must include supported claims.")
            for claim in claims:
                require(isinstance(claim, dict), "Claims must be objects.")
                text(claim.get("text"), "Claim text")
                text(claim.get("source"), "Claim source")
            resume = safe_file(root, files["resume_md"]).read_text(encoding="utf-8")
            require(len(resume.split()) >= 40, "Editable resume has too little substantive text.")
            description = safe_file(root, files["job_description"]).read_text(encoding="utf-8")
            require(
                len(description.split()) >= 40, "Job description is too short for ready materials."
            )
            quality[job_id] = pdf_quality(safe_file(root, files["resume_pdf"]), resume)
        else:
            text(materials.get("reason"), "Incomplete material reason")
        summary[status] += 1
        summary[decision] += 1
    questions = batch.get("pending_questions", [])
    require(isinstance(questions, list), "Pending questions must be a list.")
    for question in questions:
        text(question, "Pending question")
    summary["requested"] = target
    summary["shortfall"] = max(0, target - summary["ready"])
    if batch["schema_version"] == 2:
        from strategy import validate_strategy

        validate_strategy(batch)
    return batch, summary, quality
