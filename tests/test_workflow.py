"""Behavioral contracts for profiles, screening, deduplication, and truthful status."""

from collections import Counter

import pytest

from applypilot.demo import RESUME, seed
from applypilot.domain import Answer, Fact, Job, Profile, Resume, Rules, Status, StatusUpdate
from applypilot.materials import generate, select_resume, tailor
from applypilot.screening import assess
from applypilot.service import export, import_jobs
from applypilot.storage import Workspace, canonical_url


def job(**changes):
    return Job.model_validate(
        {
            "title": "Operations Analyst",
            "company": "Example Employer",
            "url": "https://example.com/jobs?id=123",
            **changes,
        }
    )


def test_profiles_are_isolated(tmp_path):
    a, b = Workspace(tmp_path, "person-a"), Workspace(tmp_path, "person-b")
    a.save_profile(Profile(name="Fictional A"))
    import_jobs(a, [job()])
    assert not b.profile().name
    assert b.jobs() == []
    assert a.profile().name == "Fictional A"


@pytest.mark.parametrize("profile_id", ["../other", "a/b", "", ".hidden", "a\\b"])
def test_profile_ids_cannot_escape_data_root(tmp_path, profile_id):
    with pytest.raises(ValueError):
        Workspace(tmp_path, profile_id)


def test_dedup_keeps_requisition_identifiers(workspace):
    first = job(url="https://example.com/jobs?id=123&utm_source=mail")
    same = job(url="https://example.com/jobs?utm_medium=email&id=123#apply")
    other = job(url="https://example.com/jobs?id=124")
    assert import_jobs(workspace, [first, same, other]) == {"imported": 2, "duplicates": 1}
    assert len(workspace.jobs()) == 2
    assert "id=123" in canonical_url(first.url)


def test_same_source_id_dedups_changed_links(workspace):
    result = import_jobs(
        workspace,
        [
            job(source="test", source_id="1"),
            job(source="test", source_id="1", url="https://example.com/new"),
        ],
    )
    assert result["duplicates"] == 1


@pytest.mark.parametrize(
    "period,currency,status",
    [
        ("year", "EUR", Status.NEEDS_USER),
        ("hour", "USD", Status.NEEDS_USER),
        ("year", "USD", Status.SKIPPED),
    ],
)
def test_salary_units_are_never_assumed(period, currency, status):
    result = assess(
        job(salary_max=40, currency=currency, period=period),
        Profile(rules=Rules(minimum_salary=50000)),
    )
    assert result.status == status


@pytest.mark.parametrize(
    "policy,status",
    [("allow", Status.PENDING), ("review", Status.NEEDS_USER), ("skip", Status.SKIPPED)],
)
def test_unknown_salary_policy(policy, status):
    assert (
        assess(job(), Profile(rules=Rules(minimum_salary=50000, unknown_salary=policy))).status
        == status
    )


def test_salary_ceiling_not_floor_controls_minimum():
    assert (
        assess(
            job(salary_min=40000, salary_max=90000, currency="USD", period="year"),
            Profile(rules=Rules(minimum_salary=80000)),
        ).status
        == Status.PENDING
    )


def test_sponsorship_scope_and_unknown_are_respected():
    posting = job(sponsorship="unavailable", country="GB")
    profile = Profile(facts={"needs_sponsorship": Fact(value=False, scope="US")})
    assert assess(posting, profile).status == Status.NEEDS_USER
    profile.facts["needs_sponsorship"] = Fact(value=False, scope="GB")
    assert assess(posting, profile).status == Status.PENDING
    profile.facts["needs_sponsorship"] = Fact(value=True, scope="GB")
    assert assess(posting, profile).status == Status.SKIPPED


def test_non_engineering_profile_and_locations():
    profile = Profile(
        target_roles=["Analyst"], skills=["Excel", "forecasting"], rules=Rules(locations=["London"])
    )
    result = assess(job(location="London, GB", description="Excel and forecasting"), profile)
    assert result.status == Status.PENDING
    assert result.fit == "High"
    assert assess(job(location="Berlin, DE"), profile).status == Status.SKIPPED


def test_empty_location_is_review_not_guessed():
    assert assess(job(), Profile(rules=Rules(locations=["London"]))).status == Status.NEEDS_USER


def test_keyword_boundaries_prevent_single_letter_matches():
    assert (
        assess(
            job(description="Research and communication"), Profile(skills=["R", "C"])
        ).matched_skills
        == []
    )


def test_submitted_requires_evidence(workspace):
    key = workspace.add_job(job(), assess(job(), Profile()))[0]
    with pytest.raises(ValueError, match="confirmation"):
        workspace.update_status(key, StatusUpdate(status=Status.SUBMITTED))
    assert workspace.job(key)["status"] == "Pending"
    workspace.update_status(
        key, StatusUpdate(status=Status.SUBMITTED, evidence="User observed application receipt 123")
    )
    assert workspace.events(key)[0]["evidence_type"] == "user_reported"
    assert workspace.job(key)["status"] == "Submitted"


def test_rule_changes_do_not_erase_user_decisions(workspace):
    key = workspace.add_job(job(), assess(job(), Profile()))[0]
    workspace.update_status(
        key, StatusUpdate(status=Status.SUBMITTED, evidence="User-reported email receipt")
    )
    workspace.save_profile(Profile(rules=Rules(excluded_titles=["Analyst"])))
    workspace.reassess(assess)
    assert workspace.job(key)["status"] == "Submitted"
    assert workspace.job(key)["assessment"]["status"] == "Skipped"


def test_materials_preserve_source_and_application_state(workspace):
    seed(workspace)
    key = next(j["id"] for j in workspace.jobs() if j["status"] == "Pending")
    first = generate(workspace, key)
    second = generate(workspace, key)
    assert first["id"] != second["id"]
    assert first["quality"]["text_verified"]
    assert first["quality"]["words"] >= 40
    assert (workspace.path / "materials" / first["id"] / "resume.pdf").is_file()
    assert (workspace.path / "materials" / second["id"] / "source-resume.txt").read_text() == RESUME
    assert workspace.job(key)["status"] == "Pending"
    assert workspace.events(key) == []


def test_tailoring_only_permutes_existing_lines():
    tailored, _ = tailor(RESUME, job(description="accessibility design systems"))
    assert Counter(tailored.splitlines()) == Counter(RESUME.splitlines())
    assert "2022 - 2025" in tailored


def test_route_resume_by_role_and_allow_explicit_override():
    a = Resume(id="a", label="General", text=RESUME)
    b = Resume(id="b", label="Operations", roles=["Analyst"], text=RESUME)
    assert select_resume([a, b], job()).id == "b"
    assert select_resume([a, b], job(), "a").id == "a"
    with pytest.raises(ValueError):
        select_resume([a, b], job(), "missing")


def test_question_dedup_respects_scope_and_confirmed_answers(workspace):
    a = workspace.add_question("Do you need sponsorship?", "US")
    b = workspace.add_question("do you need sponsorship!", "US")
    c = workspace.add_question("Do you need sponsorship?", "GB")
    assert a == b and a != c
    workspace.save_answer(Answer(question="Do you need sponsorship?", scope="US", text="No"))
    questions = workspace.questions()
    assert sum(bool(q["resolved"]) for q in questions) == 1
    assert workspace.answer("Do you need sponsorship?", "GB") is None


def test_resume_based_draft_does_not_become_confirmed(workspace):
    resume = workspace.add_resume(Resume(label="Example", text=RESUME))
    workspace.add_question("Describe teamwork", "general")
    workspace.save_answer(
        Answer(
            question="Describe teamwork",
            scope="general",
            text="Draft based on source",
            source="resume_based_draft",
            resume_id=resume.id,
        )
    )
    workspace.add_question("Describe teamwork", "general")
    assert not workspace.questions()[0]["resolved"]
    assert workspace.questions()[0]["answer"]["source"] == "resume_based_draft"


def test_short_resume_rejected(workspace):
    with pytest.raises(ValueError, match="40 words"):
        workspace.add_resume(Resume(label="Empty", text="Hello world"))


def test_csv_export_neutralizes_spreadsheet_formulas(workspace):
    import_jobs(workspace, [job(title="=1+2")])
    assert "'=1+2" in export(workspace, "csv")


def test_demo_does_not_overwrite_existing_profile(workspace):
    workspace.save_profile(Profile(name="Existing User"))
    with pytest.raises(ValueError):
        seed(workspace)
    assert workspace.profile().name == "Existing User"
