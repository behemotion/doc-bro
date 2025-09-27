"""Setup orchestrator to coordinate all setup operations."""

import asyncio
from pathlib import Path
from typing import Optional, Dict, Any
from src.logic.setup.models.operation import SetupOperation, OperationType, OperationStatus
from src.logic.setup.models.configuration import SetupConfiguration
from src.logic.setup.services.initializer import SetupInitializer
from src.logic.setup.services.uninstaller import SetupUninstaller
from src.logic.setup.services.configurator import SetupConfigurator
from src.logic.setup.services.validator import SetupValidator
from src.logic.setup.services.detector import ServiceDetector
from src.logic.setup.services.reset_handler import ResetHandler
from src.logic.setup.core.menu import InteractiveMenu
from src.logic.setup.utils.prompts import confirm_action
from src.core.lib_logger import get_logger

logger = get_logger(__name__)


class SetupOrchestrator:
    """Orchestrates all setup operations."""

    def __init__(self, home_dir: Optional[Path] = None):
        """Initialize the orchestrator.

        Args:
            home_dir: Optional home directory for testing
        """
        self.home_dir = home_dir or Path.home()
        self.config_dir = self.home_dir / ".config" / "docbro"
        self.data_dir = self.home_dir / ".local" / "share" / "docbro"
        self.cache_dir = self.home_dir / ".cache" / "docbro"

        # Initialize services
        self.initializer = SetupInitializer(home_dir=self.home_dir)
        self.uninstaller = SetupUninstaller(home_dir=self.home_dir)
        self.configurator = SetupConfigurator(home_dir=self.home_dir)
        self.validator = SetupValidator()
        self.detector = ServiceDetector()
        self.reset_handler = ResetHandler(home_dir=self.home_dir)

        self.current_operation: Optional[SetupOperation] = None

    def initialize(
        self,
        auto: bool = False,
        force: bool = False,
        vector_store: Optional[str] = None,
        non_interactive: bool = False,
        **kwargs
    ) -> SetupOperation:
        """Initialize DocBro configuration.

        Args:
            auto: Use automatic mode with defaults
            force: Force initialization even if already exists
            vector_store: Pre-selected vector store provider
            non_interactive: Disable interactive prompts
            **kwargs: Additional options

        Returns:
            SetupOperation with results
        """
        # Create operation
        operation = SetupOperation(
            operation_type=OperationType.INIT,
            flags=self._build_flags(locals())
        )
        self.current_operation = operation

        try:
            operation.transition_to(OperationStatus.IN_PROGRESS)

            # Check if already initialized
            if self._is_initialized() and not force:
                raise RuntimeError(
                    "DocBro is already initialized. Use --force to reinitialize."
                )

            # Validate system requirements
            logger.info("Validating system requirements...")
            validation = self.validator.validate_system()
            if not validation.get("valid", False):
                raise RuntimeError(f"System validation failed: {validation.get('error')}")

            # Detect available services
            logger.info("Detecting available services...")
            services = asyncio.run(self.detector.detect_all_async())

            # Create directory structure
            logger.info("Creating directory structure...")
            self.initializer.create_directories()

            # Configure vector store
            if vector_store:
                operation.add_selection("vector_store", vector_store)
            elif not auto and not non_interactive:
                vector_store = self._prompt_vector_store()
                operation.add_selection("vector_store", vector_store)
            else:
                vector_store = "sqlite_vec"  # Default
                operation.add_selection("vector_store", vector_store)

            # Initialize vector store
            logger.info(f"Initializing {vector_store}...")
            if vector_store == "sqlite_vec":
                self.initializer.initialize_sqlite_vec()
            elif vector_store == "qdrant":
                self.initializer.initialize_qdrant()

            # Create configuration
            config = SetupConfiguration(
                vector_store_provider=vector_store,
                directories={
                    "config": self.config_dir,
                    "data": self.data_dir,
                    "cache": self.cache_dir
                },
                services_detected=services
            )
            config.mark_initialized()

            # Save configuration
            logger.info("Saving configuration...")
            self.configurator.save_config(config.to_yaml_dict())

            operation.transition_to(OperationStatus.COMPLETED)
            logger.info("✅ DocBro initialization completed successfully")

        except Exception as e:
            logger.error(f"Initialization failed: {e}")
            operation.transition_to(OperationStatus.FAILED, error=str(e))
            raise

        return operation

    def uninstall(
        self,
        force: bool = False,
        backup: bool = False,
        dry_run: bool = False,
        preserve_data: bool = False,
        **kwargs
    ) -> SetupOperation:
        """Uninstall DocBro.

        Args:
            force: Skip confirmation prompts
            backup: Create backup before uninstalling
            dry_run: Show what would be removed without removing
            preserve_data: Keep user project data
            **kwargs: Additional options

        Returns:
            SetupOperation with results
        """
        operation = SetupOperation(
            operation_type=OperationType.UNINSTALL,
            flags=self._build_flags(locals())
        )
        self.current_operation = operation

        try:
            operation.transition_to(OperationStatus.IN_PROGRESS)

            # Generate uninstall manifest
            logger.info("Generating uninstall manifest...")
            manifest = self.uninstaller.generate_manifest(preserve_data=preserve_data)

            if dry_run:
                # Just show what would be removed
                operation.add_selection("would_remove", manifest.to_display_list())
                operation.add_selection("status", "dry_run")
                operation.transition_to(OperationStatus.COMPLETED)
                return operation

            # Confirm unless forced
            if not force:
                if not confirm_action(
                    f"This will remove {manifest.get_item_count()} items "
                    f"and free {manifest.get_size_display()}. Continue?"
                ):
                    operation.transition_to(OperationStatus.CANCELLED)
                    return operation

            # Create backup if requested
            if backup:
                backup_path = self.uninstaller.create_backup(manifest)
                operation.add_selection("backup_location", str(backup_path))

            # Execute uninstall
            logger.info("Removing DocBro installation...")
            result = self.uninstaller.execute(
                manifest=manifest,
                force=True  # Already confirmed
            )

            operation.add_selection("removed_items", result.get("removed", []))
            operation.add_selection("space_recovered", manifest.total_size_bytes)
            operation.transition_to(OperationStatus.COMPLETED)
            logger.info("✅ DocBro uninstalled successfully")

        except Exception as e:
            logger.error(f"Uninstall failed: {e}")
            operation.transition_to(OperationStatus.FAILED, error=str(e))
            raise

        return operation

    def reset(
        self,
        force: bool = False,
        vector_store: Optional[str] = None,
        preserve_data: bool = False,
        **kwargs
    ) -> SetupOperation:
        """Reset DocBro to fresh state.

        Args:
            force: Skip confirmation prompts
            vector_store: Vector store for new installation
            preserve_data: Keep user project data
            **kwargs: Additional options

        Returns:
            SetupOperation with results
        """
        operation = SetupOperation(
            operation_type=OperationType.RESET,
            flags=self._build_flags(locals())
        )
        self.current_operation = operation

        try:
            operation.transition_to(OperationStatus.IN_PROGRESS)

            # Double confirmation unless forced
            if not force:
                if not confirm_action("This will reset DocBro to a fresh state. Continue?"):
                    operation.transition_to(OperationStatus.CANCELLED)
                    return operation

                if not confirm_action("Are you absolutely sure? This cannot be undone."):
                    operation.transition_to(OperationStatus.CANCELLED)
                    return operation

            # Execute reset
            logger.info("Resetting DocBro installation...")
            result = self.reset_handler.execute(
                preserve_data=preserve_data,
                vector_store=vector_store
            )

            operation.add_selection("backup_created", result.backup_created)
            if result.backup_created:
                operation.add_selection("backup_path", str(result.backup_path))

            operation.transition_to(OperationStatus.COMPLETED)
            logger.info("✅ DocBro reset completed successfully")

        except Exception as e:
            logger.error(f"Reset failed: {e}")
            operation.transition_to(OperationStatus.FAILED, error=str(e))
            raise

        return operation

    def run_interactive_menu(self) -> SetupOperation:
        """Run the interactive setup menu.

        Returns:
            SetupOperation with results
        """
        operation = SetupOperation(
            operation_type=OperationType.MENU,
            flags=set()
        )
        self.current_operation = operation

        try:
            operation.transition_to(OperationStatus.IN_PROGRESS)

            menu = InteractiveMenu()
            result = menu.run()

            if result:
                # Process the menu selection
                return self.process_menu_selection(result)
            else:
                # User exited
                operation.transition_to(OperationStatus.CANCELLED)

        except Exception as e:
            logger.error(f"Menu operation failed: {e}")
            operation.transition_to(OperationStatus.FAILED, error=str(e))
            raise

        return operation

    def process_menu_selection(self, selection: str) -> SetupOperation:
        """Process a menu selection.

        Args:
            selection: The menu option selected

        Returns:
            SetupOperation with results
        """
        if selection == "initialize":
            return self.initialize()
        elif selection == "uninstall":
            return self.uninstall()
        elif selection == "reset":
            return self.reset()
        else:
            # Unknown selection
            operation = SetupOperation(
                operation_type=OperationType.MENU,
                flags=set()
            )
            operation.transition_to(OperationStatus.CANCELLED)
            return operation

    def _is_initialized(self) -> bool:
        """Check if DocBro is already initialized."""
        config_file = self.config_dir / "settings.yaml"
        return config_file.exists()

    def _prompt_vector_store(self) -> str:
        """Prompt user to select vector store."""
        from src.logic.setup.utils.prompts import prompt_choice

        choices = [
            ("sqlite_vec", "SQLite-vec (Local, no external dependencies)"),
            ("qdrant", "Qdrant (Scalable, requires Docker)")
        ]

        return prompt_choice(
            "Select vector store provider:",
            choices,
            default="sqlite_vec"
        )

    def _build_flags(self, options: Dict[str, Any]) -> set:
        """Build flags set from options."""
        flags = set()

        for key, value in options.items():
            if key in ["self", "kwargs"]:
                continue
            if value is True:
                flags.add(key.replace("_", "-"))
            elif value and key == "vector_store":
                flags.add("vector-store")

        return flags