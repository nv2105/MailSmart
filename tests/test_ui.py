import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_dashboard_route():
    response = client.get("/dashboard")
    assert response.status_code == 200
    assert b"Dashboard" in response.content

def test_history_route():
    response = client.get("/history")
    assert response.status_code == 200
    assert b"History of Summaries" in response.content

@pytest.mark.skip(reason="Run-now requires Gmail API and real execution")
def test_run_now_route():
    response = client.post("/run-now")
    assert response.status_code == 200
    json_data = response.json()
    assert "message" in json_data
