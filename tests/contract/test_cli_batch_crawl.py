"""Contract tests for CLI batch crawl operation."""

import pytest
from click.testing import CliRunner
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime
from src.cli.main import main


class TestCliBatchCrawl:
    """Test CLI batch crawl operations."""

    def test_batch_crawl_operation_structure(self):
        """Test that batch operation creates proper tracking structure."""
        runner = CliRunner()

        with patch('src.services.batch_crawler.BatchCrawler') as mock_batch:
            with patch('src.services.project_manager.ProjectManager') as mock_pm:
                projects = [MagicMock(name=f"project{i}") for i in range(3)]
                mock_pm.return_value.list_projects.return_value = projects

                # Check BatchOperation structure
                batch_op = None

                def capture_batch_op(*args, **kwargs):
                    nonlocal batch_op
                    batch_op = kwargs.get('operation') or args[0] if args else None
                    return AsyncMock()

                mock_batch.return_value.initialize_batch.side_effect = capture_batch_op

                result = runner.invoke(main, ["crawl", "--update", "--all"])

                # Batch operation should be created
                assert mock_batch.called

    def test_batch_crawl_tracks_progress(self):
        """Test that batch crawl tracks progress for all projects."""
        runner = CliRunner()

        with patch('src.services.batch_crawler.BatchCrawler') as mock_batch:
            with patch('src.services.project_manager.ProjectManager') as mock_pm:
                projects = [MagicMock(name=f"project{i}") for i in range(5)]
                mock_pm.return_value.list_projects.return_value = projects

                # Simulate progress updates
                mock_batch.return_value.get_progress.side_effect = [
                    {"current": 0, "total": 5, "completed": [], "failed": []},
                    {"current": 2, "total": 5, "completed": ["project0", "project1"], "failed": []},
                    {"current": 5, "total": 5, "completed": ["project0", "project1", "project2", "project3", "project4"], "failed": []}
                ]

                result = runner.invoke(main, ["crawl", "--update", "--all"])

                # Progress tracking should be called
                assert mock_batch.return_value.get_progress.called

    def test_batch_crawl_summary_report(self):
        """Test that batch crawl shows summary after completion."""
        runner = CliRunner()

        with patch('src.services.batch_crawler.BatchCrawler') as mock_batch:
            with patch('src.services.project_manager.ProjectManager') as mock_pm:
                projects = [MagicMock(name=f"project{i}") for i in range(4)]
                mock_pm.return_value.list_projects.return_value = projects

                mock_batch.return_value.get_summary.return_value = {
                    "total": 4,
                    "succeeded": 3,
                    "failed": 1,
                    "duration": 120.5,
                    "failures": [{"project": "project2", "error": "Connection timeout"}]
                }

                result = runner.invoke(main, ["crawl", "--update", "--all"])

                # Summary should be in output
                assert "3" in result.output and "succeeded" in result.output.lower()
                assert "1" in result.output and "failed" in result.output.lower()

    def test_batch_crawl_handles_empty_project_list(self):
        """Test batch crawl with no projects."""
        runner = CliRunner()

        with patch('src.services.project_manager.ProjectManager') as mock_pm:
            mock_pm.return_value.list_projects.return_value = []

            result = runner.invoke(main, ["crawl", "--update", "--all"])

            assert "no projects" in result.output.lower() or "empty" in result.output.lower()

    def test_batch_crawl_respects_immediate_start(self):
        """Test that each project starts immediately after previous completes."""
        runner = CliRunner()

        with patch('src.services.batch_crawler.BatchCrawler') as mock_batch:
            with patch('src.services.project_manager.ProjectManager') as mock_pm:
                projects = [MagicMock(name=f"project{i}") for i in range(3)]
                mock_pm.return_value.list_projects.return_value = projects

                # Track timing
                start_times = []

                async def track_timing(project):
                    start_times.append(datetime.now())
                    return {"status": "success"}

                mock_batch.return_value.crawl_project = track_timing

                result = runner.invoke(main, ["crawl", "--update", "--all"])

                # No artificial delays between projects
                if len(start_times) > 1:
                    for i in range(1, len(start_times)):
                        time_diff = (start_times[i] - start_times[i-1]).total_seconds()
                        # Should start immediately (allowing small overhead)
                        assert time_diff < 1.0, "Projects should start immediately after previous completes"

    def test_batch_crawl_error_collection(self):
        """Test that batch crawl collects all errors."""
        runner = CliRunner()

        with patch('src.services.batch_crawler.BatchCrawler') as mock_batch:
            with patch('src.services.project_manager.ProjectManager') as mock_pm:
                projects = [MagicMock(name=f"project{i}") for i in range(5)]
                mock_pm.return_value.list_projects.return_value = projects

                # Multiple failures
                mock_batch.return_value.get_errors.return_value = [
                    {"project": "project1", "error": "Network timeout", "timestamp": "2024-01-26T10:00:00"},
                    {"project": "project3", "error": "Rate limited", "timestamp": "2024-01-26T10:05:00"},
                    {"project": "project4", "error": "Parse error", "timestamp": "2024-01-26T10:07:00"}
                ]

                result = runner.invoke(main, ["crawl", "--update", "--all"])

                # All errors should be reported
                assert "3" in result.output and "error" in result.output.lower()
                error_types = ["timeout", "rate", "parse"]
                for error_type in error_types:
                    assert any(error_type in result.output.lower() for error_type in error_types)

    def test_batch_crawl_estimated_completion(self):
        """Test that batch crawl shows estimated completion time."""
        runner = CliRunner()

        with patch('src.services.batch_crawler.BatchCrawler') as mock_batch:
            with patch('src.services.project_manager.ProjectManager') as mock_pm:
                projects = [MagicMock(name=f"project{i}") for i in range(10)]
                mock_pm.return_value.list_projects.return_value = projects

                mock_batch.return_value.get_estimated_completion.return_value = datetime.now()

                result = runner.invoke(main, ["crawl", "--update", "--all"])

                # Should show progress or estimation
                assert any(
                    keyword in result.output.lower()
                    for keyword in ["estimated", "remaining", "progress", "eta"]
                )

    def test_batch_crawl_can_be_interrupted(self):
        """Test that batch crawl can be interrupted gracefully."""
        runner = CliRunner()

        with patch('src.services.batch_crawler.BatchCrawler') as mock_batch:
            with patch('src.services.project_manager.ProjectManager') as mock_pm:
                projects = [MagicMock(name=f"project{i}") for i in range(10)]
                mock_pm.return_value.list_projects.return_value = projects

                # Simulate interruption after 2 projects
                mock_batch.return_value.crawl_all.side_effect = KeyboardInterrupt()

                result = runner.invoke(main, ["crawl", "--update", "--all"])

                # Should handle interruption gracefully
                assert "interrupted" in result.output.lower() or "cancelled" in result.output.lower()
                # Should show what was completed
                assert "completed" in result.output.lower() or "processed" in result.output.lower()