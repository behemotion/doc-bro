# DocBro Quickstart Validation Scripts

This directory contains comprehensive validation scripts for testing all 7 quickstart scenarios from the DocBro UV command installation feature specification.

## Overview

These scripts validate the complete DocBro installation experience, testing everything from fresh installations to error handling, cross-platform compatibility, and UV tool management integration.

## Scripts

### Individual Scenario Scripts

1. **`scenario-1-fresh-install.sh`** - Fresh Installation (Happy Path)
   - Tests clean system installation with UV
   - Validates system requirements checking
   - Verifies installation wizard behavior
   - Confirms basic functionality

2. **`scenario-2-critical-decisions.sh`** - Installation with Critical Decisions
   - Simulates port conflicts and configuration issues
   - Tests interactive decision prompts
   - Validates alternative configuration handling
   - Uses expect scripts for interaction testing

3. **`scenario-3-existing-upgrade.sh`** - Existing Installation Upgrade
   - Tests upgrade vs clean install options
   - Validates data preservation during upgrades
   - Tests rollback capabilities
   - Creates test data to verify preservation

4. **`scenario-4-system-requirements.sh`** - System Requirements Failure
   - Tests Python version requirement enforcement
   - Validates memory and disk space checking
   - Tests error message quality
   - Verifies clean rollback after failures

5. **`scenario-5-service-failure.sh`** - Service Setup Failure
   - Simulates Docker/Ollama unavailability
   - Tests service detection and error handling
   - Validates recovery instructions
   - Checks clean rollback after service failures

6. **`scenario-6-uv-tool-management.sh`** - UV Tool Management Integration
   - Tests `uv tool list`, `uv tool update`, `uv tool uninstall`
   - Validates UV environment cleanup
   - Tests multiple operation cycles
   - Verifies PATH integration

7. **`scenario-7-cross-platform.sh`** - Cross-Platform Installation
   - Tests platform-specific directory structures
   - Validates XDG compliance (Linux) and macOS conventions
   - Tests path handling and service compatibility
   - Checks file permissions and environment integration

### Master Runner Script

**`run-all-scenarios.sh`** - Master validation runner
- Runs all scenarios or specific subsets
- Supports parallel or sequential execution
- Generates comprehensive reports
- Provides detailed logging and error handling

## Usage

### Run All Scenarios
```bash
# Run all scenarios sequentially (recommended)
./run-all-scenarios.sh

# Run all scenarios in parallel (faster but less isolated)
./run-all-scenarios.sh --parallel

# Dry run to see what would be executed
./run-all-scenarios.sh --dry-run
```

### Run Specific Scenarios
```bash
# Run specific scenarios by number
./run-all-scenarios.sh 1 3 5

# Run just the happy path scenario
./run-all-scenarios.sh 1

# Run failure scenarios only
./run-all-scenarios.sh 4 5
```

### Run Individual Scenarios
```bash
# Run a specific scenario directly
./scenario-1-fresh-install.sh

# All scripts support direct execution
./scenario-6-uv-tool-management.sh
```

### Get Help and Information
```bash
# Show help
./run-all-scenarios.sh --help

# List available scenarios
./run-all-scenarios.sh --list

# Run with verbose output
./run-all-scenarios.sh --verbose 1 2
```

## Output Files

Each script generates detailed logs and JSON results:

### Individual Scenario Outputs
- `scenario-N-*.log` - Detailed execution logs
- `scenario-N-*-result.json` - Structured test results
- Temporary files during execution (cleaned up automatically)

### Master Runner Outputs
- `master-validation.log` - Master execution log
- `master-validation-result.json` - Comprehensive JSON results
- `validation-summary.md` - Human-readable summary report

## Prerequisites

### System Requirements
- **UV installed** (`curl -LsSf https://astral.sh/uv/install.sh | sh`)
- **Python 3.13+** available in PATH
- **Bash 4.0+** for associative array support (on macOS: `brew install bash`)
- **Internet connection** for GitHub repository access
- **4GB RAM, 2GB free disk space** (for full testing)

### Optional Tools
- **expect** - For interactive scenario testing (auto-detected)
- **bc** - For percentage calculations (usually available)
- **Docker** - For service failure testing (optional)
- **Ollama** - For AI service testing (optional)

### Platform Support
- **macOS** - Full support with Homebrew integration testing
- **Linux** - Full support with XDG compliance and systemd testing
- **Windows/WSL** - Basic support with path handling testing

## Features

### Comprehensive Testing
- **Installation workflows** - Fresh, upgrade, conflict resolution
- **Error handling** - Requirements failures, service unavailability
- **Platform compatibility** - Cross-platform path and service handling
- **UV integration** - Tool management, updates, cleanup

### Advanced Capabilities
- **Interactive testing** - Expect scripts for user decision simulation
- **Service simulation** - Port blocking, service stopping for failure testing
- **Environment isolation** - Backup and restore configurations
- **Parallel execution** - Faster testing with proper isolation
- **Detailed reporting** - JSON results and markdown summaries

### Safety Features
- **Automatic cleanup** - Restores system state after testing
- **Backup/restore** - Preserves existing DocBro installations
- **Timeout protection** - Prevents hanging scenarios
- **Error isolation** - Failed scenarios don't affect others

## Configuration

### Environment Variables
```bash
# Customize timeouts
export TIMEOUT_PER_SCENARIO=1200  # 20 minutes

# Customize test parameters
export TEST_PROJECT_NAME="custom-test-project"
export GITHUB_REPO="git+https://github.com/your-fork/doc-bro"
```

### Script Parameters
Most scenarios support internal configuration via variables at the top of each script:
- Port numbers for conflict testing
- Timeout values for operations
- Test data names and paths

## Troubleshooting

### Common Issues

1. **Bash Version Compatibility**
   ```bash
   # On macOS with older bash (3.2), install newer bash
   brew install bash
   # Then run scripts with explicit bash path
   /usr/local/bin/bash ./run-all-scenarios.sh --help

   # Or update default bash (requires admin)
   sudo echo "/usr/local/bin/bash" >> /etc/shells
   chsh -s /usr/local/bin/bash
   ```

2. **Permission Errors**
   ```bash
   chmod +x validation/*.sh
   ```

3. **UV Not Found**
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   source ~/.bashrc  # or restart shell
   ```

3. **Python Version Issues**
   ```bash
   python3 --version  # Should be 3.13+
   # Install Python 3.13+ if needed
   ```

4. **Missing expect Command**
   ```bash
   # macOS
   brew install expect

   # Ubuntu/Debian
   sudo apt install expect

   # CentOS/RHEL
   sudo yum install expect
   ```

### Debug Mode
Run individual scenarios with debug output:
```bash
bash -x ./scenario-1-fresh-install.sh
```

### Clean Environment
If tests are interfering with each other:
```bash
# Remove any partial installations
uv tool uninstall docbro || true
rm -rf ~/.config/docbro ~/.local/share/docbro ~/.cache/docbro

# Run scenarios individually
./scenario-1-fresh-install.sh
```

## Development

### Adding New Scenarios
1. Create `scenario-N-description.sh` following the existing pattern
2. Add entry to `SCENARIOS` array in `run-all-scenarios.sh`
3. Test individually and with the master runner

### Script Structure
Each scenario script follows this pattern:
- Configuration and setup
- Logging functions with colors
- Result tracking with JSON output
- Cleanup function with trap
- Individual test functions
- Main execution function

### Testing the Validators
```bash
# Test master runner help
./run-all-scenarios.sh --help

# Test dry run functionality
./run-all-scenarios.sh --dry-run 1

# Test individual scenario structure
./scenario-1-fresh-install.sh --help 2>/dev/null || echo "No help implemented"
```

## Integration

These validation scripts are designed to integrate with:
- **CI/CD pipelines** - Automated testing on pull requests
- **Release testing** - Pre-release validation
- **Development workflows** - Local testing during development
- **Documentation generation** - Results can inform documentation

## Support

For issues with the validation scripts:
1. Check individual scenario logs for specific errors
2. Review the master validation results JSON
3. Run scenarios individually to isolate issues
4. Check system requirements and dependencies
5. Review the DocBro installation documentation

---

**Generated for DocBro T039 Validation Task**
*Comprehensive validation of UV command installation quickstart scenarios*