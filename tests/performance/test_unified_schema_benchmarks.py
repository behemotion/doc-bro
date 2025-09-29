"""Performance benchmarks for unified schema operations."""

import asyncio
import time
import uuid
from datetime import datetime
from typing import Any, Dict, List

import pytest

from src.models.compatibility_status import CompatibilityStatus
from src.models.migration_record import ProjectMigrationRecord, MigrationOperation
from src.models.schema_version import SchemaVersion
from src.models.unified_project import UnifiedProject, UnifiedProjectStatus
from src.services.compatibility_checker import CompatibilityChecker
from src.logic.projects.models.project import ProjectType


class TestUnifiedProjectPerformance:
    """Performance benchmarks for UnifiedProject model operations."""

    @pytest.fixture
    def sample_projects(self) -> List[UnifiedProject]:
        """Create a list of sample projects for testing."""
        projects = []
        for i in range(100):
            project = UnifiedProject(
                name=f"test-project-{i}",
                type=ProjectType.CRAWLING if i % 3 == 0 else
                     ProjectType.DATA if i % 3 == 1 else ProjectType.STORAGE,
                status=UnifiedProjectStatus.ACTIVE,
                settings={'test_setting': f'value_{i}'},
                statistics={'test_stat': i * 10},
                metadata={'description': f'Test project {i}'}
            )
            projects.append(project)
        return projects

    def test_project_creation_performance(self, benchmark):
        """Benchmark project creation performance."""
        def create_project():
            return UnifiedProject(
                name=f"benchmark-project-{uuid.uuid4()}",
                type=ProjectType.CRAWLING,
                settings={'crawl_depth': 3, 'rate_limit': 1.0},
                statistics={'total_pages': 100},
                metadata={'created_by': 'benchmark'}
            )

        result = benchmark(create_project)

        # Verify the created project is valid
        assert isinstance(result, UnifiedProject)
        assert result.name.startswith('benchmark-project-')
        assert result.type == ProjectType.CRAWLING

    def test_project_validation_performance(self, benchmark):
        """Benchmark project validation performance."""
        project_data = {
            'name': 'validation-test',
            'type': ProjectType.DATA,
            'status': UnifiedProjectStatus.ACTIVE,
            'settings': {'chunk_size': 1000, 'embedding_model': 'test-model'},
            'statistics': {'total_documents': 500},
            'metadata': {'version': '1.0'}
        }

        def validate_project():
            return UnifiedProject(**project_data)

        result = benchmark(validate_project)
        assert result.name == 'validation-test'

    def test_project_serialization_performance(self, benchmark, sample_projects):
        """Benchmark project serialization to dictionary."""
        project = sample_projects[0]

        def serialize_project():
            return project.to_dict()

        result = benchmark(serialize_project)

        assert isinstance(result, dict)
        assert result['name'] == project.name
        assert 'id' in result
        assert 'created_at' in result

    def test_project_deserialization_performance(self, benchmark, sample_projects):
        """Benchmark project deserialization from dictionary."""
        project_dict = sample_projects[0].to_dict()

        def deserialize_project():
            return UnifiedProject.from_dict(project_dict)

        result = benchmark(deserialize_project)

        assert isinstance(result, UnifiedProject)
        assert result.name == sample_projects[0].name

    def test_project_update_operations_performance(self, benchmark, sample_projects):
        """Benchmark project update operations."""
        project = sample_projects[0]

        def update_operations():
            # Test multiple update operations
            project.update_status(UnifiedProjectStatus.PROCESSING)
            project.update_settings({'new_setting': 'new_value'})
            project.update_statistics(new_stat=999)
            return project

        result = benchmark(update_operations)

        assert result.status == UnifiedProjectStatus.PROCESSING
        assert result.settings['new_setting'] == 'new_value'
        assert result.statistics['new_stat'] == 999

    def test_bulk_project_operations_performance(self, benchmark):
        """Benchmark bulk project operations."""
        def bulk_operations():
            projects = []
            for i in range(50):  # Smaller batch for individual benchmark
                project = UnifiedProject(
                    name=f"bulk-project-{i}",
                    type=ProjectType.DATA,
                    settings={'chunk_size': 500 + i},
                    statistics={'documents': i * 2},
                    metadata={'batch': 'performance_test'}
                )
                projects.append(project)

            # Perform operations on all projects
            for project in projects:
                project.update_status(UnifiedProjectStatus.READY)
                project.to_dict()

            return projects

        result = benchmark(bulk_operations)

        assert len(result) == 50
        for project in result:
            assert project.status == UnifiedProjectStatus.READY

    def test_project_compatibility_check_performance(self, benchmark, sample_projects):
        """Benchmark compatibility checking operations."""
        project = sample_projects[0]

        def check_compatibility():
            return (
                project.is_compatible(),
                project.allows_modification(),
                project.needs_recreation(),
                project.is_ready_for_search(),
                project.is_outdated()
            )

        result = benchmark(check_compatibility)

        assert isinstance(result, tuple)
        assert len(result) == 5
        assert all(isinstance(val, bool) for val in result)


class TestCompatibilityCheckerPerformance:
    """Performance benchmarks for CompatibilityChecker operations."""

    @pytest.fixture
    def checker(self) -> CompatibilityChecker:
        """Create a CompatibilityChecker instance."""
        return CompatibilityChecker()

    @pytest.fixture
    def test_projects(self) -> List[UnifiedProject]:
        """Create test projects with different schema versions."""
        projects = []

        # Compatible projects (current schema)
        for i in range(20):
            project = UnifiedProject(
                name=f"compatible-{i}",
                schema_version=SchemaVersion.CURRENT_VERSION,
                type=ProjectType.CRAWLING,
                settings={'crawl_depth': 3}
            )
            projects.append(project)

        # Incompatible v1 projects
        for i in range(15):
            project = UnifiedProject(
                name=f"v1-project-{i}",
                schema_version=1,
                type=ProjectType.CRAWLING,
                settings={'crawl_depth': 2}
            )
            projects.append(project)

        # Incompatible v2 projects
        for i in range(15):
            project = UnifiedProject(
                name=f"v2-project-{i}",
                schema_version=2,
                type=ProjectType.DATA,
                settings={'chunk_size': 1000}
            )
            projects.append(project)

        return projects

    @pytest.mark.asyncio
    async def test_single_project_compatibility_check_performance(self, benchmark, checker, test_projects):
        """Benchmark single project compatibility check."""
        project = test_projects[0]

        async def check_single_project():
            return await checker.check_project_compatibility(project)

        # Use asyncio benchmark for async functions
        def sync_wrapper():
            return asyncio.run(check_single_project())

        result = benchmark(sync_wrapper)

        assert result.current_version == SchemaVersion.CURRENT_VERSION
        assert result.project_version == project.schema_version

    @pytest.mark.asyncio
    async def test_multiple_projects_compatibility_check_performance(self, benchmark, checker, test_projects):
        """Benchmark multiple projects compatibility check."""
        # Use smaller batch for individual benchmark
        batch_projects = test_projects[:20]

        async def check_multiple_projects():
            return await checker.check_multiple_projects(batch_projects)

        def sync_wrapper():
            return asyncio.run(check_multiple_projects())

        result = benchmark(sync_wrapper)

        assert len(result) == 20
        for project_id, comp_result in result.items():
            assert comp_result.current_version == SchemaVersion.CURRENT_VERSION

    def test_compatibility_summary_generation_performance(self, benchmark, checker):
        """Benchmark compatibility summary generation."""
        # Create mock results for summary
        from src.services.compatibility_checker import CompatibilityResult

        results = {}
        for i in range(100):
            result = CompatibilityResult(
                is_compatible=(i % 3 == 0),
                current_version=3,
                project_version=(i % 3) + 1,
                status=CompatibilityStatus.COMPATIBLE if i % 3 == 0 else CompatibilityStatus.INCOMPATIBLE,
                can_be_migrated=(i % 4 == 0),
                migration_required=(i % 3 != 0)
            )
            results[f"project_{i}"] = result

        def generate_summary():
            return checker.get_compatibility_summary(results)

        result = benchmark(generate_summary)

        assert result['total_projects'] == 100
        assert 'compatibility_rate' in result
        assert 'version_distribution' in result


class TestSchemaVersionPerformance:
    """Performance benchmarks for SchemaVersion operations."""

    def test_get_version_history_performance(self, benchmark):
        """Benchmark version history retrieval."""
        def get_history():
            return SchemaVersion.get_version_history()

        result = benchmark(get_history)

        assert isinstance(result, list)
        assert len(result) >= 3
        assert all(isinstance(v, SchemaVersion) for v in result)

    def test_version_info_lookup_performance(self, benchmark):
        """Benchmark version info lookup."""
        def lookup_versions():
            results = []
            for version in [1, 2, 3, 4, 5]:
                info = SchemaVersion.get_version_info(version)
                results.append(info)
            return results

        result = benchmark(lookup_versions)

        assert len(result) == 5
        # First three should exist, last two should be None
        assert result[0] is not None
        assert result[1] is not None
        assert result[2] is not None

    def test_version_validation_methods_performance(self, benchmark):
        """Benchmark version validation methods."""
        test_versions = [1, 2, 3, 4, 5, 10, 100]

        def validate_versions():
            results = []
            for version in test_versions:
                results.append({
                    'version': version,
                    'is_current': SchemaVersion.is_current_version(version),
                    'is_compatible': SchemaVersion.is_compatible_version(version),
                    'can_migrate': SchemaVersion.can_migrate_from(version),
                    'requires_recreation': SchemaVersion.requires_recreation(version)
                })
            return results

        result = benchmark(validate_versions)

        assert len(result) == len(test_versions)
        for item in result:
            assert 'version' in item
            assert isinstance(item['is_current'], bool)
            assert isinstance(item['is_compatible'], bool)


class TestMigrationRecordPerformance:
    """Performance benchmarks for migration record operations."""

    def test_migration_record_creation_performance(self, benchmark):
        """Benchmark migration record creation."""
        def create_migration_record():
            return ProjectMigrationRecord(
                project_id=str(uuid.uuid4()),
                project_name="test-project",
                operation=MigrationOperation.RECREATION,
                from_schema_version=1,
                to_schema_version=3,
                preserved_settings={'setting1': 'value1'},
                preserved_metadata={'meta1': 'value1'},
                data_size_bytes=1048576,
                user_initiated=True,
                initiated_by_command='docbro project --recreate'
            )

        result = benchmark(create_migration_record)

        assert result.operation == MigrationOperation.RECREATION
        assert result.from_schema_version == 1
        assert result.to_schema_version == 3
        assert result.success is False  # Default value

    def test_migration_record_completion_performance(self, benchmark):
        """Benchmark migration record completion."""
        record = ProjectMigrationRecord(
            project_id=str(uuid.uuid4()),
            project_name="completion-test",
            operation=MigrationOperation.RECREATION,
            from_schema_version=1,
            to_schema_version=3
        )

        def mark_completed():
            record.mark_completed(success=True)
            return record

        result = benchmark(mark_completed)

        assert result.success is True
        assert result.completed_at is not None

    def test_bulk_migration_records_performance(self, benchmark):
        """Benchmark bulk migration record operations."""
        def bulk_migration_operations():
            records = []
            for i in range(50):
                record = ProjectMigrationRecord(
                    project_id=str(uuid.uuid4()),
                    project_name=f"bulk-project-{i}",
                    operation=MigrationOperation.RECREATION,
                    from_schema_version=1 + (i % 2),
                    to_schema_version=3,
                    data_size_bytes=1024 * (i + 1)
                )

                # Simulate completion
                record.mark_completed(success=(i % 5 != 0))
                records.append(record)

            return records

        result = benchmark(bulk_migration_operations)

        assert len(result) == 50
        for record in result:
            assert record.completed_at is not None
            assert isinstance(record.success, bool)


class TestIntegratedPerformanceScenarios:
    """Performance benchmarks for integrated scenarios."""

    @pytest.fixture
    def performance_test_data(self):
        """Create comprehensive test data for performance testing."""
        return {
            'projects': [
                UnifiedProject(
                    name=f"integrated-project-{i}",
                    type=ProjectType.CRAWLING if i % 3 == 0 else
                         ProjectType.DATA if i % 3 == 1 else ProjectType.STORAGE,
                    schema_version=1 + (i % 3),
                    settings={
                        'crawl_depth': 3 + (i % 3),
                        'rate_limit': 1.0 + (i * 0.1),
                        'chunk_size': 500 + (i * 10)
                    },
                    statistics={
                        'total_pages': i * 10,
                        'successful_pages': i * 9,
                        'failed_pages': i
                    },
                    metadata={
                        'description': f'Performance test project {i}',
                        'category': 'benchmark',
                        'priority': i % 5
                    }
                ) for i in range(100)
            ]
        }

    def test_full_project_lifecycle_performance(self, benchmark, performance_test_data):
        """Benchmark full project lifecycle operations."""
        def project_lifecycle():
            projects = performance_test_data['projects'][:20]  # Smaller batch for individual benchmark
            results = []

            for project in projects:
                # Creation (already done, but simulate validation)
                validated = UnifiedProject(**project.dict())

                # Update operations
                validated.update_status(UnifiedProjectStatus.PROCESSING)
                validated.update_settings({'new_setting': 'benchmark_value'})
                validated.update_statistics(benchmark_run=True)

                # Compatibility checks
                is_compatible = validated.is_compatible()
                needs_recreation = validated.needs_recreation()

                # Serialization
                project_dict = validated.to_dict()

                # Deserialization
                restored_project = UnifiedProject.from_dict(project_dict)

                results.append({
                    'project': restored_project,
                    'is_compatible': is_compatible,
                    'needs_recreation': needs_recreation
                })

            return results

        result = benchmark(project_lifecycle)

        assert len(result) == 20
        for item in result:
            assert isinstance(item['project'], UnifiedProject)
            assert isinstance(item['is_compatible'], bool)
            assert isinstance(item['needs_recreation'], bool)

    @pytest.mark.asyncio
    async def test_compatibility_analysis_workflow_performance(self, benchmark, performance_test_data):
        """Benchmark complete compatibility analysis workflow."""
        checker = CompatibilityChecker()
        projects = performance_test_data['projects'][:30]

        async def compatibility_workflow():
            # Check all projects
            results = await checker.check_multiple_projects(projects)

            # Generate summary
            summary = checker.get_compatibility_summary(results)

            # Get recreation instructions for incompatible projects
            instructions = []
            for project_id, result in results.items():
                if not result.is_compatible:
                    project = next(p for p in projects if p.id == project_id)
                    instr = checker.get_recreation_instructions(result, project.name)
                    instructions.append(instr)

            return {
                'results': results,
                'summary': summary,
                'instruction_count': len(instructions)
            }

        def sync_wrapper():
            return asyncio.run(compatibility_workflow())

        result = benchmark(sync_wrapper)

        assert len(result['results']) == 30
        assert 'total_projects' in result['summary']
        assert result['instruction_count'] >= 0


class TestPerformanceRegressionValidation:
    """Validate performance against expected thresholds."""

    def test_project_creation_speed_threshold(self):
        """Validate project creation meets speed requirements."""
        start_time = time.perf_counter()

        projects = []
        for i in range(100):
            project = UnifiedProject(
                name=f"speed-test-{i}",
                type=ProjectType.CRAWLING,
                settings={'crawl_depth': 3}
            )
            projects.append(project)

        elapsed_time = time.perf_counter() - start_time

        # Should create 100 projects in under 100ms (target: <1ms per project)
        assert elapsed_time < 0.1, f"Project creation too slow: {elapsed_time:.4f}s for 100 projects"
        assert len(projects) == 100

    @pytest.mark.asyncio
    async def test_compatibility_check_speed_threshold(self):
        """Validate compatibility checking meets speed requirements."""
        checker = CompatibilityChecker()

        # Create test projects
        projects = [
            UnifiedProject(name=f"speed-compat-{i}", schema_version=1 + (i % 3))
            for i in range(50)
        ]

        start_time = time.perf_counter()
        results = await checker.check_multiple_projects(projects)
        elapsed_time = time.perf_counter() - start_time

        # Should check 50 projects in under 50ms (target: <1ms per project)
        assert elapsed_time < 0.05, f"Compatibility checking too slow: {elapsed_time:.4f}s for 50 projects"
        assert len(results) == 50

    def test_serialization_speed_threshold(self):
        """Validate serialization meets speed requirements."""
        # Create a complex project
        project = UnifiedProject(
            name="serialization-speed-test",
            type=ProjectType.DATA,
            settings={f"setting_{i}": f"value_{i}" for i in range(100)},
            statistics={f"stat_{i}": i * 10 for i in range(50)},
            metadata={f"meta_{i}": f"data_{i}" for i in range(25)}
        )

        # Test serialization speed
        start_time = time.perf_counter()
        for _ in range(100):
            project_dict = project.to_dict()
        serialization_time = time.perf_counter() - start_time

        # Test deserialization speed
        start_time = time.perf_counter()
        for _ in range(100):
            restored = UnifiedProject.from_dict(project_dict)
        deserialization_time = time.perf_counter() - start_time

        # Should serialize/deserialize 100 times in under 10ms each
        assert serialization_time < 0.01, f"Serialization too slow: {serialization_time:.4f}s for 100 operations"
        assert deserialization_time < 0.01, f"Deserialization too slow: {deserialization_time:.4f}s for 100 operations"


# Performance test configuration
@pytest.fixture(scope="session")
def benchmark_config():
    """Configure benchmark parameters."""
    return {
        'min_rounds': 5,
        'max_time': 2.0,  # Maximum 2 seconds per benchmark
        'timer': time.perf_counter,
        'disable_gc': True,
        'warmup': True,
        'warmup_iterations': 2
    }