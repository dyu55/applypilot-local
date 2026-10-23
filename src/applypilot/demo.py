"""Fictional, offline-only sample data. No accounts or job sites are contacted."""

from applypilot.domain import Job, Profile, Resume, Rules
from applypilot.screening import assess
from applypilot.storage import Workspace

RESUME = """# Alex Morgan
Product Designer | Portland, OR | alex@example.com

## SUMMARY
Product designer with experience translating customer needs into clear digital experiences.
Works across research, interaction design, prototyping, and accessible interfaces.

## EXPERIENCE
Product Designer | Northstar Studio (fictional) | 2022 - 2025
- Conducted customer interviews and usability testing to inform product decisions.
- Built accessible interface components and documented a shared design system in Figma.
- Partnered with engineers to deliver responsive web experiences and review implementation.
- Created interactive prototypes to explore onboarding flows and clarify product requirements.

Design Associate | Paperplane Collective (fictional) | 2020 - 2022
- Synthesized UX research into journey maps and practical recommendations.
- Designed wireframes and visual concepts for small business websites.
- Presented design rationale and incorporated feedback from clients and teammates.

## SKILLS
Figma, UX research, prototyping, accessibility, design systems, usability testing

## EDUCATION
Bachelor of Design | Example School of Design (fictional) | 2020
"""


def seed(workspace: Workspace) -> dict:
    if workspace.jobs() or workspace.resumes() or workspace.profile().name:
        raise ValueError("Load the demo into an empty profile to keep your own data separate.")
    profile = Profile(
        name="Alex Morgan",
        email="alex@example.com",
        location="Portland, OR",
        target_roles=["Designer", "UX Researcher"],
        skills=["Figma", "UX research", "prototyping", "accessibility", "design systems"],
        rules=Rules(minimum_salary=85000, salary_currency="USD", excluded_titles=["Director"]),
    )
    workspace.save_profile(profile)
    workspace.add_resume(
        Resume(
            label="Product design", roles=["Designer"], text=RESUME, source_name="fictional demo"
        )
    )
    entries = [
        (
            "Product Designer",
            "Forma Studio",
            "Portland, OR",
            105000,
            "Figma UX research prototyping accessibility design systems",
            "open",
        ),
        (
            "Senior Product Designer",
            "Orbit Health",
            "Remote, US",
            140000,
            "Figma prototyping accessibility design systems for patient experiences",
            "open",
        ),
        (
            "UX Researcher",
            "Fieldwork",
            "Seattle, WA",
            110000,
            "UX research usability testing and customer interviews",
            "unknown",
        ),
        (
            "Interaction Designer",
            "Common Ground",
            "Remote, US",
            100000,
            "Figma accessibility prototyping public services",
            "open",
        ),
        (
            "Director of Design",
            "Evergreen Labs",
            "Portland, OR",
            160000,
            "Design systems leadership and Figma",
            "open",
        ),
        (
            "Junior Designer",
            "Little Office",
            "Portland, OR",
            60000,
            "Figma and prototyping",
            "open",
        ),
        (
            "Product Designer",
            "Archive Works",
            "Austin, TX",
            100000,
            "Figma UX research and accessibility",
            "expired",
        ),
    ]
    for index, (title, company, location, salary, description, availability) in enumerate(entries):
        job = Job(
            source="demo",
            source_id=f"fictional-{index}",
            title=title,
            company=company,
            url=f"https://example.com/fictional-jobs/{index}",
            location=location,
            salary_min=salary - 15000,
            salary_max=salary,
            currency="USD",
            period="year",
            description=(
                f"Fictional demo posting. Work on {description}. Collaborate with a "
                "cross-functional team, communicate design decisions, and help improve "
                "the customer experience."
            ),
            remote="Remote" in location,
            availability=availability,
            availability_evidence="Fictional offline fixture; this is not a real vacancy.",
        )
        workspace.add_job(job, assess(job, profile))
    return {
        "imported": len(entries),
        "demo": True,
        "message": "Fictional demo loaded. No real applications were made.",
    }
