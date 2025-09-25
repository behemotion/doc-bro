# DocBro Performance Tests

This directory contains comprehensive performance tests to validate that DocBro installation meets the **<30 second installation requirement** specified in `quickstart.md`.

## Overview

The performance tests ensure that:

1. **Total installation time** is under 30 seconds
2. **System validation** completes in under 5 seconds
3. **Service detection** handles timeouts appropriately
4. **Critical decision handling** responds quickly
5. **Installation components** perform within acceptable limits

## Test Structure

### Core Test Files

- **`test_speed.py`**: Main performance test suite with pytest-benchmark integration
- **`test_runner.py`**: Standalone test runner for environments without pytest-benchmark
- **`__init__.py`**: Performance test module initialization
- **`README.md`**: This documentation file

### Test Classes

#### `TestInstallationPerformance`
- **`test_full_installation_under_30_seconds`**: End-to-end installation timing (primary requirement)
- **`test_interactive_installation_performance`**: Interactive setup pathway timing

#### `TestSystemValidationPerformance`
- **`test_system_validation_under_5_seconds`**: System requirements validation timing
- **`test_individual_validation_components_performance`**: Component-level timing breakdown
- **`test_concurrent_validation_performance`**: Concurrent validation efficiency

#### `TestServiceDetectionPerformance`
- **`test_service_detection_timeout_handling`**: Timeout behavior validation
- **`test_service_detection_failure_handling`**: Fast failure handling

#### `TestCriticalDecisionPerformance`
- **`test_decision_detection_performance`**: Critical decision point detection speed
- **`test_port_conflict_detection_performance`**: Port conflict checking speed
- **`test_data_directory_check_performance`**: Data directory validation speed

#### `TestInstallationRegressionDetection`
- **`test_baseline_performance_metrics`**: Baseline performance tracking
- **`test_memory_usage_during_installation`**: Memory consumption monitoring

#### `TestRealisticSystemConditions`
- **`test_installation_with_limited_resources`**: Performance under resource constraints
- **`test_installation_with_slow_network`**: Network delay handling

#### `TestEndToEndPerformance`
- **`test_uv_tool_installation_performance`**: UV tool pathway timing
- **`test_development_installation_performance`**: Development setup timing

#### `TestDetailedTimingBreakdown`
- **`test_installation_phase_timing`**: Detailed phase-by-phase timing analysis

## Running Performance Tests

### Method 1: Full pytest-benchmark Suite

Requires `pytest-benchmark` dependency (included in `pyproject.toml`):

```bash
# Run all performance tests
pytest tests/performance/ -m performance -v

# Run specific test class
pytest tests/performance/test_speed.py::TestInstallationPerformance -v

# Run with benchmark output
pytest tests/performance/ -m performance -v --benchmark-only

# Run with detailed benchmark statistics
pytest tests/performance/ -m performance -v --benchmark-verbose
```

### Method 2: Standalone Test Runner

No additional dependencies required:

```bash
# Run validation suite
python tests/performance/test_runner.py

# Run from project root
python -m tests.performance.test_runner
```

## Performance Requirements

### Primary Requirements

| Component | Requirement | Test Coverage |
|-----------|------------|---------------|
| **Full Installation** | < 30 seconds | ✅ `test_full_installation_under_30_seconds` |
| **System Validation** | < 5 seconds | ✅ `test_system_validation_under_5_seconds` |
| **Service Detection** | Reasonable timeouts | ✅ `test_service_detection_timeout_handling` |
| **Critical Decisions** | < 2 seconds | ✅ `test_decision_detection_performance` |

### Component-Level Requirements

| Component | Requirement | Test Coverage |
|-----------|------------|---------------|
| Model Creation | < 10ms | ✅ `test_baseline_performance_metrics` |
| Port Checking | < 100ms | ✅ `test_port_conflict_detection_performance` |
| Directory Checks | < 50ms | ✅ `test_data_directory_check_performance` |
| Memory Usage | < 10MB increase | ✅ `test_memory_usage_during_installation` |

## Test Environment Configuration

### Environment Variables

```bash
# Enable performance mode
export DOCBRO_PERFORMANCE_MODE=true

# Reduce timeouts for testing
export DOCBRO_TEST_TIMEOUT=1

# Enable detailed timing
export DOCBRO_DEBUG_TIMING=true
```

### Pytest Markers

```bash
# Run only performance tests
pytest -m performance

# Exclude slow tests
pytest -m "performance and not slow"

# Run integration performance tests
pytest -m "performance and integration"
```

## Benchmark Configuration

### pytest-benchmark Settings

The tests use `pytest-benchmark` with these settings:

- **Rounds**: 3-5 for most tests (balances accuracy with speed)
- **Iterations**: 1-10 depending on test complexity
- **Warmup**: 1 round to avoid cold start effects

### Performance Thresholds

```python
INSTALLATION_TIMEOUT = 30.0      # 30 seconds max for full installation
SYSTEM_VALIDATION_TIMEOUT = 5.0  # 5 seconds max for system validation
SERVICE_DETECTION_TIMEOUT = 10.0 # 10 seconds max for service detection
CRITICAL_DECISION_TIMEOUT = 2.0  # 2 seconds max for decision handling
```

## Interpreting Results

### Successful Test Output

```
============================================================
DocBro Performance Test Suite
============================================================
Testing InstallationContext creation performance...
  Mean: 0.000004s
  ✓ PASS: Context creation is fast enough

Testing SystemRequirementsService performance...
  Mean: 0.013291s
  ✓ PASS: System validation is fast enough

Testing complete mocked installation workflow...
  Mean: 0.075900s
  ✓ PASS: Mock installation workflow is fast enough

============================================================
All performance tests PASSED! ✓
Installation should meet <30s requirement.
============================================================
```

### Performance Regression Detection

If performance degrades:

1. **Compare timing results** with previous runs
2. **Check system resources** (CPU, memory, disk)
3. **Verify test environment** consistency
4. **Profile slow components** using detailed breakdown tests

### Troubleshooting Slow Performance

#### Common Issues

1. **System resource constraints**:
   - Low available memory (< 4GB)
   - Limited disk space (< 2GB)
   - High CPU usage from other processes

2. **Network connectivity issues**:
   - Slow DNS resolution
   - Firewall blocking service checks
   - Network timeouts

3. **File system performance**:
   - Slow disk I/O
   - Network-mounted directories
   - Antivirus scanning

#### Optimization Strategies

1. **Parallel execution**: Service detection runs concurrently
2. **Timeout management**: Aggressive timeouts for external services
3. **Caching**: System information cached between checks
4. **Lazy evaluation**: Only check services when needed

## Contributing Performance Tests

### Adding New Tests

1. **Follow naming convention**: `test_*_performance`
2. **Use appropriate markers**: `@pytest.mark.performance`
3. **Set realistic thresholds**: Based on requirement analysis
4. **Include error handling**: Graceful degradation in sandbox environments

### Test Categories

- **Unit Performance**: Individual component timing
- **Integration Performance**: Service interaction timing
- **End-to-End Performance**: Complete workflow timing
- **Regression Detection**: Performance tracking over time

### Example Test Structure

```python
@pytest.mark.performance
def test_component_performance(self, benchmark):
    """Test component meets performance requirements."""

    def component_operation():
        # Simulate component work
        return perform_operation()

    result = benchmark.pedantic(
        component_operation,
        rounds=5,
        iterations=3
    )

    # Validate performance threshold
    assert benchmark.stats["mean"] < COMPONENT_TIMEOUT
    assert result is not None  # Validate correctness
```

## Integration with CI/CD

### GitHub Actions

Performance tests can be integrated into CI/CD pipelines:

```yaml
- name: Run Performance Tests
  run: |
    pytest tests/performance/ -m performance --benchmark-only
    python tests/performance/test_runner.py
```

### Performance Monitoring

Track performance metrics over time:

- **Mean execution time** trends
- **Memory usage** patterns
- **Regression detection** alerts
- **Environment impact** analysis

## Related Documentation

- **Installation Requirements**: See `quickstart.md` for <30s requirement
- **System Requirements**: See `src/models/system_requirements.py`
- **Setup Process**: See `src/services/setup.py`
- **Test Configuration**: See `pyproject.toml` pytest settings