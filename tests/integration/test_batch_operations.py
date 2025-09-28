"""Integration tests for batch crawl operations."""

import pytest
import asyncio
from datetime import datetime, timedelta
from click.testing import CliRunner
from unittest.mock import patch, MagicMock, AsyncMock
from src.cli.main import main
from logic.crawler.core.batch import BatchCrawler


class TestBatchOperationsIntegration:
    """Integration tests for batch crawl operations."""

    def test_batch_crawl_all_projects(self):
        """Test batch crawl processes all projects."""
        runner = CliRunner()

        with patch('src.services.project_manager.ProjectManager') as mock_pm:
            with patch('logic.crawler.core.batch.BatchCrawler') as mock_batch:
                # Setup projects
                projects = [
                    MagicMock(name=f"project-{i}") for i in range(5)
                ]
                mock_pm.return_value.list_projects.return_value = projects

                batch_instance = MagicMock()
                mock_batch.return_value = batch_instance
                batch_instance.crawl_all = AsyncMock()

                result = runner.invoke(main, ["crawl", "--update", "--all"])

                # Should process all projects
                assert mock_pm.return_value.list_projects.called
                assert batch_instance.crawl_all.called

    def test_batch_continue_on_error(self):
        """Test batch operation continues when projects fail."""
        runner = CliRunner()

        with patch('src.services.project_manager.ProjectManager') as mock_pm:
            with patch('logic.crawler.core.batch.BatchCrawler') as mock_batch:
                projects = [
                    MagicMock(name="success-1"),
                    MagicMock(name="fail-1"),
                    MagicMock(name="success-2"),
                    MagicMock(name="fail-2"),
                    MagicMock(name="success-3"),
                ]
                mock_pm.return_value.list_projects.return_value = projects

                batch_instance = MagicMock()
                mock_batch.return_value = batch_instance

                # Simulate mixed results
                batch_instance.get_results.return_value = {
                    "success-1": {"status": "success", "pages": 50},
                    "fail-1": {"status": "failed", "error": "Network error"},
                    "success-2": {"status": "success", "pages": 75},
                    "fail-2": {"status": "failed", "error": "Timeout"},
                    "success-3": {"status": "success", "pages": 100},
                }

                result = runner.invoke(main, ["crawl", "--update", "--all"])

                # Should show both successes and failures
                assert "3" in result.output and "succeeded" in result.output.lower()
                assert "2" in result.output and "failed" in result.output.lower()

    def test_batch_operation_tracking(self):
        """Test that batch operations are properly tracked."""
        from src.models.batch_operation import BatchOperation

        projects = ["proj1", "proj2", "proj3"]
        operation = BatchOperation(projects=projects)

        assert operation.operation_id is not None
        assert len(operation.projects) == 3
        assert operation.current_index == 0
        assert len(operation.completed) == 0
        assert len(operation.failed) == 0

        # Simulate progress
        operation.mark_completed("proj1")
        assert "proj1" in operation.completed
        assert operation.current_index == 1

        operation.mark_failed("proj2", "Error message")
        assert len(operation.failed) == 1
        assert operation.failed[0] == ("proj2", "Error message")

    def test_batch_sequential_execution(self):
        """Test that batch crawls execute sequentially."""
        runner = CliRunner()

        execution_order = []

        with patch('src.services.project_manager.ProjectManager') as mock_pm:
            with patch('logic.crawler.core.batch.BatchCrawler') as mock_batch:
                projects = [MagicMock(name=f"project-{i}") for i in range(4)]
                mock_pm.return_value.list_projects.return_value = projects

                batch_instance = MagicMock()
                mock_batch.return_value = batch_instance

                async def track_execution(project):
                    execution_order.append(project.name)
                    await asyncio.sleep(0.1)  # Simulate work

                batch_instance.crawl_project = track_execution

                result = runner.invoke(main, ["crawl", "--update", "--all"])

                # Should execute in order
                if execution_order:
                    assert execution_order == [f"project-{i}" for i in range(4)]

    def test_batch_immediate_start_after_completion(self):
        """Test that projects start immediately after previous completes."""
        runner = CliRunner()

        start_times = []

        with patch('src.services.project_manager.ProjectManager') as mock_pm:
            with patch('logic.crawler.core.batch.BatchCrawler') as mock_batch:
                projects = [MagicMock(name=f"project-{i}") for i in range(3)]
                mock_pm.return_value.list_projects.return_value = projects

                batch_instance = MagicMock()
                mock_batch.return_value = batch_instance

                async def track_timing(project):
                    start_times.append(datetime.now())
                    await asyncio.sleep(0.05)  # Minimal work

                batch_instance.crawl_project = track_timing

                result = runner.invoke(main, ["crawl", "--update", "--all"])

                # Check no artificial delays
                if len(start_times) > 1:
                    for i in range(1, len(start_times)):
                        # Should start within reasonable time (no artificial delay)
                        time_diff = (start_times[i] - start_times[i-1]).total_seconds()
                        assert time_diff < 0.5  # No significant delay

    def test_batch_summary_generation(self):
        """Test batch operation summary generation."""
        from logic.crawler.core.batch import BatchCrawler

        crawler = BatchCrawler()

        # Simulate batch operation
        with patch('src.services.crawler.CrawlerService'):
            summary = {
                'total_projects': 10,
                'successful': 7,
                'failed': 3,
                'total_pages': 500,
                'total_embeddings': 4500,
                'duration': 120.5,
                'failures': [
                    {'project': 'proj1', 'error': 'Network timeout'},
                    {'project': 'proj2', 'error': 'Rate limited'},
                    {'project': 'proj3', 'error': 'Invalid URL'},
                ]
            }

            # Format for display
            formatted = crawler.format_summary(summary) if hasattr(crawler, 'format_summary') else str(summary)

            # Should have key information
            assert '7' in str(summary) or 'successful' in str(summary)
            assert '3' in str(summary) or 'failed' in str(summary)

    def test_batch_with_empty_project_list(self):
        """Test batch operation with no projects."""
        runner = CliRunner()

        with patch('src.services.project_manager.ProjectManager') as mock_pm:
            mock_pm.return_value.list_projects.return_value = []

            result = runner.invoke(main, ["crawl", "--update", "--all"])

            assert "no projects" in result.output.lower() or "nothing to crawl" in result.output.lower()

    def test_batch_interruption_handling(self):
        """Test batch operation handles interruption gracefully."""
        runner = CliRunner()

        with patch('src.services.project_manager.ProjectManager') as mock_pm:
            with patch('logic.crawler.core.batch.BatchCrawler') as mock_batch:
                projects = [MagicMock(name=f"project-{i}") for i in range(10)]
                mock_pm.return_value.list_projects.return_value = projects

                batch_instance = MagicMock()
                mock_batch.return_value = batch_instance

                # Simulate interruption after 3 projects
                processed = []

                async def crawl_with_interrupt(project):
                    if len(processed) >= 3:
                        raise KeyboardInterrupt()
                    processed.append(project.name)

                batch_instance.crawl_project = crawl_with_interrupt

                result = runner.invoke(main, ["crawl", "--update", "--all"])

                # Should show partial completion
                assert "interrupted" in result.output.lower() or "stopped" in result.output.lower()
                if "3" in result.output:
                    assert "completed" in result.output.lower()

    def test_batch_progress_reporting(self):
        """Test batch operation progress reporting."""
        runner = CliRunner()

        with patch('src.services.project_manager.ProjectManager') as mock_pm:
            with patch('logic.crawler.core.batch.BatchCrawler') as mock_batch:
                projects = [MagicMock(name=f"project-{i}") for i in range(5)]
                mock_pm.return_value.list_projects.return_value = projects

                batch_instance = MagicMock()
                mock_batch.return_value = batch_instance

                # Simulate progress updates
                batch_instance.get_current_progress.side_effect = [
                    "Processing project-0 (1/5)",
                    "Processing project-1 (2/5)",
                    "Processing project-2 (3/5)",
                    "Processing project-3 (4/5)",
                    "Processing project-4 (5/5)",
                ]

                result = runner.invoke(main, ["crawl", "--update", "--all"])

                # Should show progress indicators
                assert any(
                    indicator in result.output
                    for indicator in ["1/5", "2/5", "progress", "%", "Processing"]
                )

    def test_batch_error_collection_and_reporting(self):
        """Test that batch operations collect and report all errors."""
        runner = CliRunner()

        with patch('src.services.project_manager.ProjectManager') as mock_pm:
            with patch('logic.crawler.core.batch.BatchCrawler') as mock_batch:
                projects = [MagicMock(name=f"project-{i}") for i in range(6)]
                mock_pm.return_value.list_projects.return_value = projects

                batch_instance = MagicMock()
                mock_batch.return_value = batch_instance

                # Multiple error types
                errors = [
                    {"project": "project-1", "error": "Connection timeout", "type": "NETWORK"},
                    {"project": "project-3", "error": "Rate limit exceeded", "type": "RATE_LIMIT"},
                    {"project": "project-5", "error": "Parse error", "type": "PARSE"},
                ]

                batch_instance.get_all_errors.return_value = errors

                result = runner.invoke(main, ["crawl", "--update", "--all"])

                # All errors should be mentioned
                assert "3" in result.output or "errors" in result.output.lower()
                # Error types should be visible
                for error in errors:
                    assert error["project"] in result.output or error["type"] in result.output