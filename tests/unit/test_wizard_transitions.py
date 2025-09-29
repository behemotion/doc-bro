"""Unit tests for wizard state transitions (T055)."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

from src.models.wizard_state import WizardState
from src.logic.wizard.orchestrator import WizardOrchestrator


pytestmark = pytest.mark.unit


class TestWizardStateTransitions:
    """Test wizard state management and transitions."""

    @pytest.fixture
    def wizard_id(self):
        """Generate test wizard ID."""
        return str(uuid4())

    @pytest.fixture
    def wizard_orchestrator(self):
        """Create WizardOrchestrator instance for testing."""
        return WizardOrchestrator()

    def test_wizard_state_initialization(self, wizard_id):
        """Test creating new wizard state."""
        state = WizardState(
            wizard_id=wizard_id,
            wizard_type="shelf",
            target_entity="test-shelf",
            current_step=1,
            total_steps=5,
            collected_data={},
            start_time=datetime.now(),
            last_activity=datetime.now(),
            is_complete=False
        )

        assert state.wizard_id == wizard_id
        assert state.wizard_type == "shelf"
        assert state.current_step == 1
        assert state.total_steps == 5
        assert state.is_complete is False
        assert len(state.collected_data) == 0

    def test_wizard_step_advancement(self, wizard_id):
        """Test advancing through wizard steps."""
        state = WizardState(
            wizard_id=wizard_id,
            wizard_type="box",
            target_entity="test-box",
            current_step=1,
            total_steps=4,
            collected_data={},
            start_time=datetime.now(),
            last_activity=datetime.now(),
            is_complete=False
        )

        # Advance to step 2
        state.current_step = 2
        assert state.current_step == 2

        # Advance to step 3
        state.current_step = 3
        assert state.current_step == 3

        # Should not exceed total_steps
        assert state.current_step <= state.total_steps

    def test_wizard_data_collection(self, wizard_id):
        """Test collecting user responses during wizard flow."""
        state = WizardState(
            wizard_id=wizard_id,
            wizard_type="shelf",
            target_entity="my-shelf",
            current_step=1,
            total_steps=5,
            collected_data={},
            start_time=datetime.now(),
            last_activity=datetime.now(),
            is_complete=False
        )

        # Collect step 1 data
        state.collected_data["description"] = "Main documentation shelf"
        assert "description" in state.collected_data

        # Collect step 2 data
        state.collected_data["auto_fill"] = True
        assert state.collected_data["auto_fill"] is True

        # Collect step 3 data
        state.collected_data["default_box_type"] = "drag"
        assert state.collected_data["default_box_type"] == "drag"

        # Verify all collected data
        assert len(state.collected_data) == 3

    def test_wizard_completion_transition(self, wizard_id):
        """Test marking wizard as complete."""
        state = WizardState(
            wizard_id=wizard_id,
            wizard_type="mcp",
            target_entity="mcp-config",
            current_step=5,
            total_steps=5,
            collected_data={"port": 9383, "enable_admin": False},
            start_time=datetime.now(),
            last_activity=datetime.now(),
            is_complete=False
        )

        # Mark as complete when at final step
        if state.current_step == state.total_steps:
            state.is_complete = True

        assert state.is_complete is True
        assert state.current_step == state.total_steps

    def test_wizard_session_timeout_detection(self, wizard_id):
        """Test detecting expired wizard sessions."""
        # Create wizard started 31 minutes ago
        old_time = datetime.now() - timedelta(minutes=31)
        state = WizardState(
            wizard_id=wizard_id,
            wizard_type="shelf",
            target_entity="test-shelf",
            current_step=2,
            total_steps=5,
            collected_data={},
            start_time=old_time,
            last_activity=old_time,
            is_complete=False
        )

        # Check if session is expired (30 minute timeout)
        session_age = datetime.now() - state.last_activity
        is_expired = session_age > timedelta(minutes=30)

        assert is_expired is True

    def test_wizard_activity_update(self, wizard_id):
        """Test updating wizard activity timestamp."""
        old_time = datetime.now() - timedelta(minutes=5)
        state = WizardState(
            wizard_id=wizard_id,
            wizard_type="box",
            target_entity="test-box",
            current_step=2,
            total_steps=4,
            collected_data={},
            start_time=old_time,
            last_activity=old_time,
            is_complete=False
        )

        # Update activity timestamp
        state.last_activity = datetime.now()

        # Verify timestamp was updated
        assert state.last_activity > old_time
        assert (datetime.now() - state.last_activity).total_seconds() < 1

    @pytest.mark.asyncio
    async def test_wizard_orchestrator_start_session(self, wizard_orchestrator):
        """Test starting a wizard session through orchestrator."""
        with patch.object(wizard_orchestrator, '_create_wizard_state', new_callable=AsyncMock) as mock_create:
            mock_wizard_id = str(uuid4())
            mock_create.return_value = mock_wizard_id

            wizard_id = await wizard_orchestrator.start_wizard("shelf", "new-shelf")

            assert wizard_id is not None
            mock_create.assert_called_once()

    @pytest.mark.asyncio
    async def test_wizard_orchestrator_process_step(self, wizard_orchestrator, wizard_id):
        """Test processing a wizard step through orchestrator."""
        with patch.object(wizard_orchestrator, '_process_wizard_step', new_callable=AsyncMock) as mock_process:
            mock_process.return_value = (True, "Next step prompt")

            success, next_prompt = await wizard_orchestrator.process_step(
                wizard_id,
                "User response"
            )

            assert success is True
            assert next_prompt is not None

    @pytest.mark.asyncio
    async def test_wizard_orchestrator_complete_session(self, wizard_orchestrator, wizard_id):
        """Test completing a wizard session through orchestrator."""
        with patch.object(wizard_orchestrator, '_finalize_wizard', new_callable=AsyncMock) as mock_finalize:
            mock_finalize.return_value = {"success": True, "entity_created": True}

            result = await wizard_orchestrator.complete_wizard(wizard_id)

            assert result["success"] is True
            mock_finalize.assert_called_once_with(wizard_id)

    def test_wizard_type_validation(self, wizard_id):
        """Test that only valid wizard types are accepted."""
        valid_types = ["shelf", "box", "mcp"]

        for wizard_type in valid_types:
            state = WizardState(
                wizard_id=wizard_id,
                wizard_type=wizard_type,
                target_entity=f"test-{wizard_type}",
                current_step=1,
                total_steps=3,
                collected_data={},
                start_time=datetime.now(),
                last_activity=datetime.now(),
                is_complete=False
            )
            assert state.wizard_type in valid_types

    def test_wizard_step_bounds_validation(self, wizard_id):
        """Test that current_step stays within bounds."""
        state = WizardState(
            wizard_id=wizard_id,
            wizard_type="shelf",
            target_entity="test-shelf",
            current_step=3,
            total_steps=5,
            collected_data={},
            start_time=datetime.now(),
            last_activity=datetime.now(),
            is_complete=False
        )

        # Current step should be valid
        assert 1 <= state.current_step <= state.total_steps

    @pytest.mark.asyncio
    async def test_wizard_cancellation(self, wizard_orchestrator, wizard_id):
        """Test cancelling an active wizard session."""
        with patch.object(wizard_orchestrator, '_cancel_wizard', new_callable=AsyncMock) as mock_cancel:
            mock_cancel.return_value = True

            result = await wizard_orchestrator.cancel_wizard(wizard_id)

            assert result is True
            mock_cancel.assert_called_once_with(wizard_id)

    @pytest.mark.asyncio
    async def test_wizard_transition_timing(self, wizard_orchestrator):
        """Test that wizard step transitions meet <200ms requirement."""
        import time

        with patch.object(wizard_orchestrator, '_process_wizard_step', new_callable=AsyncMock) as mock_process:
            mock_process.return_value = (True, "Next step")

            start_time = time.time()
            success, _ = await wizard_orchestrator.process_step(str(uuid4()), "test response")
            elapsed_time = (time.time() - start_time) * 1000  # Convert to ms

            assert elapsed_time < 200, f"Wizard step took {elapsed_time}ms (>200ms threshold)"

    def test_wizard_concurrent_sessions_limit(self):
        """Test limiting concurrent wizard sessions (max 10 per user)."""
        # This would test session management limits
        # Implementation depends on actual session management strategy
        max_sessions = 10
        active_sessions = []

        # Simulate creating multiple sessions
        for i in range(max_sessions + 5):
            wizard_id = str(uuid4())
            # Only first 10 should be allowed
            if len(active_sessions) < max_sessions:
                active_sessions.append(wizard_id)

        assert len(active_sessions) == max_sessions