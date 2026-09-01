"""Tests for FastAPI Web Server endpoints."""

import pytest
from starlette.testclient import TestClient
from fb_downloader.web_server import app

client = TestClient(app)


def test_api_health():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "python_version" in data


def test_serve_index():
    response = client.get("/")
    assert response.status_code == 200
    assert "Facebook Post Image Downloader" in response.text
    assert "FB Downloader" in response.text


def test_api_scrape_invalid_url():
    response = client.post("/api/scrape", json={"url": "https://invalid-non-fb.com/test", "headless": True})
    assert response.status_code == 400
    assert "Invalid Facebook URL" in response.json()["detail"]


def test_api_download_zip():
    items = [
        {"url": "https://httpbin.org/image/jpeg", "suggested_filename": "photo_001", "index": 1}
    ]
    response = client.post("/api/download-zip", json={"post_id": "test_zip_post", "items": items})
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/zip"
    assert "attachment; filename=" in response.headers["content-disposition"]


def test_api_open_folder_not_found():
    response = client.post("/api/open-folder", json={"path": "/non/existent/path/12345"})
    assert response.status_code == 404


def test_serve_tutorial():
    response = client.get("/tutorial")
    assert response.status_code == 200
    assert "How to Get the" in response.text
    assert "Interactive URL Inspector" in response.text


def test_api_download_single_missing_url():
    response = client.get("/api/download-single?url=")
    assert response.status_code == 400
