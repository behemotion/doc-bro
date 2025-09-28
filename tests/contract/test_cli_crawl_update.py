"""Contract tests for CLI crawl update functionality."""

import pytest
from click.testing import CliRunner
from unittest.mock import patch, MagicMock, AsyncMock
from src.cli.main import main


class TestCliCrawlUpdate:
    """Test CLI crawl --update command functionality."""

    def test_crawl_update_single_project(self):
        """Test crawl --update with single project name."""
        runner = CliRunner()

        with patch('src.services.project_manager.ProjectManager') as mock_pm:
            with patch('src.services.crawler.CrawlerService') as mock_crawler:
                # Setup mocks
                mock_project = MagicMock()
                mock_project.name = "test-project"
                mock_pm.return_value.get_project.return_value = mock_project
                mock_crawler.return_value.crawl = AsyncMock()

                result = runner.invoke(main, ["crawl", "--update", "test-project"])

                # Should call crawler for the project
                assert mock_pm.return_value.get_project.called
                mock_pm.return_value.get_project.assert_called_with("test-project")

    def test_crawl_update_all_projects(self):
        """Test crawl --update --all for batch processing."""
        runner = CliRunner()

        with patch('src.services.project_manager.ProjectManager') as mock_pm:
            with patch('src.services.batch_crawler.BatchCrawler') as mock_batch:
                # Setup mocks for multiple projects
                projects = [
                    MagicMock(name="project1"),
                    MagicMock(name="project2"),
                    MagicMock(name="project3")
                ]
                mock_pm.return_value.list_projects.return_value = projects
                mock_batch.return_value.crawl_all = AsyncMock()

                result = runner.invoke(main, ["crawl", "--update", "--all"])

                # Should list all projects
                assert mock_pm.return_value.list_projects.called
                # Should initiate batch crawl
                assert mock_batch.return_value.crawl_all.called

    def test_crawl_update_nonexistent_project(self):
        """Test crawl --update with nonexistent project."""
        runner = CliRunner()

        with patch('src.services.project_manager.ProjectManager') as mock_pm:
            mock_pm.return_value.get_project.return_value = None

            result = runner.invoke(main, ["crawl", "--update", "nonexistent"])

            assert result.exit_code != 0
            assert "not found" in result.output.lower() or "does not exist" in result.output.lower()

    def test_crawl_update_with_options(self):
        """Test crawl --update with additional options."""
        runner = CliRunner()

        with patch('src.services.project_manager.ProjectManager') as mock_pm:
            with patch('src.services.crawler.CrawlerService') as mock_crawler:
                mock_project = MagicMock()
                mock_pm.return_value.get_project.return_value = mock_project
                mock_crawler.return_value.crawl = AsyncMock()

                result = runner.invoke(main, [
                    "crawl", "--update", "test-project",
                    "--max-pages", "100",
                    "--rate-limit", "2.0"
                ])

                # Options should be passed to crawler
                crawl_call = mock_crawler.return_value.crawl.call_args
                assert crawl_call is not None

    def test_crawl_update_all_continue_on_error(self):
        """Test that --update --all continues when individual projects fail."""
        runner = CliRunner()

        with patch('src.services.project_manager.ProjectManager') as mock_pm:
            with patch('src.services.batch_crawler.BatchCrawler') as mock_batch:
                projects = [
                    MagicMock(name="project1"),
                    MagicMock(name="project2"),
                    MagicMock(name="project3")
                ]
                mock_pm.return_value.list_projects.return_value = projects

                # Simulate one project failing
                mock_batch.return_value.get_results.return_value = {
                    "project1": {"status": "success"},
                    "project2": {"status": "failed", "error": "Network error"},
                    "project3": {"status": "success"}
                }

                result = runner.invoke(main, ["crawl", "--update", "--all"])

                # Should complete despite failure
                assert "2 succeeded" in result.output or "completed" in result.output
                assert "1 failed" in result.output or "error" in result.output.lower()

    def test_crawl_update_shows_progress(self):
        """Test that crawl update shows progress for each project."""
        runner = CliRunner()

        with patch('src.services.project_manager.ProjectManager') as mock_pm:
            with patch('src.services.crawler.CrawlerService') as mock_crawler:
                with patch('src.services.progress_reporter.ProgressReporter') as mock_progress:
                    mock_project = MagicMock()
                    mock_pm.return_value.get_project.return_value = mock_project

                    result = runner.invoke(main, ["crawl", "--update", "test-project"])

                    # Progress should be shown
                    assert mock_progress.called or "crawling" in result.output.lower()

    def test_crawl_without_update_requires_project_name(self):
        """Test that regular crawl still requires project name."""
        runner = CliRunner()

        result = runner.invoke(main, ["crawl"])

        assert result.exit_code != 0
        assert "missing" in result.output.lower() or "required" in result.output.lower()

    def test_crawl_update_sequential_execution(self):
        """Test that --update --all processes projects sequentially."""
        runner = CliRunner()

        with patch('src.services.project_manager.ProjectManager') as mock_pm:
            with patch('src.services.batch_crawler.BatchCrawler') as mock_batch:
                projects = [MagicMock(name=f"project{i}") for i in range(3)]
                mock_pm.return_value.list_projects.return_value = projects

                # Track call order
                call_order = []

                async def track_crawl(project):
                    call_order.append(project.name)
                    return {"status": "success"}

                mock_batch.return_value.crawl_project = track_crawl

                result = runner.invoke(main, ["crawl", "--update", "--all"])

                # Projects should be processed in order
                assert len(call_order) == 3
                assert call_order == ["project0", "project1", "project2"]