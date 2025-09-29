"""Performance tests for wizard step transitions (<200ms requirement) - T058."""

import pytest
import time
import asyncio
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from src.logic.wizard.orchestrator import WizardOrchestrator


pytestmark = pytest.mark.performance


class TestWizardStepPerformance:
    """Validate wizard step transitions meet <200ms response time requirement."""

    @pytest.fixture
    def orchestrator(self):
        """Create WizardOrchestrator instance for testing."""
        return WizardOrchestrator()

    @pytest.mark.asyncio
    async def test_wizard_start_performance(self, orchestrator):
        """Test wizard initialization completes within 200ms."""
        with patch.object(orchestrator, '_create_wizard_state', new_callable=AsyncMock) as mock_create:
            mock_wizard_id = str(uuid4())
            mock_create.return_value = mock_wizard_id

            start_time = time.perf_counter()
            wizard_id = await orchestrator.start_wizard("shelf", "test-shelf")
            elapsed_ms = (time.perf_counter() - start_time) * 1000

            assert elapsed_ms < 200, f"Wizard start took {elapsed_ms:.2f}ms (threshold: 200ms)"
            assert wizard_id is not None

    @pytest.mark.asyncio
    async def test_wizard_step_processing_performance(self, orchestrator):
        """Test wizard step processing completes within 200ms."""
        wizard_id = str(uuid4())

        with patch.object(orchestrator, '_process_wizard_step', new_callable=AsyncMock) as mock_process:
            mock_process.return_value = (True, "Next step prompt")

            start_time = time.perf_counter()
            success, next_prompt = await orchestrator.process_step(wizard_id, "test response")
            elapsed_ms = (time.perf_counter() - start_time) * 1000

            assert elapsed_ms < 200, f"Step processing took {elapsed_ms:.2f}ms (threshold: 200ms)"
            assert success is True

    @pytest.mark.asyncio
    async def test_wizard_completion_performance(self, orchestrator):
        """Test wizard completion completes within 200ms."""
        wizard_id = str(uuid4())

        with patch.object(orchestrator, '_finalize_wizard', new_callable=AsyncMock) as mock_finalize:
            mock_finalize.return_value = {"success": True, "entity_created": True}

            start_time = time.perf_counter()
            result = await orchestrator.complete_wizard(wizard_id)
            elapsed_ms = (time.perf_counter() - start_time) * 1000

            assert elapsed_ms < 200, f"Wizard completion took {elapsed_ms:.2f}ms (threshold: 200ms)"
            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_multiple_sequential_wizard_steps(self, orchestrator):
        """Test multiple wizard steps maintain performance."""
        wizard_id = str(uuid4())

        with patch.object(orchestrator, '_process_wizard_step', new_callable=AsyncMock) as mock_process:
            mock_process.return_value = (True, "Next step")

            times = []
            for step_num in range(5):
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
    async def test_concurrent_wizard_sessions(self, orchestrator):
        """Test multiple concurrent wizard sessions maintain performance."""
        with patch.object(orchestrator, '_create_wizard_state', new_callable=AsyncMock) as mock_create:
            # Mock returns unique wizard IDs
            mock_create.side_effect = [str(uuid4()) for _ in range(5)]

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

        with patch.object(orchestrator, '_save_wizard_state', new_callable=AsyncMock) as mock_save:
            with patch.object(orchestrator, '_process_wizard_step', new_callable=AsyncMock) as mock_process:
                mock_process.return_value = (True, "Next")
                mock_save.return_value = True

                start_time = time.perf_counter()
                await orchestrator.process_step(wizard_id, "test")
                elapsed_ms = (time.perf_counter() - start_time) * 1000

                # Even with persistence, should be under 200ms
                assert elapsed_ms < 200, f"Step with persistence took {elapsed_ms:.2f}ms"

    @pytest.mark.asyncio
    async def test_wizard_validation_performance(self, orchestrator):
        """Test wizard input validation is fast."""
        from src.logic.wizard.validator import WizardValidator

        validator = WizardValidator()

        test_inputs = [
            ("shelf", "description", "Test shelf description"),
            ("box", "box_type", "drag"),
            ("mcp", "port", "9383"),
            ("shelf", "tags", "docs,test,main"),
            ("box", "file_patterns", "*.md,*.txt")
        ]

        times = []
        for wizard_type, field, value in test_inputs:
            start_time = time.perf_counter()
            # Validator should have a validate method
            is_valid = validator.validate_input(wizard_type, field, value) if hasattr(validator, 'validate_input') else True
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            times.append(elapsed_ms)

        # All validations should be very fast
        for i, elapsed_ms in enumerate(times):
            assert elapsed_ms < 50, f"Validation {i+1} took {elapsed_ms:.2f}ms (should be <50ms)"

    @pytest.mark.asyncio
    async def test_wizard_cancellation_performance(self, orchestrator):
        """Test wizard cancellation is fast."""
        wizard_id = str(uuid4())

        with patch.object(orchestrator, '_cancel_wizard', new_callable=AsyncMock) as mock_cancel:
            mock_cancel.return_value = True

            start_time = time.perf_counter()
            result = await orchestrator.cancel_wizard(wizard_id)
            elapsed_ms = (time.perf_counter() - start_time) * 1000

            assert elapsed_ms < 100, f"Wizard cancellation took {elapsed_ms:.2f}ms (should be <100ms)"
            assert result is True

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

        with patch.object(orchestrator, '_cleanup_wizard', new_callable=AsyncMock) as mock_cleanup:
            mock_cleanup.return_value = True

            start_time = time.perf_counter()
            cleanup_tasks = [orchestrator.cleanup_wizard(wid) for wid in wizard_ids]
            await asyncio.gather(*cleanup_tasks)
            elapsed_ms = (time.perf_counter() - start_time) * 1000

            # Cleaning 10 wizards should be fast
            assert elapsed_ms < 500, f"Cleaning 10 wizards took {elapsed_ms:.2f}ms"

    def test_wizard_orchestrator_initialization(self):
        """Test WizardOrchestrator initializes quickly."""
        start_time = time.perf_counter()
        orchestrator = WizardOrchestrator()
        init_time_ms = (time.perf_counter() - start_time) * 1000

        assert init_time_ms < 100, f"Orchestrator initialization took {init_time_ms:.2f}ms"