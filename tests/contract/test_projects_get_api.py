"""Contract tests for GET /api/projects/{id} with compatibility status."""

import pytest
from fastapi.testclient import TestClient


@pytest.mark.contract
def test_projects_get_api_contract():
    """Test GET /api/projects/{id} contract with compatibility status."""
    from src.api.main import app

    client = TestClient(app)

    # First create a project
    project_data = {
        "name": "test-get-project",
        "type": "data",
        "settings": {"chunk_size": 1000},
        "metadata": {"description": "Test project for GET API"}
    }

    create_response = client.post("/api/projects", json=project_data)
    assert create_response.status_code == 201
    project_id = create_response.json()["id"]

    # Test getting the project
    response = client.get(f"/api/projects/{project_id}")
    assert response.status_code == 200

    data = response.json()
    assert data["id"] == project_id
    assert data["name"] == project_data["name"]
    assert data["type"] == project_data["type"]
    assert "compatibility_status" in data
    assert data["compatibility_status"] in ["compatible", "incompatible", "migrating"]


@pytest.mark.contract
def test_projects_get_not_found_contract():
    """Test GET /api/projects/{id} for non-existent project."""
    from src.api.main import app

    client = TestClient(app)

    # Test with non-existent project ID
    fake_id = "00000000-0000-0000-0000-000000000000"
    response = client.get(f"/api/projects/{fake_id}")
    assert response.status_code == 404

    error_data = response.json()
    assert "error" in error_data
    assert "message" in error_data
    assert "not found" in error_data["message"].lower()


@pytest.mark.contract
def test_projects_get_response_schema():
    """Test that project GET response has correct unified schema."""
    from src.api.main import app

    client = TestClient(app)

    # Create a project first
    project_data = {
        "name": "test-schema-get-project",
        "type": "crawling",
        "source_url": "https://example.com",
        "settings": {
            "crawl_depth": 3,
            "rate_limit": 1.0,
            "embedding_model": "mxbai-embed-large"
        },
        "metadata": {
            "description": "Test project for schema validation",
            "tags": ["test", "api"]
        }
    }

    create_response = client.post("/api/projects", json=project_data)
    assert create_response.status_code == 201
    project_id = create_response.json()["id"]

    # Get the project and validate schema
    response = client.get(f"/api/projects/{project_id}")
    assert response.status_code == 200

    data = response.json()

    # Required fields from UnifiedProject schema
    required_fields = [
        "id", "name", "schema_version", "type", "status",
        "compatibility_status", "created_at", "updated_at"
    ]
    for field in required_fields:
        assert field in data, f"Missing required field: {field}"

    # Field types and values
    assert isinstance(data["id"], str)
    assert isinstance(data["name"], str)
    assert isinstance(data["schema_version"], int)
    assert data["schema_version"] == 3
    assert data["type"] in ["crawling", "data", "storage"]
    assert data["status"] in ["active", "inactive", "error", "processing"]
    assert data["compatibility_status"] in ["compatible", "incompatible", "migrating"]

    # Optional fields should be present
    assert "last_crawl_at" in data
    assert "source_url" in data
    assert "settings" in data
    assert "statistics" in data
    assert "metadata" in data

    # Check field values
    assert data["source_url"] == project_data["source_url"]
    assert isinstance(data["settings"], dict)
    assert isinstance(data["statistics"], dict)
    assert isinstance(data["metadata"], dict)

    # Validate settings content
    assert data["settings"]["crawl_depth"] == project_data["settings"]["crawl_depth"]
    assert data["settings"]["rate_limit"] == project_data["settings"]["rate_limit"]

    # Validate metadata content
    assert data["metadata"]["description"] == project_data["metadata"]["description"]


@pytest.mark.contract
def test_projects_get_compatible_status():
    """Test that newly created projects have compatible status."""
    from src.api.main import app

    client = TestClient(app)

    # Create a new project (should be compatible by default)
    project_data = {
        "name": "test-compatible-project",
        "type": "data"
    }

    create_response = client.post("/api/projects", json=project_data)
    assert create_response.status_code == 201
    project_id = create_response.json()["id"]

    # Get the project and check compatibility
    response = client.get(f"/api/projects/{project_id}")
    assert response.status_code == 200

    data = response.json()
    assert data["compatibility_status"] == "compatible"
    assert data["schema_version"] == 3


@pytest.mark.contract
def test_projects_get_all_project_types():
    """Test GET API for all project types."""
    from src.api.main import app

    client = TestClient(app)

    # Test crawling project
    crawling_data = {
        "name": "test-crawling-get",
        "type": "crawling",
        "source_url": "https://docs.example.com"
    }
    create_response = client.post("/api/projects", json=crawling_data)
    assert create_response.status_code == 201
    crawling_id = create_response.json()["id"]

    response = client.get(f"/api/projects/{crawling_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["type"] == "crawling"
    assert data["source_url"] == crawling_data["source_url"]

    # Test data project
    data_project_data = {
        "name": "test-data-get",
        "type": "data"
    }
    create_response = client.post("/api/projects", json=data_project_data)
    assert create_response.status_code == 201
    data_id = create_response.json()["id"]

    response = client.get(f"/api/projects/{data_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["type"] == "data"
    assert data["source_url"] is None

    # Test storage project
    storage_data = {
        "name": "test-storage-get",
        "type": "storage"
    }
    create_response = client.post("/api/projects", json=storage_data)
    assert create_response.status_code == 201
    storage_id = create_response.json()["id"]

    response = client.get(f"/api/projects/{storage_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["type"] == "storage"