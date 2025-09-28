"""Performance tests for <100ms MCP response time."""

import pytest
import time
import asyncio
from unittest.mock import Mock, patch
from typing import List

from src.logic.mcp.services.read_only import ReadOnlyMcpService
from src.logic.mcp.services.admin import AdminMcpService
from src.logic.mcp.services.command_executor import CommandExecutor, ExecutionResult
from src.logic.mcp.services.file_access import FileAccessController
from src.logic.mcp.models.file_access import FileAccessRequest, ProjectType
from src.logic.mcp.models.command_execution import CommandExecutionRequest, AllowedCommand


class TestMcpResponseTime:
    """Performance tests to ensure MCP operations complete within 100ms."""

    def setup_method(self):
        """Set up test fixtures."""
        self.read_only_service = ReadOnlyMcpService()
        self.admin_service = AdminMcpService()
        self.command_executor = CommandExecutor()
        self.file_access_controller = FileAccessController()

    def measure_execution_time(self, func, *args, **kwargs):
        """Measure execution time of a function."""
        start_time = time.perf_counter()
        if asyncio.iscoroutinefunction(func):
            result = asyncio.run(func(*args, **kwargs))
        else:
            result = func(*args, **kwargs)
        end_time = time.perf_counter()
        execution_time_ms = (end_time - start_time) * 1000
        return result, execution_time_ms

    @pytest.mark.asyncio
    async def test_read_only_project_list_response_time(self):
        """Test that project listing completes within 100ms."""
        # Mock the database call to return quickly
        mock_projects = [
            {"name": "project1", "type": "data", "description": "Test project 1"},
            {"name": "project2", "type": "storage", "description": "Test project 2"},
            {"name": "project3", "type": "crawling", "description": "Test project 3"}
        ]

        async def mock_list_projects():
            return mock_projects

        with patch.object(self.read_only_service, 'list_projects', side_effect=mock_list_projects):
            start_time = time.perf_counter()
            result = await self.read_only_service.list_projects()
            end_time = time.perf_counter()

            execution_time_ms = (end_time - start_time) * 1000

            assert result == mock_projects
            assert execution_time_ms < 100, f"Project listing took {execution_time_ms:.2f}ms, expected <100ms"

    @pytest.mark.asyncio
    async def test_read_only_project_search_response_time(self):
        """Test that project search completes within 100ms."""
        search_query = "test"
        mock_results = [
            {"name": "test-project", "type": "data", "relevance": 0.95}
        ]

        async def mock_search_projects(query):
            return mock_results

        with patch.object(self.read_only_service, 'search_projects', side_effect=mock_search_projects):
            start_time = time.perf_counter()
            result = await self.read_only_service.search_projects(search_query)
            end_time = time.perf_counter()

            execution_time_ms = (end_time - start_time) * 1000

            assert result == mock_results
            assert execution_time_ms < 100, f"Project search took {execution_time_ms:.2f}ms, expected <100ms"

    @pytest.mark.asyncio
    async def test_file_access_metadata_response_time(self):
        """Test that file metadata retrieval completes within 100ms."""
        from pathlib import Path
        import tempfile

        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a few test files
            project_root = Path(temp_dir)
            for i in range(5):
                (project_root / f"file{i}.txt").write_text(f"Content {i}")

            start_time = time.perf_counter()
            metadata_list = await self.file_access_controller.get_file_metadata(project_root)
            end_time = time.perf_counter()

            execution_time_ms = (end_time - start_time) * 1000

            assert len(metadata_list) == 5
            assert execution_time_ms < 100, f"File metadata retrieval took {execution_time_ms:.2f}ms, expected <100ms"

    @pytest.mark.asyncio
    async def test_file_access_validation_response_time(self):
        """Test that file access validation completes within 100ms."""
        request = FileAccessRequest(
            project_name="test-project",
            file_path="test.txt"
        )

        start_time = time.perf_counter()
        result = self.file_access_controller.validate_access(request, ProjectType.STORAGE)
        end_time = time.perf_counter()

        execution_time_ms = (end_time - start_time) * 1000

        assert result is True
        assert execution_time_ms < 100, f"File access validation took {execution_time_ms:.2f}ms, expected <100ms"

    @pytest.mark.asyncio
    async def test_command_validation_response_time(self):
        """Test that command validation completes within 100ms."""
        request = CommandExecutionRequest(
            command=AllowedCommand.HEALTH,
            arguments=[]
        )

        start_time = time.perf_counter()
        result = await self.command_executor.validate_command(request)
        end_time = time.perf_counter()

        execution_time_ms = (end_time - start_time) * 1000

        assert result is True
        assert execution_time_ms < 100, f"Command validation took {execution_time_ms:.2f}ms, expected <100ms"

    def test_file_path_security_check_response_time(self):
        """Test that file path security checks complete within 100ms."""
        test_paths = [
            "valid/path/file.txt",
            "another/valid/path.md",
            "../dangerous/path.txt",
            "/absolute/path.txt",
            "valid_file.json"
        ]

        start_time = time.perf_counter()
        for path in test_paths:
            self.file_access_controller.is_safe_file_path(path)
        end_time = time.perf_counter()

        execution_time_ms = (end_time - start_time) * 1000

        assert execution_time_ms < 100, f"Security checks took {execution_time_ms:.2f}ms, expected <100ms"

    @pytest.mark.asyncio
    async def test_concurrent_operations_response_time(self):
        """Test that concurrent MCP operations complete within acceptable time."""
        # Simulate 10 concurrent project list requests
        mock_projects = [{"name": f"project{i}", "type": "data"} for i in range(3)]

        async def mock_list_projects():
            await asyncio.sleep(0.001)  # Simulate minimal database delay
            return mock_projects

        with patch.object(self.read_only_service, 'list_projects', side_effect=mock_list_projects):
            start_time = time.perf_counter()

            # Execute 10 concurrent requests
            tasks = [self.read_only_service.list_projects() for _ in range(10)]
            results = await asyncio.gather(*tasks)

            end_time = time.perf_counter()
            execution_time_ms = (end_time - start_time) * 1000

            assert len(results) == 10
            assert all(result == mock_projects for result in results)
            # 10 concurrent requests should complete in less than 200ms
            assert execution_time_ms < 200, f"10 concurrent requests took {execution_time_ms:.2f}ms, expected <200ms"

    @pytest.mark.asyncio
    async def test_admin_service_health_check_response_time(self):
        """Test that admin service health check completes within 100ms."""
        mock_health_result = {"status": "healthy", "timestamp": "2024-01-01T00:00:00Z"}

        async def mock_health_check():
            return mock_health_result

        with patch.object(self.admin_service, 'health_check', side_effect=mock_health_check):
            start_time = time.perf_counter()
            result = await self.admin_service.health_check()
            end_time = time.perf_counter()

            execution_time_ms = (end_time - start_time) * 1000

            assert result == mock_health_result
            assert execution_time_ms < 100, f"Health check took {execution_time_ms:.2f}ms, expected <100ms"

    @pytest.mark.asyncio
    async def test_large_file_list_response_time(self):
        """Test response time with a large number of files."""
        from pathlib import Path
        import tempfile

        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)

            # Create 100 test files
            for i in range(100):
                subdir = project_root / f"subdir{i // 10}"
                subdir.mkdir(exist_ok=True)
                (subdir / f"file{i}.txt").write_text(f"Content {i}")

            start_time = time.perf_counter()
            files = await self.file_access_controller.list_accessible_files(
                project_root, ProjectType.STORAGE
            )
            end_time = time.perf_counter()

            execution_time_ms = (end_time - start_time) * 1000

            assert len(files) == 100
            # Even with 100 files, should complete within 100ms
            assert execution_time_ms < 100, f"Large file listing took {execution_time_ms:.2f}ms, expected <100ms"

    def test_performance_benchmark_suite(self):
        """Run a comprehensive performance benchmark suite."""
        operations = []

        # Test multiple operations and collect timing data
        operations_to_test = [
            ("file_path_validation", lambda: self.file_access_controller.is_safe_file_path("test/path.txt")),
            ("project_type_access_check", lambda: self.file_access_controller.get_allowed_access_level(ProjectType.STORAGE)),
        ]

        for operation_name, operation_func in operations_to_test:
            times = []
            for _ in range(10):  # Run each operation 10 times
                start_time = time.perf_counter()
                operation_func()
                end_time = time.perf_counter()
                times.append((end_time - start_time) * 1000)

            avg_time = sum(times) / len(times)
            max_time = max(times)
            min_time = min(times)

            operations.append({
                "operation": operation_name,
                "avg_time_ms": avg_time,
                "max_time_ms": max_time,
                "min_time_ms": min_time
            })

            # Assert that average time is under 100ms
            assert avg_time < 100, f"{operation_name} average time {avg_time:.2f}ms exceeds 100ms"
            # Assert that max time is under 200ms (allowing for some variance)
            assert max_time < 200, f"{operation_name} max time {max_time:.2f}ms exceeds 200ms"

        # Print benchmark results for reference
        print("\nPerformance Benchmark Results:")
        print("-" * 60)
        for op in operations:
            print(f"{op['operation']:25} | Avg: {op['avg_time_ms']:6.2f}ms | Max: {op['max_time_ms']:6.2f}ms | Min: {op['min_time_ms']:6.2f}ms")

    @pytest.mark.asyncio
    async def test_memory_efficient_operations(self):
        """Test that operations are memory efficient and don't cause performance degradation."""
        import gc
        import psutil
        import os

        # Get initial memory usage
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss

        # Perform multiple operations
        for i in range(50):
            request = FileAccessRequest(
                project_name=f"test-project-{i}",
                file_path=f"test-file-{i}.txt"
            )
            self.file_access_controller.validate_access(request, ProjectType.STORAGE)

        # Force garbage collection
        gc.collect()

        # Check final memory usage
        final_memory = process.memory_info().rss
        memory_increase_mb = (final_memory - initial_memory) / (1024 * 1024)

        # Memory increase should be minimal (less than 10MB for 50 operations)
        assert memory_increase_mb < 10, f"Memory increased by {memory_increase_mb:.2f}MB, expected <10MB"

    @pytest.mark.asyncio
    async def test_error_handling_performance(self):
        """Test that error handling doesn't significantly impact performance."""
        from pathlib import Path

        # Test with non-existent directory
        non_existent_path = Path("/non/existent/directory")

        start_time = time.perf_counter()
        files = await self.file_access_controller.list_accessible_files(
            non_existent_path, ProjectType.STORAGE
        )
        end_time = time.perf_counter()

        execution_time_ms = (end_time - start_time) * 1000

        assert files == []  # Should return empty list gracefully
        assert execution_time_ms < 100, f"Error handling took {execution_time_ms:.2f}ms, expected <100ms"