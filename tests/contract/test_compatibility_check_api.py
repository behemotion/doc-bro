"""Contract tests for GET /api/projects/{id}/compatibility."""

import pytest
from fastapi.testclient import TestClient


@pytest.mark.contract
def test_compatibility_check_api_contract():
    """Test GET /api/projects/{id}/compatibility contract."""
    from src.api.main import app

    client = TestClient(app)

    # Create a project first
    project_data = {"name": "test-compatibility-check", "type": "data"}
    create_response = client.post("/api/projects", json=project_data)
    assert create_response.status_code == 201
    project_id = create_response.json()["id"]

    # Check compatibility
    response = client.get(f"/api/projects/{project_id}/compatibility")
    assert response.status_code == 200

    data = response.json()
    required_fields = [
        "is_compatible", "current_version", "project_version", "status",
        "missing_fields", "extra_fields", "issues", "can_be_migrated",
        "migration_required", "needs_recreation"
    ]
    for field in required_fields:
        assert field in data

    assert isinstance(data["is_compatible"], bool)
    assert isinstance(data["current_version"], int)
    assert isinstance(data["project_version"], int)
    assert data["status"] in ["compatible", "incompatible", "migrating"]


@pytest.mark.contract
def test_compatibility_check_not_found():
    """Test compatibility check for non-existent project."""
    from src.api.main import app

    client = TestClient(app)
    fake_id = "00000000-0000-0000-0000-000000000000"
    
    response = client.get(f"/api/projects/{fake_id}/compatibility")
    assert response.status_code == 404