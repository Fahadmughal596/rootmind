from uuid import uuid4

from app.schemas import IncidentRequest, IncidentAnalysis, Hypothesis

def _all_evidence(incident: IncidentRequest) -> list[str]:
    evidence = [f"incident: {incident.error}"]

    evidence += [f"log: {x.message}" for x in incident.logs]

    evidence += [
        f"metric: {x.name}={x.value}{(' ' + x.unit) if x.unit else ''}"
        + (f" baseline={x.baseline}" if x.baseline is not None else "")
        + (f" note={x.note}" if x.note else "")
        for x in incident.metrics
    ]

    evidence += [
        "code: " + " | ".join(v for v in [x.commit, x.file, x.message] if v)
        for x in incident.recent_changes
    ]

    evidence += [
        f"history: {x.incident_id} | {x.summary} | root_cause={x.root_cause}"
        for x in incident.historical_incidents
    ]

    return evidence

def analyze_incident(
    incident: IncidentRequest,
    github_changes_collected: int = 0,
) -> IncidentAnalysis:
    evidence = _all_evidence(incident)
    joined = " ".join(evidence).lower()
    hypotheses: list[Hypothesis] = []

    def add(cause, confidence, keywords, checks):
        supporting = [
            e for e in evidence
            if any(k in e.lower() for k in keywords)
        ][:7]

        hypotheses.append(
            Hypothesis(
                rank=1,
                cause=cause,
                confidence=confidence,
                supporting_evidence=supporting,
                recommended_checks=checks,
            )
        )

    if any(k in joined for k in [
        "connection pool",
        "pool exhausted",
        "database connection",
        "too many connections",
        "db/session",
        "database session",
    ]):
        add(
            "Database connection pool exhaustion or connection leak",
            0.88,
            ["connection", "pool", "database", "db/session"],
            [
                "Compare active/idle DB connections before and after deployment.",
                "Inspect recent DB session lifecycle changes.",
                "Verify connections are released on success and exception paths.",
            ],
        )

    if any(k in joined for k in ["memory leak", "out of memory", "oom", "heap"]):
        add(
            "Application memory regression",
            0.80,
            ["memory", "oom", "heap"],
            [
                "Compare memory usage before and after deployment.",
                "Inspect new caches or long-lived objects.",
                "Check container/process OOM events.",
            ],
        )

    if any(k in joined for k in ["401", "403", "unauthorized", "forbidden", "auth"]):
        add(
            "Authentication or authorization regression",
            0.76,
            ["401", "403", "unauthorized", "forbidden", "auth"],
            [
                "Compare auth configuration between releases.",
                "Inspect recent token/session middleware changes.",
                "Verify deployment secrets and environment variables.",
            ],
        )

    if any(k in joined for k in ["latency", "timeout", "slow", "p95", "p99"]):
        add(
            "Request-path or downstream dependency regression",
            0.69,
            ["latency", "timeout", "slow", "p95", "p99"],
            [
                "Compare endpoint latency before and after deployment.",
                "Find the slowest downstream dependency.",
                "Inspect saturation and timeout metrics.",
            ],
        )

    if not hypotheses:
        add(
            "Unknown post-deployment regression",
            0.42,
            ["incident"],
            [
                "Collect stack traces and error distribution.",
                "Compare recent commits with the failing code path.",
                "Collect CPU, memory, latency and dependency metrics.",
            ],
        )

    hypotheses.sort(key=lambda h: h.confidence, reverse=True)
    hypotheses = hypotheses[:3]

    for i, h in enumerate(hypotheses, start=1):
        h.rank = i

    top = hypotheses[0]
    status = (
        "completed"
        if top.confidence >= 0.5 and len(evidence) >= 2
        else "needs_more_evidence"
    )

    return IncidentAnalysis(
        incident_id=f"INC-{uuid4().hex[:10].upper()}",
        status=status,
        summary=f"{incident.service}: {incident.error}",
        hypotheses=hypotheses,
        recommended_action=(
            f"Verify the top hypothesis: {top.cause}. "
            "Run diagnostic checks before any production change and keep a "
            "human engineer in the approval loop."
        ),
        needs_human_review=True,
        evidence_count=len(evidence),
        github_changes_collected=github_changes_collected,
    )
