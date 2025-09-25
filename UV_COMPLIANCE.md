# UV Compliance Validation for DocBro

This document explains how to use and interpret the UV compliance validation script created for DocBro.

## Overview

The UV compliance validation script (`tests/uv_compliance.py`) is a comprehensive testing tool that validates DocBro's compliance with UV (Universal Virtualenv) and UVX tool standards. It ensures that the package can be properly installed, updated, and managed using UV tools.

## What is UV Compliance?

UV compliance means that a Python package:
1. Can be installed globally using `uvx install`
2. Has proper entry points configured for UV tools
3. Works in isolated environments
4. Can be updated and uninstalled cleanly
5. Provides post-installation validation capabilities
6. Follows UV packaging standards

## Running the Validator

### Quick Start

```bash
# From the project root
python3 test_uv_compliance.py
```

### Direct Script Execution

```bash
# Run the validator directly
python3 tests/uv_compliance.py
```

### Requirements

The validator requires these dependencies:
- `uv` and `uvx` tools installed
- `httpx` for HTTP requests
- `rich` for beautiful console output
- `packaging` for version validation

## Test Categories

The validator performs comprehensive testing across 9 categories:

### 1. UV Installation (2 tests)
- **UV Available**: Checks if `uv` command is installed and accessible
- **UVX Available**: Checks if `uvx` command is installed and accessible

### 2. Entry Points Validation (4 tests)
- **Pyproject Exists**: Validates `pyproject.toml` file exists
- **Console Scripts**: Checks `[project.scripts]` entry point configuration
- **UV Tool Entry**: Validates `[project.entry-points."uv.tool"]` configuration
- **Python Version**: Ensures Python >=3.13 requirement is set

### 3. UV Install Commands (4 tests)
- **Create Venv**: Tests virtual environment creation with UV
- **Install Local**: Tests local package installation with `uv pip install`
- **Entry Point Created**: Verifies executable entry point creation
- **Entry Point Works**: Tests that the created entry point executes correctly

### 4. UVX Installation (2 tests)
- **UVX Available**: Confirms UVX tool accessibility
- **Install Command**: Tests `uvx install` functionality

### 5. Global PATH Availability (2 tests)
- **Executable Created**: Tests global executable creation
- **Path Resolution**: Validates PATH-based command resolution

### 6. Isolated Environment (3 tests)
- **Env1 Creation**: Creates first isolated environment
- **Env2 Creation**: Creates second isolated environment
- **Separate Site Packages**: Confirms environment isolation

### 7. Package Metadata (7 tests)
- **Package Name**: Validates package name is "docbro"
- **Version**: Checks version field presence
- **Description**: Validates description field
- **Python Requirement**: Confirms Python version requirement
- **Scripts Section**: Checks `[project.scripts]` section
- **UV Tool Entry Points**: Validates UV tool entry points
- **Build System**: Confirms hatchling build system configuration

### 8. Post-Install Validation (3 tests)
- **Installation Context**: Tests InstallationContext model functionality
- **Service Status**: Validates ServiceStatus model
- **Package Metadata**: Tests PackageMetadata model

### 9. Service Detection (2 tests)
- **Docker Check**: Tests Docker service detection
- **Ollama Check**: Tests Ollama service detection

## Understanding Results

### Result Interpretation

The validator provides:
- **Individual test results**: ✓ PASS or ✗ FAIL for each test
- **Category summaries**: Pass/fail status for each test category
- **Overall compliance score**: Percentage of tests passed
- **Compliance rating**: Excellent (≥90%), Good (≥75%), or Needs Improvement (<75%)

### Sample Output

```
UV Compliance Validation Results
Test Results Summary
┏━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Category          ┃ Test                   ┃ Status ┃ Details                ┃
┡━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━┩
│ Uv Installation   │ Uv Available           │  PASS  │ UV version: uv 0.8.9   │
│ Entry Points      │ Console Scripts        │  PASS  │ Entry point configured │
└───────────────────┴────────────────────────┴────────┴────────────────────────┘

Overall Result
EXCELLENT UV COMPLIANCE
Passed: 27/29 (93.1%)
```

## Common Issues and Solutions

### UV/UVX Not Available
**Issue**: Tests fail because UV tools aren't installed
**Solution**: Install UV tools:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Entry Point Configuration Missing
**Issue**: UV tool entry points not configured
**Solution**: Ensure `pyproject.toml` includes:
```toml
[project.entry-points."uv.tool"]
docbro = "src.cli.main:main"
```

### Python Version Requirement
**Issue**: Python version requirement not set correctly
**Solution**: Update `pyproject.toml`:
```toml
[project]
requires-python = ">=3.13"
```

### Service Detection Failures
**Issue**: External services (Docker, Ollama) not available
**Solution**: These are informational tests. Install services if needed:
```bash
# Docker
brew install docker  # macOS
sudo apt install docker.io  # Ubuntu

# Ollama
curl -fsSL https://ollama.com/install.sh | sh
```

## Integration with CI/CD

### GitHub Actions Integration

Add to your workflow:
```yaml
- name: Run UV Compliance Tests
  run: |
    pip install httpx rich packaging
    python3 test_uv_compliance.py
```

### Pre-release Validation

Use the validator before releases:
```bash
# Validate compliance before creating release
python3 test_uv_compliance.py

# Only proceed if compliance score >= 90%
```

## Extending the Validator

### Adding New Tests

To add new UV compliance tests:

1. Add test method to `UVComplianceValidator` class
2. Call `self.log_test()` to record results
3. Add to `run_all_tests()` method
4. Update documentation

Example:
```python
def test_new_feature(self) -> bool:
    """Test new UV feature compliance."""
    self.console.print("\n[bold blue]10. Testing New Feature[/bold blue]")

    try:
        # Your test logic here
        result = check_feature_compliance()

        self.log_test("new_feature", "feature_check", result,
                     details="Feature works correctly" if result else None,
                     error="Feature failed" if not result else None)
        return result
    except Exception as e:
        self.log_test("new_feature", "feature_check", False, error=str(e))
        return False
```

### Custom Validation Rules

Override validation behavior by modifying:
- `check_uv_installation()` for UV tool detection
- `validate_entry_points()` for entry point validation
- `test_package_metadata()` for metadata requirements

## Best Practices

### Development Workflow
1. Run validator during development
2. Ensure ≥90% compliance before committing
3. Fix failing tests before merging PRs
4. Re-run after dependency updates

### Release Process
1. Run full validation suite
2. Document any known issues
3. Ensure all critical tests pass
4. Include compliance report in release notes

### Continuous Monitoring
- Run validator in CI/CD pipelines
- Monitor compliance score over time
- Track regression in compliance

## Troubleshooting

### Debug Mode
Enable debug output by modifying the validator:
```python
# Add to validator initialization
self.console = Console(stderr=True, force_terminal=True)
```

### Verbose Logging
For detailed debugging:
```python
# Modify log_test method to include stack traces
def log_test(self, category, test_name, passed, details=None, error=None):
    # Add stack trace for failures
    if not passed and error:
        import traceback
        error += f"\n{traceback.format_exc()}"
```

### Test-Specific Issues

**Virtual Environment Issues**:
- Ensure sufficient disk space
- Check directory permissions
- Verify UV installation

**Network-Related Tests**:
- Check internet connectivity
- Verify service endpoints
- Consider proxy configuration

## Compliance Standards

### Minimum Requirements
For DocBro to be considered UV-compliant:
- ≥85% overall test pass rate
- All entry point tests must pass
- UV installation tests must pass
- Package metadata tests must pass

### Excellence Criteria
For excellent UV compliance:
- ≥90% overall test pass rate
- All critical functionality tests pass
- Service detection working (when services available)
- Comprehensive error handling

## Support

For issues with the UV compliance validator:
1. Check this documentation
2. Review test output carefully
3. Ensure all dependencies are installed
4. Check UV tool installation
5. Open an issue with full test output

The validator is designed to be comprehensive yet practical, ensuring DocBro meets professional UV packaging standards while remaining maintainable and extensible.