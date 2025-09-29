"""Contract tests for POST /api/projects with unified schema."""

import pytest
from fastapi.testclient import TestClient


@pytest.mark.contract
def test_projects_create_api_contract():
    """Test POST /api/projects contract with unified schema."""
    from src.api.main import app

    client = TestClient(app)

    # Test basic project creation
    project_data = {
        "name": "test-unified-project",
        "type": "crawling",
        "source_url": "https://example.com",
        "settings": {
            "crawl_depth": 3,
            "rate_limit": 1.0
        },
        "metadata": {
            "description": "Test project for unified schema"
        }
    }

    response = client.post("/api/projects", json=project_data)
    assert response.status_code == 201

    data = response.json()
    assert "id" in data
    assert data["name"] == project_data["name"]
    assert data["type"] == project_data["type"]
    assert data["schema_version"] == 3
    assert data["compatibility_status"] == "compatible"
    assert data["status"] in ["active", "inactive", "error", "processing"]
    assert "created_at" in data
    assert "updated_at" in data


@pytest.mark.contract
def test_projects_create_crawling_type_contract():
    """Test POST /api/projects for crawling type with required fields."""
    from src.api.main import app

    client = TestClient(app)

    project_data = {
        "name": "test-crawling-project",
        "type": "crawling",
        "source_url": "https://docs.example.com",
        "settings": {
            "crawl_depth": 2,
            "rate_limit": 1.5,
            "embedding_model": "mxbai-embed-large"
        }
    }

    response = client.post("/api/projects", json=project_data)
    assert response.status_code == 201

    data = response.json()
    assert data["type"] == "crawling"
    assert data["source_url"] == project_data["source_url"]
    assert "settings" in data
    assert "statistics" in data
    assert "metadata" in data


@pytest.mark.contract
def test_projects_create_data_type_contract():
    """Test POST /api/projects for data type."""
    from src.api.main import app

    client = TestClient(app)

    project_data = {
        "name": "test-data-project",
        "type": "data",
        "settings": {
            "chunk_size": 1000,
            "embedding_model": "mxbai-embed-large"
        },
        "metadata": {
            "description": "Data project for testing"
        }
    }

    response = client.post("/api/projects", json=project_data)
    assert response.status_code == 201

    data = response.json()
    assert data["type"] == "data"
    assert data["source_url"] is None  # Optional for data projects


@pytest.mark.contract
def test_projects_create_storage_type_contract():
    """Test POST /api/projects for storage type."""
    from src.api.main import app

    client = TestClient(app)

    project_data = {
        "name": "test-storage-project",
        "type": "storage",
        "settings": {
            "enable_compression": True
        }
    }

    response = client.post("/api/projects", json=project_data)
    assert response.status_code == 201

    data = response.json()
    assert data["type"] == "storage"


@pytest.mark.contract
def test_projects_create_validation_contract():
    """Test POST /api/projects validation errors."""
    from src.api.main import app

    client = TestClient(app)

    # Test missing required fields
    response = client.post("/api/projects", json={})
    assert response.status_code == 400

    # Test invalid type
    project_data = {
        "name": "test-invalid-type",
        "type": "invalid_type"
    }
    response = client.post("/api/projects", json=project_data)
    assert response.status_code == 400

    # Test invalid name length
    project_data = {
        "name": "",  # Too short
        "type": "data"
    }
    response = client.post("/api/projects", json=project_data)
    assert response.status_code == 400

    # Test name too long
    project_data = {
        "name": "x" * 101,  # Too long (max 100)
        "type": "data"
    }
    response = client.post("/api/projects", json=project_data)
    assert response.status_code == 400


@pytest.mark.contract
def test_projects_create_duplicate_name_contract():
    """Test POST /api/projects with duplicate name."""
    from src.api.main import app

    client = TestClient(app)

    project_data = {
        "name": "duplicate-test-project",
        "type": "data"
    }

    # Create first project
    response = client.post("/api/projects", json=project_data)
    assert response.status_code == 201

    # Try to create second project with same name
    response = client.post("/api/projects", json=project_data)
    assert response.status_code == 409
    assert "already exists" in response.json()["message"]


@pytest.mark.contract
def test_projects_create_response_schema():
    """Test that project creation response has correct unified schema."""
    from src.api.main import app

    client = TestClient(app)

    project_data = {
        "name": "schema-test-project",
        "type": "crawling",
        "source_url": "https://example.com"
    }

    response = client.post("/api/projects", json=project_data)
    assert response.status_code == 201

    data = response.json()

    # Required fields
    required_fields = [
        "id", "name", "schema_version", "type", "status",
        "compatibility_status", "created_at", "updated_at"
    ]
    for field in required_fields:
        assert field in data

    # Field types and values
    assert isinstance(data["id"], str)
    assert isinstance(data["name"], str)
    assert isinstance(data["schema_version"], int)
    assert data["schema_version"] == 3
    assert data["type"] in ["crawling", "data", "storage"]
    assert data["status"] in ["active", "inactive", "error", "processing"]
    assert data["compatibility_status"] in ["compatible", "incompatible", "migrating"]

    # Optional fields
    assert "last_crawl_at" in data
    assert "source_url" in data
    assert "settings" in data
    assert "statistics" in data
    assert "metadata" in data

    # JSON fields should be objects
    assert isinstance(data["settings"], dict)
    assert isinstance(data["statistics"], dict)
    assert isinstance(data["metadata"], dict)