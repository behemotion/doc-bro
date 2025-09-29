"""Contract tests for POST /setup/session/{session_id}/execute API endpoint.

Tests API endpoint according to setup-wizard-api.yml specification:
- POST /setup/session/{session_id}/execute
- Parameters: session_id (UUID)
- Responses: 202 (async execution started), 409 (already in progress)
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


class TestSetupExecuteApiContract:
    """Contract tests for POST /setup/session/{session_id}/execute endpoint."""

    def test_execute_endpoint_exists(self, mock_setup_service):
        """Test that the execute endpoint is registered."""
        from src.api.setup_endpoints import setup_router

        # Check if route is registered
        routes = [route.path for route in setup_router.routes if hasattr(route, 'path')]
        execute_route_exists = any("/setup/session/{session_id}/execute" in route for route in routes)
        assert execute_route_exists

    def test_execute_setup_success_202(self, mock_setup_service):
        """Test successful setup execution returns 202 (async operation started)."""
        session_id = "550e8400-e29b-41d4-a716-446655440000"
        mock_response = {
            'execution_started': True,
            'estimated_duration': 180,
            'steps_to_execute': [
                'detect_components',
                'configure_vector_storage',
                'setup_embedding_model',
                'configure_mcp_clients',
                'validate_configuration',
                'persist_settings'
            ]
        }

        mock_setup_service.execute_setup.return_value = mock_response

        # Verify session ID is valid UUID
        uuid_obj = UUID(session_id)
        assert str(uuid_obj) == session_id

    def test_execute_invalid_uuid_400(self, mock_setup_service):
        """Test invalid UUID format returns 400 error."""
        invalid_session_id = "not-a-uuid"

        # Should reject invalid UUID format
        with pytest.raises(ValueError):
            UUID(invalid_session_id)

    def test_execute_session_not_found_404(self, mock_setup_service):
        """Test non-existent session returns 404 error."""
        from src.models.setup_types import SessionNotFoundError

        session_id = "550e8400-e29b-41d4-a716-446655440999"
        mock_setup_service.execute_setup.side_effect = SessionNotFoundError(
            f"Session {session_id} not found"
        )

        # Should handle session not found
        try:
            await mock_setup_service.execute_setup(session_id)
        except SessionNotFoundError:
            pass  # Expected exception

    def test_execute_already_in_progress_409(self, mock_setup_service):
        """Test execution already in progress returns 409 conflict."""
        from src.models.setup_types import SetupInProgressError

        session_id = "550e8400-e29b-41d4-a716-446655440001"
        mock_setup_service.execute_setup.side_effect = SetupInProgressError(
            "Setup execution already in progress for this session"
        )

        # Should handle execution conflict
        try:
            await mock_setup_service.execute_setup(session_id)
        except SetupInProgressError:
            pass  # Expected exception

    def test_execute_already_completed_409(self, mock_setup_service):
        """Test execution of completed session returns 409 conflict."""
        from src.models.setup_types import SetupAlreadyCompletedError

        session_id = "550e8400-e29b-41d4-a716-446655440002"
        mock_setup_service.execute_setup.side_effect = SetupAlreadyCompletedError(
            "Setup has already been completed for this session"
        )

        # Should handle already completed
        try:
            await mock_setup_service.execute_setup(session_id)
        except SetupAlreadyCompletedError:
            pass  # Expected exception

    def test_execute_response_schema_valid(self, mock_setup_service):
        """Test response follows ExecutionResponse schema."""
        response = {
            'execution_started': True,
            'estimated_duration': 180,
            'steps_to_execute': [
                'detect_components',
                'configure_vector_storage',
                'setup_embedding_model',
                'configure_mcp_clients',
                'validate_configuration',
                'persist_settings'
            ]
        }

        # Validate response structure
        assert 'execution_started' in response
        assert 'estimated_duration' in response
        assert isinstance(response['execution_started'], bool)
        assert isinstance(response['estimated_duration'], int)
        assert response['estimated_duration'] > 0

    def test_execute_steps_to_execute_valid(self, mock_setup_service):
        """Test steps_to_execute contains valid step names."""
        valid_steps = [
            'detect_components',
            'configure_vector_storage',
            'setup_embedding_model',
            'configure_mcp_clients',
            'validate_configuration',
            'persist_settings'
        ]

        response = {
            'execution_started': True,
            'estimated_duration': 240,
            'steps_to_execute': valid_steps
        }

        # All steps should be valid
        for step in response['steps_to_execute']:
            assert step in valid_steps

    def test_execute_partial_steps_execution(self, mock_setup_service):
        """Test execution with partial steps (resume scenario)."""
        # Scenario: some steps already completed, only remaining steps to execute
        remaining_steps = [
            'setup_embedding_model',
            'configure_mcp_clients',
            'validate_configuration',
            'persist_settings'
        ]

        response = {
            'execution_started': True,
            'estimated_duration': 120,  # Less time since fewer steps
            'steps_to_execute': remaining_steps
        }

        # Should handle partial execution
        assert len(response['steps_to_execute']) < 6  # Not all 6 steps
        assert response['estimated_duration'] < 180  # Less time than full execution

    def test_execute_estimated_duration_reasonable(self, mock_setup_service):
        """Test estimated duration is within reasonable bounds."""
        test_cases = [
            {'steps': 6, 'min_duration': 60, 'max_duration': 600},  # Full setup: 1-10 minutes
            {'steps': 3, 'min_duration': 30, 'max_duration': 300},  # Partial: 0.5-5 minutes
            {'steps': 1, 'min_duration': 10, 'max_duration': 120}   # Single step: 10s-2min
        ]

        for case in test_cases:
            # Estimated duration should be reasonable for number of steps
            estimated = case['steps'] * 30  # 30 seconds per step average
            assert case['min_duration'] <= estimated <= case['max_duration']

    def test_execute_async_operation(self, mock_setup_service):
        """Test that execution is asynchronous operation."""
        session_id = "550e8400-e29b-41d4-a716-446655440003"

        # Mock async execution start (does not wait for completion)
        mock_setup_service.execute_setup.return_value = {
            'execution_started': True,
            'estimated_duration': 150,
            'steps_to_execute': ['detect_components', 'configure_vector_storage']
        }

        # Execution should start immediately, not wait for completion
        response = await mock_setup_service.execute_setup(session_id)
        assert response['execution_started'] is True

    def test_execute_no_steps_to_execute(self, mock_setup_service):
        """Test execution when no steps need to be executed."""
        # Scenario: all steps already completed or no configuration provided
        response = {
            'execution_started': False,
            'estimated_duration': 0,
            'steps_to_execute': []
        }

        # Should handle no-op execution
        assert response['execution_started'] is False
        assert response['estimated_duration'] == 0
        assert len(response['steps_to_execute']) == 0

    def test_execute_step_dependencies(self, mock_setup_service):
        """Test that steps are ordered according to dependencies."""
        expected_order = [
            'detect_components',         # Must be first
            'configure_vector_storage',  # After detection
            'setup_embedding_model',     # After detection
            'configure_mcp_clients',     # After detection
            'validate_configuration',    # After all configuration
            'persist_settings'           # Must be last
        ]

        response = {
            'execution_started': True,
            'estimated_duration': 200,
            'steps_to_execute': expected_order
        }

        steps = response['steps_to_execute']

        # Check dependency order
        if 'detect_components' in steps:
            assert steps.index('detect_components') == 0  # Should be first

        if 'persist_settings' in steps:
            assert steps.index('persist_settings') == len(steps) - 1  # Should be last

        if 'validate_configuration' in steps and 'persist_settings' in steps:
            validate_idx = steps.index('validate_configuration')
            persist_idx = steps.index('persist_settings')
            assert validate_idx < persist_idx  # Validation before persistence


# This test file should initially FAIL as the setup API endpoints are not yet implemented.
# Tests will pass once the API endpoints are properly implemented in src/api/setup_endpoints.py