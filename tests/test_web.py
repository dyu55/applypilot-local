"""Complete local API flows, private-origin controls, and safe material delivery."""

from fastapi.testclient import TestClient

from applypilot.web import create_app


def test_workspace_page_and_packaged_assets(client):
    assert client.get("/").status_code == 200
    assert "__WORKSPACE_TOKEN__" not in client.get("/").text
    assert client.get("/static/app.js").status_code == 200
    assert client.get("/static/style.css").status_code == 200
    assert client.get("/health").json()["status"] == "ok"


def test_api_requires_server_token(workspace):
    with TestClient(create_app(workspace)) as client:
        assert client.get("/api/state").status_code == 403
        assert client.post("/api/demo").status_code == 403


def test_foreign_origin_and_dns_rebinding_hosts_are_blocked(client):
    assert client.post("/api/demo", headers={"Origin": "https://example.org"}).status_code == 403
    assert client.get("/", headers={"Host": "malicious.example"}).status_code == 400


def test_full_demo_material_and_submission_flow(client):
    assert client.post("/api/demo").status_code == 200
    state = client.get("/api/state").json()
    assert len(state["jobs"]) == 7
    job = next(j for j in state["jobs"] if j["status"] == "Pending")
    path = f"/api/jobs/{job['id']}"
    material = client.post(path + "/materials", json={})
    assert material.status_code == 200, material.text
    assert client.get(path + "/materials/resume.pdf").content.startswith(b"%PDF")
    assert client.patch(path + "/status", json={"status": "Submitted"}).status_code == 400
    assert (
        client.patch(
            path + "/status", json={"status": "Submitted", "evidence": "User-reported receipt 123"}
        ).status_code
        == 200
    )
    assert client.get(path + "/events").json()[0]["evidence_type"] == "user_reported"
    assert client.get("/api/export/csv").status_code == 200
    assert "Submitted" in client.get("/api/export/json").text


def test_upload_editable_resume(client):
    from applypilot.demo import RESUME

    response = client.post(
        "/api/resumes/upload",
        files={"file": ("source.md", RESUME.encode(), "text/plain")},
        data={"label": "My resume", "roles": "Designer"},
    )
    assert response.status_code == 200
    assert response.json()["text"] == RESUME
    assert response.json()["roles"] == ["Designer"]


def test_questions_answers_and_dedup_in_api(client):
    for text in ["Are you available?", "are you available!"]:
        assert (
            client.post("/api/questions", json={"text": text, "scope": "general"}).status_code
            == 200
        )
    assert len(client.get("/api/state").json()["questions"]) == 1
    assert (
        client.post(
            "/api/answers",
            json={
                "question": "Are you available?",
                "scope": "general",
                "text": "After notice period",
            },
        ).status_code
        == 200
    )
    assert client.get("/api/state").json()["questions"][0]["resolved"]


def test_missing_record_is_404(client):
    assert client.patch("/api/jobs/missing/status", json={"status": "Pending"}).status_code == 404


def test_no_source_returns_actionable_error(client):
    response = client.post("/api/collect")
    assert response.status_code == 400
    assert "Settings" in response.json()["detail"]
