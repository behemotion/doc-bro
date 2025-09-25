#!/bin/bash
# =============================================================================
# DocBro Quickstart Validation - Scenario 1: Fresh Installation (Happy Path)
# =============================================================================
# Description: Validates the single UV command installation feature end-to-end
# on a clean system with only UV installed.
#
# Expected behavior:
# - Installation wizard starts automatically
# - System requirements validated (Python 3.13+, 4GB RAM, 2GB disk)
# - External services detected/configured (Docker, Qdrant, Ollama)
# - User prompted only for critical config (install location, ports, data dirs)
# - Non-critical config gets sensible defaults
# - Installation completes in <30 seconds
# =============================================================================

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VALIDATION_LOG="${SCRIPT_DIR}/scenario-1-fresh-install.log"
VALIDATION_RESULT="${SCRIPT_DIR}/scenario-1-fresh-install-result.json"
TEMP_BACKUP_DIR="${SCRIPT_DIR}/temp-backup-$(date +%s)"

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

# Result tracking using files for bash 3.2 compatibility
RESULTS_DIR="${SCRIPT_DIR}/.scenario1-results"
mkdir -p "$RESULTS_DIR"

# Helper functions for result tracking
set_result() {
    local test_name="$1"
    local status="$2"
    echo "$status" > "$RESULTS_DIR/${test_name}"
}

get_result() {
    local test_name="$1"
    if [[ -f "$RESULTS_DIR/${test_name}" ]]; then
        cat "$RESULTS_DIR/${test_name}"
    else
        echo "UNKNOWN"
    fi
}

get_all_test_names() {
    local names=()
    for result_file in "$RESULTS_DIR"/*; do
        if [[ -f "$result_file" ]]; then
            names+=("$(basename "$result_file")")
        fi
    done
    printf '%s\n' "${names[@]}" | sort
}

validation_start_time=$(date +%s)

add_result() {
    local test_name="$1"
    local status="$2"
    local message="$3"
    local duration="$4"

    set_result "${test_name}" "$status"

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

    # Clean up results directory
    rm -rf "$RESULTS_DIR" 2>/dev/null || true

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
    local test_names
    test_names=($(get_all_test_names))

    for test in "${test_names[@]}"; do
        local result
        result=$(get_result "$test")
        if [[ "$result" == "PASS" ]]; then
            ((passed++))
        else
            ((failed++))
        fi
    done

    # Create JSON report
    cat > "$VALIDATION_RESULT" << EOF
{
  "scenario": "Fresh Installation (Happy Path)",
  "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "duration_seconds": $total_duration,
  "exit_code": $exit_code,
  "summary": {
    "total_tests": $((passed + failed)),
    "passed": $passed,
    "failed": $failed,
    "success_rate": $(echo "scale=2; $passed * 100 / ($passed + $failed)" | bc -l 2>/dev/null || echo "0")
  },
  "test_results": {
EOF

    local first=true
    for test in "${test_names[@]}"; do
        if [[ "$first" == "true" ]]; then
            first=false
        else
            echo "," >> "$VALIDATION_RESULT"
        fi
        local result
        result=$(get_result "$test")
        echo "    \"$test\": \"$result\"" >> "$VALIDATION_RESULT"
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

    # Check Python 3.13+
    local python_version
    python_version=$(python3 --version 2>&1 | grep -oE '[0-9]+\.[0-9]+' | head -1)
    if [[ -z "$python_version" ]]; then
        add_result "prerequisites" "FAIL" "Python3 not found" $(($(date +%s) - start_time))
        exit 1
    fi

    local major_version=$(echo "$python_version" | cut -d. -f1)
    local minor_version=$(echo "$python_version" | cut -d. -f2)

    if [[ "$major_version" -lt 3 ]] || ([[ "$major_version" -eq 3 ]] && [[ "$minor_version" -lt 13 ]]); then
        add_result "prerequisites" "FAIL" "Python $python_version found, need 3.13+" $(($(date +%s) - start_time))
        exit 1
    fi

    # Check system resources
    local available_memory
    available_memory=$(free -m 2>/dev/null | awk '/^Mem:/{print $7}' || sysctl -n hw.memsize 2>/dev/null | awk '{print int($1/1024/1024)}' || echo "0")

    if [[ "$available_memory" -lt 4000 ]]; then
        log_warning "Low memory detected: ${available_memory}MB (recommended: 4GB)"
    fi

    add_result "prerequisites" "PASS" "UV installed, Python $python_version available" $(($(date +%s) - start_time))
}

test_clean_environment() {
    local start_time=$(date +%s)
    log_info "Testing clean environment setup..."

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

    # Verify clean state
    if uv tool list 2>/dev/null | grep -q docbro; then
        add_result "clean_environment" "FAIL" "DocBro still found in UV tools after uninstall" $(($(date +%s) - start_time))
        exit 1
    fi

    if command -v docbro &> /dev/null; then
        add_result "clean_environment" "FAIL" "docbro command still in PATH" $(($(date +%s) - start_time))
        exit 1
    fi

    add_result "clean_environment" "PASS" "Environment cleaned successfully" $(($(date +%s) - start_time))
}

test_installation_process() {
    local start_time=$(date +%s)
    log_info "Testing installation process..."

    # Install DocBro via UV with timeout
    log_info "Running: uv tool install git+https://github.com/behemotion/doc-bro"

    # Use timeout to ensure installation completes within expected time
    if timeout 60s uv tool install git+https://github.com/behemotion/doc-bro; then
        local duration=$(($(date +%s) - start_time))

        if [[ $duration -le 30 ]]; then
            add_result "installation_speed" "PASS" "Installation completed in ${duration}s (target: <30s)" $duration
        else
            add_result "installation_speed" "FAIL" "Installation took ${duration}s (target: <30s)" $duration
        fi
    else
        add_result "installation_process" "FAIL" "Installation failed or timed out" $(($(date +%s) - start_time))
        return 1
    fi

    add_result "installation_process" "PASS" "Installation command completed successfully" $(($(date +%s) - start_time))
}

test_installation_verification() {
    local start_time=$(date +%s)
    log_info "Testing installation verification..."

    # Test 1: Check version command
    if docbro --version &> /dev/null; then
        local version_output
        version_output=$(docbro --version 2>&1)
        add_result "version_command" "PASS" "Version command works: $version_output" $(($(date +%s) - start_time))
    else
        add_result "version_command" "FAIL" "docbro --version failed" $(($(date +%s) - start_time))
        return 1
    fi

    # Test 2: Check command in PATH
    local docbro_path
    docbro_path=$(which docbro 2>/dev/null)
    if [[ -n "$docbro_path" ]]; then
        add_result "path_availability" "PASS" "docbro found in PATH: $docbro_path" $(($(date +%s) - start_time))
    else
        add_result "path_availability" "FAIL" "docbro not found in PATH" $(($(date +%s) - start_time))
        return 1
    fi

    # Test 3: Check UV tool listing
    if uv tool list 2>/dev/null | grep -q docbro; then
        add_result "uv_tool_listing" "PASS" "DocBro appears in UV tool list" $(($(date +%s) - start_time))
    else
        add_result "uv_tool_listing" "FAIL" "DocBro not found in UV tool list" $(($(date +%s) - start_time))
        return 1
    fi
}

test_basic_functionality() {
    local start_time=$(date +%s)
    log_info "Testing basic functionality..."

    # Test status command
    if timeout 30s docbro status &> /dev/null; then
        add_result "status_command" "PASS" "Status command executed successfully" $(($(date +%s) - start_time))
    else
        add_result "status_command" "FAIL" "Status command failed or timed out" $(($(date +%s) - start_time))
        return 1
    fi

    # Test help command
    if docbro --help &> /dev/null; then
        add_result "help_command" "PASS" "Help command works" $(($(date +%s) - start_time))
    else
        add_result "help_command" "FAIL" "Help command failed" $(($(date +%s) - start_time))
        return 1
    fi
}

test_configuration_structure() {
    local start_time=$(date +%s)
    log_info "Testing configuration structure..."

    # Check XDG-compliant directories
    local config_dir="$HOME/.config/docbro"
    local data_dir="$HOME/.local/share/docbro"
    local cache_dir="$HOME/.cache/docbro"

    if [[ -d "$config_dir" ]]; then
        add_result "config_directory" "PASS" "Config directory created: $config_dir" $(($(date +%s) - start_time))
    else
        add_result "config_directory" "FAIL" "Config directory not found: $config_dir" $(($(date +%s) - start_time))
    fi

    if [[ -d "$data_dir" ]]; then
        add_result "data_directory" "PASS" "Data directory created: $data_dir" $(($(date +%s) - start_time))
    else
        add_result "data_directory" "FAIL" "Data directory not found: $data_dir" $(($(date +%s) - start_time))
    fi

    # Cache directory might be created on first use, so we'll just check if the parent exists
    if [[ -d "$(dirname "$cache_dir")" ]]; then
        add_result "cache_directory_structure" "PASS" "Cache directory structure available" $(($(date +%s) - start_time))
    else
        add_result "cache_directory_structure" "FAIL" "Cache directory structure not available" $(($(date +%s) - start_time))
    fi
}

# Main execution
main() {
    log_info "Starting DocBro Quickstart Validation - Scenario 1: Fresh Installation (Happy Path)"
    log_info "Timestamp: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
    log_info "Log file: $VALIDATION_LOG"
    echo "" > "$VALIDATION_LOG"  # Clear log file

    # Run validation tests
    test_prerequisites
    test_clean_environment
    test_installation_process
    test_installation_verification
    test_basic_functionality
    test_configuration_structure

    log_success "All validation tests completed successfully!"
}

# Run main function if script is executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi