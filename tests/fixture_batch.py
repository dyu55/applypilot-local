"""Fictional fixtures; review flags simulate the agent's recorded attestations."""

import json
import subprocess
import sys
from pathlib import Path

RESUME = """# Alex Morgan
alex@example.com | Example City

## Profile
Product designer with experience planning research, building prototypes, and improving clear
interaction patterns. Comfortable collaborating with engineers and explaining design decisions
using observations from usability sessions. Interested in accessible products and practical
solutions that help people complete everyday tasks with less confusion.

## Experience
Product Designer | Example Studio | 2022-2025
- Planned moderated usability sessions for a mobile account prototype and documented findings.
- Created wireframes and interactive prototypes for account settings and notification preferences.
- Worked with engineers to clarify acceptance criteria and review implemented interaction states.
- Maintained a small library of reusable components and documented accessibility considerations.

## Projects
Community Library Concept
- Interviewed volunteers about common catalog questions and summarized recurring navigation issues.
- Built a prototype for browsing books and collecting feedback from local participants.

## Education
Bachelor of Design | Example College | 2022
"""
DESCRIPTION = """# Product Designer at Example Studio
This fictional fixture is not a real opening. The product designer plans research sessions,
creates prototypes, and works with engineering partners to improve account workflows.
Responsibilities include documenting usability findings, reviewing interface states, and
maintaining reusable design components. The role values clear communication, practical
accessibility knowledge, and experience explaining decisions using research observations.
The team works remotely and expects collaboration across product and engineering disciplines.
"""


def fixture(stage, skill, ready=True, run_id="fixture-run"):
    stage = Path(stage)
    folder = stage / "jobs" / "design-01"
    folder.mkdir(parents=True)
    (folder / "resume.md").write_text(RESUME, encoding="utf-8")
    (folder / "job_description.md").write_text(DESCRIPTION, encoding="utf-8")
    (folder / "notes.md").write_text(
        "Fictional test material. No application occurred.\n", encoding="utf-8"
    )
    (folder / "fact_map.json").write_text(
        json.dumps(
            {
                "reviewed": True,
                "claims": [
                    {
                        "text": "Planned moderated usability sessions.",
                        "source": "state/resumes/design.md:10",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    files = {
        key: f"jobs/design-01/{name}"
        for key, name in {
            "resume_md": "resume.md",
            "job_description": "job_description.md",
            "notes": "notes.md",
            "fact_map": "fact_map.json",
        }.items()
    }
    if ready:
        subprocess.run(
            [
                sys.executable,
                str(Path(skill) / "scripts" / "render_resume.py"),
                str(folder / "resume.md"),
                str(folder / "resume.pdf"),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        files["resume_pdf"] = "jobs/design-01/resume.pdf"
    batch = {
        "schema_version": 1,
        "date": "2026-10-23",
        "run_id": run_id,
        "created_at": "2026-10-23T09:00:00+00:00",
        "time_zone": "UTC",
        "requested_count": 1,
        "source_reports": [
            {
                "source": "Fictional fixture",
                "outcome": "ok",
                "checked_at": "2026-10-23T09:00:00+00:00",
                "detail": "Synthetic records; no live search was performed.",
            }
        ],
        "pending_questions": [],
        "jobs": [
            {
                "id": "design-01",
                "company": "Example Studio",
                "title": "Product Designer",
                "location": "Remote",
                "url": "https://example.com/jobs/design-01",
                "requisition_id": "design-01",
                "availability": {
                    "status": "open" if ready else "unknown",
                    "evidence": "Synthetic availability for a fixture, not a live check.",
                    "checked_at": "2026-10-23T09:00:00+00:00",
                },
                "decision": "selected",
                "reasons": ["Fixture design experience matches the fixture description."],
                "application_status": "Pending",
                "materials": {
                    "status": "ready" if ready else "draft",
                    "reason": "Fixture lacks PDF review." if not ready else "",
                    "source_resume_id": "fictional-design-v1",
                    "review": {"facts_checked": True, "pdf_visual_checked": True},
                    "files": files,
                },
            }
        ],
    }
    save(stage, batch)
    return batch


def save(stage, batch):
    (Path(stage) / "batch.json").write_text(json.dumps(batch, indent=2), encoding="utf-8")
