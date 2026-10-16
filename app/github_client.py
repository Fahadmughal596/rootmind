from typing import Any
import httpx

from app.config import settings
from app.schemas import CodeChange

GITHUB_API = "https://api.github.com"

class GitHubCollectorError(RuntimeError):
    pass

def _headers() -> dict[str, str]:
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "RootMind-Incident-Investigator",
    }
    if settings.github_token:
        headers["Authorization"] = f"Bearer {settings.github_token}"
    return headers

def _validate_repository(repository: str) -> tuple[str, str]:
    parts = repository.strip().strip("/").split("/")
    if len(parts) != 2 or not all(parts):
        raise GitHubCollectorError(
            "Repository must use the format OWNER/REPO, for example: octocat/Hello-World"
        )
    return parts[0], parts[1]

async def fetch_recent_changes(
    repository: str,
    limit: int = 3,
    branch: str | None = None,
) -> list[CodeChange]:
    owner, repo = _validate_repository(repository)
    limit = min(max(limit, 1), 10)

    params: dict[str, Any] = {"per_page": limit}
    if branch:
        params["sha"] = branch

    async with httpx.AsyncClient(timeout=20.0, headers=_headers()) as client:
        commits_resp = await client.get(
            f"{GITHUB_API}/repos/{owner}/{repo}/commits",
            params=params,
        )

        if commits_resp.status_code == 404:
            raise GitHubCollectorError(
                "Repository not found or GitHub token does not have access."
            )
        if commits_resp.status_code == 403:
            raise GitHubCollectorError(
                "GitHub API access denied or rate limit exceeded. Add GITHUB_TOKEN to .env."
            )
        try:
            commits_resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise GitHubCollectorError(
                f"GitHub commits request failed with status {commits_resp.status_code}."
            ) from exc

        commits = commits_resp.json()

        changes: list[CodeChange] = []

        for commit_item in commits[:limit]:
            sha = commit_item.get("sha")
            message = (
                commit_item.get("commit", {})
                .get("message", "")
                .splitlines()[0]
            )

            if not sha:
                continue

            detail_resp = await client.get(
                f"{GITHUB_API}/repos/{owner}/{repo}/commits/{sha}"
            )
            try:
                detail_resp.raise_for_status()
            except httpx.HTTPStatusError:
                # Keep useful commit evidence even if detail lookup fails.
                changes.append(
                    CodeChange(
                        commit=sha[:12],
                        file=None,
                        message=message or "GitHub commit",
                    )
                )
                continue

            detail = detail_resp.json()
            files = detail.get("files", [])

            if not files:
                changes.append(
                    CodeChange(
                        commit=sha[:12],
                        file=None,
                        message=message or "GitHub commit",
                    )
                )
                continue

            # Add one evidence item per changed file.
            for changed_file in files[:20]:
                filename = changed_file.get("filename")
                status = changed_file.get("status")
                additions = changed_file.get("additions", 0)
                deletions = changed_file.get("deletions", 0)

                enriched_message = (
                    f"{message} | status={status} | +{additions}/-{deletions}"
                )

                changes.append(
                    CodeChange(
                        commit=sha[:12],
                        file=filename,
                        message=enriched_message,
                    )
                )

        return changes
