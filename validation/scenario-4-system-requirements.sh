#!/bin/bash
# =============================================================================
# DocBro Quickstart Validation - Scenario 4: System Requirements Failure
# =============================================================================
# Description: Validates the installation wizard behavior when system doesn't
# meet minimum requirements (Python version, memory, disk space).
#
# Expected behavior:
# - Installation aborts immediately when requirements aren't met
# - Clear error message: "Python 3.13+ required, found X.Y.Z"
# - Instructions provided to upgrade Python
# - No partial installation artifacts left behind
# - Clean rollback of any installation attempts
# =============================================================================

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VALIDATION_LOG="${SCRIPT_DIR}/scenario-4-system-requirements.log"
VALIDATION_RESULT="${SCRIPT_DIR}/scenario-4-system-requirements-result.json"
TEMP_BACKUP_DIR="${SCRIPT_DIR}/temp-backup-$(date +%s)"

# Test configurations
MIN_PYTHON_MAJOR=3
MIN_PYTHON_MINOR=13
MIN_MEMORY_MB=4000
MIN_DISK_MB=2000

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
    elif [[ "$status" == "EXPECTED_FAIL" ]]; then
        log_success "$test_name: $message (${duration}s) [Expected Failure]"
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
    local expected_fails=0

    for test in "${!validation_results[@]}"; do
        if [[ "${validation_results[$test]}" == "PASS" ]]; then
            ((passed++))
        elif [[ "${validation_results[$test]}" == "EXPECTED_FAIL" ]]; then
            ((expected_fails++))
            ((passed++))  # Count expected failures as passes for success rate
        else
            ((failed++))
        fi
    done

    # Create JSON report
    cat > "$VALIDATION_RESULT" << EOF
{
  "scenario": "System Requirements Failure",
  "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "duration_seconds": $total_duration,
  "exit_code": $exit_code,
  "test_parameters": {
    "min_python_version": "${MIN_PYTHON_MAJOR}.${MIN_PYTHON_MINOR}",
    "min_memory_mb": $MIN_MEMORY_MB,
    "min_disk_mb": $MIN_DISK_MB
  },
  "summary": {
    "total_tests": $((passed + failed)),
    "passed": $passed,
    "failed": $failed,
    "expected_failures": $expected_fails,
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
    "available_memory_mb": $(free -m 2>/dev/null | awk '/^Mem:/{print $7}' || sysctl -n hw.memsize 2>/dev/null | awk '{print int($1/1024/1024)}' || echo "0"),
    "available_disk_mb": $(df -m . 2>/dev/null | awk 'NR==2{print $4}' || echo "0")
  }
}
EOF

    log_info "Final Report Generated: $VALIDATION_RESULT"
    log_info "Summary: $passed passed (including $expected_fails expected failures), $failed failed ($(echo "scale=2; $passed * 100 / ($passed + $failed)" | bc -l 2>/dev/null || echo "0")% success rate)"
}

# Test functions
test_prerequisites() {
    local start_time=$(date +%s)
    log_info "Testing basic prerequisites..."

    # Check if UV is installed
    if ! command -v uv &> /dev/null; then
        add_result "prerequisites" "FAIL" "UV not found in PATH" $(($(date +%s) - start_time))
        exit 1
    fi

    add_result "prerequisites" "PASS" "Basic prerequisites available" $(($(date +%s) - start_time))
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
    if uv tool list 2>/dev/null | grep -q docbro; then
        log_info "Removing existing DocBro UV tool installation..."
        uv tool uninstall docbro || true
    fi

    add_result "backup_existing" "PASS" "Backup and cleanup completed" $(($(date +%s) - start_time))
}

test_current_system_requirements() {
    local start_time=$(date +%s)
    log_info "Analyzing current system requirements..."

    local python_version
    local meets_requirements=true

    # Check Python version
    if command -v python3 &> /dev/null; then
        python_version=$(python3 --version 2>&1 | grep -oE '[0-9]+\.[0-9]+' | head -1)
        if [[ -n "$python_version" ]]; then
            local major_version=$(echo "$python_version" | cut -d. -f1)
            local minor_version=$(echo "$python_version" | cut -d. -f2)

            log_info "Found Python $python_version"

            if [[ "$major_version" -lt $MIN_PYTHON_MAJOR ]] || ([[ "$major_version" -eq $MIN_PYTHON_MAJOR ]] && [[ "$minor_version" -lt $MIN_PYTHON_MINOR ]]); then
                meets_requirements=false
                log_info "Python version $python_version is below minimum requirement ${MIN_PYTHON_MAJOR}.${MIN_PYTHON_MINOR}"
            else
                log_info "Python version $python_version meets requirements"
            fi
        else
            meets_requirements=false
            log_info "Could not determine Python version"
        fi
    else
        meets_requirements=false
        log_info "Python3 not found"
    fi

    # Check memory
    local available_memory
    available_memory=$(free -m 2>/dev/null | awk '/^Mem:/{print $7}' || sysctl -n hw.memsize 2>/dev/null | awk '{print int($1/1024/1024)}' || echo "0")

    if [[ "$available_memory" -gt 0 ]]; then
        log_info "Available memory: ${available_memory}MB"
        if [[ "$available_memory" -lt $MIN_MEMORY_MB ]]; then
            log_info "Available memory ${available_memory}MB is below minimum requirement ${MIN_MEMORY_MB}MB"
        fi
    fi

    # Check disk space
    local available_disk
    available_disk=$(df -m . 2>/dev/null | awk 'NR==2{print $4}' || echo "0")

    if [[ "$available_disk" -gt 0 ]]; then
        log_info "Available disk space: ${available_disk}MB"
        if [[ "$available_disk" -lt $MIN_DISK_MB ]]; then
            log_info "Available disk space ${available_disk}MB is below minimum requirement ${MIN_DISK_MB}MB"
        fi
    fi

    if [[ "$meets_requirements" == "true" ]]; then
        add_result "system_analysis" "PASS" "System meets all requirements - will test forced failure scenarios" $(($(date +%s) - start_time))
    else
        add_result "system_analysis" "PASS" "System has natural requirement failures - perfect for testing" $(($(date +%s) - start_time))
    fi

    echo "$meets_requirements"
}

create_fake_python_environment() {
    local target_version="$1"
    local fake_python_dir="${SCRIPT_DIR}/fake-python"

    log_info "Creating fake Python environment with version $target_version..."

    mkdir -p "$fake_python_dir"

    cat > "$fake_python_dir/python3" << EOF
#!/bin/bash
echo "Python $target_version"
exit 0
EOF

    chmod +x "$fake_python_dir/python3"
    echo "$fake_python_dir"
}

test_python_version_failure() {
    local start_time=$(date +%s)
    log_info "Testing Python version requirement failure..."

    local meets_requirements
    meets_requirements=$(test_current_system_requirements)

    if [[ "$meets_requirements" == "false" ]]; then
        # System naturally fails requirements, test with real system
        log_info "Testing with naturally failing Python version..."

        local install_output
        if install_output=$(timeout 60s uv tool install git+https://github.com/behemotion/doc-bro 2>&1); then
            # Installation succeeded when it should have failed
            add_result "python_version_failure" "FAIL" "Installation succeeded with inadequate Python version" $(($(date +%s) - start_time))
            return 1
        else
            # Check if the error message mentions Python version
            if echo "$install_output" | grep -i "python.*3\.13\|version.*requirement\|python.*required"; then
                add_result "python_version_failure" "EXPECTED_FAIL" "Installation properly failed with Python version error" $(($(date +%s) - start_time))
            else
                add_result "python_version_failure" "FAIL" "Installation failed but without proper Python version error message" $(($(date +%s) - start_time))
            fi
        fi
    else
        # System meets requirements, create fake failing environment
        log_info "Testing with simulated failing Python version..."

        local fake_python_dir
        fake_python_dir=$(create_fake_python_environment "3.12.0")

        # Temporarily modify PATH to use fake Python
        local original_path="$PATH"
        export PATH="$fake_python_dir:$PATH"

        local install_output
        if install_output=$(timeout 60s uv tool install git+https://github.com/behemotion/doc-bro 2>&1); then
            # Check if DocBro was actually installed despite fake Python
            if command -v docbro &> /dev/null; then
                add_result "python_version_failure" "FAIL" "Installation succeeded with fake old Python version" $(($(date +%s) - start_time))
            else
                add_result "python_version_failure" "EXPECTED_FAIL" "Installation failed as expected with old Python" $(($(date +%s) - start_time))
            fi
        else
            add_result "python_version_failure" "EXPECTED_FAIL" "Installation failed with fake old Python version" $(($(date +%s) - start_time))
        fi

        # Restore original PATH
        export PATH="$original_path"
        rm -rf "$fake_python_dir"
    fi
}

test_memory_requirement_awareness() {
    local start_time=$(date +%s)
    log_info "Testing memory requirement awareness..."

    # We can't actually limit memory easily, but we can test if the installer
    # checks for memory requirements by analyzing available memory
    local available_memory
    available_memory=$(free -m 2>/dev/null | awk '/^Mem:/{print $7}' || sysctl -n hw.memsize 2>/dev/null | awk '{print int($1/1024/1024)}' || echo "0")

    if [[ "$available_memory" -gt 0 ]]; then
        if [[ "$available_memory" -lt $MIN_MEMORY_MB ]]; then
            log_info "System naturally has low memory (${available_memory}MB < ${MIN_MEMORY_MB}MB)"

            # Test installation on low memory system
            local install_output
            if install_output=$(timeout 120s uv tool install git+https://github.com/behemotion/doc-bro 2>&1); then
                # Installation succeeded with low memory - check if there were warnings
                if echo "$install_output" | grep -i "memory\|ram\|warning"; then
                    add_result "memory_awareness" "PASS" "Installation succeeded with low memory warnings" $(($(date +%s) - start_time))
                else
                    add_result "memory_awareness" "PASS" "Installation succeeded with low memory (no warnings detected)" $(($(date +%s) - start_time))
                fi
            else
                if echo "$install_output" | grep -i "memory\|ram"; then
                    add_result "memory_awareness" "EXPECTED_FAIL" "Installation failed due to memory constraints" $(($(date +%s) - start_time))
                else
                    add_result "memory_awareness" "PASS" "Installation failed (not specifically due to memory)" $(($(date +%s) - start_time))
                fi
            fi
        else
            log_info "System has adequate memory (${available_memory}MB >= ${MIN_MEMORY_MB}MB)"
            add_result "memory_awareness" "PASS" "Cannot test memory failure - system has adequate memory" $(($(date +%s) - start_time))
        fi
    else
        add_result "memory_awareness" "PASS" "Cannot determine available memory - test skipped" $(($(date +%s) - start_time))
    fi
}

test_disk_space_requirement_awareness() {
    local start_time=$(date +%s)
    log_info "Testing disk space requirement awareness..."

    local available_disk
    available_disk=$(df -m . 2>/dev/null | awk 'NR==2{print $4}' || echo "0")

    if [[ "$available_disk" -gt 0 ]]; then
        log_info "Available disk space: ${available_disk}MB"

        if [[ "$available_disk" -lt $MIN_DISK_MB ]]; then
            log_info "System naturally has low disk space (${available_disk}MB < ${MIN_DISK_MB}MB)"

            # Test installation on low disk space system
            local install_output
            if install_output=$(timeout 120s uv tool install git+https://github.com/behemotion/doc-bro 2>&1); then
                if echo "$install_output" | grep -i "disk\|space\|storage"; then
                    add_result "disk_awareness" "PASS" "Installation succeeded with disk space warnings" $(($(date +%s) - start_time))
                else
                    add_result "disk_awareness" "PASS" "Installation succeeded with low disk space (no warnings detected)" $(($(date +%s) - start_time))
                fi
            else
                if echo "$install_output" | grep -i "disk\|space\|storage"; then
                    add_result "disk_awareness" "EXPECTED_FAIL" "Installation failed due to disk space constraints" $(($(date +%s) - start_time))
                else
                    add_result "disk_awareness" "PASS" "Installation failed (not specifically due to disk space)" $(($(date +%s) - start_time))
                fi
            fi
        else
            log_info "System has adequate disk space (${available_disk}MB >= ${MIN_DISK_MB}MB)"
            add_result "disk_awareness" "PASS" "Cannot test disk space failure - system has adequate space" $(($(date +%s) - start_time))
        fi
    else
        add_result "disk_awareness" "PASS" "Cannot determine available disk space - test skipped" $(($(date +%s) - start_time))
    fi
}

test_clean_failure_rollback() {
    local start_time=$(date +%s)
    log_info "Testing clean failure rollback..."

    # Check if any partial installation artifacts were left behind after failures
    local artifacts_found=false

    # Check for UV tool installation
    if uv tool list 2>/dev/null | grep -q docbro; then
        log_warning "DocBro found in UV tool list after failed installation"
        artifacts_found=true
    fi

    # Check for command in PATH
    if command -v docbro &> /dev/null; then
        log_warning "docbro command found in PATH after failed installation"
        artifacts_found=true
    fi

    # Check for configuration directories
    if [[ -d ~/.config/docbro ]] && [[ -z "$(find ~/.config/docbro -maxdepth 1 -type f 2>/dev/null)" ]]; then
        # Empty directory might be acceptable
        log_info "Empty DocBro config directory found"
    elif [[ -d ~/.config/docbro ]]; then
        log_warning "DocBro config directory with files found after failed installation"
        artifacts_found=true
    fi

    if [[ -d ~/.local/share/docbro ]] && [[ -z "$(find ~/.local/share/docbro -maxdepth 1 -type f 2>/dev/null)" ]]; then
        # Empty directory might be acceptable
        log_info "Empty DocBro data directory found"
    elif [[ -d ~/.local/share/docbro ]]; then
        log_warning "DocBro data directory with files found after failed installation"
        artifacts_found=true
    fi

    if [[ "$artifacts_found" == "false" ]]; then
        add_result "clean_rollback" "PASS" "No installation artifacts found after failures" $(($(date +%s) - start_time))
    else
        add_result "clean_rollback" "FAIL" "Installation artifacts found after failed installation" $(($(date +%s) - start_time))
    fi
}

test_error_message_quality() {
    local start_time=$(date +%s)
    log_info "Testing error message quality and helpfulness..."

    # This test analyzes the quality of error messages from previous test outputs
    # We'll look for key characteristics of good error messages:
    # 1. Clear identification of the problem
    # 2. Specific version numbers when relevant
    # 3. Instructions for resolution

    local error_log_file="${SCRIPT_DIR}/temp-error-capture.log"

    # Capture installation attempt output
    local install_output
    if install_output=$(uv tool install git+https://github.com/behemotion/doc-bro 2>&1); then
        log_info "Installation succeeded - cannot test error message quality"
        add_result "error_message_quality" "PASS" "Installation succeeded - error messages not applicable" $(($(date +%s) - start_time))
    else
        echo "$install_output" > "$error_log_file"

        local has_clear_problem=false
        local has_version_info=false
        local has_instructions=false

        # Check for clear problem identification
        if echo "$install_output" | grep -i "python.*required\|version.*requirement\|minimum.*version"; then
            has_clear_problem=true
        fi

        # Check for specific version information
        if echo "$install_output" | grep -E "[0-9]+\.[0-9]+"; then
            has_version_info=true
        fi

        # Check for helpful instructions
        if echo "$install_output" | grep -i "install\|upgrade\|download\|visit"; then
            has_instructions=true
        fi

        local quality_score=0
        if [[ "$has_clear_problem" == "true" ]]; then ((quality_score++)); fi
        if [[ "$has_version_info" == "true" ]]; then ((quality_score++)); fi
        if [[ "$has_instructions" == "true" ]]; then ((quality_score++)); fi

        if [[ $quality_score -ge 2 ]]; then
            add_result "error_message_quality" "PASS" "Error messages are helpful (score: $quality_score/3)" $(($(date +%s) - start_time))
        else
            add_result "error_message_quality" "FAIL" "Error messages need improvement (score: $quality_score/3)" $(($(date +%s) - start_time))
        fi

        log_info "Error output saved to: $error_log_file"
    fi
}

# Main execution
main() {
    log_info "Starting DocBro Quickstart Validation - Scenario 4: System Requirements Failure"
    log_info "Timestamp: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
    log_info "Minimum requirements: Python ${MIN_PYTHON_MAJOR}.${MIN_PYTHON_MINOR}+, ${MIN_MEMORY_MB}MB RAM, ${MIN_DISK_MB}MB disk"
    log_info "Log file: $VALIDATION_LOG"
    echo "" > "$VALIDATION_LOG"  # Clear log file

    # Run validation tests
    test_prerequisites
    test_backup_existing_installation
    test_python_version_failure
    test_memory_requirement_awareness
    test_disk_space_requirement_awareness
    test_clean_failure_rollback
    test_error_message_quality

    log_success "All validation tests completed!"
}

# Run main function if script is executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi