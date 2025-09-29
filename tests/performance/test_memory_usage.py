"""Memory usage tests for wizard sessions (<50MB requirement) - T059."""

import pytest
import tracemalloc
from datetime import datetime
from uuid import uuid4

from src.models.wizard_state import WizardState
from src.logic.wizard.orchestrator import WizardOrchestrator


pytestmark = pytest.mark.performance


class TestMemoryUsage:
    """Validate memory usage meets <50MB per wizard session requirement."""

    def test_single_wizard_session_memory(self):
        """Test single wizard session uses less than 50MB."""
        tracemalloc.start()
        baseline_memory = tracemalloc.get_traced_memory()[0]

        # Create a single wizard session
        wizard = WizardState(
            wizard_id=str(uuid4()),
            wizard_type="shelf",
            target_entity="memory-test-shelf",
            current_step=1,
            total_steps=5,
            collected_data={
                "description": "Test shelf for memory profiling",
                "auto_fill": True,
                "default_box_type": "drag",
                "tags": ["test", "memory", "profiling"]
            },
            start_time=datetime.now(),
            last_activity=datetime.now(),
            is_complete=False
        )

        current_memory = tracemalloc.get_traced_memory()[0]
        tracemalloc.stop()

        memory_used_mb = (current_memory - baseline_memory) / (1024 * 1024)

        assert memory_used_mb < 50, f"Single wizard session used {memory_used_mb:.2f}MB (threshold: 50MB)"
        assert wizard.wizard_id is not None

    def test_multiple_wizard_sessions_memory(self):
        """Test multiple wizard sessions stay within memory limits."""
        tracemalloc.start()
        baseline_memory = tracemalloc.get_traced_memory()[0]

        # Create 10 wizard sessions (max concurrent limit)
        wizards = []
        for i in range(10):
            wizard = WizardState(
                wizard_id=str(uuid4()),
                wizard_type="box" if i % 2 == 0 else "shelf",
                target_entity=f"entity-{i}",
                current_step=1,
                total_steps=5,
                collected_data={},
                start_time=datetime.now(),
                last_activity=datetime.now(),
                is_complete=False
            )
            wizards.append(wizard)

        current_memory = tracemalloc.get_traced_memory()[0]
        tracemalloc.stop()

        memory_used_mb = (current_memory - baseline_memory) / (1024 * 1024)

        # 10 sessions should use less than 50MB total (much less than 50MB each)
        assert memory_used_mb < 50, f"10 wizard sessions used {memory_used_mb:.2f}MB"

    def test_wizard_with_large_collected_data(self):
        """Test wizard with large collected data stays within limits."""
        tracemalloc.start()
        baseline_memory = tracemalloc.get_traced_memory()[0]

        # Create wizard with substantial collected data
        large_data = {
            "description": "A" * 1000,  # 1KB description
            "tags": [f"tag-{i}" for i in range(100)],  # 100 tags
            "configuration": {
                "setting_1": "value" * 100,
                "setting_2": ["item" * 10 for _ in range(50)],
                "setting_3": {"nested": {"data": ["x" * 100 for _ in range(10)]}}
            }
        }

        wizard = WizardState(
            wizard_id=str(uuid4()),
            wizard_type="box",
            target_entity="large-data-box",
            current_step=5,
            total_steps=5,
            collected_data=large_data,
            start_time=datetime.now(),
            last_activity=datetime.now(),
            is_complete=False
        )

        current_memory = tracemalloc.get_traced_memory()[0]
        tracemalloc.stop()

        memory_used_mb = (current_memory - baseline_memory) / (1024 * 1024)

        # Even with large data, should stay under 50MB
        assert memory_used_mb < 50, f"Wizard with large data used {memory_used_mb:.2f}MB"
        assert len(wizard.collected_data) > 0

    def test_wizard_orchestrator_memory_footprint(self):
        """Test WizardOrchestrator instance has minimal memory footprint."""
        tracemalloc.start()
        baseline_memory = tracemalloc.get_traced_memory()[0]

        # Create orchestrator
        orchestrator = WizardOrchestrator()

        current_memory = tracemalloc.get_traced_memory()[0]
        tracemalloc.stop()

        memory_used_mb = (current_memory - baseline_memory) / (1024 * 1024)

        # Orchestrator initialization should use minimal memory
        assert memory_used_mb < 5, f"WizardOrchestrator used {memory_used_mb:.2f}MB (should be <5MB)"

    def test_wizard_state_garbage_collection(self):
        """Test completed wizard states are properly garbage collected."""
        import gc

        tracemalloc.start()
        baseline_memory = tracemalloc.get_traced_memory()[0]

        # Create many wizards
        for i in range(100):
            wizard = WizardState(
                wizard_id=str(uuid4()),
                wizard_type="shelf",
                target_entity=f"gc-test-{i}",
                current_step=5,
                total_steps=5,
                collected_data={},
                start_time=datetime.now(),
                last_activity=datetime.now(),
                is_complete=True  # Completed, should be eligible for cleanup
            )
            # Immediately drop reference
            del wizard

        # Force garbage collection
        gc.collect()

        after_gc_memory = tracemalloc.get_traced_memory()[0]
        tracemalloc.stop()

        memory_used_mb = (after_gc_memory - baseline_memory) / (1024 * 1024)

        # After GC, memory should not have increased significantly
        assert memory_used_mb < 10, f"Memory after 100 deleted wizards: {memory_used_mb:.2f}MB"

    def test_wizard_memory_leak_detection(self):
        """Test for memory leaks in wizard lifecycle."""
        import gc

        tracemalloc.start()

        # Create and complete many wizard lifecycles
        for cycle in range(3):
            wizards = []
            for i in range(10):
                wizard = WizardState(
                    wizard_id=str(uuid4()),
                    wizard_type="mcp",
                    target_entity=f"leak-test-{cycle}-{i}",
                    current_step=1,
                    total_steps=3,
                    collected_data={},
                    start_time=datetime.now(),
                    last_activity=datetime.now(),
                    is_complete=False
                )
                wizards.append(wizard)

            # Simulate completion
            for wizard in wizards:
                wizard.is_complete = True

            # Clear all wizards
            wizards.clear()
            gc.collect()

        final_memory = tracemalloc.get_traced_memory()[0]
        tracemalloc.stop()

        # Memory should not grow unbounded across cycles
        memory_used_mb = final_memory / (1024 * 1024)
        assert memory_used_mb < 100, f"Memory after 3 cycles: {memory_used_mb:.2f}MB (potential leak?)"

    def test_context_service_memory_usage(self):
        """Test ContextService memory usage is reasonable."""
        from src.services.context_service import ContextService

        tracemalloc.start()
        baseline_memory = tracemalloc.get_traced_memory()[0]

        # Create context service
        service = ContextService()

        current_memory = tracemalloc.get_traced_memory()[0]
        tracemalloc.stop()

        memory_used_mb = (current_memory - baseline_memory) / (1024 * 1024)

        assert memory_used_mb < 10, f"ContextService used {memory_used_mb:.2f}MB"

    def test_peak_memory_during_wizard_flow(self):
        """Test peak memory usage during complete wizard flow."""
        tracemalloc.start()

        # Simulate full wizard flow
        wizard = WizardState(
            wizard_id=str(uuid4()),
            wizard_type="shelf",
            target_entity="peak-memory-test",
            current_step=1,
            total_steps=5,
            collected_data={},
            start_time=datetime.now(),
            last_activity=datetime.now(),
            is_complete=False
        )

        # Simulate collecting data through all steps
        for step in range(1, 6):
            wizard.current_step = step
            wizard.collected_data[f"step_{step}"] = f"data for step {step}" * 10
            wizard.last_activity = datetime.now()

        wizard.is_complete = True

        current_memory, peak_memory = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        peak_memory_mb = peak_memory / (1024 * 1024)

        assert peak_memory_mb < 50, f"Peak memory during wizard flow: {peak_memory_mb:.2f}MB"