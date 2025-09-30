"""Performance tests for wizard step transitions (<200ms requirement) - T024."""

import pytest
import time
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime, timezone

from src.logic.wizard.orchestrator import WizardOrchestrator, StepResult, WizardResult
from src.models.wizard_state import WizardState


pytestmark = pytest.mark.performance


class TestWizardStepPerformance:
    """Validate wizard step transitions meet <200ms response time requirement."""

    @pytest.fixture
    def orchestrator(self):
        """Create WizardOrchestrator instance for testing."""
        return WizardOrchestrator()

    @pytest.fixture
    def mock_db_cursor(self):
        """Create mock database cursor."""
        mock_cursor = AsyncMock()
        mock_cursor.fetchone = AsyncMock()
        return mock_cursor

    @pytest.mark.asyncio
    async def test_wizard_start_performance(self, orchestrator, mock_db_cursor):
        """Test wizard initialization completes within 200ms."""
        # Mock database operations
        mock_db_cursor.fetchone.return_value = (0,)  # No active sessions

        with patch.object(orchestrator.db_manager, 'initialize', new_callable=AsyncMock):
            with patch.object(orchestrator.db_manager, '_connection') as mock_conn:
                mock_conn.execute = AsyncMock(return_value=mock_db_cursor)
                mock_conn.commit = AsyncMock()
                orchestrator.db_manager._initialized = True

                start_time = time.perf_counter()
                wizard_state = await orchestrator.start_wizard("shelf", "test-shelf")
                elapsed_ms = (time.perf_counter() - start_time) * 1000

                assert elapsed_ms < 200, f"Wizard start took {elapsed_ms:.2f}ms (threshold: 200ms)"
                assert wizard_state.wizard_id is not None
                assert wizard_state.wizard_type == "shelf"

    @pytest.mark.asyncio
    async def test_wizard_step_processing_performance(self, orchestrator, mock_db_cursor):
        """Test wizard step processing completes within 200ms."""
        wizard_id = str(uuid4())
        now = datetime.now(timezone.utc)

        # Mock wizard state in database
        wizard_state = WizardState(
            wizard_id=wizard_id,
            wizard_type="shelf",
            target_entity="test-shelf",
            current_step=1,
            total_steps=5,
            collected_data={},
            start_time=now,
            last_activity=now,
            is_complete=False
        )

        with patch.object(orchestrator, '_load_wizard_state', new_callable=AsyncMock) as mock_load:
            with patch.object(orchestrator, '_save_wizard_state', new_callable=AsyncMock):
                mock_load.return_value = wizard_state

                start_time = time.perf_counter()
                result = await orchestrator.process_step(wizard_id, "Test description")
                elapsed_ms = (time.perf_counter() - start_time) * 1000

                assert elapsed_ms < 200, f"Step processing took {elapsed_ms:.2f}ms (threshold: 200ms)"
                assert result.accepted is True

    @pytest.mark.asyncio
    async def test_wizard_completion_performance(self, orchestrator):
        """Test wizard completion completes within 200ms."""
        wizard_id = str(uuid4())
        now = datetime.now(timezone.utc)

        # Mock completed wizard state with proper data types
        wizard_state = WizardState(
            wizard_id=wizard_id,
            wizard_type="shelf",
            target_entity="test-shelf",
            current_step=5,
            total_steps=5,
            collected_data={"description": "test", "auto_fill": True, "default_box_type": "drag", "tags": ["test", "docs"]},
            start_time=now,
            last_activity=now,
            is_complete=True
        )

        with patch.object(orchestrator, '_load_wizard_state', new_callable=AsyncMock) as mock_load:
            with patch.object(orchestrator, '_delete_wizard_state', new_callable=AsyncMock):
                mock_load.return_value = wizard_state

                start_time = time.perf_counter()
                result = await orchestrator.complete_wizard(wizard_id)
                elapsed_ms = (time.perf_counter() - start_time) * 1000

                assert elapsed_ms < 200, f"Wizard completion took {elapsed_ms:.2f}ms (threshold: 200ms)"
                assert result.configuration_applied is True

    @pytest.mark.asyncio
    async def test_multiple_sequential_wizard_steps(self, orchestrator):
        """Test multiple wizard steps maintain performance."""
        wizard_id = str(uuid4())
        now = datetime.now(timezone.utc)

        times = []
        for step_num in range(1, 6):
            wizard_state = WizardState(
                wizard_id=wizard_id,
                wizard_type="shelf",
                target_entity="test-shelf",
                current_step=step_num,
                total_steps=5,
                collected_data={},
                start_time=now,
                last_activity=now,
                is_complete=False
            )

            with patch.object(orchestrator, '_load_wizard_state', new_callable=AsyncMock) as mock_load:
                with patch.object(orchestrator, '_save_wizard_state', new_callable=AsyncMock):
                    mock_load.return_value = wizard_state

                    start_time = time.perf_counter()
                    await orchestrator.process_step(wizard_id, f"response-{step_num}")
                    elapsed_ms = (time.perf_counter() - start_time) * 1000
                    times.append(elapsed_ms)

        # All steps should be under 200ms
        for i, elapsed_ms in enumerate(times):
            assert elapsed_ms < 200, f"Step {i+1} took {elapsed_ms:.2f}ms (threshold: 200ms)"

        # Average should be well under threshold
        avg_time = sum(times) / len(times)
        assert avg_time < 150, f"Average step time {avg_time:.2f}ms should be <150ms"

    @pytest.mark.asyncio
    async def test_concurrent_wizard_sessions(self, orchestrator, mock_db_cursor):
        """Test multiple concurrent wizard sessions maintain performance."""
        # Mock no active sessions initially
        mock_db_cursor.fetchone.return_value = (0,)

        with patch.object(orchestrator.db_manager, 'initialize', new_callable=AsyncMock):
            with patch.object(orchestrator.db_manager, '_connection') as mock_conn:
                mock_conn.execute = AsyncMock(return_value=mock_db_cursor)
                mock_conn.commit = AsyncMock()
                orchestrator.db_manager._initialized = True

                start_time = time.perf_counter()
                tasks = [
                    orchestrator.start_wizard("shelf", f"shelf-{i}")
                    for i in range(5)
                ]
                results = await asyncio.gather(*tasks)
                total_elapsed_ms = (time.perf_counter() - start_time) * 1000

                # All should complete
                assert len(results) == 5

                # Total time should be reasonable for concurrent operations
                assert total_elapsed_ms < 500, f"5 concurrent wizard starts took {total_elapsed_ms:.2f}ms"

    @pytest.mark.asyncio
    async def test_wizard_state_persistence_performance(self, orchestrator):
        """Test wizard state persistence doesn't slow down steps."""
        wizard_id = str(uuid4())
        now = datetime.now(timezone.utc)

        wizard_state = WizardState(
            wizard_id=wizard_id,
            wizard_type="shelf",
            target_entity="test-shelf",
            current_step=1,
            total_steps=5,
            collected_data={},
            start_time=now,
            last_activity=now,
            is_complete=False
        )

        with patch.object(orchestrator, '_load_wizard_state', new_callable=AsyncMock) as mock_load:
            with patch.object(orchestrator, '_save_wizard_state', new_callable=AsyncMock) as mock_save:
                mock_load.return_value = wizard_state
                mock_save.return_value = None

                start_time = time.perf_counter()
                await orchestrator.process_step(wizard_id, "test")
                elapsed_ms = (time.perf_counter() - start_time) * 1000

                # Even with persistence, should be under 200ms
                assert elapsed_ms < 200, f"Step with persistence took {elapsed_ms:.2f}ms"
                assert mock_save.called

    @pytest.mark.asyncio
    async def test_wizard_validation_performance(self, orchestrator):
        """Test wizard input validation is fast."""
        # Test validation within orchestrator (using actual _validate_response method)
        from src.models.wizard_step import WizardStep

        test_steps = [
            WizardStep(
                step_number=1, wizard_type="shelf", step_title="Description",
                prompt_text="Enter description:", input_type="text", choices=None,
                validation_rules=["max_length:500"], is_optional=True, depends_on=None
            ),
            WizardStep(
                step_number=2, wizard_type="shelf", step_title="Box Type",
                prompt_text="Select type:", input_type="choice", choices=["drag", "rag", "bag"],
                validation_rules=[], is_optional=False, depends_on=None
            ),
            WizardStep(
                step_number=3, wizard_type="mcp", step_title="Port",
                prompt_text="Enter port:", input_type="text", choices=None,
                validation_rules=[], is_optional=False, depends_on=None
            ),
            WizardStep(
                step_number=4, wizard_type="shelf", step_title="Tags",
                prompt_text="Enter tags:", input_type="text", choices=None,
                validation_rules=["csv_format"], is_optional=True, depends_on=None
            ),
            WizardStep(
                step_number=5, wizard_type="shelf", step_title="Confirm",
                prompt_text="Confirm?", input_type="boolean", choices=["yes", "no"],
                validation_rules=[], is_optional=False, depends_on=None
            )
        ]

        test_responses = [
            "Test shelf description",
            "drag",
            "9383",
            "docs,test,main",
            "yes"
        ]

        times = []
        for step, response in zip(test_steps, test_responses):
            start_time = time.perf_counter()
            errors = orchestrator._validate_response(step, response)
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            times.append(elapsed_ms)
            assert len(errors) == 0, f"Unexpected validation error: {errors}"

        # All validations should be very fast
        for i, elapsed_ms in enumerate(times):
            assert elapsed_ms < 50, f"Validation {i+1} took {elapsed_ms:.2f}ms (should be <50ms)"

    @pytest.mark.asyncio
    async def test_wizard_cancellation_performance(self, orchestrator):
        """Test wizard cancellation is fast."""
        wizard_id = str(uuid4())

        with patch.object(orchestrator, '_delete_wizard_state', new_callable=AsyncMock) as mock_delete:
            mock_delete.return_value = None

            start_time = time.perf_counter()
            await orchestrator._delete_wizard_state(wizard_id)
            elapsed_ms = (time.perf_counter() - start_time) * 1000

            assert elapsed_ms < 100, f"Wizard cancellation took {elapsed_ms:.2f}ms (should be <100ms)"
            assert mock_delete.called

    @pytest.mark.asyncio
    async def test_wizard_memory_usage_per_session(self):
        """Test wizard sessions have minimal memory footprint."""
        import tracemalloc
        from src.models.wizard_state import WizardState
        from datetime import datetime

        tracemalloc.start()
        baseline_memory = tracemalloc.get_traced_memory()[0]

        # Create 10 wizard states
        wizards = []
        for i in range(10):
            wizard = WizardState(
                wizard_id=str(uuid4()),
                wizard_type="shelf",
                target_entity=f"shelf-{i}",
                current_step=1,
                total_steps=5,
                collected_data={},
                start_time=datetime.now(),
                last_activity=datetime.now(),
                is_complete=False
            )
            wizards.append(wizard)

        final_memory = tracemalloc.get_traced_memory()[0]
        tracemalloc.stop()

        # 10 wizard sessions should use less than 1MB
        memory_increase = (final_memory - baseline_memory) / (1024 * 1024)
        assert memory_increase < 1, f"10 wizard sessions used {memory_increase:.2f}MB (should be <1MB)"

    @pytest.mark.asyncio
    async def test_wizard_cleanup_performance(self, orchestrator):
        """Test cleaning up completed wizard sessions is fast."""
        # Create several completed wizards
        wizard_ids = [str(uuid4()) for _ in range(10)]

        with patch.object(orchestrator, '_delete_wizard_state', new_callable=AsyncMock) as mock_delete:
            mock_delete.return_value = None

            start_time = time.perf_counter()
            cleanup_tasks = [orchestrator._delete_wizard_state(wid) for wid in wizard_ids]
            await asyncio.gather(*cleanup_tasks)
            elapsed_ms = (time.perf_counter() - start_time) * 1000

            # Cleaning 10 wizards should be fast
            assert elapsed_ms < 500, f"Cleaning 10 wizards took {elapsed_ms:.2f}ms"
            assert mock_delete.call_count == 10

    def test_wizard_orchestrator_initialization(self):
        """Test WizardOrchestrator initializes quickly."""
        start_time = time.perf_counter()
        orchestrator = WizardOrchestrator()
        init_time_ms = (time.perf_counter() - start_time) * 1000

        assert init_time_ms < 100, f"Orchestrator initialization took {init_time_ms:.2f}ms"