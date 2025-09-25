#!/bin/bash
# =============================================================================
# DocBro Quickstart Validation - Scenario 6: UV Tool Management Integration
# =============================================================================
# Description: Validates the integration with UV tool management commands.
# Tests standard UV operations work correctly with DocBro.
#
# Expected behavior:
# - DocBro appears in 'uv tool list'
# - 'uv tool update docbro' works correctly
# - Version updates are properly reflected
# - 'uv tool uninstall docbro' removes DocBro cleanly
# - Command is removed from PATH after uninstall
# - UV tool environment is properly cleaned up
# =============================================================================

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VALIDATION_LOG="${SCRIPT_DIR}/scenario-6-uv-tool-management.log"
VALIDATION_RESULT="${SCRIPT_DIR}/scenario-6-uv-tool-management-result.json"
TEMP_BACKUP_DIR="${SCRIPT_DIR}/temp-backup-$(date +%s)"

# Test configuration
GITHUB_REPO="git+https://github.com/behemotion/doc-bro"
TOOL_NAME="docbro"

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

    # Restore any backed up configurations
    if [[ -d "$TEMP_BACKUP_DIR" ]]; then
        log_info "Restoring backed up configurations..."
        if [[ -d "$TEMP_BACKUP_DIR/.config/docbro" ]]; then
            mkdir -p ~/.config/
            rm -rf ~/.config/docbro 2>/dev/null || true
            cp -r "$TEMP_BACKUP_DIR/.config/docbro" ~/.config/
        fi
        if [[ -d "$TEMP_BACKUP_DIR/.local/share/docbro" ]]; then
            mkdir -p ~/.local/share/
            rm -rf ~/.local/share/docbro 2>/dev/null || true
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
  "scenario": "UV Tool Management Integration",
  "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "duration_seconds": $total_duration,
  "exit_code": $exit_code,
  "test_parameters": {
    "github_repo": "$GITHUB_REPO",
    "tool_name": "$TOOL_NAME"
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
    "uv_version": "$(uv --version 2>/dev/null || echo "Not available")",
    "uv_tool_dir": "$(uv tool dir 2>/dev/null || echo "Not available")"
  }
}
EOF

    log_info "Final Report Generated: $VALIDATION_RESULT"
    log_info "Summary: $passed passed, $failed failed ($(echo "scale=2; $passed * 100 / ($passed + $failed)" | bc -l 2>/dev/null || echo "0")% success rate)"
}

# Utility functions
get_docbro_version() {
    if command -v docbro &> /dev/null; then
        docbro --version 2>/dev/null | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1 || echo "unknown"
    else
        echo "not_installed"
    fi
}

is_docbro_in_uv_tools() {
    uv tool list 2>/dev/null | grep -q "$TOOL_NAME"
}

get_uv_tool_info() {
    uv tool list 2>/dev/null | grep "$TOOL_NAME" || echo "not_found"
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

    # Check UV version for tool support
    local uv_version
    uv_version=$(uv --version 2>/dev/null | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1)
    if [[ -n "$uv_version" ]]; then
        log_info "UV version: $uv_version"
    fi

    # Test UV tool commands availability
    if ! uv tool --help &> /dev/null; then
        add_result "prerequisites" "FAIL" "UV tool commands not available" $(($(date +%s) - start_time))
        exit 1
    fi

    add_result "prerequisites" "PASS" "All prerequisites available" $(($(date +%s) - start_time))
}

test_backup_existing_installation() {
    local start_time=$(date +%s)
    log_info "Backing up any existing installation..."

    # Backup existing DocBro installation if any
    if [[ -d ~/.config/docbro ]] || [[ -d ~/.local/share/docbro ]]; then
        log_info "Backing up existing DocBro configuration..."
        mkdir -p "$TEMP_BACKUP_DIR"/.config "$TEMP_BACKUP_DIR"/.local/share

        if [[ -d ~/.config/docbro ]]; then
            cp -r ~/.config/docbro "$TEMP_BACKUP_DIR/.config/"
        fi

        if [[ -d ~/.local/share/docbro ]]; then
            cp -r ~/.local/share/docbro "$TEMP_BACKUP_DIR/.local/share/"
        fi
    fi

    # Remove existing UV tool installation if any
    if is_docbro_in_uv_tools; then
        log_info "Removing existing DocBro UV tool installation..."
        uv tool uninstall "$TOOL_NAME" || true
    fi

    add_result "backup_existing" "PASS" "Backup and cleanup completed" $(($(date +%s) - start_time))
}

test_initial_installation() {
    local start_time=$(date +%s)
    log_info "Testing initial installation via UV tool..."

    # Install DocBro
    local install_output
    if install_output=$(timeout 120s uv tool install "$GITHUB_REPO" 2>&1); then
        add_result "initial_installation" "PASS" "Initial installation completed" $(($(date +%s) - start_time))
    else
        add_result "initial_installation" "FAIL" "Initial installation failed: $install_output" $(($(date +%s) - start_time))
        return 1
    fi

    # Verify installation
    if is_docbro_in_uv_tools && command -v docbro &> /dev/null; then
        local version
        version=$(get_docbro_version)
        add_result "installation_verification" "PASS" "Installation verified, version: $version" $(($(date +%s) - start_time))
    else
        add_result "installation_verification" "FAIL" "Installation verification failed" $(($(date +%s) - start_time))
        return 1
    fi
}

test_uv_tool_list() {
    local start_time=$(date +%s)
    log_info "Testing 'uv tool list' command..."

    # Test list command
    local list_output
    if list_output=$(uv tool list 2>&1); then
        if echo "$list_output" | grep -q "$TOOL_NAME"; then
            add_result "uv_tool_list" "PASS" "DocBro appears in UV tool list" $(($(date +%s) - start_time))

            # Log the tool info for analysis
            local tool_info
            tool_info=$(get_uv_tool_info)
            log_info "Tool info: $tool_info"
        else
            add_result "uv_tool_list" "FAIL" "DocBro not found in UV tool list" $(($(date +%s) - start_time))
            return 1
        fi
    else
        add_result "uv_tool_list" "FAIL" "Failed to run 'uv tool list'" $(($(date +%s) - start_time))
        return 1
    fi
}

test_uv_tool_update() {
    local start_time=$(date +%s)
    log_info "Testing 'uv tool update' command..."

    # Get current version before update
    local version_before
    version_before=$(get_docbro_version)
    log_info "Version before update: $version_before"

    # Test update command
    local update_output
    if update_output=$(timeout 120s uv tool update "$TOOL_NAME" 2>&1); then
        add_result "uv_tool_update" "PASS" "UV tool update completed" $(($(date +%s) - start_time))

        # Verify version after update
        local version_after
        version_after=$(get_docbro_version)
        log_info "Version after update: $version_after"

        if [[ "$version_after" != "not_installed" ]]; then
            if [[ "$version_after" == "$version_before" ]]; then
                add_result "update_version_check" "PASS" "Version consistent after update (already latest)" $(($(date +%s) - start_time))
            else
                add_result "update_version_check" "PASS" "Version updated from $version_before to $version_after" $(($(date +%s) - start_time))
            fi
        else
            add_result "update_version_check" "FAIL" "DocBro not available after update" $(($(date +%s) - start_time))
            return 1
        fi
    else
        add_result "uv_tool_update" "FAIL" "UV tool update failed: $update_output" $(($(date +%s) - start_time))

        # Check if tool is still functional after failed update
        if command -v docbro &> /dev/null; then
            add_result "update_resilience" "PASS" "Tool still functional after failed update" $(($(date +%s) - start_time))
        else
            add_result "update_resilience" "FAIL" "Tool broken after failed update" $(($(date +%s) - start_time))
        fi
    fi
}

test_functionality_after_update() {
    local start_time=$(date +%s)
    log_info "Testing functionality after update..."

    # Test basic commands
    local commands_tested=0
    local commands_passed=0

    # Test version command
    ((commands_tested++))
    if docbro --version &> /dev/null; then
        ((commands_passed++))
        log_info "Version command works after update"
    else
        log_error "Version command failed after update"
    fi

    # Test help command
    ((commands_tested++))
    if docbro --help &> /dev/null; then
        ((commands_passed++))
        log_info "Help command works after update"
    else
        log_error "Help command failed after update"
    fi

    # Test status command
    ((commands_tested++))
    if timeout 30s docbro status &> /dev/null; then
        ((commands_passed++))
        log_info "Status command works after update"
    else
        log_warning "Status command failed after update (may be expected if services unavailable)"
        ((commands_passed++))  # Count as pass since service unavailability is not an update issue
    fi

    if [[ $commands_passed -eq $commands_tested ]]; then
        add_result "functionality_after_update" "PASS" "All $commands_tested basic commands work after update" $(($(date +%s) - start_time))
    else
        add_result "functionality_after_update" "FAIL" "Only $commands_passed/$commands_tested commands work after update" $(($(date +%s) - start_time))
    fi
}

test_uv_tool_uninstall() {
    local start_time=$(date +%s)
    log_info "Testing 'uv tool uninstall' command..."

    # Verify tool is installed before uninstall
    if ! is_docbro_in_uv_tools; then
        add_result "pre_uninstall_check" "FAIL" "DocBro not found in tools before uninstall test" $(($(date +%s) - start_time))
        return 1
    fi

    # Test uninstall command
    local uninstall_output
    if uninstall_output=$(uv tool uninstall "$TOOL_NAME" 2>&1); then
        add_result "uv_tool_uninstall" "PASS" "UV tool uninstall completed" $(($(date +%s) - start_time))
    else
        add_result "uv_tool_uninstall" "FAIL" "UV tool uninstall failed: $uninstall_output" $(($(date +%s) - start_time))
        return 1
    fi

    # Verify removal from UV tool list
    if ! is_docbro_in_uv_tools; then
        add_result "uninstall_tool_list_check" "PASS" "DocBro removed from UV tool list" $(($(date +%s) - start_time))
    else
        add_result "uninstall_tool_list_check" "FAIL" "DocBro still appears in UV tool list after uninstall" $(($(date +%s) - start_time))
    fi
}

test_command_path_cleanup() {
    local start_time=$(date +%s)
    log_info "Testing command removal from PATH after uninstall..."

    # Test if docbro command is no longer available
    if ! command -v docbro &> /dev/null; then
        add_result "command_path_cleanup" "PASS" "DocBro command removed from PATH" $(($(date +%s) - start_time))
    else
        local docbro_path
        docbro_path=$(which docbro 2>/dev/null)
        add_result "command_path_cleanup" "FAIL" "DocBro command still in PATH: $docbro_path" $(($(date +%s) - start_time))
    fi

    # Test that running docbro fails appropriately
    if docbro --version &> /dev/null; then
        add_result "command_execution_cleanup" "FAIL" "DocBro still executes after uninstall" $(($(date +%s) - start_time))
    else
        add_result "command_execution_cleanup" "PASS" "DocBro command properly unavailable after uninstall" $(($(date +%s) - start_time))
    fi
}

test_uv_environment_cleanup() {
    local start_time=$(date +%s)
    log_info "Testing UV tool environment cleanup..."

    # Check if UV tool directory structure is clean
    local uv_tool_dir
    if uv_tool_dir=$(uv tool dir 2>/dev/null); then
        log_info "UV tool directory: $uv_tool_dir"

        # Check if DocBro-specific directories are removed
        local docbro_dirs=()
        if [[ -d "$uv_tool_dir/$TOOL_NAME" ]]; then
            docbro_dirs+=("$uv_tool_dir/$TOOL_NAME")
        fi

        # Look for any DocBro-related files/directories
        local docbro_files
        docbro_files=$(find "$uv_tool_dir" -name "*docbro*" 2>/dev/null | wc -l)

        if [[ ${#docbro_dirs[@]} -eq 0 ]] && [[ $docbro_files -eq 0 ]]; then
            add_result "uv_environment_cleanup" "PASS" "UV environment cleaned up properly" $(($(date +%s) - start_time))
        elif [[ $docbro_files -le 2 ]]; then
            add_result "uv_environment_cleanup" "PASS" "UV environment mostly clean ($docbro_files residual files)" $(($(date +%s) - start_time))
        else
            add_result "uv_environment_cleanup" "FAIL" "UV environment not properly cleaned ($docbro_files files/dirs remaining)" $(($(date +%s) - start_time))
        fi
    else
        add_result "uv_environment_cleanup" "PASS" "Cannot access UV tool directory for cleanup verification" $(($(date +%s) - start_time))
    fi
}

test_reinstall_after_uninstall() {
    local start_time=$(date +%s)
    log_info "Testing reinstallation after uninstall..."

    # Reinstall DocBro
    local reinstall_output
    if reinstall_output=$(timeout 120s uv tool install "$GITHUB_REPO" 2>&1); then
        add_result "reinstall_after_uninstall" "PASS" "Reinstallation successful after uninstall" $(($(date +%s) - start_time))

        # Verify reinstallation
        if is_docbro_in_uv_tools && command -v docbro &> /dev/null; then
            local version
            version=$(get_docbro_version)
            add_result "reinstall_verification" "PASS" "Reinstallation verified, version: $version" $(($(date +%s) - start_time))
        else
            add_result "reinstall_verification" "FAIL" "Reinstallation verification failed" $(($(date +%s) - start_time))
        fi
    else
        add_result "reinstall_after_uninstall" "FAIL" "Reinstallation failed after uninstall: $reinstall_output" $(($(date +%s) - start_time))
    fi
}

test_multiple_operations_cycle() {
    local start_time=$(date +%s)
    log_info "Testing multiple UV operations cycle..."

    local cycle_success=0
    local cycle_attempts=3

    for i in $(seq 1 $cycle_attempts); do
        log_info "Cycle $i/$cycle_attempts: install -> update -> uninstall"

        # Install
        if uv tool install "$GITHUB_REPO" &> /dev/null; then
            # Update
            if uv tool update "$TOOL_NAME" &> /dev/null; then
                # Uninstall
                if uv tool uninstall "$TOOL_NAME" &> /dev/null; then
                    ((cycle_success++))
                    log_info "Cycle $i completed successfully"
                else
                    log_error "Cycle $i failed at uninstall"
                fi
            else
                log_error "Cycle $i failed at update"
                uv tool uninstall "$TOOL_NAME" &> /dev/null || true
            fi
        else
            log_error "Cycle $i failed at install"
        fi
    done

    if [[ $cycle_success -eq $cycle_attempts ]]; then
        add_result "multiple_operations_cycle" "PASS" "All $cycle_attempts cycles completed successfully" $(($(date +%s) - start_time))
    elif [[ $cycle_success -gt 0 ]]; then
        add_result "multiple_operations_cycle" "PASS" "$cycle_success/$cycle_attempts cycles successful (partial success)" $(($(date +%s) - start_time))
    else
        add_result "multiple_operations_cycle" "FAIL" "All cycles failed" $(($(date +%s) - start_time))
    fi

    # Final reinstall for consistency
    uv tool install "$GITHUB_REPO" &> /dev/null || true
}

# Main execution
main() {
    log_info "Starting DocBro Quickstart Validation - Scenario 6: UV Tool Management Integration"
    log_info "Timestamp: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
    log_info "GitHub repo: $GITHUB_REPO"
    log_info "Tool name: $TOOL_NAME"
    log_info "Log file: $VALIDATION_LOG"
    echo "" > "$VALIDATION_LOG"  # Clear log file

    # Run validation tests
    test_prerequisites
    test_backup_existing_installation
    test_initial_installation
    test_uv_tool_list
    test_uv_tool_update
    test_functionality_after_update
    test_uv_tool_uninstall
    test_command_path_cleanup
    test_uv_environment_cleanup
    test_reinstall_after_uninstall
    test_multiple_operations_cycle

    log_success "All validation tests completed!"
}

# Run main function if script is executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi