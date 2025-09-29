"""Contract tests for GET /api/projects/{id}/export."""

import pytest
from fastapi.testclient import TestClient


@pytest.mark.contract
def test_project_export_api_contract():
    """Test GET /api/projects/{id}/export contract."""
    from src.api.main import app

    client = TestClient(app)

    # Create a project to export
    project_data = {
        "name": "test-export-project",
        "type": "crawling",
        "source_url": "https://example.com",
        "settings": {"crawl_depth": 3},
        "metadata": {"description": "Test export project"}
    }
    
    create_response = client.post("/api/projects", json=project_data)
    assert create_response.status_code == 201
    project_id = create_response.json()["id"]

    # Export the project
    response = client.get(f"/api/projects/{project_id}/export")
    assert response.status_code == 200

    data = response.json()
    
    # Required fields
    required_fields = [
        "project_name", "project_type", "schema_version", "exported_at"
    ]
    for field in required_fields:
        assert field in data

    # Validate field values
    assert data["project_name"] == project_data["name"]
    assert data["project_type"] == project_data["type"]
    assert isinstance(data["schema_version"], int)
    assert "settings" in data
    assert "metadata" in data
    
    # Optional fields based on project type
    if data["project_type"] == "crawling":
        assert "source_url" in data
        assert data["source_url"] == project_data["source_url"]


@pytest.mark.contract
def test_project_export_not_found():
    """Test export for non-existent project."""
    from src.api.main import app

    client = TestClient(app)
    fake_id = "00000000-0000-0000-0000-000000000000"
    
    response = client.get(f"/api/projects/{fake_id}/export")
    assert response.status_code == 404


@pytest.mark.contract
def test_project_export_all_types():
    """Test export for all project types."""
    from src.api.main import app

    client = TestClient(app)

    project_types = [
        {"name": "export-crawling", "type": "crawling", "source_url": "https://example.com"},
        {"name": "export-data", "type": "data"},
        {"name": "export-storage", "type": "storage"}
    ]

    for project_data in project_types:
        create_response = client.post("/api/projects", json=project_data)
        assert create_response.status_code == 201
        project_id = create_response.json()["id"]

        export_response = client.get(f"/api/projects/{project_id}/export")
        assert export_response.status_code == 200
        
        export_data = export_response.json()
        assert export_data["project_type"] == project_data["type"]