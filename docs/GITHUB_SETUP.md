# GitHub Setup

## Public repositories

No token is required for basic testing.

Use:

`GET /api/v1/github/changes?repository=OWNER/REPO&limit=3`

## Private repositories

Create a GitHub personal access token with the minimum repository read permissions
needed for the repository you want RootMind to inspect.

Put it in `.env`:

```text
GITHUB_TOKEN=your_token_here
```

Never commit `.env`.

## Analyze with automatic GitHub evidence

Example:

```json
{
  "service": "rootmind-api",
  "repository": "OWNER/REPO",
  "github_commit_limit": 3,
  "error": "500 errors started after deployment",
  "severity": "critical",
  "logs": [
    {
      "level": "error",
      "message": "database connection pool exhausted"
    }
  ],
  "metrics": [],
  "recent_changes": [],
  "historical_incidents": [],
  "metadata": {
    "environment": "production"
  }
}
```
