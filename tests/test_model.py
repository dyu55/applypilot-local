"""No provider credentials needed: models may permute IDs, never author facts."""

import json

import httpx
import pytest

from applypilot.domain import ModelSettings
from applypilot.model import BulletRanker, validate_endpoint


def response(order):
    return httpx.Response(
        200,
        json={"choices": [{"message": {"content": json.dumps({"order": order})}}]},
        request=httpx.Request("POST", "http://localhost/v1/chat/completions"),
    )


def test_valid_model_permutation_and_call_budget():
    ranker = BulletRanker(
        ModelSettings(model="example", max_calls_per_run=1),
        post=lambda *args, **kwargs: response([1, 0]),
    )
    assert ranker.order(["First fact", "Second fact"], "Job description") == [1, 0]
    with pytest.raises(ValueError, match="limit"):
        ranker.order(["First fact"], "Job")


@pytest.mark.parametrize("order", [[0, 0], [2, 0], ["1", 0], [True, 0], "New fabricated claim"])
def test_model_cannot_replace_or_drop_source_bullets(order):
    ranker = BulletRanker(
        ModelSettings(model="example"), post=lambda *args, **kwargs: response(order)
    )
    with pytest.raises(ValueError):
        ranker.order(["First fact", "Second fact"], "Job")


def test_remote_model_requires_https_and_key(monkeypatch):
    monkeypatch.delenv("APPLYPILOT_MODEL_API_KEY", raising=False)
    with pytest.raises(ValueError):
        validate_endpoint(ModelSettings(base_url="http://example.com/v1", model="example"))
    with pytest.raises(ValueError):
        validate_endpoint(ModelSettings(base_url="https://example.com/v1", model="example"))


def test_model_request_omits_profile_and_answer_bank():
    requests = []

    def post(*args, **kwargs):
        requests.append(kwargs["json"])
        return response([0])

    BulletRanker(ModelSettings(model="example"), post=post).order(
        ["A source bullet"], "A job excerpt"
    )
    data = json.loads(requests[0]["messages"][1]["content"])
    assert set(data) == {"job_description", "bullets"}
