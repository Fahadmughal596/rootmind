import json
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query
from sqlalchemy import select

from app.config import settings
from app.database import SessionLocal, IncidentRecord, create_tables
from app.github_client import (
    GitHubCollectorError,
    fetch_recent_changes,
)
from app.investigator import analyze_incident
from app.schemas import (
    IncidentRequest,
    IncidentAnalysis,
    IncidentRecordOut,
    CodeChange,
)

@asynccontextmanager
async def lifespan(_: FastAPI):
    create_tables()
    yield

app = FastAPI(
    title=settings.app_name,
    version="0.2.0",
    description="AI post-deployment incident investigation API",
    lifespan=lifespan,
)

@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": settings.app_name,
        "environment": settings.app_env,
        "version": "0.2.0",
    }

@app.get(
    "/api/v1/github/changes",
    response_model=list[CodeChange],
    tags=["github"],
)
async def github_changes(
    repository: str = Query(..., description="OWNER/REPO"),
    limit: int = Query(3, ge=1, le=10),
    branch: str | None = Query(None),
):
    try:
        return await fetch_recent_changes(
            repository=repository,
            limit=limit,
            branch=branch,
        )
    except GitHubCollectorError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

@app.post(
    "/api/v1/incidents/analyze",
    response_model=IncidentAnalysis,
    tags=["incidents"],
)
async def analyze(payload: IncidentRequest):
    github_changes_collected = 0

    if payload.repository:
        try:
            github_changes = await fetch_recent_changes(
                repository=payload.repository,
                limit=payload.github_commit_limit,
                branch=payload.github_branch,
            )
        except GitHubCollectorError as exc:
            raise HTTPException(
                status_code=400,
                detail=f"GitHub evidence collection failed: {exc}",
            ) from exc

        # Merge GitHub evidence with any manually supplied code changes.
        payload.recent_changes.extend(github_changes)
        github_changes_collected = len(github_changes)

    try:
        result = analyze_incident(
            payload,
            github_changes_collected=github_changes_collected,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Investigation failed: {exc}",
        ) from exc

    with SessionLocal() as db:
        db.add(
            IncidentRecord(
                incident_id=result.incident_id,
                service=payload.service,
                deployment_id=payload.deployment_id,
                error=payload.error,
                status=result.status,
                result_json=result.model_dump_json(),
            )
        )
        db.commit()

    return result

@app.get(
    "/api/v1/incidents",
    response_model=list[IncidentRecordOut],
    tags=["incidents"],
)
def list_incidents(limit: int = 20):
    limit = min(max(limit, 1), 100)

    with SessionLocal() as db:
        rows = db.scalars(
            select(IncidentRecord)
            .order_by(IncidentRecord.created_at.desc())
            .limit(limit)
        ).all()

    return [
        IncidentRecordOut(
            incident_id=r.incident_id,
            service=r.service,
            deployment_id=r.deployment_id,
            error=r.error,
            status=r.status,
            created_at=r.created_at,
            result=json.loads(r.result_json),
        )
        for r in rows
    ]

@app.get(
    "/api/v1/incidents/{incident_id}",
    response_model=IncidentRecordOut,
    tags=["incidents"],
)
def get_incident(incident_id: str):
    with SessionLocal() as db:
        row = db.scalar(
            select(IncidentRecord).where(
                IncidentRecord.incident_id == incident_id
            )
        )

    if row is None:
        raise HTTPException(status_code=404, detail="Incident not found")

    return IncidentRecordOut(
        incident_id=row.incident_id,
        service=row.service,
        deployment_id=row.deployment_id,
        error=row.error,
        status=row.status,
        created_at=row.created_at,
        result=json.loads(row.result_json),
    )
