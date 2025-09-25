"""Test fixtures for package validation."""

import subprocess
import tempfile
from pathlib import Path
from typing import List
import zipfile


def build_wheel(project_dir: Path) -> Path:
    """Build wheel and return path to .whl file."""
    result = subprocess.run(
        ["uv", "build", "."],
        cwd=project_dir,
        capture_output=True,
        text=True
    )
    if result.returncode != 0:
        raise RuntimeError(f"Wheel build failed: {result.stderr}")

    dist_dir = project_dir / "dist"
    whl_files = list(dist_dir.glob("*.whl"))
    if not whl_files:
        raise RuntimeError("No wheel file found after build")

    return whl_files[0]


def inspect_wheel_contents(wheel_path: Path) -> List[str]:
    """Return list of files in wheel."""
    with zipfile.ZipFile(wheel_path, 'r') as zf:
        return zf.namelist()


def install_wheel_in_temp_env(wheel_path: Path) -> subprocess.CompletedProcess:
    """Install wheel using uv and return installation result."""
    return subprocess.run(
        ["uv", "tool", "install", str(wheel_path)],
        capture_output=True,
        text=True
    )


def test_cli_command(command: List[str]) -> subprocess.CompletedProcess:
    """Test CLI command and return result."""
    return subprocess.run(
        command,
        capture_output=True,
        text=True
    )


def cleanup_installation():
    """Clean up any test installations."""
    subprocess.run(
        ["uv", "tool", "uninstall", "docbro"],
        capture_output=True
    )