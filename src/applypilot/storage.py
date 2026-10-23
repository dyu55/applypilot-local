"""Profile-isolated local storage with transactional history and atomic files."""

import contextlib
import hashlib
import json
import os
import re
import sqlite3
import tempfile
import uuid
from collections.abc import Iterator
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from platformdirs import user_data_path

from applypilot.domain import Answer, Assessment, Job, Profile, Resume, Status, StatusUpdate, now


def canonical_url(url: str) -> str:
    parts = urlsplit(url)
    query = sorted(
        (k, v)
        for k, v in parse_qsl(parts.query, keep_blank_values=True)
        if not k.lower().startswith("utm_")
        and k.lower() not in {"ref", "source", "referrer", "trackingid", "trk"}
    )
    return urlunsplit(
        (parts.scheme.lower(), parts.netloc.lower(), parts.path.rstrip("/"), urlencode(query), "")
    )


def job_key(job: Job) -> str:
    identity = (
        f"{job.source}:{job.company.casefold()}:{job.source_id}"
        if job.source_id
        else canonical_url(job.url)
    )
    return hashlib.sha256(identity.encode()).hexdigest()[:24]


def atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(dir=path.parent, prefix=".staging-")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(content)
        os.replace(temporary, path)
    finally:
        with contextlib.suppress(FileNotFoundError):
            os.unlink(temporary)


class Workspace:
    def __init__(self, root: str | Path | None = None, profile: str = "default") -> None:
        if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}", profile):
            raise ValueError(
                "Profile ID must contain only letters, numbers, hyphens, or underscores."
            )
        self.root = Path(
            root or os.environ.get("APPLYPILOT_DATA_DIR") or user_data_path("applypilot")
        )
        self.path = self.root.expanduser().resolve() / "profiles" / profile
        self.path.mkdir(parents=True, exist_ok=True)
        with contextlib.suppress(OSError):
            self.path.chmod(0o700)
        self.profile_id = profile
        self.db_path = self.path / "workspace.sqlite3"
        with self.connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
                INSERT OR IGNORE INTO meta VALUES ('schema_version', '1');
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY, canonical TEXT UNIQUE NOT NULL, data TEXT NOT NULL,
                    assessment TEXT NOT NULL, status TEXT NOT NULL, material TEXT,
                    created_at TEXT NOT NULL, updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS resumes (id TEXT PRIMARY KEY, data TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS events (
                    id TEXT PRIMARY KEY, job_id TEXT NOT NULL, data TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS answers (key TEXT PRIMARY KEY, data TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS questions (
                    key TEXT PRIMARY KEY, text TEXT NOT NULL, scope TEXT NOT NULL,
                    jobs TEXT NOT NULL, resolved INTEGER NOT NULL DEFAULT 0
                );
                CREATE TABLE IF NOT EXISTS runs (
                    id TEXT PRIMARY KEY, data TEXT NOT NULL, created_at TEXT NOT NULL
                );
            """)

    @contextlib.contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        db = sqlite3.connect(self.db_path, timeout=20)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys = ON")
        try:
            with db:
                yield db
        finally:
            db.close()

    def profile(self) -> Profile:
        path = self.path / "profile.json"
        return Profile.model_validate_json(path.read_text()) if path.exists() else Profile()

    def save_profile(self, profile: Profile) -> None:
        atomic_write(self.path / "profile.json", profile.model_dump_json(indent=2))

    def add_job(self, job: Job, assessment: Assessment) -> tuple[str, bool]:
        key = job_key(job)
        job.id = key
        stamp = now()
        with self.connect() as db:
            existing = db.execute(
                "SELECT id FROM jobs WHERE id=? OR canonical=?", (key, canonical_url(job.url))
            ).fetchone()
            if existing:
                return existing["id"], False
            db.execute(
                "INSERT INTO jobs VALUES (?, ?, ?, ?, ?, NULL, ?, ?)",
                (
                    key,
                    canonical_url(job.url),
                    job.model_dump_json(),
                    assessment.model_dump_json(),
                    assessment.status.value,
                    stamp,
                    stamp,
                ),
            )
        return key, True

    def jobs(self) -> list[dict[str, Any]]:
        with self.connect() as db:
            rows = db.execute("SELECT * FROM jobs ORDER BY created_at DESC, id").fetchall()
        return [self._job(row) for row in rows]

    @staticmethod
    def _job(row: sqlite3.Row) -> dict[str, Any]:
        return {
            **json.loads(row["data"]),
            "assessment": json.loads(row["assessment"]),
            "status": row["status"],
            "material": json.loads(row["material"]) if row["material"] else None,
            "created_at": row["created_at"],
        }

    def job(self, key: str) -> dict[str, Any]:
        with self.connect() as db:
            row = db.execute("SELECT * FROM jobs WHERE id=?", (key,)).fetchone()
        if row is None:
            raise KeyError("Job not found.")
        return self._job(row)

    def set_material(self, key: str, material: dict[str, Any]) -> None:
        self.job(key)
        with self.connect() as db:
            db.execute(
                "UPDATE jobs SET material=?, updated_at=? WHERE id=?",
                (json.dumps(material), now(), key),
            )

    def update_status(self, key: str, update: StatusUpdate) -> None:
        if update.status == Status.SUBMITTED and not update.evidence.strip():
            raise ValueError(
                "Submission requires a confirmation reference or a user-reported receipt."
            )
        self.job(key)
        with self.connect() as db:
            db.execute(
                "UPDATE jobs SET status=?, updated_at=? WHERE id=?",
                (update.status.value, now(), key),
            )
            db.execute(
                "INSERT INTO events VALUES (?, ?, ?, ?)",
                (uuid.uuid4().hex, key, update.model_dump_json(), now()),
            )

    def events(self, key: str) -> list[dict[str, Any]]:
        self.job(key)
        with self.connect() as db:
            rows = db.execute(
                "SELECT data, created_at FROM events WHERE job_id=? ORDER BY created_at", (key,)
            ).fetchall()
        return [{**json.loads(row["data"]), "created_at": row["created_at"]} for row in rows]

    def reassess(self, assess: Any) -> None:
        profile = self.profile()
        with self.connect() as db:
            for row in db.execute("SELECT * FROM jobs").fetchall():
                assessment = assess(Job.model_validate_json(row["data"]), profile)
                status = row["status"]
                # A user's decision or confirmed submission survives a rule change.
                has_event = db.execute(
                    "SELECT 1 FROM events WHERE job_id=? LIMIT 1", (row["id"],)
                ).fetchone()
                if not has_event:
                    status = assessment.status.value
                db.execute(
                    "UPDATE jobs SET assessment=?, status=?, updated_at=? WHERE id=?",
                    (assessment.model_dump_json(), status, now(), row["id"]),
                )

    def add_resume(self, resume: Resume) -> Resume:
        if len(resume.text.split()) < 40:
            raise ValueError(
                "Add a substantive resume with at least 40 words before generating PDFs."
            )
        resume.id = uuid.uuid4().hex[:16]
        with self.connect() as db:
            db.execute("INSERT INTO resumes VALUES (?, ?)", (resume.id, resume.model_dump_json()))
        return resume

    def resumes(self) -> list[Resume]:
        with self.connect() as db:
            return [
                Resume.model_validate_json(row[0]) for row in db.execute("SELECT data FROM resumes")
            ]

    def answer(self, question: str, scope: str) -> dict[str, Any] | None:
        with self.connect() as db:
            row = db.execute(
                "SELECT data FROM answers WHERE key=?", (self.question_key(question, scope),)
            ).fetchone()
        return json.loads(row[0]) if row else None

    @staticmethod
    def question_key(question: str, scope: str) -> str:
        normalized = " ".join(re.findall(r"\w+", question.casefold()))
        return hashlib.sha256(f"{scope.casefold().strip()}:{normalized}".encode()).hexdigest()

    def add_question(self, text: str, scope: str, job_id: str | None = None) -> str:
        key = self.question_key(text, scope)
        if job_id:
            self.job(job_id)
        with self.connect() as db:
            row = db.execute("SELECT jobs FROM questions WHERE key=?", (key,)).fetchone()
            jobs = json.loads(row[0]) if row else []
            if job_id and job_id not in jobs:
                jobs.append(job_id)
            answer = self.answer(text, scope)
            resolved = bool(answer and answer["source"] == "user_confirmed")
            db.execute(
                "INSERT INTO questions VALUES (?, ?, ?, ?, ?) "
                "ON CONFLICT(key) DO UPDATE SET jobs=excluded.jobs",
                (key, text, scope, json.dumps(jobs), resolved),
            )
        return key

    def save_answer(self, answer: Answer) -> None:
        key = self.question_key(answer.question, answer.scope)
        if answer.source == "resume_based_draft" and answer.resume_id not in {
            resume.id for resume in self.resumes()
        }:
            raise ValueError("A resume-based draft must reference an existing source resume.")
        with self.connect() as db:
            db.execute(
                "INSERT OR REPLACE INTO answers VALUES (?, ?)", (key, answer.model_dump_json())
            )
            db.execute(
                "UPDATE questions SET resolved=? WHERE key=?",
                (answer.source == "user_confirmed", key),
            )

    def questions(self) -> list[dict[str, Any]]:
        with self.connect() as db:
            rows = db.execute("SELECT * FROM questions ORDER BY resolved, rowid DESC").fetchall()
        return [
            {
                **dict(row),
                "jobs": json.loads(row["jobs"]),
                "answer": self.answer(row["text"], row["scope"]),
            }
            for row in rows
        ]

    def record_run(self, data: dict[str, Any]) -> str:
        run_id = uuid.uuid4().hex
        with self.connect() as db:
            db.execute("INSERT INTO runs VALUES (?, ?, ?)", (run_id, json.dumps(data), now()))
        return run_id

    def runs(self) -> list[dict[str, Any]]:
        with self.connect() as db:
            rows = db.execute("SELECT * FROM runs ORDER BY created_at DESC LIMIT 20").fetchall()
        return [{**dict(row), "data": json.loads(row["data"])} for row in rows]
