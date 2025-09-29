"""Contract tests for GET /api/projects with compatibility filtering."""

import pytest
from fastapi.testclient import TestClient


@pytest.mark.contract
def test_projects_list_api_contract():
    """Test GET /api/projects contract with compatibility filtering."""
    from src.api.main import app

    client = TestClient(app)

    # Test basic project listing
    response = client.get("/api/projects")
    assert response.status_code == 200

    data = response.json()
    assert "projects" in data
    assert "total" in data
    assert "compatible_count" in data
    assert "incompatible_count" in data
    assert isinstance(data["projects"], list)
    assert isinstance(data["total"], int)
    assert isinstance(data["compatible_count"], int)
    assert isinstance(data["incompatible_count"], int)


@pytest.mark.contract
def test_projects_list_compatibility_filter_contract():
    """Test GET /api/projects with compatibility status filtering."""
    from src.api.main import app

    client = TestClient(app)

    # Test compatibility filter
    response = client.get("/api/projects?compatibility=compatible")
    assert response.status_code == 200

    data = response.json()
    assert "projects" in data
    for project in data["projects"]:
        assert project["compatibility_status"] == "compatible"


@pytest.mark.contract
def test_projects_list_status_filter_contract():
    """Test GET /api/projects with status filtering."""
    from src.api.main import app

    client = TestClient(app)

    # Test status filter
    response = client.get("/api/projects?status=active")
    assert response.status_code == 200

    data = response.json()
    assert "projects" in data
    for project in data["projects"]:
        assert project["status"] == "active"


@pytest.mark.contract
def test_projects_list_type_filter_contract():
    """Test GET /api/projects with type filtering."""
    from src.api.main import app

    client = TestClient(app)

    # Test type filter
    response = client.get("/api/projects?type=crawling")
    assert response.status_code == 200

    data = response.json()
    assert "projects" in data
    for project in data["projects"]:
        assert project["type"] == "crawling"


@pytest.mark.contract
def test_projects_list_limit_contract():
    """Test GET /api/projects with limit parameter."""
    from src.api.main import app

    client = TestClient(app)

    # Test limit parameter
    response = client.get("/api/projects?limit=5")
    assert response.status_code == 200

    data = response.json()
    assert "projects" in data
    assert len(data["projects"]) <= 5


@pytest.mark.contract
def test_projects_list_project_summary_schema():
    """Test that project summaries have the correct schema."""
    from src.api.main import app

    client = TestClient(app)

    response = client.get("/api/projects")
    assert response.status_code == 200

    data = response.json()
    if data["projects"]:
        project = data["projects"][0]

        # Required fields
        assert "id" in project
        assert "name" in project
        assert "type" in project
        assert "status" in project
        assert "compatibility_status" in project
        assert "created_at" in project
        assert "updated_at" in project

        # Validate field types
        assert isinstance(project["id"], str)
        assert isinstance(project["name"], str)
        assert project["type"] in ["crawling", "data", "storage"]
        assert project["status"] in ["active", "inactive", "error", "processing"]
        assert project["compatibility_status"] in ["compatible", "incompatible", "migrating"]

        # Optional fields
        if "page_count" in project:
            assert isinstance(project["page_count"], (int, type(None)))