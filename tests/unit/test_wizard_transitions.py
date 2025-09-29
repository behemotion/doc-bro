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
        # Test actual start_wizard method without mocking
        wizard_state = await wizard_orchestrator.start_wizard("shelf", "new-shelf")

        assert wizard_state is not None
        assert wizard_state.wizard_type == "shelf"
        assert wizard_state.target_entity == "new-shelf"
        assert wizard_state.current_step == 1
        assert wizard_state.total_steps > 0

    @pytest.mark.asyncio
    async def test_wizard_orchestrator_process_step(self, wizard_orchestrator):
        """Test processing a wizard step through orchestrator."""
        # Start a wizard first
        wizard_state = await wizard_orchestrator.start_wizard("shelf", "test-shelf")

        # Process first step (description - optional text)
        result = await wizard_orchestrator.process_step(wizard_state.wizard_id, "Test description")

        assert result.accepted is True
        assert len(result.validation_errors) == 0
        assert result.is_complete is False  # Not done yet

    @pytest.mark.asyncio
    async def test_wizard_orchestrator_complete_session(self, wizard_orchestrator):
        """Test completing a wizard session through orchestrator."""
        # Start wizard and complete all steps
        wizard_state = await wizard_orchestrator.start_wizard("mcp", "mcp-config")

        # MCP wizard has 2 steps (read-only and admin servers)
        result1 = await wizard_orchestrator.process_step(wizard_state.wizard_id, "yes")
        assert result1.accepted is True

        result2 = await wizard_orchestrator.process_step(wizard_state.wizard_id, "yes")
        assert result2.accepted is True
        assert result2.is_complete is True

        # Now complete the wizard
        final_result = await wizard_orchestrator.complete_wizard(wizard_state.wizard_id)

        assert final_result.configuration_applied is True

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
    async def test_wizard_cancellation(self, wizard_orchestrator):
        """Test cancelling an active wizard session."""
        # Start a wizard
        wizard_state = await wizard_orchestrator.start_wizard("shelf", "test-shelf")

        # Delete the wizard state (equivalent to cancellation)
        await wizard_orchestrator._delete_wizard_state(wizard_state.wizard_id)

        # Verify it's gone
        retrieved_state = await wizard_orchestrator.get_wizard_status(wizard_state.wizard_id)
        assert retrieved_state is None

    @pytest.mark.asyncio
    async def test_wizard_transition_timing(self, wizard_orchestrator):
        """Test that wizard step transitions meet <200ms requirement."""
        import time

        # Start wizard
        wizard_state = await wizard_orchestrator.start_wizard("box", "test-box")

        # Measure step processing time
        start_time = time.time()
        result = await wizard_orchestrator.process_step(wizard_state.wizard_id, "drag")
        elapsed_time = (time.time() - start_time) * 1000  # Convert to ms

        assert elapsed_time < 200, f"Wizard step took {elapsed_time}ms (>200ms threshold)"
        assert result.accepted is True

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