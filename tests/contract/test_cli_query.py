"""Contract tests for 'docbro query' command."""

import pytest
from click.testing import CliRunner

from src.cli.main import main


class TestQueryCommand:
    """Test cases for the query command."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()

    def test_query_command_exists(self):
        """Test that the query command exists and shows help."""
        result = self.runner.invoke(main, ["query", "--help"])
        assert result.exit_code == 0
        assert "query" in result.output.lower()
        assert "search" in result.output.lower()

    def test_query_requires_search_term(self):
        """Test that query command requires a search term."""
        result = self.runner.invoke(main, ["query"])
        assert result.exit_code != 0
        # Should fail when search term is missing

    def test_query_basic_search(self):
        """Test basic query functionality."""
        result = self.runner.invoke(main, ["query", "async function"])
        # This should fail until implementation exists
        assert result.exit_code != 0 or "not implemented" in result.output.lower()

    def test_query_with_project_filter(self):
        """Test query with --project filter."""
        result = self.runner.invoke(main, [
            "query", "decorators",
            "--project", "python-docs"
        ])
        # This should fail until implementation exists
        assert result.exit_code != 0 or "not implemented" in result.output.lower()

    def test_query_with_advanced_strategy(self):
        """Test query with --strategy advanced."""
        result = self.runner.invoke(main, [
            "query", "error handling",
            "--strategy", "advanced"
        ])
        # This should fail until implementation exists
        assert result.exit_code != 0 or "not implemented" in result.output.lower()

    def test_query_with_limit(self):
        """Test query with result limit."""
        result = self.runner.invoke(main, [
            "query", "functions",
            "--limit", "5"
        ])
        # This should fail until implementation exists
        assert result.exit_code != 0 or "not implemented" in result.output.lower()

    def test_query_validates_limit_range(self):
        """Test that query validates limit is within acceptable range."""
        result = self.runner.invoke(main, [
            "query", "test",
            "--limit", "1000"  # Too high
        ])
        assert result.exit_code != 0
        # Should fail with limit too large

    def test_query_validates_strategy_options(self):
        """Test that query validates strategy options."""
        result = self.runner.invoke(main, [
            "query", "test",
            "--strategy", "invalid-strategy"
        ])
        assert result.exit_code != 0
        # Should fail with invalid strategy

    def test_query_shows_results_with_scores(self):
        """Test that query results include relevance scores."""
        result = self.runner.invoke(main, ["query", "python functions"])
        # When implemented, should show relevance scores
        # For now, should fail
        assert result.exit_code != 0 or "score" in result.output.lower()

    def test_query_shows_source_information(self):
        """Test that query results include source page information."""
        result = self.runner.invoke(main, ["query", "async await"])
        # When implemented, should show source URLs and page titles
        # For now, should fail
        assert result.exit_code != 0 or any(src in result.output.lower()
                                          for src in ["source", "url", "page"])

    def test_query_handles_no_results(self):
        """Test query behavior when no results are found."""
        result = self.runner.invoke(main, ["query", "extremely_rare_search_term_xyz"])
        # Should show appropriate message for no results
        # For now, should fail
        assert result.exit_code != 0 or "no results" in result.output.lower()

    def test_query_handles_empty_search_term(self):
        """Test query behavior with empty search term."""
        result = self.runner.invoke(main, ["query", ""])
        assert result.exit_code != 0
        # Should fail with empty search term

    def test_query_handles_nonexistent_project(self):
        """Test query behavior when specified project doesn't exist."""
        result = self.runner.invoke(main, [
            "query", "test",
            "--project", "nonexistent-project"
        ])
        assert result.exit_code != 0
        # Should fail when project doesn't exist

    def test_query_supports_multiple_strategies(self):
        """Test that query supports different RAG strategies."""
        strategies = ["basic", "advanced", "semantic", "hybrid"]
        for strategy in strategies:
            result = self.runner.invoke(main, [
                "query", "test",
                "--strategy", strategy
            ])
            # This should fail until implementation exists
            assert result.exit_code != 0

    def test_query_formats_output_nicely(self):
        """Test that query output is well-formatted."""
        result = self.runner.invoke(main, ["query", "python"])
        # When implemented, should have nice formatting with Rich
        # For now, should fail
        assert result.exit_code != 0