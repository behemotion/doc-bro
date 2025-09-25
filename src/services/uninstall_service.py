"""Uninstall service orchestrator for managing the uninstall process."""

from typing import Dict, Any, List, Optional
from pathlib import Path
import click
from src.models.uninstall_config import UninstallConfig
from src.models.uninstall_progress import UninstallProgress
from src.models.component_status import ComponentStatus, RemovalStatus
from src.models.removal_operation import RemovalOperation, OperationType
from src.services.component_detection import ComponentDetectionService
from src.services.removal_executor import RemovalExecutor
from src.services.backup_service import BackupService
from src.core.lib_logger import get_logger

logger = get_logger(__name__)


class UninstallService:
    """Main orchestration service for uninstall operations."""

    def __init__(self):
        """Initialize the uninstall service."""
        self.detection_service = ComponentDetectionService()
        self.removal_executor = RemovalExecutor()
        self.backup_service = BackupService()
        self.progress = UninstallProgress()

    async def validate_installation(self) -> List[ComponentStatus]:
        """Detect what needs removal."""
        components = await self.detection_service.detect_all_components()

        # Flatten components into a list of ComponentStatus
        all_components = []

        for container in components.get('containers', []):
            all_components.append(container)

        for volume in components.get('volumes', []):
            all_components.append(volume)

        for directory in components.get('directories', []):
            all_components.append(directory)

        for config in components.get('configs', []):
            all_components.append(config)

        if components.get('package'):
            all_components.append(components['package'])

        return all_components

    async def create_backup(self, config: UninstallConfig, components: Dict[str, Any]) -> Optional[Dict]:
        """Create backup if requested."""
        if not config.backup:
            return None

        try:
            logger.info("Creating backup before uninstall")
            backup_info = await self.backup_service.create_backup(
                components=components,
                path=config.backup_path
            )
            self.progress.set_backup_info(backup_info['path'])
            return backup_info
        except Exception as e:
            logger.error(f"Backup creation failed: {e}")
            if not config.force:
                # Ask user if they want to continue without backup
                if not self.handle_failure(None, f"Backup failed: {e}"):
                    raise
            return None

    async def execute(
        self,
        config: UninstallConfig,
        components: Optional[Dict[str, Any]] = None,
        preserve_external: bool = True
    ) -> Dict[str, Any]:
        """Perform uninstall operation."""
        # Detect components if not provided
        if components is None:
            components = await self.detection_service.detect_all_components()

        # Count total components
        total = 0
        for key in ['containers', 'volumes', 'directories', 'configs']:
            total += len(components.get(key, []))
        if components.get('package'):
            total += 1

        self.progress.total_components = total

        # Create operations queue
        operations = self._create_operations_queue(components, preserve_external)

        # Execute operations
        for operation in operations:
            if config.dry_run:
                logger.info(f"[DRY RUN] Would execute: {operation.get_display_name()}")
                self.progress.increment_skipped()
            else:
                success = await self._execute_operation(operation, config)
                if success:
                    self.progress.increment_removed()
                else:
                    self.progress.increment_failed()

                    # Handle failure
                    if not config.force:
                        if not self.handle_failure(
                            None,
                            f"Failed to {operation.get_display_name()}"
                        ):
                            break  # User chose to stop

        self.progress.mark_complete()

        return {
            'success': self.progress.failed_components == 0,
            'removed': self.progress.removed_components,
            'failed': self.progress.failed_components,
            'skipped': self.progress.skipped_components,
            'summary': self.progress.get_summary()
        }

    def handle_failure(self, component: Optional[ComponentStatus], error_message: str) -> bool:
        """Prompt user on failure (without --force)."""
        logger.error(error_message)

        # In non-interactive mode, continue
        if not click.get_current_context().obj.get('interactive', True):
            return True

        return click.confirm(
            f"\n{error_message}\nContinue with remaining removals?",
            default=False
        )

    def _create_operations_queue(
        self,
        components: Dict[str, Any],
        preserve_external: bool
    ) -> List[RemovalOperation]:
        """Create ordered queue of removal operations."""
        operations = []

        # 1. Stop containers first
        for container in components.get('containers', []):
            if hasattr(container, 'component_name'):
                name = container.component_name
            else:
                name = container.get('Names', ['/unknown'])[0].lstrip('/')

            container_id = container.get('Id', name) if isinstance(container, dict) else name
            op = RemovalOperation.create_stop_container(container_id, name)
            operations.append(op)

        # 2. Remove containers
        for container in components.get('containers', []):
            if hasattr(container, 'component_name'):
                name = container.component_name
            else:
                name = container.get('Names', ['/unknown'])[0].lstrip('/')

            container_id = container.get('Id', name) if isinstance(container, dict) else name
            # Find corresponding stop operation
            stop_op = next((op for op in operations if op.target == container_id), None)
            depends_on = stop_op.operation_id if stop_op else None

            op = RemovalOperation.create_remove_container(container_id, depends_on)
            operations.append(op)

        # 3. Remove volumes (skip external if preserve_external is True)
        for volume in components.get('volumes', []):
            if hasattr(volume, '__dict__'):
                # ComponentStatus object
                if preserve_external and volume.is_external:
                    logger.info(f"Preserving external volume: {volume.component_name}")
                    continue
                name = volume.component_name
            else:
                # Dictionary
                name = volume.get('Name', 'unknown')

            op = RemovalOperation.create_remove_volume(name)
            operations.append(op)

        # 4. Delete config files
        for config in components.get('configs', []):
            if hasattr(config, 'component_path'):
                path = str(config.component_path)
            elif isinstance(config, Path):
                path = str(config)
            else:
                continue

            op = RemovalOperation.create_delete_config(path)
            operations.append(op)

        # 5. Delete directories
        for directory in components.get('directories', []):
            if hasattr(directory, 'component_path'):
                path = str(directory.component_path)
            elif isinstance(directory, Path):
                path = str(directory)
            else:
                continue

            op = RemovalOperation.create_delete_directory(path)
            operations.append(op)

        # 6. Uninstall package last
        if components.get('package'):
            op = RemovalOperation.create_uninstall_package('docbro')
            operations.append(op)

        # Sort by priority
        operations.sort(key=lambda x: x.priority)

        return operations

    async def _execute_operation(
        self,
        operation: RemovalOperation,
        config: UninstallConfig
    ) -> bool:
        """Execute a single removal operation."""
        logger.info(f"Executing: {operation.get_display_name()}")

        try:
            if operation.operation_type == OperationType.STOP_CONTAINER:
                return await self.removal_executor.stop_container(operation.target)

            elif operation.operation_type == OperationType.REMOVE_CONTAINER:
                return await self.removal_executor.remove_container(
                    operation.target,
                    force=config.force
                )

            elif operation.operation_type == OperationType.REMOVE_VOLUME:
                return await self.removal_executor.remove_volume(
                    operation.target,
                    force=config.force
                )

            elif operation.operation_type == OperationType.DELETE_DIRECTORY:
                return await self.removal_executor.delete_directory(Path(operation.target))

            elif operation.operation_type == OperationType.DELETE_CONFIG:
                return await self.removal_executor.delete_directory(Path(operation.target))

            elif operation.operation_type == OperationType.UNINSTALL_PACKAGE:
                return await self.removal_executor.uninstall_package()

            else:
                logger.warning(f"Unknown operation type: {operation.operation_type}")
                return False

        except Exception as e:
            logger.error(f"Operation failed: {e}")
            operation.mark_failed(str(e))

            # Retry if possible
            if operation.can_retry:
                operation.increment_retry()
                logger.info(f"Retrying operation (attempt {operation.retry_count}/{operation.max_retries})")
                return await self._execute_operation(operation, config)

            return False