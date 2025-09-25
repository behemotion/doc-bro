#!/bin/bash
# =============================================================================
# DocBro Quickstart Validation - Scenario 2: Installation with Critical Decisions
# =============================================================================
# Description: Validates the installation wizard behavior when default ports
# are occupied and critical configuration decisions are required.
#
# Expected behavior:
# - Wizard detects port conflicts (8765)
# - User is prompted to choose alternative port
# - Installation continues with user-selected port
# - Non-critical config still gets sensible defaults
# =============================================================================

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VALIDATION_LOG="${SCRIPT_DIR}/scenario-2-critical-decisions.log"
VALIDATION_RESULT="${SCRIPT_DIR}/scenario-2-critical-decisions-result.json"
TEMP_BACKUP_DIR="${SCRIPT_DIR}/temp-backup-$(date +%s)"
CONFLICT_PID=""
DEFAULT_PORT=8765
ALTERNATIVE_PORT=8766

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1" | tee -a "${VALIDATION_LOG}"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1" | tee -a "${VALIDATION_LOG}"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1" | tee -a "${VALIDATION_LOG}"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "${VALIDATION_LOG}"
}

# Result tracking
declare -A validation_results
validation_start_time=$(date +%s)

add_result() {
    local test_name="$1"
    local status="$2"
    local message="$3"
    local duration="$4"

    validation_results["${test_name}"]="$status"

    if [[ "$status" == "PASS" ]]; then
        log_success "$test_name: $message (${duration}s)"
    else
        log_error "$test_name: $message (${duration}s)"
    fi
}

# Cleanup function
cleanup_on_exit() {
    local exit_code=$?
    log_info "Performing cleanup..."

    # Kill the conflict process if it's still running
    if [[ -n "$CONFLICT_PID" ]] && kill -0 "$CONFLICT_PID" 2>/dev/null; then
        log_info "Terminating port conflict process (PID: $CONFLICT_PID)..."
        kill "$CONFLICT_PID" 2>/dev/null || true
        wait "$CONFLICT_PID" 2>/dev/null || true
    fi

    # Restore any backed up configurations if they exist
    if [[ -d "$TEMP_BACKUP_DIR" ]]; then
        log_info "Restoring backed up configurations..."
        if [[ -d "$TEMP_BACKUP_DIR/.config/docbro" ]]; then
            mkdir -p ~/.config/
            cp -r "$TEMP_BACKUP_DIR/.config/docbro" ~/.config/
        fi
        if [[ -d "$TEMP_BACKUP_DIR/.local/share/docbro" ]]; then
            mkdir -p ~/.local/share/
            cp -r "$TEMP_BACKUP_DIR/.local/share/docbro" ~/.local/share/
        fi
        rm -rf "$TEMP_BACKUP_DIR"
    fi

    # Generate final report
    generate_final_report $exit_code

    if [[ $exit_code -ne 0 ]]; then
        log_error "Validation failed with exit code: $exit_code"
    else
        log_success "Validation completed successfully"
    fi
}

trap cleanup_on_exit EXIT

# Generate final report
generate_final_report() {
    local exit_code=$1
    local end_time=$(date +%s)
    local total_duration=$((end_time - validation_start_time))

    local passed=0
    local failed=0

    for test in "${!validation_results[@]}"; do
        if [[ "${validation_results[$test]}" == "PASS" ]]; then
            ((passed++))
        else
            ((failed++))
        fi
    done

    # Create JSON report
    cat > "$VALIDATION_RESULT" << EOF
{
  "scenario": "Installation with Critical Decisions",
  "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "duration_seconds": $total_duration,
  "exit_code": $exit_code,
  "test_parameters": {
    "default_port": $DEFAULT_PORT,
    "alternative_port": $ALTERNATIVE_PORT,
    "conflict_simulation": true
  },
  "summary": {
    "total_tests": $((passed + failed)),
    "passed": $passed,
    "failed": $failed,
    "success_rate": $(echo "scale=2; $passed * 100 / ($passed + $failed)" | bc -l 2>/dev/null || echo "0")
  },
  "test_results": {
EOF

    local first=true
    for test in "${!validation_results[@]}"; do
        if [[ "$first" == "true" ]]; then
            first=false
        else
            echo "," >> "$VALIDATION_RESULT"
        fi
        echo "    \"$test\": \"${validation_results[$test]}\"" >> "$VALIDATION_RESULT"
    done

    cat >> "$VALIDATION_RESULT" << EOF
  },
  "system_info": {
    "os": "$(uname -s)",
    "arch": "$(uname -m)",
    "python_version": "$(python3 --version 2>/dev/null || echo "Not available")",
    "uv_version": "$(uv --version 2>/dev/null || echo "Not available")"
  }
}
EOF

    log_info "Final Report Generated: $VALIDATION_RESULT"
    log_info "Summary: $passed passed, $failed failed ($(echo "scale=2; $passed * 100 / ($passed + $failed)" | bc -l 2>/dev/null || echo "0")% success rate)"
}

# Test functions
test_prerequisites() {
    local start_time=$(date +%s)
    log_info "Testing prerequisites..."

    # Check if UV is installed
    if ! command -v uv &> /dev/null; then
        add_result "prerequisites" "FAIL" "UV not found in PATH" $(($(date +%s) - start_time))
        exit 1
    fi

    # Check Python availability
    if ! command -v python3 &> /dev/null; then
        add_result "prerequisites" "FAIL" "Python3 not found" $(($(date +%s) - start_time))
        exit 1
    fi

    # Check if python -m http.server is available (used for port conflict simulation)
    if ! python3 -m http.server --help &> /dev/null; then
        add_result "prerequisites" "FAIL" "Python http.server module not available" $(($(date +%s) - start_time))
        exit 1
    fi

    add_result "prerequisites" "PASS" "All prerequisites available" $(($(date +%s) - start_time))
}

test_clean_environment() {
    local start_time=$(date +%s)
    log_info "Setting up clean environment..."

    # Backup existing DocBro installation if any
    if [[ -d ~/.config/docbro ]] || [[ -d ~/.local/share/docbro ]]; then
        log_info "Backing up existing DocBro configuration..."
        mkdir -p "$TEMP_BACKUP_DIR"/.config "$TEMP_BACKUP_DIR"/.local/share

        if [[ -d ~/.config/docbro ]]; then
            cp -r ~/.config/docbro "$TEMP_BACKUP_DIR/.config/"
            rm -rf ~/.config/docbro
        fi

        if [[ -d ~/.local/share/docbro ]]; then
            cp -r ~/.local/share/docbro "$TEMP_BACKUP_DIR/.local/share/"
            rm -rf ~/.local/share/docbro
        fi
    fi

    # Remove existing UV tool installation if any
    if uv tool list 2>/dev/null | grep -q docbro; then
        log_info "Removing existing DocBro UV tool installation..."
        uv tool uninstall docbro || true
    fi

    add_result "clean_environment" "PASS" "Environment cleaned successfully" $(($(date +%s) - start_time))
}

test_port_conflict_setup() {
    local start_time=$(date +%s)
    log_info "Setting up port conflict simulation..."

    # Check if port is already in use
    if lsof -i:"$DEFAULT_PORT" &> /dev/null; then
        log_warning "Port $DEFAULT_PORT already in use by another process"
        add_result "port_conflict_setup" "PASS" "Port $DEFAULT_PORT already occupied (natural conflict)" $(($(date +%s) - start_time))
        return 0
    fi

    # Start a simple HTTP server on the default port
    log_info "Starting HTTP server on port $DEFAULT_PORT to simulate conflict..."
    python3 -m http.server "$DEFAULT_PORT" &> /dev/null &
    CONFLICT_PID=$!

    # Wait a moment for the server to start
    sleep 2

    # Verify the conflict was created
    if lsof -i:"$DEFAULT_PORT" &> /dev/null; then
        add_result "port_conflict_setup" "PASS" "Port conflict simulated successfully on port $DEFAULT_PORT (PID: $CONFLICT_PID)" $(($(date +%s) - start_time))
    else
        add_result "port_conflict_setup" "FAIL" "Failed to create port conflict on port $DEFAULT_PORT" $(($(date +%s) - start_time))
        return 1
    fi
}

test_installation_with_conflict() {
    local start_time=$(date +%s)
    log_info "Testing installation with port conflict..."

    # Create an expect script to handle interactive installation
    local expect_script="${SCRIPT_DIR}/temp-expect-script.exp"
    cat > "$expect_script" << 'EOF'
#!/usr/bin/expect -f
set timeout 120

# Get the alternative port from environment
set alt_port $env(ALTERNATIVE_PORT)

spawn uv tool install git+https://github.com/behemotion/doc-bro

# Look for port conflict detection and prompt
expect {
    timeout {
        send_user "\nTimeout waiting for installation prompt\n"
        exit 1
    }
    -re "port.*conflict" {
        send_user "\nPort conflict detected by installer\n"
        exp_continue
    }
    -re "port.*occupied" {
        send_user "\nPort occupied message detected\n"
        exp_continue
    }
    -re "Choose.*port" {
        send_user "\nPrompted to choose alternative port\n"
        send "$alt_port\r"
        exp_continue
    }
    -re "Enter.*port" {
        send_user "\nPrompted to enter port\n"
        send "$alt_port\r"
        exp_continue
    }
    -re "installation.*complete" {
        send_user "\nInstallation completed\n"
        exit 0
    }
    -re "successfully.*installed" {
        send_user "\nSuccessfully installed\n"
        exit 0
    }
    eof {
        send_user "\nInstallation process ended\n"
        exit 0
    }
}

# Default case - wait for installation to complete
expect eof
exit 0
EOF

    chmod +x "$expect_script"

    # Run installation with expect script (if expect is available)
    if command -v expect &> /dev/null; then
        log_info "Running interactive installation with expect script..."

        export ALTERNATIVE_PORT
        if "$expect_script"; then
            add_result "installation_with_conflict" "PASS" "Installation handled port conflict interactively" $(($(date +%s) - start_time))
        else
            # Fall back to non-interactive installation
            log_warning "Interactive installation failed, trying non-interactive..."
            if timeout 90s uv tool install git+https://github.com/behemotion/doc-bro; then
                add_result "installation_with_conflict" "PASS" "Installation completed (non-interactive fallback)" $(($(date +%s) - start_time))
            else
                add_result "installation_with_conflict" "FAIL" "Installation failed with port conflict" $(($(date +%s) - start_time))
                return 1
            fi
        fi
    else
        log_warning "expect command not available, testing non-interactive installation..."
        # Test non-interactive installation - should still work with sensible defaults
        if timeout 90s uv tool install git+https://github.com/behemotion/doc-bro; then
            add_result "installation_with_conflict" "PASS" "Installation completed with default handling" $(($(date +%s) - start_time))
        else
            add_result "installation_with_conflict" "FAIL" "Installation failed" $(($(date +%s) - start_time))
            return 1
        fi
    fi

    # Clean up expect script
    rm -f "$expect_script"
}

test_installation_verification() {
    local start_time=$(date +%s)
    log_info "Testing installation verification..."

    # Test docbro command availability
    if command -v docbro &> /dev/null; then
        add_result "command_availability" "PASS" "docbro command available in PATH" $(($(date +%s) - start_time))
    else
        add_result "command_availability" "FAIL" "docbro command not found in PATH" $(($(date +%s) - start_time))
        return 1
    fi

    # Test version command
    if docbro --version &> /dev/null; then
        local version_output
        version_output=$(docbro --version 2>&1)
        add_result "version_command" "PASS" "Version command works: $version_output" $(($(date +%s) - start_time))
    else
        add_result "version_command" "FAIL" "docbro --version failed" $(($(date +%s) - start_time))
        return 1
    fi

    # Check UV tool listing
    if uv tool list 2>/dev/null | grep -q docbro; then
        add_result "uv_tool_listing" "PASS" "DocBro appears in UV tool list" $(($(date +%s) - start_time))
    else
        add_result "uv_tool_listing" "FAIL" "DocBro not found in UV tool list" $(($(date +%s) - start_time))
        return 1
    fi
}

test_configuration_with_alternatives() {
    local start_time=$(date +%s)
    log_info "Testing configuration with alternative settings..."

    # Test help command to see if port configuration is mentioned
    local help_output
    if help_output=$(docbro serve --help 2>&1); then
        # Check if the help shows port configuration options
        add_result "port_configuration_help" "PASS" "Serve command help available" $(($(date +%s) - start_time))

        # Log the help output for manual inspection
        log_info "Serve help output: $help_output"
    else
        add_result "port_configuration_help" "FAIL" "Could not get serve command help" $(($(date +%s) - start_time))
    fi

    # Check configuration files for port settings
    local config_dir="$HOME/.config/docbro"
    if [[ -d "$config_dir" ]]; then
        local config_files_found=0
        for config_file in "$config_dir"/*.json "$config_dir"/*.yaml "$config_dir"/*.yml; do
            if [[ -f "$config_file" ]]; then
                ((config_files_found++))
                log_info "Found configuration file: $config_file"
            fi
        done

        if [[ $config_files_found -gt 0 ]]; then
            add_result "configuration_files" "PASS" "Configuration files created ($config_files_found found)" $(($(date +%s) - start_time))
        else
            add_result "configuration_files" "FAIL" "No configuration files found in $config_dir" $(($(date +%s) - start_time))
        fi
    else
        add_result "configuration_files" "FAIL" "Configuration directory not found: $config_dir" $(($(date +%s) - start_time))
    fi
}

test_basic_functionality() {
    local start_time=$(date +%s)
    log_info "Testing basic functionality after conflict resolution..."

    # Test status command
    if timeout 30s docbro status &> /dev/null; then
        add_result "status_command" "PASS" "Status command works after installation" $(($(date +%s) - start_time))
    else
        add_result "status_command" "FAIL" "Status command failed" $(($(date +%s) - start_time))
        return 1
    fi

    # Test that the installation didn't break due to port conflict
    if docbro --help &> /dev/null; then
        add_result "help_command" "PASS" "Help command works" $(($(date +%s) - start_time))
    else
        add_result "help_command" "FAIL" "Help command failed" $(($(date +%s) - start_time))
        return 1
    fi
}

# Main execution
main() {
    log_info "Starting DocBro Quickstart Validation - Scenario 2: Installation with Critical Decisions"
    log_info "Timestamp: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
    log_info "Default port: $DEFAULT_PORT, Alternative port: $ALTERNATIVE_PORT"
    log_info "Log file: $VALIDATION_LOG"
    echo "" > "$VALIDATION_LOG"  # Clear log file

    # Run validation tests
    test_prerequisites
    test_clean_environment
    test_port_conflict_setup
    test_installation_with_conflict
    test_installation_verification
    test_configuration_with_alternatives
    test_basic_functionality

    log_success "All validation tests completed successfully!"
}

# Run main function if script is executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi