"""Validate the user's recorded preparation preferences, without inferring answers."""

from batch_lib import require, text, timestamp

PREFERENCE_GROUPS = (
    "roles",
    "levels",
    "employers",
    "locations",
    "work_arrangement",
    "skills",
    "compensation",
    "employment",
    "eligibility",
    "freshness",
    "materials",
    "delivery",
    "other",
)
WORKFLOW_STAGES = ("intake", "deduplication", "screening", "ranking", "resume_routing")


def validate_strategy(batch):
    strategy = batch.get("strategy")
    require(isinstance(strategy, dict), "A completed first-run strategy is required.")
    require(
        strategy.get("setup_complete") is True, "Finish first-run setup before publishing v0.2."
    )
    timestamp(strategy.get("confirmed_at"))
    require(
        type(strategy.get("target_count")) is int
        and strategy["target_count"] == batch["requested_count"],
        "Batch target disagrees with the confirmed strategy.",
    )
    preferences = strategy.get("preferences")
    require(isinstance(preferences, dict), "Record the first-run preference responses.")
    for group in PREFERENCE_GROUPS:
        answer = preferences.get(group)
        require(isinstance(answer, dict), f"First-run response missing: {group}")
        require(
            answer.get("status") in {"answered", "no_preference", "unknown"},
            f"Invalid first-run response: {group}",
        )
        if answer["status"] == "answered":
            require(
                answer.get("value") not in (None, "", [], {}),
                f"Record the user's answer for {group}.",
            )
    ranking = strategy.get("ranking", {})
    require(isinstance(ranking, dict), "Ranking must be an object.")
    criteria = ranking.get("criteria")
    require(
        isinstance(criteria, list) and criteria,
        "Record ordered ranking criteria, or an explicit discovery_order choice.",
    )
    for criterion in criteria:
        text(criterion, "Ranking criterion")
    require(len(set(criteria)) == len(criteria), "Ranking criteria must not repeat.")
    quotas = strategy.get("role_quotas")
    require(
        isinstance(quotas, dict),
        "Role quotas must be an object; use an empty object for no quotas.",
    )
    require(
        all(
            isinstance(k, str) and k.strip() and type(v) is int and v >= 0
            for k, v in quotas.items()
        ),
        "Role quotas require names and nonnegative integers.",
    )
    require(
        sum(quotas.values()) <= strategy["target_count"],
        "Role quotas cannot exceed the batch target.",
    )
    collection = strategy.get("collection", {})
    require(isinstance(collection, dict), "Collection settings must be an object.")
    require(
        collection.get("mode") in {"parallel", "sequential"},
        "Choose the collection mode during setup.",
    )
    maximum = collection.get("max_parallel")
    require(type(maximum) is int and 1 <= maximum <= 16, "Choose a parallel limit from 1 to 16.")
    if collection["mode"] == "sequential":
        require(maximum == 1, "Sequential collection uses max_parallel=1.")
    else:
        require(maximum >= 2, "Parallel mode requires a concurrency limit of at least two.")
    sources = collection.get("sources")
    require(isinstance(sources, list) and sources, "Record the chosen source/query groups.")
    for source in sources:
        text(source, "Collection source")
    require(len(set(sources)) == len(sources), "Collection source IDs must be unique.")
    for name, low, high in (("retry_limit", 0, 5), ("timeout_seconds", 1, 3600)):
        value = collection.get(name)
        require(type(value) is int and low <= value <= high, f"Invalid collection {name}.")
    fallback = strategy.get("fallback", {})
    require(
        isinstance(fallback, dict) and type(fallback.get("enabled")) is bool,
        "Ask whether fallback is enabled.",
    )
    allowed = fallback.get("allowed_relaxations")
    require(isinstance(allowed, list), "List explicitly allowed fallback changes.")
    for rule in allowed:
        text(rule, "Fallback rule")
    if not fallback["enabled"]:
        require(not allowed, "Disabled fallback cannot have active relaxations.")
    else:
        require(bool(allowed), "Enabled fallback needs explicit allowed changes.")
    checks = batch.get("workflow_checks")
    require(isinstance(checks, dict), "Include workflow check results in the batch.")
    for stage in WORKFLOW_STAGES:
        item = checks.get(stage)
        require(isinstance(item, dict), f"Missing workflow check: {stage}")
        require(
            item.get("status") in {"pass", "warning", "failed", "not_run"},
            f"Invalid workflow check: {stage}",
        )
        text(item.get("detail"), f"Workflow detail: {stage}")
    execution = batch.get("collection_execution", {})
    require(isinstance(execution, dict), "Record actual collection execution.")
    require(
        execution.get("mode") in {"parallel", "sequential"}, "Record the actual collection mode."
    )
    in_flight = execution.get("max_in_flight")
    require(
        type(in_flight) is int and 1 <= in_flight <= maximum,
        "Actual concurrency exceeds the recorded limit.",
    )
    require(in_flight <= len(sources), "Actual concurrency exceeds the chosen source count.")
    require(
        (execution["mode"] == "parallel") == (in_flight > 1),
        "Actual mode and concurrency disagree.",
    )
    text(execution.get("detail"), "Collection execution detail")
    selected = [job for job in batch["jobs"] if job["decision"] == "selected"]
    ranks = []
    for job in selected:
        rank = job.get("rank")
        require(type(rank) is int and rank > 0, "Selected jobs require a positive frozen rank.")
        ranks.append(rank)
        reasons = job.get("ranking_reasons")
        require(
            isinstance(reasons, list) and reasons, "Explain each selected job's customized rank."
        )
        for reason in reasons:
            text(reason, "Ranking reason")
        text(job.get("role_family"), "Selected role family")
        tier = job.get("selection_tier")
        require(tier in {"primary", "fallback"}, "Mark selected jobs as primary or fallback.")
        used = job.get("fallback_rules_used", [])
        require(isinstance(used, list), "Fallback rules used must be a list.")
        if tier == "fallback":
            require(
                fallback["enabled"] and used, "Fallback jobs require explicit opt-in and rules."
            )
            require(
                all(rule in allowed for rule in used), "Job uses an unapproved fallback change."
            )
        else:
            require(not used, "Primary jobs cannot use fallback changes.")
    require(
        sorted(ranks) == list(range(1, len(selected) + 1)),
        "Selected ranks must be unique and consecutive.",
    )
    return strategy
