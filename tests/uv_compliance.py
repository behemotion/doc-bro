"""UV compliance validation module."""

import subprocess
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional


class UVComplianceValidator:
    """Validator for UV compliance across the project."""

    def __init__(self, project_root: Optional[Path] = None):
        self.project_root = project_root or Path(__file__).parent.parent

    def validate_pyproject_toml(self) -> Dict[str, Any]:
        """Validate pyproject.toml compliance with UV."""
        pyproject_path = self.project_root / "pyproject.toml"

        if not pyproject_path.exists():
            return {"status": "error", "message": "pyproject.toml not found"}

        # Basic validation - check if UV can parse it
        try:
            result = subprocess.run(
                ["uv", "lock", "--dry-run"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                return {"status": "pass", "message": "pyproject.toml is UV compliant"}
            else:
                return {
                    "status": "fail",
                    "message": f"UV validation failed: {result.stderr}"
                }
        except subprocess.TimeoutExpired:
            return {"status": "timeout", "message": "UV validation timed out"}
        except FileNotFoundError:
            return {"status": "error", "message": "UV not found"}

    def validate_dependencies(self) -> Dict[str, Any]:
        """Validate that all dependencies can be resolved by UV."""
        try:
            result = subprocess.run(
                ["uv", "tree"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                return {"status": "pass", "message": "All dependencies resolved"}
            else:
                return {
                    "status": "fail",
                    "message": f"Dependency resolution failed: {result.stderr}"
                }
        except subprocess.TimeoutExpired:
            return {"status": "timeout", "message": "Dependency check timed out"}
        except FileNotFoundError:
            return {"status": "error", "message": "UV not found"}

    def validate_tool_installation(self) -> Dict[str, Any]:
        """Validate that the tool can be installed via UV."""
        try:
            # Test UV tool install in dry-run mode
            result = subprocess.run(
                ["uv", "tool", "install", "--dry-run", str(self.project_root)],
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.returncode == 0:
                return {"status": "pass", "message": "Tool installation validation passed"}
            else:
                return {
                    "status": "fail",
                    "message": f"Tool installation failed: {result.stderr}"
                }
        except subprocess.TimeoutExpired:
            return {"status": "timeout", "message": "Tool installation test timed out"}
        except FileNotFoundError:
            return {"status": "error", "message": "UV not found"}

    def run_full_validation(self) -> Dict[str, Any]:
        """Run complete UV compliance validation."""
        results = {
            "pyproject": self.validate_pyproject_toml(),
            "dependencies": self.validate_dependencies(),
            "tool_install": self.validate_tool_installation()
        }

        all_passed = all(r["status"] == "pass" for r in results.values())

        return {
            "overall_status": "pass" if all_passed else "fail",
            "results": results
        }


def main():
    """Main entry point for UV compliance validation."""
    validator = UVComplianceValidator()
    results = validator.run_full_validation()

    print(f"UV Compliance Validation: {results['overall_status'].upper()}")
    print("-" * 50)

    for test_name, result in results["results"].items():
        status_icon = "✅" if result["status"] == "pass" else "❌"
        print(f"{status_icon} {test_name}: {result['message']}")

    return 0 if results["overall_status"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())