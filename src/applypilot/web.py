"""Loopback-only UI and API, with per-server request tokens and strict origins."""

import secrets
from pathlib import Path
from typing import Annotated, Literal
from urllib.parse import urlsplit

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, ValidationError
from starlette.middleware.trustedhost import TrustedHostMiddleware

from applypilot import __version__
from applypilot.demo import seed
from applypilot.domain import Answer, Job, Profile, Question, Resume, StatusUpdate
from applypilot.materials import extract_resume, generate
from applypilot.model import validate_endpoint
from applypilot.screening import assess
from applypilot.service import collect_jobs, export, import_jobs
from applypilot.sources import import_csv, job_from_url
from applypilot.storage import Workspace


class TextImport(BaseModel):
    text: str = Field(max_length=3_000_000)


class URLImport(BaseModel):
    url: str = Field(max_length=3000)


class MaterialRequest(BaseModel):
    resume_id: str | None = None


def create_app(workspace: Workspace | None = None) -> FastAPI:
    workspace = workspace or Workspace()
    app = FastAPI(title="ApplyPilot Local", docs_url=None, redoc_url=None, openapi_url=None)
    app.state.workspace = workspace
    app.state.token = secrets.token_urlsafe(32)
    static = Path(__file__).parent / "static"
    app.add_middleware(
        TrustedHostMiddleware, allowed_hosts=["localhost", "127.0.0.1", "[::1]", "testserver"]
    )

    @app.middleware("http")
    async def protect(request: Request, call_next):
        if request.url.path.startswith("/api/"):
            origin = request.headers.get("origin")
            if origin and urlsplit(origin).netloc != request.headers.get("host"):
                return JSONResponse(
                    {"detail": "Cross-origin requests are not allowed."}, status_code=403
                )
            token = request.headers.get("x-workspace-token", "")
            if not secrets.compare_digest(token, app.state.token):
                return JSONResponse(
                    {"detail": "Reload the workspace to refresh its request token."},
                    status_code=403,
                )
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Cache-Control"] = "no-store"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self'; "
            "img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'"
        )
        return response

    @app.exception_handler(ValueError)
    async def invalid_value(request: Request, exc: ValueError):
        if isinstance(exc, ValidationError):
            return JSONResponse(
                {"detail": "Input does not match the required fields."}, status_code=422
            )
        return JSONResponse({"detail": str(exc)}, status_code=400)

    @app.exception_handler(KeyError)
    async def not_found(request: Request, exc: KeyError):
        return JSONResponse({"detail": "Record not found in this profile."}, status_code=404)

    @app.get("/", response_class=HTMLResponse)
    def index():
        return (static / "index.html").read_text().replace("__WORKSPACE_TOKEN__", app.state.token)

    @app.get("/health")
    def health():
        return {"status": "ok", "version": __version__}

    @app.get("/api/state")
    def state():
        return {
            "profile": workspace.profile(),
            "profile_id": workspace.profile_id,
            "jobs": workspace.jobs(),
            "resumes": workspace.resumes(),
            "questions": workspace.questions(),
            "runs": workspace.runs(),
            "version": __version__,
        }

    @app.put("/api/profile")
    def save_profile(profile: Profile):
        if profile.model.enabled:
            validate_endpoint(profile.model)
        workspace.save_profile(profile)
        workspace.reassess(assess)
        return profile

    @app.post("/api/demo")
    def demo():
        return seed(workspace)

    @app.post("/api/jobs")
    def add_job(job: Job):
        return import_jobs(workspace, [job])

    @app.post("/api/import/csv")
    def csv_import(payload: TextImport):
        return import_jobs(workspace, import_csv(payload.text))

    @app.post("/api/import/url")
    def url_import(payload: URLImport):
        return import_jobs(workspace, [job_from_url(payload.url)])

    @app.post("/api/collect")
    def collect():
        return collect_jobs(workspace)

    @app.post("/api/resumes")
    def add_resume(resume: Resume):
        return workspace.add_resume(resume)

    @app.post("/api/resumes/upload")
    async def upload_resume(
        file: Annotated[UploadFile, File()],
        label: Annotated[str, Form()] = "Imported resume",
        roles: Annotated[str, Form()] = "",
    ):
        content = await file.read(5_000_001)
        filename = Path(file.filename or "resume.txt").name
        try:
            text = extract_resume(filename, content)
        except (OSError, LookupError) as exc:
            raise HTTPException(
                400, "The resume could not be read. Try a text or Markdown file."
            ) from exc
        return workspace.add_resume(
            Resume(
                label=label,
                text=text,
                roles=[role.strip() for role in roles.split(",") if role.strip()],
                source_name=filename,
            )
        )

    @app.post("/api/jobs/{job_id}/materials")
    def materials(job_id: str, payload: MaterialRequest):
        return generate(workspace, job_id, payload.resume_id)

    @app.get("/api/jobs/{job_id}/materials/{filename}")
    def download_material(job_id: str, filename: str):
        material = workspace.job(job_id)["material"]
        allowed = {
            "resume.pdf",
            "resume.md",
            "preparation.md",
            "source-resume.txt",
            "manifest.json",
        }
        if not material or filename not in allowed:
            raise HTTPException(404, "Material not found.")
        path = workspace.path / "materials" / material["id"] / filename
        if not path.is_file():
            raise HTTPException(404, "Material file is missing. Generate it again.")
        return FileResponse(path, filename=filename)

    @app.patch("/api/jobs/{job_id}/status")
    def update_status(job_id: str, update: StatusUpdate):
        workspace.update_status(job_id, update)
        return workspace.job(job_id)

    @app.get("/api/jobs/{job_id}/events")
    def events(job_id: str):
        return workspace.events(job_id)

    @app.post("/api/questions")
    def add_question(question: Question):
        return {"id": workspace.add_question(question.text, question.scope, question.job_id)}

    @app.post("/api/answers")
    def save_answer(answer: Answer):
        workspace.save_answer(answer)
        return {"saved": True}

    @app.get("/api/export/{format}")
    def export_jobs(format: Literal["csv", "json"]):
        return Response(
            export(workspace, format),
            media_type="text/csv" if format == "csv" else "application/json",
            headers={"Content-Disposition": f'attachment; filename="applications.{format}"'},
        )

    app.mount("/static", StaticFiles(directory=static), name="static")
    return app
