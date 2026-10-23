"""Read-only public job sources. No application submission endpoints are called."""

import csv
import html
import io
import ipaddress
import json
import os
import re
import socket
import time
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any
from urllib.parse import quote, urljoin, urlsplit

import httpx
from bs4 import BeautifulSoup

from applypilot.domain import Job, Profile, Source

MAX_DOWNLOAD = 3_000_000


def plain(content: str) -> str:
    soup = BeautifulSoup(html.unescape(content or ""), "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    return soup.get_text(" ", strip=True)


def validate_public_url(url: str) -> None:
    parsed = urlsplit(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username:
        raise ValueError("Use a public HTTP or HTTPS URL without credentials.")
    if parsed.port not in {None, 80, 443}:
        raise ValueError("Public job sources must use standard HTTP or HTTPS ports.")
    try:
        addresses = socket.getaddrinfo(parsed.hostname, parsed.port or 443, type=socket.SOCK_STREAM)
    except OSError as exc:
        raise ValueError("The job source hostname could not be resolved.") from exc
    if not addresses or any(not ipaddress.ip_address(item[4][0]).is_global for item in addresses):
        raise ValueError("Job sources must not point to private or local network addresses.")


class PublicReader:
    """Bounded downloads with redirect validation and limited read-only retries."""

    def __init__(self) -> None:
        self.client = httpx.Client(
            timeout=15,
            headers={"User-Agent": "ApplyPilotLocal/0.1 (personal job search)"},
            follow_redirects=False,
        )

    def close(self) -> None:
        self.client.close()

    def get(self, url: str, params: dict[str, Any] | None = None) -> str:
        for _ in range(4):
            validate_public_url(url)
            for attempt in range(2):
                try:
                    with self.client.stream("GET", url, params=params) as response:
                        if response.is_redirect:
                            url = urljoin(url, response.headers["location"])
                            params = None
                            break
                        response.raise_for_status()
                        body = bytearray()
                        for part in response.iter_bytes():
                            body.extend(part)
                            if len(body) > MAX_DOWNLOAD:
                                raise ValueError("The job source exceeds the download size limit.")
                        return body.decode("utf-8", errors="replace")
                except (httpx.TimeoutException, httpx.NetworkError):
                    if attempt:
                        raise ValueError("The source could not be reached; retry later.") from None
                    time.sleep(0.2)
                except httpx.HTTPStatusError as exc:
                    code = exc.response.status_code
                    raise ValueError(
                        f"The source returned HTTP {code}; availability is unknown."
                    ) from None
            else:
                continue
        raise ValueError("The source redirected too many times; availability is unknown.")


def _board(value: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,120}", value):
        raise ValueError("Enter the board identifier, not a URL, for this source.")
    return quote(value, safe="")


def greenhouse(source: Source, get: Callable[..., str]) -> list[Job]:
    data = json.loads(
        get(
            f"https://boards-api.greenhouse.io/v1/boards/{_board(source.board)}/jobs",
            {"content": "true"},
        )
    )
    return [
        Job(
            source=f"greenhouse:{source.board}",
            source_id=str(item["id"]),
            title=item["title"],
            company=source.board,
            url=item["absolute_url"],
            location=item.get("location", {}).get("name", ""),
            description=plain(item.get("content", "")),
            availability="open",
            availability_evidence="Listed by the public Greenhouse board API at fetch time.",
            # Greenhouse updated_at is not a publication timestamp.
        )
        for item in data["jobs"][:250]
    ]


def lever(source: Source, get: Callable[..., str]) -> list[Job]:
    host = "api.eu.lever.co" if source.region == "eu" else "api.lever.co"
    data = json.loads(get(f"https://{host}/v0/postings/{_board(source.board)}", {"mode": "json"}))
    return [
        Job(
            source=f"lever:{source.board}",
            source_id=item["id"],
            title=item["text"],
            company=source.board,
            url=item["hostedUrl"],
            location=item.get("categories", {}).get("location", ""),
            description=plain(
                item.get("description", "")
                + " ".join(part.get("content", "") for part in item.get("lists", []))
                + item.get("additional", "")
            ),
            remote=item.get("workplaceType") == "remote",
            availability="open",
            availability_evidence="Listed by the public Lever postings API at fetch time.",
            posted_at=(
                datetime.fromtimestamp(item["createdAt"] / 1000, UTC).isoformat()
                if item.get("createdAt")
                else None
            ),
        )
        for item in data[:250]
    ]


def remoteok(source: Source, get: Callable[..., str]) -> list[Job]:
    data = json.loads(get("https://remoteok.com/api"))
    query = source.query.casefold()
    return [
        Job(
            source="remoteok",
            source_id=str(item["id"]),
            title=item["position"],
            company=item["company"],
            url=item["url"],
            location=item.get("location", "Remote"),
            description=plain(item.get("description", "")),
            salary_min=item.get("salary_min") or None,
            salary_max=item.get("salary_max") or None,
            currency="USD" if item.get("salary_min") or item.get("salary_max") else "",
            period="year" if item.get("salary_min") or item.get("salary_max") else "",
            posted_at=item.get("date"),
            remote=True,
            availability="open",
            availability_evidence="Listed by Remote OK; verify employer location restrictions.",
        )
        for item in data
        if isinstance(item, dict)
        and item.get("position")
        and (not query or query in f"{item['position']} {item.get('tags', [])}".casefold())
    ][:100]


def adzuna(source: Source, get: Callable[..., str]) -> list[Job]:
    app_id, api_key = os.getenv("ADZUNA_APP_ID"), os.getenv("ADZUNA_APP_KEY")
    if not app_id or not api_key:
        raise ValueError("Set ADZUNA_APP_ID and ADZUNA_APP_KEY to enable this search source.")
    if not re.fullmatch(r"[a-z]{2}", source.region):
        raise ValueError("Adzuna requires a two-letter country code.")
    data = json.loads(
        get(
            f"https://api.adzuna.com/v1/api/jobs/{source.region}/search/1",
            {"app_id": app_id, "app_key": api_key, "what": source.query, "results_per_page": 50},
        )
    )
    # The API's salary_is_predicted flag distinguishes estimates from disclosed pay.
    return [
        Job(
            source=f"adzuna:{source.region}",
            source_id=str(item["id"]),
            title=plain(item["title"]),
            company=item.get("company", {}).get("display_name", "Undisclosed employer"),
            url=item["redirect_url"],
            location=item.get("location", {}).get("display_name", ""),
            description=plain(item.get("description", "")),
            posted_at=item.get("created"),
            country=source.region.upper(),
            # Search results alone do not prove an employer posting is still open.
            availability="unknown",
        )
        for item in data.get("results", [])[:50]
    ]


def collect(profile: Profile, get: Callable[..., str] | None = None) -> dict[str, Any]:
    reader = PublicReader() if get is None else None
    fetch = get or reader.get  # type: ignore[union-attr]
    jobs: list[Job] = []
    results = []
    adapters = {"greenhouse": greenhouse, "lever": lever, "remoteok": remoteok, "adzuna": adzuna}
    try:
        for source in (entry for entry in profile.sources if entry.enabled):
            try:
                found = adapters[source.kind](source, fetch)
                jobs.extend(found)
                results.append({"source": source.kind, "board": source.board, "count": len(found)})
            except (ValueError, KeyError, TypeError, httpx.HTTPError):
                results.append(
                    {
                        "source": source.kind,
                        "board": source.board,
                        "error": "Source unavailable or incomplete. Check its settings.",
                    }
                )
    finally:
        if reader:
            reader.close()
    return {"jobs": jobs, "sources": results}


def import_csv(text: str) -> list[Job]:
    rows = csv.DictReader(io.StringIO(text))
    if not rows.fieldnames or not {"title", "company", "url"}.issubset(rows.fieldnames):
        raise ValueError("CSV requires title, company, and url columns.")
    jobs = []
    for index, raw in enumerate(rows):
        if index >= 1000:
            raise ValueError("Import at most 1,000 jobs per file.")
        data: dict[str, Any] = {k: v for k, v in raw.items() if k in Job.model_fields and v != ""}
        for field in ("remote",):
            if field in data:
                data[field] = data[field].casefold() in {"true", "1", "yes"}
        jobs.append(Job.model_validate(data))
    return jobs


def job_from_url(url: str, get: Callable[..., str] | None = None) -> Job:
    Job(title="Imported posting", company="Unverified employer", url=url)
    reader = PublicReader() if get is None else None
    try:
        page = (get or reader.get)(url)  # type: ignore[union-attr]
    finally:
        if reader:
            reader.close()
    soup = BeautifulSoup(page, "html.parser")
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.get_text())
        except (ValueError, TypeError):
            continue
        if not isinstance(data, (list, dict)):
            continue
        entries = data if isinstance(data, list) else data.get("@graph", [data])
        for item in entries:
            if not isinstance(item, dict) or "JobPosting" not in str(item.get("@type", "")):
                continue
            org = item.get("hiringOrganization") or {}
            location = item.get("jobLocation") or {}
            if isinstance(location, list):
                location = location[0] if location else {}
            address = location.get("address", {}) if isinstance(location, dict) else {}
            address = address if isinstance(address, dict) else {}
            expiry = item.get("validThrough")
            expired = False
            if expiry:
                try:
                    expires = datetime.fromisoformat(expiry.replace("Z", "+00:00"))
                    expired = expires.replace(tzinfo=expires.tzinfo or UTC) < datetime.now(UTC)
                except ValueError:
                    pass
            return Job(
                title=item.get("title") or "Imported posting",
                company=org.get("name", "Unverified employer")
                if isinstance(org, dict)
                else str(org),
                url=url,
                description=plain(item.get("description", "")),
                location=", ".join(
                    str(address.get(k, ""))
                    for k in ("addressLocality", "addressRegion", "addressCountry")
                    if address.get(k)
                ),
                country=str(address.get("addressCountry", "")),
                posted_at=item.get("datePosted"),
                remote=item.get("jobLocationType") == "TELECOMMUTE",
                availability="expired" if expired else "unknown",
                availability_evidence="Structured job data found; inspect the Apply page.",
            )
    raise ValueError(
        "No structured job posting was found. Paste the job details or import a CSV instead."
    )
