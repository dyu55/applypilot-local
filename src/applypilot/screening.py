"""Deterministic screening with explicit reasons and no inferred personal facts."""

import re
from datetime import UTC, datetime

from applypilot.domain import Assessment, Job, Profile, Status


def contains(text: str, phrase: str) -> bool:
    return bool(re.search(r"(?<!\w)" + re.escape(phrase.casefold()) + r"(?!\w)", text.casefold()))


def assess(job: Job, profile: Profile) -> Assessment:
    result = Assessment()
    rules = profile.rules
    text = f"{job.title} {job.description}"
    result.matched_skills = [skill for skill in profile.skills if contains(text, skill)]
    result.missing_skills = [
        skill for skill in profile.skills if skill not in result.matched_skills
    ]
    skip = []
    review = []
    if job.availability == "expired":
        skip.append("The source explicitly marks this posting as closed.")
    if any(contains(job.title, title) for title in rules.excluded_titles):
        skip.append("The title matches an excluded role.")
    if job.company.casefold() in {value.casefold() for value in rules.excluded_companies}:
        skip.append("The company is excluded by your rules.")
    if profile.target_roles and not any(contains(job.title, role) for role in profile.target_roles):
        skip.append("The title does not match your target roles.")
    if rules.locations and not (job.remote and rules.allow_remote):
        if not job.location:
            review.append("The posting does not provide a location.")
        elif not any(contains(job.location, place) for place in rules.locations):
            skip.append("The location does not match your preferences.")
    if job.remote and not rules.allow_remote:
        skip.append("Remote roles are disabled in your rules.")
    if rules.minimum_salary is not None:
        salary = job.salary_max if job.salary_max is not None else job.salary_min
        if salary is None:
            if rules.unknown_salary == "skip":
                skip.append("Salary is undisclosed and your rules exclude undisclosed salaries.")
            elif rules.unknown_salary == "review":
                review.append("Salary is undisclosed; confirm compensation before proceeding.")
        elif job.currency.casefold() != rules.salary_currency.casefold():
            review.append("Salary currency differs from your rule; no exchange rate was assumed.")
        elif job.period != rules.salary_period:
            review.append("Salary period differs from your rule; no annualization was assumed.")
        elif salary < rules.minimum_salary:
            skip.append("The published salary ceiling is below your minimum.")
    if rules.max_age_days and job.posted_at:
        try:
            posted = datetime.fromisoformat(job.posted_at.replace("Z", "+00:00"))
            posted = posted.replace(tzinfo=UTC) if posted.tzinfo is None else posted
            if (datetime.now(UTC) - posted).days > rules.max_age_days:
                skip.append("The posting is older than your configured freshness limit.")
        except ValueError:
            review.append("The posting date could not be verified.")
    if job.sponsorship == "unavailable":
        fact = profile.facts.get("needs_sponsorship")
        scope_matches = bool(
            fact and job.country and fact.scope.casefold() == job.country.casefold()
        )
        if not scope_matches or fact is None or fact.value is None:
            review.append("Confirm sponsorship requirements for the posting's country.")
        elif fact.value is True:
            skip.append(
                "The posting does not sponsor and your confirmed profile requires sponsorship."
            )
    if job.availability == "unknown":
        result.reasons.append("Posting availability has not been independently confirmed.")
    if skip:
        result.status = Status.SKIPPED
        result.reasons = skip + review + result.reasons
    elif review:
        result.status = Status.NEEDS_USER
        result.reasons = review + result.reasons
    else:
        result.reasons.insert(0, "Matches your configured screening rules.")
    if profile.skills:
        ratio = len(result.matched_skills) / len(profile.skills)
        result.fit = "High" if ratio >= 0.6 else "Medium" if ratio >= 0.25 else "Low"
    return result
