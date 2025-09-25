#!/bin/bash
# =============================================================================
# DocBro Quickstart Validation - Master Runner
# =============================================================================
# Description: Master script to run all 7 quickstart validation scenarios.
# Can run scenarios individually or all together with comprehensive reporting.
#
# Usage:
#   ./run-all-scenarios.sh                    # Run all scenarios
#   ./run-all-scenarios.sh 1 3 5             # Run specific scenarios
#   ./run-all-scenarios.sh --list             # List available scenarios
#   ./run-all-scenarios.sh --help             # Show help
#   ./run-all-scenarios.sh --parallel         # Run scenarios in parallel
#   ./run-all-scenarios.sh --dry-run          # Show what would be executed
# =============================================================================

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MASTER_LOG="${SCRIPT_DIR}/master-validation.log"
MASTER_RESULT="${SCRIPT_DIR}/master-validation-result.json"
SUMMARY_REPORT="${SCRIPT_DIR}/validation-summary.md"

# Default settings
RUN_PARALLEL=false
DRY_RUN=false
VERBOSE=false
TIMEOUT_PER_SCENARIO=900  # 15 minutes per scenario

# Scenario definitions
SCENARIOS=(
    "1:scenario-1-fresh-install.sh:Fresh Installation (Happy Path)"
    "2:scenario-2-critical-decisions.sh:Installation with Critical Decisions"
    "3:scenario-3-existing-upgrade.sh:Existing Installation Upgrade"
    "4:scenario-4-system-requirements.sh:System Requirements Failure"
    "5:scenario-5-service-failure.sh:Service Setup Failure"
    "6:scenario-6-uv-tool-management.sh:UV Tool Management Integration"
    "7:scenario-7-cross-platform.sh:Cross-Platform Installation"
)

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Result tracking using files instead of associative arrays for bash 3.2 compatibility
RESULTS_DIR="${SCRIPT_DIR}/.results"
mkdir -p "$RESULTS_DIR"

# Helper functions for result tracking
set_scenario_result() {
    local scenario_num="$1"
    local status="$2"
    echo "$status" > "$RESULTS_DIR/result_$scenario_num"
}

get_scenario_result() {
    local scenario_num="$1"
    if [[ -f "$RESULTS_DIR/result_$scenario_num" ]]; then
        cat "$RESULTS_DIR/result_$scenario_num"
    else
        echo "UNKNOWN"
    fi
}

set_scenario_duration() {
    local scenario_num="$1"
    local duration="$2"
    echo "$duration" > "$RESULTS_DIR/duration_$scenario_num"
}

get_scenario_duration() {
    local scenario_num="$1"
    if [[ -f "$RESULTS_DIR/duration_$scenario_num" ]]; then
        cat "$RESULTS_DIR/duration_$scenario_num"
    else
        echo "0"
    fi
}

set_scenario_details() {
    local scenario_num="$1"
    local details="$2"
    echo "$details" > "$RESULTS_DIR/details_$scenario_num"
}

get_scenario_details() {
    local scenario_num="$1"
    if [[ -f "$RESULTS_DIR/details_$scenario_num" ]]; then
        cat "$RESULTS_DIR/details_$scenario_num"
    else
        echo ""
    fi
}

get_all_scenario_numbers() {
    local numbers=()
    for result_file in "$RESULTS_DIR"/result_*; do
        if [[ -f "$result_file" ]]; then
            local num=$(basename "$result_file" | sed 's/result_//')
            numbers+=("$num")
        fi
    done
    printf '%s\n' "${numbers[@]}" | sort -n
}

master_start_time=$(date +%s)

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1" | tee -a "${MASTER_LOG}"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1" | tee -a "${MASTER_LOG}"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1" | tee -a "${MASTER_LOG}"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "${MASTER_LOG}"
}

log_scenario() {
    echo -e "${PURPLE}[SCENARIO]${NC} $1" | tee -a "${MASTER_LOG}"
}

log_header() {
    echo -e "${CYAN}[MASTER]${NC} $1" | tee -a "${MASTER_LOG}"
}

# Help function
show_help() {
    cat << EOF
DocBro Quickstart Validation - Master Runner

USAGE:
    $0 [OPTIONS] [SCENARIO_NUMBERS...]

DESCRIPTION:
    Runs DocBro quickstart validation scenarios to test all aspects of the
    UV command installation feature. Can run individual scenarios or all
    scenarios with comprehensive reporting.

OPTIONS:
    --help              Show this help message
    --list              List all available scenarios
    --parallel          Run scenarios in parallel (faster but less isolated)
    --dry-run           Show what would be executed without running
    --verbose           Enable verbose output
    --timeout SECONDS   Set timeout per scenario (default: 900)

SCENARIO NUMBERS:
    1    Fresh Installation (Happy Path)
    2    Installation with Critical Decisions
    3    Existing Installation Upgrade
    4    System Requirements Failure
    5    Service Setup Failure
    6    UV Tool Management Integration
    7    Cross-Platform Installation

EXAMPLES:
    $0                  # Run all scenarios sequentially
    $0 1 2 3           # Run scenarios 1, 2, and 3 only
    $0 --parallel      # Run all scenarios in parallel
    $0 --dry-run 1 5   # Show what running scenarios 1 and 5 would do

OUTPUT:
    - Individual scenario logs: scenario-N-*.log
    - Individual scenario results: scenario-N-*-result.json
    - Master log: master-validation.log
    - Master results: master-validation-result.json
    - Summary report: validation-summary.md

EOF
}

# List scenarios function
list_scenarios() {
    echo "Available Validation Scenarios:"
    echo "================================"
    for scenario in "${SCENARIOS[@]}"; do
        local num=$(echo "$scenario" | cut -d: -f1)
        local desc=$(echo "$scenario" | cut -d: -f3)
        printf "%2s. %s\n" "$num" "$desc"
    done
    echo ""
    echo "Use scenario numbers as arguments to run specific scenarios."
}

# Parse command line arguments
parse_arguments() {
    local scenarios_to_run=()

    while [[ $# -gt 0 ]]; do
        case $1 in
            --help|-h)
                show_help
                return 0 2>/dev/null || exit 0
                ;;
            --list|-l)
                list_scenarios
                return 0 2>/dev/null || exit 0
                ;;
            --parallel|-p)
                RUN_PARALLEL=true
                shift
                ;;
            --dry-run|-n)
                DRY_RUN=true
                shift
                ;;
            --verbose|-v)
                VERBOSE=true
                shift
                ;;
            --timeout)
                TIMEOUT_PER_SCENARIO="$2"
                shift 2
                ;;
            [1-7])
                scenarios_to_run+=("$1")
                shift
                ;;
            *)
                echo "Error: Unknown option: $1"
                echo "Use --help for usage information."
                return 1 2>/dev/null || exit 1
                ;;
        esac
    done

    if [[ ${#scenarios_to_run[@]} -eq 0 ]]; then
        # Default: run all scenarios
        scenarios_to_run=(1 2 3 4 5 6 7)
    fi

    echo "${scenarios_to_run[@]}"
}

# Get scenario info
get_scenario_info() {
    local scenario_num="$1"
    for scenario in "${SCENARIOS[@]}"; do
        local num=$(echo "$scenario" | cut -d: -f1)
        if [[ "$num" == "$scenario_num" ]]; then
            echo "$scenario"
            return 0
        fi
    done
    return 1
}

# Run single scenario
run_scenario() {
    local scenario_num="$1"
    local scenario_info
    scenario_info=$(get_scenario_info "$scenario_num")

    if [[ -z "$scenario_info" ]]; then
        log_error "Invalid scenario number: $scenario_num"
        return 1
    fi

    local script_name=$(echo "$scenario_info" | cut -d: -f2)
    local description=$(echo "$scenario_info" | cut -d: -f3)
    local script_path="${SCRIPT_DIR}/$script_name"

    if [[ ! -f "$script_path" ]]; then
        log_error "Scenario script not found: $script_path"
        set_scenario_result "$scenario_num" "ERROR"
        set_scenario_details "$scenario_num" "Script not found"
        return 1
    fi

    if [[ ! -x "$script_path" ]]; then
        log_error "Scenario script not executable: $script_path"
        set_scenario_result "$scenario_num" "ERROR"
        set_scenario_details "$scenario_num" "Script not executable"
        return 1
    fi

    log_scenario "Running Scenario $scenario_num: $description"

    local start_time=$(date +%s)
    local exit_code=0

    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "[DRY RUN] Would execute: $script_path"
        set_scenario_result "$scenario_num" "DRY_RUN"
        set_scenario_duration "$scenario_num" 0
        set_scenario_details "$scenario_num" "Dry run - not executed"
        return 0
    fi

    # Run scenario with timeout
    if timeout "${TIMEOUT_PER_SCENARIO}s" "$script_path"; then
        set_scenario_result "$scenario_num" "PASS"
        set_scenario_details "$scenario_num" "Completed successfully"
    else
        exit_code=$?
        if [[ $exit_code -eq 124 ]]; then
            set_scenario_result "$scenario_num" "TIMEOUT"
            set_scenario_details "$scenario_num" "Timed out after ${TIMEOUT_PER_SCENARIO}s"
            log_error "Scenario $scenario_num timed out"
        else
            set_scenario_result "$scenario_num" "FAIL"
            set_scenario_details "$scenario_num" "Failed with exit code $exit_code"
            log_error "Scenario $scenario_num failed with exit code: $exit_code"
        fi
    fi

    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    set_scenario_duration "$scenario_num" "$duration"

    log_info "Scenario $scenario_num completed in ${duration}s with result: $(get_scenario_result "$scenario_num")"

    return $exit_code
}

# Run scenarios in parallel
run_scenarios_parallel() {
    local scenarios=("$@")
    local pids=()

    log_header "Running ${#scenarios[@]} scenarios in parallel..."

    for scenario_num in "${scenarios[@]}"; do
        run_scenario "$scenario_num" &
        pids+=($!)
        log_info "Started scenario $scenario_num (PID: ${pids[-1]})"
    done

    # Wait for all scenarios to complete
    local failed_scenarios=0
    for i in "${!pids[@]}"; do
        local pid=${pids[$i]}
        local scenario_num=${scenarios[$i]}

        if wait "$pid"; then
            log_success "Scenario $scenario_num (PID: $pid) completed successfully"
        else
            log_error "Scenario $scenario_num (PID: $pid) failed"
            ((failed_scenarios++))
        fi
    done

    return $failed_scenarios
}

# Run scenarios sequentially
run_scenarios_sequential() {
    local scenarios=("$@")
    local failed_scenarios=0

    log_header "Running ${#scenarios[@]} scenarios sequentially..."

    for scenario_num in "${scenarios[@]}"; do
        if ! run_scenario "$scenario_num"; then
            ((failed_scenarios++))
            log_error "Scenario $scenario_num failed - continuing with next scenario"
        fi

        # Brief pause between scenarios
        if [[ "$failed_scenarios" -eq 0 ]]; then
            sleep 2
        fi
    done

    return $failed_scenarios
}

# Generate comprehensive report
generate_master_report() {
    local end_time=$(date +%s)
    local total_duration=$((end_time - master_start_time))

    local scenario_numbers
    scenario_numbers=($(get_all_scenario_numbers))
    local total_scenarios=${#scenario_numbers[@]}
    local passed=0
    local failed=0
    local errors=0
    local timeouts=0
    local dry_runs=0

    for scenario_num in "${scenario_numbers[@]}"; do
        local result
        result=$(get_scenario_result "$scenario_num")
        case "$result" in
            PASS) ((passed++)) ;;
            FAIL) ((failed++)) ;;
            ERROR) ((errors++)) ;;
            TIMEOUT) ((timeouts++)) ;;
            DRY_RUN) ((dry_runs++)) ;;
        esac
    done

    # Create JSON report
    cat > "$MASTER_RESULT" << EOF
{
  "master_validation_report": {
    "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
    "total_duration_seconds": $total_duration,
    "execution_mode": "$([ "$RUN_PARALLEL" == "true" ] && echo "parallel" || echo "sequential")",
    "dry_run": $([[ "$DRY_RUN" == "true" ]] && echo "true" || echo "false"),
    "timeout_per_scenario": $TIMEOUT_PER_SCENARIO
  },
  "summary": {
    "total_scenarios": $total_scenarios,
    "passed": $passed,
    "failed": $failed,
    "errors": $errors,
    "timeouts": $timeouts,
    "dry_runs": $dry_runs,
    "success_rate": $(echo "scale=2; $passed * 100 / ($total_scenarios - $dry_runs)" | bc -l 2>/dev/null || echo "0")
  },
  "scenario_results": {
EOF

    local first=true
    for scenario_num in "${scenario_numbers[@]}"; do
        if [[ "$first" == "true" ]]; then
            first=false
        else
            echo "," >> "$MASTER_RESULT"
        fi

        local scenario_info
        scenario_info=$(get_scenario_info "$scenario_num")
        local description=$(echo "$scenario_info" | cut -d: -f3)
        local result
        result=$(get_scenario_result "$scenario_num")
        local duration
        duration=$(get_scenario_duration "$scenario_num")
        local details
        details=$(get_scenario_details "$scenario_num")

        cat >> "$MASTER_RESULT" << EOF
    "scenario_$scenario_num": {
      "description": "$description",
      "result": "$result",
      "duration_seconds": $duration,
      "details": "$details"
    }
EOF
    done

    cat >> "$MASTER_RESULT" << EOF
  },
  "system_info": {
    "os": "$(uname -s)",
    "arch": "$(uname -m)",
    "python_version": "$(python3 --version 2>/dev/null || echo "Not available")",
    "uv_version": "$(uv --version 2>/dev/null || echo "Not available")",
    "shell": "$SHELL",
    "user": "$USER",
    "hostname": "$(hostname)"
  }
}
EOF

    log_success "Master JSON report generated: $MASTER_RESULT"
}

# Generate markdown summary
generate_summary_report() {
    cat > "$SUMMARY_REPORT" << EOF
# DocBro Quickstart Validation Summary

**Generated:** $(date -u +"%Y-%m-%d %H:%M:%S UTC")
**Execution Mode:** $([[ "$RUN_PARALLEL" == "true" ]] && echo "Parallel" || echo "Sequential")
**Total Duration:** $(($(date +%s) - master_start_time))s

## Results Overview

EOF

    local scenario_numbers
    scenario_numbers=($(get_all_scenario_numbers))
    local total_scenarios=${#scenario_numbers[@]}
    local passed=0
    local failed=0
    local errors=0
    local timeouts=0

    for scenario_num in "${scenario_numbers[@]}"; do
        local result
        result=$(get_scenario_result "$scenario_num")
        case "$result" in
            PASS) ((passed++)) ;;
            FAIL) ((failed++)) ;;
            ERROR) ((errors++)) ;;
            TIMEOUT) ((timeouts++)) ;;
        esac
    done

    cat >> "$SUMMARY_REPORT" << EOF
| Status | Count | Percentage |
|--------|-------|------------|
| ✅ Passed | $passed | $(echo "scale=1; $passed * 100 / $total_scenarios" | bc -l 2>/dev/null || echo "0")% |
| ❌ Failed | $failed | $(echo "scale=1; $failed * 100 / $total_scenarios" | bc -l 2>/dev/null || echo "0")% |
| ⚠️ Errors | $errors | $(echo "scale=1; $errors * 100 / $total_scenarios" | bc -l 2>/dev/null || echo "0")% |
| ⏱️ Timeouts | $timeouts | $(echo "scale=1; $timeouts * 100 / $total_scenarios" | bc -l 2>/dev/null || echo "0")% |
| **Total** | **$total_scenarios** | **100%** |

## Scenario Details

EOF

    for scenario_num in "${scenario_numbers[@]}"; do
        local scenario_info
        scenario_info=$(get_scenario_info "$scenario_num")
        local description=$(echo "$scenario_info" | cut -d: -f3)
        local result
        result=$(get_scenario_result "$scenario_num")
        local duration
        duration=$(get_scenario_duration "$scenario_num")
        local details
        details=$(get_scenario_details "$scenario_num")

        local status_icon
        case "$result" in
            PASS) status_icon="✅" ;;
            FAIL) status_icon="❌" ;;
            ERROR) status_icon="⚠️" ;;
            TIMEOUT) status_icon="⏱️" ;;
            DRY_RUN) status_icon="🧪" ;;
            *) status_icon="❓" ;;
        esac

        cat >> "$SUMMARY_REPORT" << EOF
### ${status_icon} Scenario $scenario_num: $description

- **Result:** $result
- **Duration:** ${duration}s
- **Details:** $details

EOF
    done

    cat >> "$SUMMARY_REPORT" << EOF
## System Information

- **OS:** $(uname -s) $(uname -m)
- **Python:** $(python3 --version 2>/dev/null || echo "Not available")
- **UV:** $(uv --version 2>/dev/null || echo "Not available")
- **Shell:** $SHELL
- **User:** $USER
- **Hostname:** $(hostname)

## Files Generated

- Master log: \`$(basename "$MASTER_LOG")\`
- Master results: \`$(basename "$MASTER_RESULT")\`
- Individual scenario logs: \`scenario-*-*.log\`
- Individual scenario results: \`scenario-*-*-result.json\`

## Next Steps

EOF

    if [[ $failed -gt 0 ]] || [[ $errors -gt 0 ]] || [[ $timeouts -gt 0 ]]; then
        cat >> "$SUMMARY_REPORT" << EOF
⚠️ **Issues found!** Review the individual scenario logs and results for detailed information about failures.

Recommended actions:
1. Check individual scenario logs for specific error messages
2. Verify system requirements and dependencies
3. Re-run failed scenarios individually for focused debugging
4. Check the DocBro installation and configuration

EOF
    else
        cat >> "$SUMMARY_REPORT" << EOF
🎉 **All scenarios passed!** The DocBro quickstart UV installation feature is working correctly across all tested scenarios.

The system is ready for:
- Production UV-based installations
- End-user documentation updates
- Release deployment

EOF
    fi

    log_success "Summary report generated: $SUMMARY_REPORT"
}

# Main execution
main() {
    log_header "DocBro Quickstart Validation - Master Runner"
    log_header "============================================="
    echo "" > "$MASTER_LOG"  # Clear master log

    # Handle help and list first
    case "${1:-}" in
        --help|-h)
            show_help
            exit 0
            ;;
        --list|-l)
            list_scenarios
            exit 0
            ;;
        --dry-run|-n)
            DRY_RUN=true
            ;;
    esac

    local scenarios_to_run
    scenarios_to_run=($(parse_arguments "$@"))

    log_info "Scenarios to run: ${scenarios_to_run[*]}"
    log_info "Execution mode: $([[ "$RUN_PARALLEL" == "true" ]] && echo "Parallel" || echo "Sequential")"
    log_info "Dry run: $([[ "$DRY_RUN" == "true" ]] && echo "Yes" || echo "No")"
    log_info "Timeout per scenario: ${TIMEOUT_PER_SCENARIO}s"
    log_info "Master log: $MASTER_LOG"

    if [[ "$DRY_RUN" == "true" ]]; then
        log_warning "DRY RUN MODE - No scenarios will be executed"
    fi

    # Validate scenario scripts exist
    local missing_scripts=0
    for scenario_num in "${scenarios_to_run[@]}"; do
        local scenario_info
        scenario_info=$(get_scenario_info "$scenario_num")
        if [[ -z "$scenario_info" ]]; then
            log_error "Invalid scenario number: $scenario_num"
            ((missing_scripts++))
            continue
        fi

        local script_name=$(echo "$scenario_info" | cut -d: -f2)
        local script_path="${SCRIPT_DIR}/$script_name"

        if [[ ! -f "$script_path" ]]; then
            log_error "Scenario script not found: $script_path"
            ((missing_scripts++))
        elif [[ ! -x "$script_path" ]]; then
            log_error "Scenario script not executable: $script_path"
            ((missing_scripts++))
        fi
    done

    if [[ $missing_scripts -gt 0 ]] && [[ "$DRY_RUN" == "false" ]]; then
        log_error "$missing_scripts scenario scripts are missing or not executable"
        exit 1
    fi

    # Initialize scenario results for requested scenarios
    for scenario_num in "${scenarios_to_run[@]}"; do
        set_scenario_result "$scenario_num" "PENDING"
        set_scenario_duration "$scenario_num" 0
        set_scenario_details "$scenario_num" ""
    done

    # Run scenarios
    local execution_exit_code=0
    if [[ "$RUN_PARALLEL" == "true" ]]; then
        run_scenarios_parallel "${scenarios_to_run[@]}" || execution_exit_code=$?
    else
        run_scenarios_sequential "${scenarios_to_run[@]}" || execution_exit_code=$?
    fi

    # Generate reports
    generate_master_report
    generate_summary_report

    # Final summary
    local scenario_numbers
    scenario_numbers=($(get_all_scenario_numbers))
    local total_scenarios=${#scenario_numbers[@]}
    local passed=0
    local failed=0

    for scenario_num in "${scenario_numbers[@]}"; do
        local result
        result=$(get_scenario_result "$scenario_num")
        case "$result" in
            PASS) ((passed++)) ;;
            FAIL|ERROR|TIMEOUT) ((failed++)) ;;
        esac
    done

    log_header "============================================="
    if [[ "$DRY_RUN" == "true" ]]; then
        log_success "DRY RUN completed - $total_scenarios scenarios would be executed"
    elif [[ $failed -eq 0 ]]; then
        log_success "ALL SCENARIOS PASSED! ($passed/$total_scenarios)"
        log_success "DocBro quickstart validation completed successfully"
    else
        log_error "VALIDATION FAILED! ($passed passed, $failed failed out of $total_scenarios total)"
        log_error "Check individual scenario logs for details"
    fi

    log_info "Reports generated:"
    log_info "- Master results: $MASTER_RESULT"
    log_info "- Summary report: $SUMMARY_REPORT"
    log_info "- Master log: $MASTER_LOG"

    # Cleanup results directory
    rm -rf "$RESULTS_DIR" 2>/dev/null || true

    if [[ $failed -gt 0 ]]; then
        exit 1
    else
        exit 0
    fi
}

# Run main function if script is executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi