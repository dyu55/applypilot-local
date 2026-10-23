"""Exercise installed CLI, packaged assets, and PDFs outside the source checkout."""

import tempfile

from fastapi.testclient import TestClient

from applypilot.demo import seed
from applypilot.materials import generate
from applypilot.storage import Workspace
from applypilot.web import create_app


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="applypilot-smoke-") as root:
        workspace = Workspace(root, "smoke")
        seed(workspace)
        app = create_app(workspace)
        with TestClient(app, headers={"X-Workspace-Token": app.state.token}) as client:
            assert client.get("/").status_code == 200
            assert client.get("/static/app.js").status_code == 200
            assert len(client.get("/api/state").json()["jobs"]) == 7
            job = next(job for job in workspace.jobs() if job["status"] == "Pending")
            material = generate(workspace, job["id"])
            assert material["quality"]["text_verified"]
            assert workspace.job(job["id"])["status"] == "Pending"
    print("Installed package smoke passed: UI assets, isolated demo, and verified PDF.")


if __name__ == "__main__":
    main()
