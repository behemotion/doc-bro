"""Contract test for UV installation testing."""

import pytest
from pathlib import Path
from .fixtures import build_wheel, install_wheel_in_temp_env, cleanup_installation


class TestUVInstallation:
    """Test UV installation process and requirements."""

    def setup_method(self):
        """Clean up before each test."""
        cleanup_installation()

    def teardown_method(self):
        """Clean up after each test."""
        cleanup_installation()

    def test_uv_installation_succeeds(self):
        """Test that UV installation completes without module errors."""
        project_dir = Path(__file__).parent.parent.parent

        # Build wheel
        wheel_path = build_wheel(project_dir)

        # Install via UV
        result = install_wheel_in_temp_env(wheel_path)

        # Verify installation succeeded
        assert result.returncode == 0, \
            f"UV installation failed. stderr: {result.stderr}, stdout: {result.stdout}"

        # Verify no module import errors in output
        assert "ModuleNotFoundError" not in result.stderr, \
            f"Module import error during installation: {result.stderr}"

        assert "No module named 'src.core'" not in result.stderr, \
            f"Missing src.core module during installation: {result.stderr}"

    def test_installation_creates_docbro_executable(self):
        """Test that installation creates the docbro executable."""
        project_dir = Path(__file__).parent.parent.parent

        # Build and install
        wheel_path = build_wheel(project_dir)
        result = install_wheel_in_temp_env(wheel_path)

        # Verify installation succeeded
        assert result.returncode == 0, f"Installation failed: {result.stderr}"

        # Check that executable was created (indicated by successful installation)
        # The executable message appears in stderr for UV
        assert "Installed 1 executable: docbro" in result.stderr, \
            f"docbro executable not created. stderr: {result.stderr}"

    def test_installation_preserves_import_structure(self):
        """Test that installation preserves correct import structure."""
        project_dir = Path(__file__).parent.parent.parent

        # Build and install
        wheel_path = build_wheel(project_dir)
        result = install_wheel_in_temp_env(wheel_path)

        # Verify installation succeeded without import structure issues
        assert result.returncode == 0, f"Installation failed: {result.stderr}"

        # Look for any import-related errors in the output
        import_errors = [
            "ImportError",
            "ModuleNotFoundError",
            "circular import",
            "cannot import name"
        ]

        for error_type in import_errors:
            assert error_type not in result.stderr, \
                f"{error_type} found during installation: {result.stderr}"