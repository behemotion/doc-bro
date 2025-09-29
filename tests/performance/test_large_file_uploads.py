"""Performance tests for large file upload operations."""

import pytest
import asyncio
import tempfile
import time
import psutil
import os
from pathlib import Path
from typing import Dict, Any, List
from unittest.mock import Mock, patch, AsyncMock

from src.logic.projects.upload.upload_manager import UploadManager
from src.logic.projects.models.project import Project, ProjectType
from src.logic.projects.models.upload import UploadSource, SourceType


class TestLargeFileUploadPerformance:
    """Test performance of large file uploads."""

    @pytest.fixture
    def upload_manager(self):
        """Create UploadManager instance."""
        return UploadManager()

    @pytest.fixture
    def large_file(self):
        """Create a large test file (100MB)."""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".bin") as f:
            # Write 100MB in chunks to avoid memory issues
            chunk_size = 1024 * 1024  # 1MB chunks
            for _ in range(100):
                f.write(b"x" * chunk_size)
            f.flush()
            yield Path(f.name)
        # Cleanup
        Path(f.name).unlink()

    @pytest.fixture
    def test_project(self):
        """Create test project."""
        return Project(
            id="test-project",
            name="Test Project",
            type=ProjectType.STORAGE,
            settings={"max_file_size": 200 * 1024 * 1024}  # 200MB limit
        )

    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_large_file_upload_under_30_seconds(
        self,
        upload_manager,
        large_file,
        test_project
    ):
        """Test that 100MB file uploads complete in under 30 seconds."""
        source = UploadSource(
            type=SourceType.LOCAL,
            location=str(large_file.parent)
        )

        start_time = time.time()

        result = await upload_manager.upload_files(
            project=test_project,
            source=source,
            files=[str(large_file)]
        )

        elapsed = time.time() - start_time

        assert result["success"] is True
        assert elapsed < 30, f"Upload took {elapsed:.2f} seconds, expected < 30"
        assert result["files_processed"] == 1
        assert result["total_size"] == 100 * 1024 * 1024

    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_multiple_file_upload_performance(
        self,
        upload_manager,
        test_project
    ):
        """Test uploading multiple files concurrently."""
        # Create 10 x 10MB files
        temp_files = []
        with tempfile.TemporaryDirectory() as tmpdir:
            for i in range(10):
                file_path = Path(tmpdir) / f"file_{i}.bin"
                file_path.write_bytes(b"x" * (10 * 1024 * 1024))
                temp_files.append(file_path)

            source = UploadSource(
                type=SourceType.LOCAL,
                location=tmpdir
            )

            start_time = time.time()

            result = await upload_manager.upload_files(
                project=test_project,
                source=source,
                files=[str(f) for f in temp_files],
                concurrent_uploads=3  # Process 3 files at a time
            )

            elapsed = time.time() - start_time

            assert result["success"] is True
            assert elapsed < 30, f"Multi-upload took {elapsed:.2f} seconds"
            assert result["files_processed"] == 10
            assert result["total_size"] == 100 * 1024 * 1024

    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_streaming_upload_memory_efficiency(
        self,
        upload_manager,
        large_file,
        test_project
    ):
        """Test that streaming uploads don't exceed memory limits."""
        source = UploadSource(
            type=SourceType.LOCAL,
            location=str(large_file.parent)
        )

        # Monitor memory usage
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        peak_memory = initial_memory
        memory_samples = []

        async def monitor_memory():
            nonlocal peak_memory
            while True:
                current_memory = process.memory_info().rss / 1024 / 1024
                memory_samples.append(current_memory)
                peak_memory = max(peak_memory, current_memory)
                await asyncio.sleep(0.1)

        # Start memory monitoring
        monitor_task = asyncio.create_task(monitor_memory())

        try:
            result = await upload_manager.upload_files(
                project=test_project,
                source=source,
                files=[str(large_file)],
                stream_chunk_size=1024 * 1024  # 1MB chunks
            )

            assert result["success"] is True

        finally:
            monitor_task.cancel()
            try:
                await monitor_task
            except asyncio.CancelledError:
                pass

        memory_increase = peak_memory - initial_memory

        # Should not load entire file into memory
        assert memory_increase < 100, (
            f"Memory increased by {memory_increase:.2f} MB, "
            "expected < 100 MB for streaming"
        )

    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_upload_progress_reporting_overhead(
        self,
        upload_manager,
        test_project
    ):
        """Test that progress reporting doesn't significantly impact performance."""
        # Create a 50MB file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".bin") as f:
            f.write(b"x" * (50 * 1024 * 1024))
            file_path = Path(f.name)

        try:
            source = UploadSource(
                type=SourceType.LOCAL,
                location=str(file_path.parent)
            )

            progress_updates = []

            def progress_callback(current, total, filename):
                progress_updates.append((current, total, filename))

            # Test with progress reporting
            start_with_progress = time.time()
            result = await upload_manager.upload_files(
                project=test_project,
                source=source,
                files=[str(file_path)],
                progress_callback=progress_callback
            )
            time_with_progress = time.time() - start_with_progress

            # Test without progress reporting
            start_without_progress = time.time()
            result = await upload_manager.upload_files(
                project=test_project,
                source=source,
                files=[str(file_path)]
            )
            time_without_progress = time.time() - start_without_progress

            # Progress reporting overhead should be minimal
            overhead = time_with_progress - time_without_progress
            overhead_percentage = (overhead / time_without_progress) * 100

            assert overhead_percentage < 10, (
                f"Progress reporting added {overhead_percentage:.2f}% overhead"
            )

            # Should have reasonable number of updates
            assert 50 <= len(progress_updates) <= 500, (
                f"Expected 50-500 progress updates, got {len(progress_updates)}"
            )

        finally:
            file_path.unlink()


class TestCLIResponsiveness:
    """Test CLI command responsiveness."""

    # Legacy CLI command performance tests removed
    # These commands have been replaced by the Shelf-Box Rhyme System


class TestMemoryUsageValidation:
    """Test memory usage during various operations."""

    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_upload_memory_usage_stays_bounded(self):
        """Test that memory usage stays within bounds during upload."""
        upload_manager = UploadManager()

        # Create multiple 10MB files
        with tempfile.TemporaryDirectory() as tmpdir:
            files = []
            for i in range(5):
                file_path = Path(tmpdir) / f"file_{i}.bin"
                file_path.write_bytes(b"x" * (10 * 1024 * 1024))
                files.append(file_path)

            project = Project(
                id="mem-test",
                name="Memory Test",
                type=ProjectType.STORAGE
            )

            source = UploadSource(
                type=SourceType.LOCAL,
                location=tmpdir
            )

            # Monitor memory during upload
            process = psutil.Process()
            initial_memory = process.memory_info().rss / 1024 / 1024

            memory_samples = []

            async def upload_with_monitoring():
                for _ in range(10):  # Sample 10 times during upload
                    await asyncio.sleep(0.1)
                    current_memory = process.memory_info().rss / 1024 / 1024
                    memory_samples.append(current_memory)

            # Run upload and monitoring concurrently
            upload_task = asyncio.create_task(
                upload_manager.upload_files(
                    project=project,
                    source=source,
                    files=[str(f) for f in files]
                )
            )
            monitor_task = asyncio.create_task(upload_with_monitoring())

            result, _ = await asyncio.gather(upload_task, monitor_task)

            assert result["success"] is True

            # Check memory stayed reasonable
            max_memory = max(memory_samples) if memory_samples else initial_memory
            memory_increase = max_memory - initial_memory

            assert memory_increase < 512, (
                f"Memory increased by {memory_increase:.2f} MB during upload"
            )

    @pytest.mark.performance
    def test_file_validation_memory_efficiency(self):
        """Test that file validation doesn't load entire files into memory."""
        from src.logic.projects.upload.validators.format_validator import FileValidator

        validator = FileValidator()

        # Create a 100MB test file
        with tempfile.NamedTemporaryFile(suffix=".bin", delete=False) as f:
            for _ in range(100):
                f.write(b"x" * (1024 * 1024))
            file_path = Path(f.name)

        try:
            process = psutil.Process()
            initial_memory = process.memory_info().rss / 1024 / 1024

            # Validate file (should not load entire content)
            result = validator.validate_file(
                file_path,
                {"allowed_formats": ["bin"], "quick_validation": True}
            )

            final_memory = process.memory_info().rss / 1024 / 1024
            memory_increase = final_memory - initial_memory

            assert result["valid"] is True
            assert memory_increase < 10, (
                f"Validation increased memory by {memory_increase:.2f} MB"
            )

        finally:
            file_path.unlink()


class TestNetworkFailureRetryLogic:
    """Test network failure handling and retry logic."""

    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_http_download_retry_performance(self):
        """Test that retry logic doesn't significantly impact performance."""
        from src.logic.projects.upload.sources.http_source import HTTPSource

        http_source = HTTPSource()

        # Mock HTTP client with controlled failures
        with patch("httpx.AsyncClient.get") as mock_get:
            # First attempt fails, second succeeds
            mock_get.side_effect = [
                Exception("Connection timeout"),
                Mock(
                    status_code=200,
                    content=b"content",
                    headers={"content-length": "7"}
                )
            ]

            start_time = time.time()

            with tempfile.NamedTemporaryFile() as tmp:
                result = await http_source.download_with_retry(
                    "https://example.com/file",
                    Path(tmp.name),
                    max_retries=3,
                    retry_delay=0.1  # Short delay for testing
                )

            elapsed = time.time() - start_time

            assert result["success"] is True
            assert result["attempts"] == 2
            assert elapsed < 2.0, f"Retry took {elapsed:.2f} seconds"

    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_concurrent_retry_handling(self):
        """Test handling multiple retrying downloads concurrently."""
        from src.logic.projects.upload.sources.http_source import HTTPSource

        http_source = HTTPSource()

        # Create multiple downloads with failures
        urls = [f"https://example.com/file{i}.pdf" for i in range(5)]

        with patch("httpx.AsyncClient.get") as mock_get:
            # Each file fails once then succeeds
            def side_effect(*args, **kwargs):
                if not hasattr(side_effect, "call_count"):
                    side_effect.call_count = 0
                side_effect.call_count += 1

                if side_effect.call_count % 2 == 1:
                    raise Exception("Connection error")
                return Mock(
                    status_code=200,
                    content=b"content",
                    headers={"content-length": "7"}
                )

            mock_get.side_effect = side_effect

            start_time = time.time()

            with tempfile.TemporaryDirectory() as tmpdir:
                tasks = []
                for url in urls:
                    dest = Path(tmpdir) / Path(url).name
                    task = http_source.download_with_retry(
                        url,
                        dest,
                        max_retries=3,
                        retry_delay=0.1
                    )
                    tasks.append(task)

                results = await asyncio.gather(*tasks)

            elapsed = time.time() - start_time

            # All should succeed
            assert all(r["success"] for r in results)
            # Should complete reasonably quickly despite retries
            assert elapsed < 5.0, f"Concurrent retries took {elapsed:.2f} seconds"


class TestProjectCleanupPerformance:
    """Test project cleanup and removal performance."""

    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_project_removal_completeness(self):
        """Test that project removal cleans up all resources."""
        from src.logic.projects.core.project_manager import ProjectManager

        manager = ProjectManager()

        # Create test project with files
        with tempfile.TemporaryDirectory() as project_dir:
            project = await manager.create_project(
                name="cleanup-test",
                type=ProjectType.STORAGE,
                data_dir=Path(project_dir)
            )

            # Add test files to project
            for i in range(10):
                file_path = Path(project_dir) / f"file_{i}.txt"
                file_path.write_text(f"content {i}")

            # Create database entries
            await manager.add_file_to_project(
                project,
                file_path,
                {"size": 100, "mime_type": "text/plain"}
            )

            start_time = time.time()

            # Remove project
            result = await manager.remove_project(
                project.name,
                cleanup_files=True,
                cleanup_database=True
            )

            elapsed = time.time() - start_time

            assert result["success"] is True
            assert elapsed < 2.0, f"Cleanup took {elapsed:.2f} seconds"

            # Verify cleanup
            assert not Path(project_dir).exists() or not any(Path(project_dir).iterdir())
            assert result["files_removed"] == 10
            assert result["database_cleaned"] is True

    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_batch_project_cleanup(self):
        """Test cleaning up multiple projects efficiently."""
        from src.logic.projects.core.project_manager import ProjectManager

        manager = ProjectManager()

        # Create multiple test projects
        projects = []
        with tempfile.TemporaryDirectory() as base_dir:
            for i in range(5):
                project_dir = Path(base_dir) / f"project_{i}"
                project_dir.mkdir()

                project = await manager.create_project(
                    name=f"batch-test-{i}",
                    type=ProjectType.STORAGE,
                    data_dir=project_dir
                )
                projects.append(project)

                # Add some files
                for j in range(5):
                    file_path = project_dir / f"file_{j}.txt"
                    file_path.write_text(f"content {j}")

            start_time = time.time()

            # Remove all projects
            tasks = [
                manager.remove_project(p.name, cleanup_files=True)
                for p in projects
            ]
            results = await asyncio.gather(*tasks)

            elapsed = time.time() - start_time

            # All should succeed
            assert all(r["success"] for r in results)
            # Should complete quickly
            assert elapsed < 5.0, f"Batch cleanup took {elapsed:.2f} seconds"

            # Verify all cleaned up
            for project_dir in Path(base_dir).iterdir():
                assert not any(project_dir.iterdir()), (
                    f"Project directory {project_dir} not cleaned"
                )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "performance"])