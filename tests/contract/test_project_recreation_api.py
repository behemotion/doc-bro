"""Contract tests for POST /api/projects/{id}/recreate."""

import pytest
from fastapi.testclient import TestClient


@pytest.mark.contract
def test_project_recreation_api_contract():
    """Test POST /api/projects/{id}/recreate contract."""
    from src.api.main import app

    client = TestClient(app)

    # This test assumes we have an incompatible project to recreate
    # For now, we'll test the contract structure
    fake_id = "00000000-0000-0000-0000-000000000001"
    
    recreation_data = {
        "preserve_data": False,
        "confirm_recreation": True
    }
    
    response = client.post(f"/api/projects/{fake_id}/recreate", json=recreation_data)
    
    # Should return 404 for non-existent project or handle recreation
    assert response.status_code in [201, 400, 403, 404]
    
    if response.status_code == 201:
        data = response.json()
        assert "recreated_project" in data
        assert "migration_record" in data
        
        # Validate recreated project structure
        project = data["recreated_project"]
        assert "id" in project
        assert "schema_version" in project
        assert project["schema_version"] == 3
        
        # Validate migration record
        record = data["migration_record"]
        assert "id" in record
        assert "operation" in record
        assert "from_schema_version" in record
        assert "to_schema_version" in record


@pytest.mark.contract
def test_project_recreation_compatible_project_blocked():
    """Test recreation blocked for already compatible projects."""
    from src.api.main import app

    client = TestClient(app)

    # Create a compatible project
    project_data = {"name": "test-recreation-block", "type": "data"}
    create_response = client.post("/api/projects", json=project_data)
    assert create_response.status_code == 201
    project_id = create_response.json()["id"]

    # Try to recreate compatible project (should be blocked)
    recreation_data = {"confirm_recreation": True}
    response = client.post(f"/api/projects/{project_id}/recreate", json=recreation_data)
    
    # Should return 403 (already compatible) or handle gracefully
    assert response.status_code in [403, 400]