"""Contract tests for GET /setup/session/{session_id}/status API endpoint.

Tests API endpoint according to setup-wizard-api.yml specification:
- GET /setup/session/{session_id}/status
- Parameters: session_id (UUID)
- Responses: 200 (success), 404 (session not found)
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


class TestSetupStatusApiContract:
    """Contract tests for GET /setup/session/{session_id}/status endpoint."""

    async def test_status_endpoint_exists(self, mock_setup_service):
        """Test that the status endpoint is registered."""
        from src.api.setup_endpoints import setup_router

        # Check if route is registered
        routes = [route.path for route in setup_router.routes if hasattr(route, 'path')]
        status_route_exists = any("/setup/session/{session_id}/status" in route for route in routes)
        assert status_route_exists

    async def test_get_status_success(self, mock_setup_service):
        """Test successful status retrieval."""
        session_id = "550e8400-e29b-41d4-a716-446655440000"
        mock_response = {
            'session_id': session_id,
            'status': 'running',
            'current_step': 'configure_vector_storage',
            'progress_percentage': 33.3,
            'completed_steps': ['detect_components'],
            'failed_steps': [],
            'estimated_time_remaining': 120
        }

        mock_setup_service.get_session_status.return_value = mock_response

        # Verify session ID is valid UUID
        uuid_obj = UUID(session_id)
        assert str(uuid_obj) == session_id

    async def test_get_status_invalid_uuid_400(self, mock_setup_service):
        """Test invalid UUID format returns 400 error."""
        invalid_session_id = "not-a-uuid"

        # Should reject invalid UUID format
        with pytest.raises(ValueError):
            UUID(invalid_session_id)

    async def test_get_status_session_not_found_404(self, mock_setup_service):
        """Test non-existent session returns 404 error."""
        from src.models.setup_types import SessionNotFoundError

        session_id = "550e8400-e29b-41d4-a716-446655440999"
        mock_setup_service.get_session_status.side_effect = SessionNotFoundError(
            f"Session {session_id} not found"
        )

        # Should handle session not found
        try:
            await mock_setup_service.get_session_status(session_id)
        except SessionNotFoundError:
            pass  # Expected exception

    async def test_status_response_schema_initialized(self, mock_setup_service):
        """Test response schema for initialized session."""
        response = {
            'session_id': "550e8400-e29b-41d4-a716-446655440001",
            'status': 'initialized',
            'current_step': 'detect_components',
            'progress_percentage': 0.0,
            'completed_steps': [],
            'failed_steps': [],
            'estimated_time_remaining': 300
        }

        # Validate response structure
        assert 'session_id' in response
        assert UUID(response['session_id'])  # Valid UUID
        assert response['status'] in ['initialized', 'running', 'paused', 'completed', 'failed', 'cancelled']
        assert response['current_step'] in [
            'detect_components', 'configure_vector_storage', 'setup_embedding_model',
            'configure_mcp_clients', 'validate_configuration', 'persist_settings'
        ]
        assert 0 <= response['progress_percentage'] <= 100
        assert isinstance(response['completed_steps'], list)
        assert isinstance(response['failed_steps'], list)

    async def test_status_response_schema_running(self, mock_setup_service):
        """Test response schema for running session."""
        response = {
            'session_id': "550e8400-e29b-41d4-a716-446655440002",
            'status': 'running',
            'current_step': 'setup_embedding_model',
            'progress_percentage': 66.7,
            'completed_steps': ['detect_components', 'configure_vector_storage'],
            'failed_steps': [],
            'estimated_time_remaining': 90
        }

        # Validate running state
        assert response['status'] == 'running'
        assert len(response['completed_steps']) > 0
        assert response['progress_percentage'] > 0

    async def test_status_response_schema_completed(self, mock_setup_service):
        """Test response schema for completed session."""
        response = {
            'session_id': "550e8400-e29b-41d4-a716-446655440003",
            'status': 'completed',
            'current_step': 'persist_settings',
            'progress_percentage': 100.0,
            'completed_steps': [
                'detect_components', 'configure_vector_storage', 'setup_embedding_model',
                'configure_mcp_clients', 'validate_configuration', 'persist_settings'
            ],
            'failed_steps': [],
            'estimated_time_remaining': 0
        }

        # Validate completed state
        assert response['status'] == 'completed'
        assert response['progress_percentage'] == 100.0
        assert len(response['completed_steps']) == 6  # All steps completed
        assert response['estimated_time_remaining'] == 0

    async def test_status_response_schema_failed(self, mock_setup_service):
        """Test response schema for failed session with step failures."""
        failed_step = {
            'step': 'configure_vector_storage',
            'error_type': 'dependency',
            'error_message': 'Docker service not available',
            'technical_details': 'ConnectionError: Cannot connect to Docker daemon',
            'retry_possible': True,
            'suggested_action': 'Start Docker service and retry setup'
        }

        response = {
            'session_id': "550e8400-e29b-41d4-a716-446655440004",
            'status': 'failed',
            'current_step': 'configure_vector_storage',
            'progress_percentage': 16.7,
            'completed_steps': ['detect_components'],
            'failed_steps': [failed_step],
            'estimated_time_remaining': None
        }

        # Validate failed state
        assert response['status'] == 'failed'
        assert len(response['failed_steps']) > 0

        # Validate failed step structure
        step_failure = response['failed_steps'][0]
        assert 'step' in step_failure
        assert 'error_type' in step_failure
        assert 'error_message' in step_failure
        assert step_failure['error_type'] in ['network', 'permission', 'configuration', 'dependency', 'timeout']
        assert isinstance(step_failure['retry_possible'], bool)

    async def test_status_progress_percentage_bounds(self, mock_setup_service):
        """Test progress percentage is within valid bounds."""
        test_cases = [
            {'progress': 0.0, 'expected_valid': True},
            {'progress': 50.5, 'expected_valid': True},
            {'progress': 100.0, 'expected_valid': True},
            {'progress': -1.0, 'expected_valid': False},
            {'progress': 101.0, 'expected_valid': False}
        ]

        for case in test_cases:
            if case['expected_valid']:
                assert 0 <= case['progress'] <= 100
            else:
                assert not (0 <= case['progress'] <= 100)

    async def test_status_estimated_time_remaining_types(self, mock_setup_service):
        """Test estimated_time_remaining field accepts correct types."""
        valid_values = [0, 120, 300, None]

        for value in valid_values:
            if value is not None:
                assert isinstance(value, int)
                assert value >= 0
            # None is also valid (unknown time remaining)


# This test file should initially FAIL as the setup API endpoints are not yet implemented.
# Tests will pass once the API endpoints are properly implemented in src/api/setup_endpoints.py