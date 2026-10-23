"""Fact-preserving resume routing, bullet ordering, and verified PDF publication."""

import hashlib
import io
import json
import re
import shutil
import tempfile
import uuid
import zipfile
from collections import Counter
from pathlib import Path
from typing import Any
from xml.etree import ElementTree
from xml.sax.saxutils import escape

import reportlab
from pypdf import PdfReader
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

from applypilot.domain import Job, Resume, now
from applypilot.model import BulletRanker
from applypilot.screening import contains
from applypilot.storage import Workspace


def extract_resume(filename: str, content: bytes) -> str:
    if len(content) > 5_000_000:
        raise ValueError("Resume files must be smaller than 5 MB.")
    suffix = Path(filename).suffix.casefold()
    if suffix == ".pdf":
        reader = PdfReader(io.BytesIO(content))
        if len(reader.pages) > 20:
            raise ValueError("Resume PDFs must contain at most 20 pages.")
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
        if len(text.split()) < 40:
            raise ValueError("This PDF has too little extractable text. Upload an editable resume.")
        return text
    if suffix == ".docx":
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            entry = archive.getinfo("word/document.xml")
            if entry.file_size > 5_000_000:
                raise ValueError("The expanded document exceeds the size limit.")
            root = ElementTree.fromstring(archive.read(entry))
            namespace = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
            return "\n".join("".join(part.itertext()) for part in root.findall(".//w:p", namespace))
    if suffix in {".txt", ".md"}:
        return content.decode("utf-8-sig")
    raise ValueError("Upload a PDF, DOCX, Markdown, or UTF-8 text resume.")


def select_resume(resumes: list[Resume], job: Job, resume_id: str | None = None) -> Resume:
    if resume_id:
        for resume in resumes:
            if resume.id == resume_id:
                return resume
        raise ValueError("The selected resume does not exist in this profile.")
    if not resumes:
        raise ValueError("Add a resume before generating materials.")
    return max(
        resumes,
        key=lambda resume: sum(contains(job.title, role) for role in resume.roles),
    )


def tailor(text: str, job: Job, ranker: BulletRanker | None = None) -> tuple[str, list[str]]:
    """Reorder only contiguous bullet groups, keeping employer and date blocks intact."""
    lines = text.splitlines()
    warnings = []
    cursor = 0
    terms = set(re.findall(r"\w{3,}", f"{job.title} {job.description}".casefold()))
    while cursor < len(lines):
        if not re.match(r"^\s*[-*\u2022]\s+", lines[cursor]):
            cursor += 1
            continue
        end = cursor
        while end < len(lines) and re.match(r"^\s*[-*\u2022]\s+", lines[end]):
            end += 1
        bullets = lines[cursor:end]
        ordered = sorted(
            range(len(bullets)),
            key=lambda index: -len(terms & set(re.findall(r"\w{3,}", bullets[index].casefold()))),
        )
        if ranker and len(bullets) > 1:
            try:
                ordered = ranker.order(bullets, job.description)
            except ValueError as exc:
                warnings.append(str(exc))
        lines[cursor:end] = [bullets[index] for index in ordered]
        cursor = end
    result = "\n".join(lines)
    if Counter(result.splitlines()) != Counter(text.splitlines()):
        raise ValueError("Resume fact-preservation validation failed.")
    return result, warnings


def _font() -> str:
    name = "ApplyPilotSans"
    if name not in pdfmetrics.getRegisteredFontNames():
        font_path = Path(reportlab.__file__).parent / "fonts" / "Vera.ttf"
        pdfmetrics.registerFont(TTFont(name, str(font_path)))
    return name


def render_pdf(text: str, path: Path) -> dict[str, Any]:
    font = _font()
    supported = pdfmetrics.getFont(font).face.charToGlyph
    unsupported = {char for char in text if not char.isspace() and ord(char) not in supported}
    if unsupported:
        raise ValueError(
            "The PDF font cannot display some characters. Use a Latin-script resume in v0.1."
        )
    body = ParagraphStyle(
        "Body",
        fontName=font,
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#263345"),
        alignment=TA_LEFT,
        spaceAfter=4,
    )
    heading = ParagraphStyle(
        "Heading",
        parent=body,
        fontSize=11,
        leading=15,
        spaceBefore=10,
        spaceAfter=6,
        textColor=colors.HexColor("#142b43"),
        keepWithNext=True,
    )
    title = ParagraphStyle("Title", parent=heading, fontSize=21, leading=26, spaceAfter=7)
    story = []
    nonempty = 0
    for line in text.splitlines():
        if not line.strip():
            story.append(Spacer(1, 5))
            continue
        clean = re.sub(r"^#{1,6}\s+", "", line).strip()
        is_heading = line.startswith("#") or (len(clean) < 45 and clean.isupper())
        style = title if nonempty == 0 else heading if is_heading else body
        nonempty += 1
        story.append(Paragraph(escape(clean), style))
    document = SimpleDocTemplate(
        str(path),
        pagesize=(595.28, 841.89),
        rightMargin=43,
        leftMargin=43,
        topMargin=38,
        bottomMargin=38,
        title="Resume",
        author="",
    )
    document.build(story)
    reader = PdfReader(path)
    extracted = "\n".join(page.extract_text() or "" for page in reader.pages)

    def words(value: str) -> Counter:
        return Counter(re.findall(r"[A-Za-z0-9]+", value.casefold()))

    if len(extracted.split()) < 40 or (words(text) - words(extracted)):
        raise ValueError("PDF quality check failed: substantive source text was not preserved.")
    return {"pages": len(reader.pages), "words": len(extracted.split()), "text_verified": True}


def generate(workspace: Workspace, job_id: str, resume_id: str | None = None) -> dict[str, Any]:
    data = workspace.job(job_id)
    job = Job.model_validate({k: v for k, v in data.items() if k in Job.model_fields})
    resume = select_resume(workspace.resumes(), job, resume_id)
    settings = workspace.profile().model
    ranker = BulletRanker(settings) if settings.enabled else None
    tailored, warnings = tailor(resume.text, job, ranker)
    run_id = uuid.uuid4().hex
    materials = workspace.path / "materials"
    materials.mkdir(exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix="staging-", dir=materials))
    try:
        (stage / "resume.md").write_text(tailored, encoding="utf-8")
        (stage / "source-resume.txt").write_text(resume.text, encoding="utf-8")
        quality = render_pdf(tailored, stage / "resume.pdf")
        assessment = data["assessment"]
        note = (
            f"# Application preparation: {job.title}\n\n"
            f"Company: {job.company}\n\nPosting: {job.url}\n\n"
            f"Resume: {resume.label}\n\n"
            "## Screening notes\n\n"
            + "\n".join(f"- {line}" for line in assessment["reasons"])
            + "\n\n## Review before applying\n\n"
            "Confirm the posting is open and review all uploaded material. "
            "Generated files are not evidence that an application was submitted.\n"
        )
        (stage / "preparation.md").write_text(note, encoding="utf-8")
        manifest = {
            "id": run_id,
            "job_id": job_id,
            "resume_id": resume.id,
            "created_at": now(),
            "quality": quality,
            "warnings": warnings,
            "mode": "model-ranked source bullets" if ranker else "keyword-ranked source bullets",
            "facts_preserved": True,
            "source_sha256": hashlib.sha256(resume.text.encode()).hexdigest(),
            "files": ["resume.pdf", "resume.md", "preparation.md", "source-resume.txt"],
        }
        (stage / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        destination = materials / run_id
        stage.rename(destination)
        workspace.set_material(job_id, manifest)
        return manifest
    finally:
        if stage.exists():
            shutil.rmtree(stage)
