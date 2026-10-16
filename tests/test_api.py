import pytest
from fastapi.testclient import TestClient

from app.main import app

@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client

def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["version"] == "0.2.0"

def test_analysis_without_github(client):
    payload = {
        "service": "checkout-api",
        "deployment_id": "deploy-test",
        "error": "500 errors after deployment",
        "logs": [
            {"level": "error", "message": "connection pool exhausted"}
        ],
        "metrics": [
            {
                "name": "db_connection_pool_usage",
                "value": 100,
                "unit": "%"
            }
        ],
        "recent_changes": [
            {
                "commit": "abc123",
                "file": "db/session.py",
                "message": "DB lifecycle change"
            }
        ]
    }

    response = client.post("/api/v1/incidents/analyze", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["incident_id"].startswith("INC-")
    assert data["hypotheses"]
    assert "Database" in data["hypotheses"][0]["cause"]
    assert data["github_changes_collected"] == 0
