import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_home_page_ui():
    response = client.get("/")
    assert response.status_code == 200
    assert b"MailSmart" in response.content

def test_dashboard_ui_elements():
    response = client.get("/dashboard")
    assert b"Run Now" in response.content
    assert b"Total Emails" in response.content
    assert b"Important" in response.content

def test_history_ui_elements():
    response = client.get("/history")
    assert b"History of Summaries" in response.content
