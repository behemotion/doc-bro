"""Integration test for UV compliance validation."""

import asyncio
import pytest
import subprocess
import sys
from pathlib import Path
from typing import Dict, Any

from tests.uv_compliance import UVComplianceValidator


class TestUVComplianceIntegration:
    """Integration tests for UV compliance validation."""

    def test_uv_compliance_script_exists(self):
        """Test that UV compliance script exists and is executable."""
        project_root = Path(__file__).parent.parent
        compliance_script = project_root / "tests" / "uv_compliance.py"

        assert compliance_script.exists(), "UV compliance script not found"
        assert compliance_script.is_file(), "UV compliance script is not a file"

        # Check if script is executable (on Unix-like systems)
        if sys.platform != "win32":
            assert compliance_script.stat().st_mode & 0o111, "UV compliance script not executable"

    def test_uv_compliance_runner_script_exists(self):
        """Test that UV compliance runner script exists."""
        project_root = Path(__file__).parent.parent
        runner_script = project_root / "test_uv_compliance.py"

        assert runner_script.exists(), "UV compliance runner script not found"
        assert runner_script.is_file(), "UV compliance runner script is not a file"

    def test_uv_compliance_shell_script_exists(self):
        """Test that shell script wrapper exists."""
        project_root = Path(__file__).parent.parent
        shell_script = project_root / "scripts" / "validate-uv-compliance.sh"

        assert shell_script.exists(), "UV compliance shell script not found"
        assert shell_script.is_file(), "UV compliance shell script is not a file"

        if sys.platform != "win32":
            assert shell_script.stat().st_mode & 0o111, "Shell script not executable"

    @pytest.mark.asyncio
    async def test_uv_compliance_validator_initialization(self):
        """Test that UVComplianceValidator can be initialized."""
        validator = UVComplianceValidator()

        assert validator is not None
        assert hasattr(validator, 'console')
        assert hasattr(validator, 'test_results')
        assert hasattr(validator, 'temp_dirs')
        assert hasattr(validator, 'project_root')

        # Ensure test results dictionary starts empty
        assert isinstance(validator.test_results, dict)
        assert len(validator.test_results) == 0

    @pytest.mark.asyncio
    async def test_uv_compliance_validator_logging(self):
        """Test that the validator logging system works."""
        validator = UVComplianceValidator()

        # Test successful logging
        validator.log_test("test_category", "test_pass", True, "Test details")
        assert "test_category" in validator.test_results
        assert "test_pass" in validator.test_results["test_category"]
        assert validator.test_results["test_category"]["test_pass"]["passed"] is True
        assert validator.test_results["test_category"]["test_pass"]["details"] == "Test details"

        # Test failure logging
        validator.log_test("test_category", "test_fail", False, error="Test error")
        assert validator.test_results["test_category"]["test_fail"]["passed"] is False
        assert validator.test_results["test_category"]["test_fail"]["error"] == "Test error"

    @pytest.mark.asyncio
    async def test_entry_point_validation_logic(self):
        """Test the entry point validation logic specifically."""
        validator = UVComplianceValidator()
        result = validator.validate_entry_points()

        # Should return True as our pyproject.toml should be properly configured
        assert isinstance(result, bool)

        # Check that entry point tests were logged
        assert "entry_points" in validator.test_results
        entry_point_tests = validator.test_results["entry_points"]

        # We should have tests for pyproject existence, console scripts, UV tool entry, etc.
        expected_tests = ["pyproject_exists", "console_scripts", "uv_tool_entry", "python_version"]
        for test_name in expected_tests:
            assert test_name in entry_point_tests, f"Missing test: {test_name}"

    @pytest.mark.asyncio
    async def test_package_metadata_validation(self):
        """Test package metadata validation logic."""
        validator = UVComplianceValidator()
        result = validator.test_package_metadata()

        assert isinstance(result, bool)
        assert "metadata" in validator.test_results

        metadata_tests = validator.test_results["metadata"]
        expected_metadata_tests = [
            "package_name", "version", "description", "python_requirement",
            "scripts_section", "uv_tool_entry_points", "build_system"
        ]

        for test_name in expected_metadata_tests:
            assert test_name in metadata_tests, f"Missing metadata test: {test_name}"

    def test_run_compliance_via_subprocess(self):
        """Test running compliance validation via subprocess."""
        project_root = Path(__file__).parent.parent
        runner_script = project_root / "test_uv_compliance.py"

        # Run the compliance script with a timeout
        result = subprocess.run([
            sys.executable, str(runner_script)
        ], capture_output=True, text=True, timeout=120)

        # The script should run successfully (exit code 0 or 1 depending on compliance)
        assert result.returncode in [0, 1], f"Unexpected exit code: {result.returncode}"

        # Should have some output
        assert len(result.stdout) > 0 or len(result.stderr) > 0, "No output from compliance script"

        # Should contain compliance indicators
        output = result.stdout + result.stderr
        assert any(phrase in output.lower() for phrase in [
            "compliance", "uv", "test", "pass", "fail"
        ]), "Output doesn't contain expected compliance indicators"

    @pytest.mark.asyncio
    async def test_cleanup_functionality(self):
        """Test that validator cleanup works properly."""
        validator = UVComplianceValidator()

        # Create some temporary directories to simulate test runs
        with validator.temporary_directory() as temp_dir:
            assert temp_dir.exists()
            assert temp_dir in validator.temp_dirs

        # After context exit, temp_dir should be cleaned up automatically
        # temp_dir should no longer exist (handled by context manager)

        # Test explicit cleanup
        validator.cleanup()
        # After cleanup, temp_dirs list should still exist but directories should be cleaned
        assert isinstance(validator.temp_dirs, list)

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        subprocess.run(["which", "uv"], capture_output=True).returncode != 0,
        reason="UV not available in PATH"
    )
    async def test_uv_installation_check_with_real_uv(self):
        """Test UV installation check with real UV if available."""
        validator = UVComplianceValidator()
        result = validator.check_uv_installation()

        # If UV is available, this should return True
        assert isinstance(result, bool)

        if result:
            # If UV check passed, should have logged UV availability
            assert "uv_installation" in validator.test_results
            uv_tests = validator.test_results["uv_installation"]
            assert "uv_available" in uv_tests
            assert uv_tests["uv_available"]["passed"] is True

    @pytest.mark.asyncio
    async def test_post_install_validation_models(self):
        """Test post-install validation model functionality."""
        validator = UVComplianceValidator()
        result = validator.test_post_install_validation()

        assert isinstance(result, bool)
        assert "post_install" in validator.test_results

        post_install_tests = validator.test_results["post_install"]
        expected_model_tests = ["installation_context", "service_status", "package_metadata"]

        for test_name in expected_model_tests:
            assert test_name in post_install_tests, f"Missing post-install test: {test_name}"

    def test_compliance_documentation_exists(self):
        """Test that UV compliance documentation exists."""
        project_root = Path(__file__).parent.parent
        docs = [
            project_root / "UV_COMPLIANCE.md",
        ]

        for doc in docs:
            assert doc.exists(), f"Documentation file not found: {doc}"
            assert doc.is_file(), f"Documentation path is not a file: {doc}"

            # Check that documentation has reasonable content
            content = doc.read_text()
            assert len(content) > 1000, f"Documentation too short: {doc}"
            assert "uv" in content.lower(), f"Documentation doesn't mention UV: {doc}"

    @pytest.mark.asyncio
    async def test_validator_error_handling(self):
        """Test that validator handles errors gracefully."""
        validator = UVComplianceValidator()

        # Test command execution error handling
        returncode, stdout, stderr = validator.run_command(["nonexistent_command_xyz"])
        assert returncode != 0
        assert isinstance(stdout, str)
        assert isinstance(stderr, str)

        # Test with invalid directory
        returncode, stdout, stderr = validator.run_command(
            ["ls"], cwd=Path("/nonexistent/directory")
        )
        assert returncode != 0

    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_full_compliance_validation_run(self):
        """Test running a full compliance validation (slow test)."""
        validator = UVComplianceValidator()

        try:
            await validator.run_all_tests()

            # After running all tests, should have results in multiple categories
            assert len(validator.test_results) > 5, "Too few test categories run"

            # Should have attempted basic tests even if they failed
            expected_categories = ["entry_points", "metadata", "post_install"]
            for category in expected_categories:
                assert category in validator.test_results, f"Missing test category: {category}"

        except Exception as e:
            pytest.fail(f"Full compliance validation raised unexpected exception: {e}")
        finally:
            # Ensure cleanup runs
            validator.cleanup()