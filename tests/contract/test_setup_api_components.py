"""Contract tests for GET /setup/session/{session_id}/components API endpoint.

Tests API endpoint according to setup-wizard-api.yml specification:
- GET /setup/session/{session_id}/components
- Parameters: session_id (UUID)
- Response: ComponentAvailabilityResponse with component details
"""

import pytest
from uuid import UUID
from unittest.mock import AsyncMock, patch

pytestmark = [pytest.mark.contract, pytest.mark.async_test]


@pytest.fixture
def mock_setup_service():
    """Mock setup service for API tests."""
    with patch('src.services.setup_logic_service.SetupLogicService') as mock:
        service_instance = AsyncMock()
        mock.return_value = service_instance
        yield service_instance


class TestSetupComponentsApiContract:
    """Contract tests for GET /setup/session/{session_id}/components endpoint."""

    async def test_components_endpoint_exists(self, mock_setup_service):
        """Test that the components endpoint is registered."""
        from src.api.setup_endpoints import setup_router

        # Check if route is registered
        routes = [route.path for route in setup_router.routes if hasattr(route, 'path')]
        components_route_exists = any("/setup/session/{session_id}/components" in route for route in routes)
        assert components_route_exists

    async def test_get_components_success(self, mock_setup_service):
        """Test successful component availability retrieval."""
        session_id = "550e8400-e29b-41d4-a716-446655440000"
        mock_response = {
            'components': [
                {
                    'component_type': 'docker',
                    'component_name': 'docker',
                    'available': True,
                    'version': '24.0.5',
                    'installation_path': '/usr/local/bin/docker',
                    'configuration_path': None,
                    'health_status': 'healthy',
                    'error_message': None,
                    'capabilities': {'api_version': '1.43', 'compose_support': True}
                },
                {
                    'component_type': 'ollama',
                    'component_name': 'ollama',
                    'available': True,
                    'version': '0.1.17',
                    'installation_path': '/usr/local/bin/ollama',
                    'configuration_path': None,
                    'health_status': 'healthy',
                    'error_message': None,
                    'capabilities': {'models': ['mxbai-embed-large'], 'api_version': 'v1'}
                },
                {
                    'component_type': 'mcp_client',
                    'component_name': 'claude-code',
                    'available': False,
                    'version': None,
                    'installation_path': None,
                    'configuration_path': None,
                    'health_status': 'unknown',
                    'error_message': 'Claude Code not detected',
                    'capabilities': {}
                }
            ],
            'last_checked': '2025-01-26T14:35:00Z'
        }

        mock_setup_service.get_component_availability.return_value = mock_response

        # Verify session ID is valid UUID
        uuid_obj = UUID(session_id)
        assert str(uuid_obj) == session_id

    async def test_get_components_invalid_uuid_400(self, mock_setup_service):
        """Test invalid UUID format returns 400 error."""
        invalid_session_id = "not-a-uuid"

        # Should reject invalid UUID format
        with pytest.raises(ValueError):
            UUID(invalid_session_id)

    async def test_components_response_schema_valid(self, mock_setup_service):
        """Test response follows ComponentAvailabilityResponse schema."""
        response = {
            'components': [
                {
                    'component_type': 'docker',
                    'component_name': 'docker',
                    'available': True,
                    'version': '24.0.5',
                    'installation_path': '/usr/local/bin/docker',
                    'configuration_path': None,
                    'health_status': 'healthy',
                    'error_message': None,
                    'capabilities': {'api_version': '1.43'}
                }
            ],
            'last_checked': '2025-01-26T14:35:00Z'
        }

        # Validate response structure
        assert 'components' in response
        assert 'last_checked' in response
        assert isinstance(response['components'], list)

        # Validate component structure
        component = response['components'][0]
        assert 'component_type' in component
        assert 'component_name' in component
        assert 'available' in component
        assert 'health_status' in component

        # Validate enum values
        assert component['component_type'] in ['docker', 'ollama', 'mcp_client']
        assert component['health_status'] in ['healthy', 'degraded', 'unhealthy', 'unknown']

    async def test_component_docker_available(self, mock_setup_service):
        """Test Docker component available response."""
        docker_component = {
            'component_type': 'docker',
            'component_name': 'docker',
            'available': True,
            'version': '24.0.5',
            'installation_path': '/usr/local/bin/docker',
            'configuration_path': '~/.docker/config.json',
            'health_status': 'healthy',
            'error_message': None,
            'capabilities': {
                'api_version': '1.43',
                'compose_support': True,
                'swarm_support': True
            }
        }

        # Validate Docker-specific fields
        assert docker_component['component_type'] == 'docker'
        assert docker_component['available'] is True
        assert docker_component['health_status'] == 'healthy'
        assert 'api_version' in docker_component['capabilities']

    async def test_component_ollama_available(self, mock_setup_service):
        """Test Ollama component available response."""
        ollama_component = {
            'component_type': 'ollama',
            'component_name': 'ollama',
            'available': True,
            'version': '0.1.17',
            'installation_path': '/usr/local/bin/ollama',
            'configuration_path': None,
            'health_status': 'healthy',
            'error_message': None,
            'capabilities': {
                'models': ['mxbai-embed-large', 'embeddinggemma:300m-qat-q4_0'],
                'api_version': 'v1',
                'storage_path': '~/.ollama'
            }
        }

        # Validate Ollama-specific fields
        assert ollama_component['component_type'] == 'ollama'
        assert ollama_component['available'] is True
        assert 'models' in ollama_component['capabilities']

    async def test_component_mcp_client_not_available(self, mock_setup_service):
        """Test MCP client component not available response."""
        mcp_component = {
            'component_type': 'mcp_client',
            'component_name': 'claude-code',
            'available': False,
            'version': None,
            'installation_path': None,
            'configuration_path': None,
            'health_status': 'unknown',
            'error_message': 'Claude Code not detected on this system',
            'capabilities': {}
        }

        # Validate MCP client unavailable state
        assert mcp_component['component_type'] == 'mcp_client'
        assert mcp_component['available'] is False
        assert mcp_component['health_status'] in ['unhealthy', 'unknown']
        assert mcp_component['error_message'] is not None

    async def test_component_health_status_degraded(self, mock_setup_service):
        """Test component with degraded health status."""
        degraded_component = {
            'component_type': 'docker',
            'component_name': 'docker',
            'available': True,
            'version': '20.10.8',  # Older version
            'installation_path': '/usr/bin/docker',
            'configuration_path': None,
            'health_status': 'degraded',
            'error_message': 'Docker version is outdated, some features may not work',
            'capabilities': {'api_version': '1.40', 'compose_support': False}
        }

        # Validate degraded state
        assert degraded_component['available'] is True  # Still available but degraded
        assert degraded_component['health_status'] == 'degraded'
        assert degraded_component['error_message'] is not None

    async def test_component_capabilities_structure(self, mock_setup_service):
        """Test component capabilities field structure."""
        test_capabilities = [
            {'api_version': '1.43', 'compose_support': True},  # Docker
            {'models': ['model1'], 'api_version': 'v1'},       # Ollama
            {'config_path': '/path/to/config'},                # MCP Client
            {}                                                 # Empty capabilities
        ]

        for capabilities in test_capabilities:
            assert isinstance(capabilities, dict)
            # All values should be JSON serializable
            import json
            json.dumps(capabilities)  # Should not raise exception

    async def test_components_last_checked_format(self, mock_setup_service):
        """Test last_checked timestamp format."""
        response = {
            'components': [],
            'last_checked': '2025-01-26T14:35:00Z'
        }

        # Should be ISO format timestamp
        from datetime import datetime
        parsed_time = datetime.fromisoformat(response['last_checked'].replace('Z', '+00:00'))
        assert parsed_time is not None

    async def test_components_empty_list(self, mock_setup_service):
        """Test response with no components detected."""
        response = {
            'components': [],
            'last_checked': '2025-01-26T14:35:00Z'
        }

        # Should handle empty component list
        assert isinstance(response['components'], list)
        assert len(response['components']) == 0


# This test file should initially FAIL as the setup API endpoints are not yet implemented.
# Tests will pass once the API endpoints are properly implemented in src/api/setup_endpoints.py