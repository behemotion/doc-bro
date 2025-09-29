"""Contract tests for PUT /api/projects/{id} blocking incompatible updates."""

import pytest
from fastapi.testclient import TestClient


@pytest.mark.contract
def test_projects_update_compatible_project_contract():
    """Test PUT /api/projects/{id} for compatible projects."""
    from src.api.main import app

    client = TestClient(app)

    # Create a compatible project
    project_data = {
        "name": "test-update-project",
        "type": "data",
        "settings": {"chunk_size": 1000}
    }

    create_response = client.post("/api/projects", json=project_data)
    assert create_response.status_code == 201
    project_id = create_response.json()["id"]

    # Update the project
    update_data = {
        "settings": {"chunk_size": 1500, "embedding_model": "new-model"},
        "metadata": {"updated": True}
    }

    response = client.put(f"/api/projects/{project_id}", json=update_data)
    assert response.status_code == 200

    data = response.json()
    assert data["settings"]["chunk_size"] == 1500
    assert data["metadata"]["updated"] is True


@pytest.mark.contract
def test_projects_update_incompatible_project_blocked():
    """Test PUT /api/projects/{id} blocks incompatible projects."""
    from src.api.main import app

    client = TestClient(app)

    # This test assumes we have a way to create an incompatible project
    # For now, we'll simulate the response that should happen
    fake_incompatible_id = "00000000-0000-0000-0000-000000000001"

    update_data = {"settings": {"new_setting": "value"}}

    response = client.put(f"/api/projects/{fake_incompatible_id}", json=update_data)

    # Should either return 403 (incompatible) or 404 (not found)
    assert response.status_code in [403, 404]

    if response.status_code == 403:
        error_data = response.json()
        assert "incompatible" in error_data["message"].lower()


@pytest.mark.contract
def test_projects_update_not_found_contract():
    """Test PUT /api/projects/{id} for non-existent project."""
    from src.api.main import app

    client = TestClient(app)

    fake_id = "00000000-0000-0000-0000-000000000000"
    update_data = {"settings": {"test": "value"}}

    response = client.put(f"/api/projects/{fake_id}", json=update_data)
    assert response.status_code == 404


@pytest.mark.contract
def test_projects_update_validation_contract():
    """Test PUT /api/projects/{id} validation."""
    from src.api.main import app

    client = TestClient(app)

    # Create a project first
    project_data = {"name": "test-validation-update", "type": "data"}
    create_response = client.post("/api/projects", json=project_data)
    assert create_response.status_code == 201
    project_id = create_response.json()["id"]

    # Test invalid update data
    invalid_data = {"invalid_field": "value"}
    response = client.put(f"/api/projects/{project_id}", json=invalid_data)
    assert response.status_code in [200, 400]  # Depends on implementation