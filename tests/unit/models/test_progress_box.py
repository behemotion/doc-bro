"""Unit tests for ProgressBox model validation"""

import pytest
import json
from pydantic import ValidationError

from src.cli.interface.models.progress_box import ProgressBox


class TestProgressBox:
    """Unit tests for ProgressBox validation"""

    def test_valid_progress_box_creation(self):
        """Test creating a valid ProgressBox"""
        box = ProgressBox(
            title="Crawling test-project",
            project_name="test-project",
            metrics={"depth": "2/2", "pages_crawled": 83, "errors": 0},
            current_operation="Processing page.html"
        )

        assert box.title == "Crawling test-project"
        assert box.project_name == "test-project"
        assert box.metrics["depth"] == "2/2"
        assert box.current_operation == "Processing page.html"
        assert box.border_style == "rounded"
        assert box.width == 80

    def test_project_name_validation(self):
        """Test project name validation"""
        # Valid project names
        valid_names = ["test-project", "my_project", "project123", "simple"]
        for name in valid_names:
            box = ProgressBox(title="Test", project_name=name)
            assert box.project_name == name

        # Invalid project names
        invalid_names = ["test project", "test@project", "test/project", "test\\project"]
        for name in invalid_names:
            with pytest.raises(ValidationError, match="Project name must contain only"):
                ProgressBox(title="Test", project_name=name)

    def test_empty_title_validation(self):
        """Test that empty title is rejected"""
        with pytest.raises(ValidationError):
            ProgressBox(title="", project_name="test")

    def test_empty_project_name_validation(self):
        """Test that empty project name is rejected"""
        with pytest.raises(ValidationError):
            ProgressBox(title="Test", project_name="")

    def test_metrics_serialization_validation(self):
        """Test that metrics must be JSON serializable"""
        # Valid metrics
        valid_metrics = {
            "depth": "2/2",
            "pages_crawled": 83,
            "errors": 0,
            "queue": 33,
            "success_rate": 95.5,
            "nested": {"count": 10, "status": "active"}
        }
        box = ProgressBox(title="Test", project_name="test", metrics=valid_metrics)
        assert box.metrics == valid_metrics

        # Invalid metrics (non-serializable)
        class NonSerializable:
            pass

        with pytest.raises(ValidationError, match="Metrics must be JSON serializable"):
            ProgressBox(
                title="Test",
                project_name="test",
                metrics={"object": NonSerializable()}
            )

    def test_width_validation(self):
        """Test width validation"""
        # Valid widths
        box = ProgressBox(title="Test", project_name="test", width=40)
        assert box.width == 40

        box = ProgressBox(title="Test", project_name="test", width=120)
        assert box.width == 120

        # Invalid width (too small)
        with pytest.raises(ValidationError):
            ProgressBox(title="Test", project_name="test", width=30)

    def test_truncate_current_operation(self):
        """Test current operation truncation"""
        box = ProgressBox(title="Test", project_name="test")

        # No truncation needed
        short_text = "Processing page.html"
        assert box.truncate_current_operation(len(short_text) + 10) == short_text

        # Truncation needed
        long_text = "Processing very long URL that exceeds the maximum width limit"
        truncated = box.truncate_current_operation(30)

        assert len(truncated) <= 30
        assert truncated.startswith("Processing very")
        assert truncated.endswith("width limit")
        assert "..." in truncated

        # Edge case: very short max_length
        very_short = box.truncate_current_operation(3)
        assert very_short == "..."

    def test_model_assignment_validation(self):
        """Test that assignment validation works"""
        box = ProgressBox(title="Test", project_name="test")

        # Valid assignment
        box.current_operation = "New operation"
        assert box.current_operation == "New operation"

        # Invalid assignment should raise validation error
        with pytest.raises(ValidationError):
            box.project_name = "invalid project name"

    def test_default_values(self):
        """Test default values are set correctly"""
        box = ProgressBox(title="Test", project_name="test")

        assert box.metrics == {}
        assert box.current_operation == ""
        assert box.border_style == "rounded"
        assert box.width == 80