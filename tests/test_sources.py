"""Adapter contracts using deterministic source fixtures, not real vacancies."""

import json

import pytest

from applypilot.domain import Profile, Source
from applypilot.sources import (
    collect,
    greenhouse,
    import_csv,
    job_from_url,
    lever,
    validate_public_url,
)


def test_greenhouse_reads_description_without_inventing_publication_date():
    data = {
        "jobs": [
            {
                "id": 1,
                "title": "Designer",
                "absolute_url": "https://example.com/jobs/1",
                "location": {"name": "London"},
                "content": "<p>Research and <b>design</b></p>",
                "updated_at": "2026-01-01",
            }
        ]
    }
    jobs = greenhouse(Source(kind="greenhouse", board="example"), lambda *args: json.dumps(data))
    assert jobs[0].description == "Research and design"
    assert jobs[0].posted_at is None
    assert jobs[0].availability == "open"


def test_lever_keeps_employment_lists_and_creation_time():
    data = [
        {
            "id": "1",
            "text": "Analyst",
            "hostedUrl": "https://example.com/jobs/1",
            "categories": {"location": "Remote"},
            "description": "<p>Analysis</p>",
            "lists": [{"content": "<li>Forecasting</li>"}],
            "createdAt": 1700000000000,
            "workplaceType": "remote",
        }
    ]
    posting = lever(Source(kind="lever", board="example"), lambda *args: json.dumps(data))[0]
    assert "Forecasting" in posting.description
    assert posting.remote
    assert posting.posted_at.startswith("2023")


def test_one_source_failure_does_not_erase_other_results():
    profile = Profile(
        sources=[Source(kind="greenhouse", board="good"), Source(kind="lever", board="bad")]
    )

    def get(url, *args):
        if "lever" in url:
            raise ValueError("Unavailable")
        return json.dumps(
            {"jobs": [{"id": 1, "title": "Designer", "absolute_url": "https://example.com/jobs/1"}]}
        )

    result = collect(profile, get)
    assert len(result["jobs"]) == 1
    assert result["sources"][1]["error"]


def test_csv_boolean_false_and_salary_types_are_preserved():
    posting = import_csv(
        "title,company,url,remote,salary_max,currency,period\nAnalyst,Example,https://example.com/1,false,95000,EUR,year\n"
    )[0]
    assert posting.remote is False
    assert posting.salary_max == 95000


def test_csv_requires_identity_columns():
    with pytest.raises(ValueError, match="columns"):
        import_csv("foo,bar\n1,2")


def test_url_import_requires_job_identity():
    with pytest.raises(ValueError, match="structured"):
        job_from_url("https://example.com", lambda _: "<h1>Welcome to a company</h1>")


def test_url_import_uses_structured_posting_not_http_success():
    data = {
        "@type": "JobPosting",
        "title": "Designer",
        "description": "<p>Design research</p>",
        "hiringOrganization": {"name": "Example"},
        "validThrough": "2000-01-01T00:00:00Z",
    }
    posting = job_from_url(
        "https://example.com/job",
        lambda _: f'<script type="application/ld+json">{json.dumps(data)}</script>',
    )
    assert posting.company == "Example"
    assert posting.availability == "expired"


@pytest.mark.parametrize(
    "url",
    [
        "file:///etc/passwd",
        "http://127.0.0.1/",
        "http://169.254.169.254/",
        "http://[::1]/",
        "https://user:secret@example.com/",
    ],
)
def test_private_network_and_credential_urls_are_rejected(url):
    with pytest.raises(ValueError):
        validate_public_url(url)


def test_missing_search_keys_are_a_visible_source_failure(monkeypatch):
    monkeypatch.delenv("ADZUNA_APP_ID", raising=False)
    monkeypatch.delenv("ADZUNA_APP_KEY", raising=False)
    result = collect(Profile(sources=[Source(kind="adzuna")]), lambda *args: "{}")
    assert result["sources"][0]["error"]
