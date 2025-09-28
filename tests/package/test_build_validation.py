"""Contract test for package build validation."""

import pytest
from pathlib import Path
from .fixtures import build_wheel, inspect_wheel_contents


class TestPackageBuildValidation:
    """Test package build produces correct wheel contents."""

    def test_wheel_contains_src_core_directory(self):
        """Test that built wheel contains src/core directory and files."""
        project_dir = Path(__file__).parent.parent.parent

        # Build wheel
        wheel_path = build_wheel(project_dir)

        # Inspect contents
        contents = inspect_wheel_contents(wheel_path)

        # Verify src/core directory is present
        assert any("src/core/__init__.py" in item for item in contents), \
            f"src/core/__init__.py not found in wheel. Contents: {contents}"

        # Verify expected core files are present
        expected_core_files = [
            "src/core/__init__.py",
            "src/core/config.py",
            "src/core/docker_utils.py",
            "src/core/lib_logger.py"  # Renamed from logging.py
        ]

        for expected_file in expected_core_files:
            assert any(expected_file in item for item in contents), \
                f"{expected_file} not found in wheel contents"

    def test_wheel_contains_all_source_directories(self):
        """Test that wheel contains all expected source directories."""
        project_dir = Path(__file__).parent.parent.parent

        # Build wheel
        wheel_path = build_wheel(project_dir)

        # Inspect contents
        contents = inspect_wheel_contents(wheel_path)

        # Verify all expected directories are present
        expected_directories = ["src/cli", "src/core", "src/models", "src/services"]

        for expected_dir in expected_directories:
            assert any(expected_dir in item for item in contents), \
                f"{expected_dir} directory not found in wheel contents"

    def test_no_import_conflicts_in_wheel(self):
        """Test that wheel doesn't contain conflicting module names."""
        project_dir = Path(__file__).parent.parent.parent

        # Build wheel
        wheel_path = build_wheel(project_dir)

        # Inspect contents
        contents = inspect_wheel_contents(wheel_path)

        # Verify old conflicting logging.py is not present
        assert not any("src/core/logging.py" in item for item in contents), \
            "Conflicting src/core/logging.py found in wheel - should be renamed to lib_logger.py"

        # Verify renamed lib_logger.py is present
        assert any("src/core/lib_logger.py" in item for item in contents), \
            "src/core/lib_logger.py not found in wheel - module rename incomplete"