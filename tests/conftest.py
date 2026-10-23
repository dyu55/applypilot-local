"""Fresh, private workspaces for every test."""

import pytest
from fastapi.testclient import TestClient

from applypilot.storage import Workspace
from applypilot.web import create_app


@pytest.fixture
def workspace(tmp_path):
    return Workspace(tmp_path / "private data")


@pytest.fixture
def client(workspace):
    app = create_app(workspace)
    with TestClient(app, headers={"X-Workspace-Token": app.state.token}) as client:
        yield client
