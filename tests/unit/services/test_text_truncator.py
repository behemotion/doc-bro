"""Unit tests for TextTruncator text truncation strategies"""

import pytest

from src.cli.interface.services.text_truncator import TextTruncator
from src.cli.interface.models.enums import TruncationStrategy


class TestTextTruncator:
    """Unit tests for TextTruncator"""

    def test_truncator_initialization(self):
        """Test TextTruncator initializes correctly"""
        truncator = TextTruncator()
        assert truncator is not None

    def test_truncate_middle_basic(self):
        """Test basic middle truncation"""
        truncator = TextTruncator()

        long_text = "very-long-project-name-that-exceeds-normal-display-width"
        result = truncator.truncate_middle(long_text, 30)

        assert len(result) <= 30
        assert result.startswith("very-long-proj")
        assert result.endswith("display-width")
        assert "..." in result

    def test_truncate_middle_no_truncation_needed(self):
        """Test middle truncation when text is already short enough"""
        truncator = TextTruncator()

        short_text = "short"
        result = truncator.truncate_middle(short_text, 30)

        assert result == "short"

    def test_truncate_middle_very_short_limit(self):
        """Test middle truncation with very short max_length"""
        truncator = TextTruncator()

        text = "long text"
        result = truncator.truncate_middle(text, 3)

        assert result == "..."
        assert len(result) == 3

    def test_truncate_middle_custom_ellipsis(self):
        """Test middle truncation with custom ellipsis"""
        truncator = TextTruncator()

        long_text = "very-long-project-name-that-exceeds-normal-display-width"
        result = truncator.truncate_middle(long_text, 30, ellipsis="…")

        assert len(result) <= 30
        assert "…" in result
        assert "..." not in result

    def test_truncate_end_basic(self):
        """Test basic end truncation"""
        truncator = TextTruncator()

        long_text = "very-long-project-name-that-exceeds-normal-display-width"
        result = truncator.truncate_end(long_text, 30)

        assert len(result) <= 30
        assert result.startswith("very-long-project-name")
        assert result.endswith("...")

    def test_truncate_end_no_truncation_needed(self):
        """Test end truncation when text is already short enough"""
        truncator = TextTruncator()

        short_text = "short"
        result = truncator.truncate_end(short_text, 30)

        assert result == "short"

    def test_truncate_end_very_short_limit(self):
        """Test end truncation with very short max_length"""
        truncator = TextTruncator()

        text = "long text"
        result = truncator.truncate_end(text, 3)

        assert result == "..."
        assert len(result) == 3

    def test_truncate_end_custom_ellipsis(self):
        """Test end truncation with custom ellipsis"""
        truncator = TextTruncator()

        long_text = "very-long-project-name-that-exceeds-normal-display-width"
        result = truncator.truncate_end(long_text, 30, ellipsis="…")

        assert len(result) <= 30
        assert result.endswith("…")
        assert "..." not in result

    def test_truncate_with_strategy_middle(self):
        """Test truncation with middle strategy"""
        truncator = TextTruncator()

        long_text = "very-long-project-name-that-exceeds-normal-display-width"
        result = truncator.truncate_with_strategy(long_text, 30, TruncationStrategy.MIDDLE)

        assert len(result) <= 30
        assert "..." in result

    def test_truncate_with_strategy_end(self):
        """Test truncation with end strategy"""
        truncator = TextTruncator()

        long_text = "very-long-project-name-that-exceeds-normal-display-width"
        result = truncator.truncate_with_strategy(long_text, 30, TruncationStrategy.END)

        assert len(result) <= 30
        assert result.endswith("...")

    def test_truncate_with_strategy_none(self):
        """Test truncation with none strategy"""
        truncator = TextTruncator()

        long_text = "very-long-project-name-that-exceeds-normal-display-width"
        result = truncator.truncate_with_strategy(long_text, 30, TruncationStrategy.NONE)

        assert result == long_text  # No truncation

    def test_truncate_with_strategy_invalid(self):
        """Test truncation with invalid strategy"""
        truncator = TextTruncator()

        with pytest.raises(ValueError, match="Unknown truncation strategy"):
            truncator.truncate_with_strategy("text", 10, "invalid_strategy")

    def test_truncate_file_path(self):
        """Test file path truncation preserving filename"""
        truncator = TextTruncator()

        path = "/very/long/path/to/important/documentation/file/with/long/name.html"
        result = truncator.truncate_file_path(path, 40)

        assert len(result) <= 40
        assert result.endswith(".html")  # Preserves extension
        assert "..." in result

    def test_truncate_file_path_short_enough(self):
        """Test file path truncation when path is short enough"""
        truncator = TextTruncator()

        path = "/short/path/file.html"
        result = truncator.truncate_file_path(path, 40)

        assert result == path

    def test_truncate_file_path_long_filename(self):
        """Test file path truncation with very long filename"""
        truncator = TextTruncator()

        path = "/path/very-long-filename-that-exceeds-the-limit-itself.html"
        result = truncator.truncate_file_path(path, 30)

        assert len(result) <= 30
        assert "..." in result

    def test_truncate_url(self):
        """Test URL truncation preserving scheme and domain"""
        truncator = TextTruncator()

        url = "https://example.com/very/long/url/path/that/exceeds/normal/terminal/width/limits"
        result = truncator.truncate_url(url, 50)

        assert len(result) <= 50
        assert result.startswith("https://example.com")
        assert "..." in result

    def test_truncate_url_short_enough(self):
        """Test URL truncation when URL is short enough"""
        truncator = TextTruncator()

        url = "https://example.com/short"
        result = truncator.truncate_url(url, 50)

        assert result == url

    def test_truncate_url_long_domain(self):
        """Test URL truncation with very long domain"""
        truncator = TextTruncator()

        url = "https://very-long-domain-name-that-exceeds-limit.com/path"
        result = truncator.truncate_url(url, 30)

        assert len(result) <= 30
        assert "..." in result

    def test_truncate_url_no_protocol(self):
        """Test URL truncation without protocol"""
        truncator = TextTruncator()

        url = "example.com/very/long/path/that/exceeds/normal/width"
        result = truncator.truncate_url(url, 30)

        assert len(result) <= 30
        assert "..." in result

    def test_edge_case_empty_string(self):
        """Test truncation with empty string"""
        truncator = TextTruncator()

        result = truncator.truncate_middle("", 10)
        assert result == ""

        result = truncator.truncate_end("", 10)
        assert result == ""

    def test_edge_case_max_length_zero(self):
        """Test truncation with max_length of zero"""
        truncator = TextTruncator()

        result = truncator.truncate_middle("text", 0)
        assert result == ""

        result = truncator.truncate_end("text", 0)
        assert result == ""