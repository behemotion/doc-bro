"""Integration test for performance validation (<100ms creation, <50ms listing) (T015)."""

import pytest
import time
from datetime import datetime
from typing import List

from src.models.unified_project import UnifiedProject, UnifiedProjectStatus
from src.models.compatibility_status import CompatibilityStatus
from src.models.schema_version import SchemaVersion
from src.logic.projects.models.project import ProjectType


class TestUnifiedSchemaPerformance:
    """Test performance requirements for unified schema operations."""

    @pytest.fixture
    def sample_projects(self) -> List[UnifiedProject]:
        """Create sample projects for performance testing."""
        projects = []

        # Create projects of different types and compatibility states
        for i in range(100):
            project_type = [ProjectType.CRAWLING, ProjectType.DATA, ProjectType.STORAGE][i % 3]
            schema_version = [3, 1, 2, 3][i % 4]  # Mix of compatible and incompatible

            project = UnifiedProject(
                name=f"perf-test-project-{i:03d}",
                type=project_type,
                schema_version=schema_version,
                source_url=f"https://example{i}.com/docs" if project_type == ProjectType.CRAWLING else None,
                settings={
                    "crawl_depth": 3 if project_type == ProjectType.CRAWLING else None,
                    "chunk_size": 500 if project_type == ProjectType.DATA else None,
                    "enable_compression": True if project_type == ProjectType.STORAGE else None
                },
                statistics={
                    "total_pages": i * 10,
                    "successful_pages": i * 9,
                    "failed_pages": i
                } if i % 2 == 0 else {},
                metadata={
                    "description": f"Performance test project {i}",
                    "tags": ["performance", "test", f"batch-{i // 20}"],
                    "priority": "high" if i % 10 == 0 else "normal"
                }
            )
            projects.append(project)

        return projects

    def test_project_creation_performance(self):
        """Test that project creation takes <100ms per project."""
        # Target: <100ms per project creation
        max_creation_time_ms = 100

        # Test different project types
        test_cases = [
            {
                "name": "creation-perf-crawling",
                "type": ProjectType.CRAWLING,
                "source_url": "https://performance.example.com",
                "settings": {
                    "crawl_depth": 5,
                    "rate_limit": 2.0,
                    "user_agent": "DocBro/1.0",
                    "max_file_size": 10485760
                },
                "metadata": {
                    "description": "Performance test crawling project",
                    "tags": ["performance", "crawling"],
                    "owner": "test-suite"
                }
            },
            {
                "name": "creation-perf-data",
                "type": ProjectType.DATA,
                "settings": {
                    "chunk_size": 1000,
                    "chunk_overlap": 100,
                    "embedding_model": "mxbai-embed-large",
                    "vector_store_type": "sqlite_vec"
                },
                "metadata": {
                    "description": "Performance test data project",
                    "tags": ["performance", "data"],
                    "processing_config": {"batch_size": 100}
                }
            },
            {
                "name": "creation-perf-storage",
                "type": ProjectType.STORAGE,
                "settings": {
                    "enable_compression": True,
                    "auto_tagging": True,
                    "full_text_indexing": True,
                    "max_file_size": 104857600
                },
                "metadata": {
                    "description": "Performance test storage project",
                    "tags": ["performance", "storage"],
                    "storage_config": {"retention_days": 365}
                }
            }
        ]

        creation_times = []

        for test_case in test_cases:
            start_time = time.perf_counter()

            # Create project
            project = UnifiedProject(**test_case)

            end_time = time.perf_counter()
            creation_time_ms = (end_time - start_time) * 1000
            creation_times.append(creation_time_ms)

            # Verify project was created correctly
            assert project.name == test_case["name"]
            assert project.type == test_case["type"]
            assert project.schema_version == SchemaVersion.CURRENT_VERSION
            assert project.is_compatible()

            # Verify performance requirement
            assert creation_time_ms < max_creation_time_ms, (
                f"Project creation took {creation_time_ms:.2f}ms, "
                f"which exceeds the {max_creation_time_ms}ms requirement"
            )

        # Statistical analysis
        avg_creation_time = sum(creation_times) / len(creation_times)
        max_creation_time = max(creation_times)

        print(f"Project creation performance:")
        print(f"  Average: {avg_creation_time:.2f}ms")
        print(f"  Maximum: {max_creation_time:.2f}ms")
        print(f"  Target: <{max_creation_time_ms}ms")

        assert avg_creation_time < max_creation_time_ms * 0.5, (
            f"Average creation time {avg_creation_time:.2f}ms should be well below limit"
        )

    def test_project_listing_performance(self, sample_projects):
        """Test that project listing takes <50ms for 100 projects."""
        # Target: <50ms for listing 100 projects
        max_listing_time_ms = 50

        # Simulate project listing operation
        start_time = time.perf_counter()

        # Generate project summaries (simulating database query + processing)
        project_summaries = []
        for project in sample_projects:
            summary = project.to_summary()
            # Add compatibility information (simulating service layer processing)
            summary.update({
                "is_compatible": project.is_compatible(),
                "allows_modification": project.allows_modification(),
                "needs_recreation": project.needs_recreation(),
                "schema_version": project.schema_version
            })
            project_summaries.append(summary)

        end_time = time.perf_counter()
        listing_time_ms = (end_time - start_time) * 1000

        # Verify listing results
        assert len(project_summaries) == 100

        # Count compatible vs incompatible projects
        compatible_count = sum(1 for summary in project_summaries if summary["is_compatible"])
        incompatible_count = len(project_summaries) - compatible_count

        # Verify performance requirement
        assert listing_time_ms < max_listing_time_ms, (
            f"Project listing took {listing_time_ms:.2f}ms, "
            f"which exceeds the {max_listing_time_ms}ms requirement"
        )

        print(f"Project listing performance:")
        print(f"  Time: {listing_time_ms:.2f}ms")
        print(f"  Target: <{max_listing_time_ms}ms")
        print(f"  Projects listed: {len(project_summaries)}")
        print(f"  Compatible: {compatible_count}")
        print(f"  Incompatible: {incompatible_count}")

    def test_compatibility_checking_performance(self, sample_projects):
        """Test that compatibility checking is fast (<10ms per project)."""
        # Target: <10ms per compatibility check
        max_check_time_ms = 10

        check_times = []

        for project in sample_projects[:20]:  # Test subset for individual timing
            start_time = time.perf_counter()

            # Perform compatibility checks
            is_compatible = project.is_compatible()
            allows_modification = project.allows_modification()
            needs_recreation = project.needs_recreation()
            compatibility_status = project.compatibility_status

            end_time = time.perf_counter()
            check_time_ms = (end_time - start_time) * 1000
            check_times.append(check_time_ms)

            # Verify check worked correctly
            if project.schema_version == SchemaVersion.CURRENT_VERSION:
                assert is_compatible
                assert allows_modification
                assert not needs_recreation
                assert compatibility_status == CompatibilityStatus.COMPATIBLE
            else:
                assert not is_compatible
                assert not allows_modification
                assert needs_recreation
                assert compatibility_status == CompatibilityStatus.INCOMPATIBLE

            # Verify performance requirement
            assert check_time_ms < max_check_time_ms, (
                f"Compatibility check took {check_time_ms:.2f}ms, "
                f"which exceeds the {max_check_time_ms}ms requirement"
            )

        avg_check_time = sum(check_times) / len(check_times)
        max_check_time = max(check_times)

        print(f"Compatibility checking performance:")
        print(f"  Average: {avg_check_time:.2f}ms")
        print(f"  Maximum: {max_check_time:.2f}ms")
        print(f"  Target: <{max_check_time_ms}ms")

    def test_schema_validation_performance(self):
        """Test that schema validation is fast (<20ms)."""
        # Target: <20ms for schema validation
        max_validation_time_ms = 20

        # Test complex project with extensive validation
        complex_project_data = {
            "name": "complex-validation-test",
            "type": ProjectType.DATA,
            "settings": {
                "chunk_size": 1500,
                "chunk_overlap": 150,
                "embedding_model": "complex-model-name-with-long-identifier",
                "vector_store_type": "sqlite_vec",
                "enable_preprocessing": True,
                "preprocessing_steps": ["tokenization", "normalization", "deduplication"],
                "batch_size": 1000,
                "parallel_processing": True,
                "custom_embeddings": {
                    "provider": "custom",
                    "config": {"dimension": 768, "metric": "cosine"}
                }
            },
            "metadata": {
                "description": "Complex project for validation performance testing with extensive metadata",
                "tags": ["performance", "validation", "complex", "testing", "metadata"],
                "owner": "performance-test-suite",
                "project_config": {
                    "data_sources": ["source1", "source2", "source3"],
                    "processing_pipeline": ["step1", "step2", "step3", "step4"],
                    "output_formats": ["json", "parquet", "csv"]
                },
                "compliance": {
                    "data_retention": "365 days",
                    "privacy_level": "high",
                    "encryption": "AES-256"
                }
            },
            "statistics": {
                "total_documents": 50000,
                "processed_documents": 45000,
                "failed_documents": 1000,
                "skipped_documents": 4000,
                "total_size_bytes": 524288000,
                "processing_time_seconds": 3600,
                "average_document_size": 10485
            }
        }

        start_time = time.perf_counter()

        # Create project (triggers all validation)
        project = UnifiedProject(**complex_project_data)

        end_time = time.perf_counter()
        validation_time_ms = (end_time - start_time) * 1000

        # Verify project was created correctly
        assert project.name == "complex-validation-test"
        assert project.type == ProjectType.DATA
        assert project.is_compatible()
        assert len(project.settings) > 5
        assert len(project.metadata) > 5
        assert len(project.statistics) > 5

        # Verify performance requirement
        assert validation_time_ms < max_validation_time_ms, (
            f"Schema validation took {validation_time_ms:.2f}ms, "
            f"which exceeds the {max_validation_time_ms}ms requirement"
        )

        print(f"Schema validation performance:")
        print(f"  Time: {validation_time_ms:.2f}ms")
        print(f"  Target: <{max_validation_time_ms}ms")

    def test_serialization_performance(self, sample_projects):
        """Test that serialization/deserialization performance is acceptable."""
        # Target: Batch serialization should be fast
        max_serialization_time_ms = 100  # For 100 projects

        # Test to_dict() performance
        start_time = time.perf_counter()

        serialized_projects = []
        for project in sample_projects:
            project_dict = project.to_dict()
            serialized_projects.append(project_dict)

        end_time = time.perf_counter()
        serialization_time_ms = (end_time - start_time) * 1000

        # Test from_dict() performance
        start_time = time.perf_counter()

        deserialized_projects = []
        for project_dict in serialized_projects:
            project = UnifiedProject.from_dict(project_dict)
            deserialized_projects.append(project)

        end_time = time.perf_counter()
        deserialization_time_ms = (end_time - start_time) * 1000

        total_time_ms = serialization_time_ms + deserialization_time_ms

        # Verify results
        assert len(serialized_projects) == 100
        assert len(deserialized_projects) == 100

        # Verify a few projects were deserialized correctly
        for i in [0, 25, 50, 75, 99]:
            original = sample_projects[i]
            restored = deserialized_projects[i]
            assert original.name == restored.name
            assert original.type == restored.type
            assert original.schema_version == restored.schema_version

        # Verify performance requirements
        assert serialization_time_ms < max_serialization_time_ms, (
            f"Serialization took {serialization_time_ms:.2f}ms, "
            f"which exceeds the {max_serialization_time_ms}ms requirement"
        )

        assert deserialization_time_ms < max_serialization_time_ms, (
            f"Deserialization took {deserialization_time_ms:.2f}ms, "
            f"which exceeds the {max_serialization_time_ms}ms requirement"
        )

        print(f"Serialization performance:")
        print(f"  Serialization: {serialization_time_ms:.2f}ms")
        print(f"  Deserialization: {deserialization_time_ms:.2f}ms")
        print(f"  Total: {total_time_ms:.2f}ms")
        print(f"  Target: <{max_serialization_time_ms}ms each")

    def test_memory_usage_efficiency(self, sample_projects):
        """Test that memory usage is reasonable for many projects."""
        import sys

        # Measure memory usage of project objects
        def get_size(obj):
            """Recursively calculate size of objects."""
            size = sys.getsizeof(obj)
            if isinstance(obj, dict):
                size += sum(get_size(k) + get_size(v) for k, v in obj.items())
            elif isinstance(obj, (list, tuple)):
                size += sum(get_size(item) for item in obj)
            elif hasattr(obj, '__dict__'):
                size += get_size(obj.__dict__)
            return size

        # Calculate total memory usage
        total_memory_bytes = sum(get_size(project) for project in sample_projects)
        average_memory_per_project = total_memory_bytes / len(sample_projects)

        # Memory targets (reasonable limits)
        max_memory_per_project_kb = 50  # 50KB per project should be reasonable
        max_total_memory_mb = 10  # 10MB for 100 projects should be reasonable

        memory_per_project_kb = average_memory_per_project / 1024
        total_memory_mb = total_memory_bytes / (1024 * 1024)

        print(f"Memory usage:")
        print(f"  Average per project: {memory_per_project_kb:.2f} KB")
        print(f"  Total for 100 projects: {total_memory_mb:.2f} MB")
        print(f"  Target per project: <{max_memory_per_project_kb} KB")
        print(f"  Target total: <{max_total_memory_mb} MB")

        # Verify memory efficiency
        assert memory_per_project_kb < max_memory_per_project_kb, (
            f"Memory usage per project ({memory_per_project_kb:.2f} KB) "
            f"exceeds target ({max_memory_per_project_kb} KB)"
        )

        assert total_memory_mb < max_total_memory_mb, (
            f"Total memory usage ({total_memory_mb:.2f} MB) "
            f"exceeds target ({max_total_memory_mb} MB)"
        )

    def test_concurrent_access_performance(self, sample_projects):
        """Test performance under simulated concurrent access."""
        import threading
        import queue

        # Simulate concurrent read operations
        results_queue = queue.Queue()
        num_threads = 10
        operations_per_thread = 20

        def worker():
            """Worker function for concurrent operations."""
            thread_times = []
            for i in range(operations_per_thread):
                project = sample_projects[i % len(sample_projects)]

                start_time = time.perf_counter()

                # Perform various read operations
                _ = project.is_compatible()
                _ = project.to_summary()
                _ = project.to_dict()
                _ = project.get_default_settings()

                end_time = time.perf_counter()
                operation_time_ms = (end_time - start_time) * 1000
                thread_times.append(operation_time_ms)

            results_queue.put(thread_times)

        # Start concurrent operations
        start_time = time.perf_counter()

        threads = []
        for _ in range(num_threads):
            thread = threading.Thread(target=worker)
            threads.append(thread)
            thread.start()

        # Wait for completion
        for thread in threads:
            thread.join()

        end_time = time.perf_counter()
        total_concurrent_time_ms = (end_time - start_time) * 1000

        # Collect results
        all_operation_times = []
        while not results_queue.empty():
            thread_times = results_queue.get()
            all_operation_times.extend(thread_times)

        # Performance analysis
        total_operations = num_threads * operations_per_thread
        avg_operation_time = sum(all_operation_times) / len(all_operation_times)
        max_operation_time = max(all_operation_times)

        # Performance targets for concurrent access
        max_avg_operation_time_ms = 20  # Average operation should be fast
        max_single_operation_time_ms = 100  # No single operation should be too slow

        print(f"Concurrent access performance:")
        print(f"  Total operations: {total_operations}")
        print(f"  Total time: {total_concurrent_time_ms:.2f}ms")
        print(f"  Average operation time: {avg_operation_time:.2f}ms")
        print(f"  Maximum operation time: {max_operation_time:.2f}ms")
        print(f"  Operations per second: {total_operations / (total_concurrent_time_ms / 1000):.0f}")

        # Verify performance requirements
        assert avg_operation_time < max_avg_operation_time_ms, (
            f"Average concurrent operation time ({avg_operation_time:.2f}ms) "
            f"exceeds target ({max_avg_operation_time_ms}ms)"
        )

        assert max_operation_time < max_single_operation_time_ms, (
            f"Maximum concurrent operation time ({max_operation_time:.2f}ms) "
            f"exceeds target ({max_single_operation_time_ms}ms)"
        )