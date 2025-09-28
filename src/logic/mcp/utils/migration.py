"""Settings migration utilities for existing DocBro installations."""

import logging
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class MigrationResult:
    """Result of a migration operation."""
    success: bool
    migration_performed: bool
    backup_created: bool
    backup_path: Optional[Path]
    errors: List[str]
    warnings: List[str]


class McpSettingsMigrator:
    """Migrates MCP settings for existing DocBro installations."""

    def __init__(self, config_dir: Path):
        """Initialize migrator.

        Args:
            config_dir: DocBro configuration directory
        """
        self.config_dir = Path(config_dir)
        self.settings_file = self.config_dir / "settings.yaml"
        self.backup_dir = self.config_dir / "backups"

        # Ensure directories exist
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    def check_migration_needed(self) -> bool:
        """Check if MCP settings migration is needed.

        Returns:
            True if migration is needed
        """
        if not self.settings_file.exists():
            logger.debug("No settings file found, migration not needed")
            return False

        try:
            with open(self.settings_file, 'r') as f:
                settings = yaml.safe_load(f) or {}

            # Check if new structured MCP config exists
            if "mcp_server_configs" in settings:
                logger.debug("Structured MCP configuration already exists")
                return False

            # Check if old MCP configuration exists that needs migration
            old_mcp_fields = [
                "mcp_read_only_host", "mcp_read_only_port", "mcp_read_only_enabled",
                "mcp_admin_host", "mcp_admin_port", "mcp_admin_enabled"
            ]

            has_old_config = any(field in settings for field in old_mcp_fields)
            if has_old_config:
                logger.info("Old MCP configuration detected, migration needed")
                return True

            logger.debug("No MCP configuration found, migration not needed")
            return False

        except Exception as e:
            logger.error(f"Error checking migration status: {e}")
            return False

    def migrate_mcp_settings(self, create_backup: bool = True) -> MigrationResult:
        """Migrate MCP settings to new structured format.

        Args:
            create_backup: Whether to create a backup before migration

        Returns:
            MigrationResult with migration details
        """
        result = MigrationResult(
            success=False,
            migration_performed=False,
            backup_created=False,
            backup_path=None,
            errors=[],
            warnings=[]
        )

        try:
            # Check if migration is needed
            if not self.check_migration_needed():
                result.success = True
                result.warnings.append("Migration not needed or already completed")
                return result

            # Load current settings
            current_settings = self._load_current_settings()
            if current_settings is None:
                result.errors.append("Failed to load current settings")
                return result

            # Create backup if requested
            if create_backup:
                backup_path = self._create_backup()
                if backup_path:
                    result.backup_created = True
                    result.backup_path = backup_path
                    logger.info(f"Created backup at: {backup_path}")
                else:
                    result.warnings.append("Failed to create backup, proceeding with migration")

            # Perform migration
            migrated_settings = self._migrate_settings(current_settings)

            # Validate migrated settings
            validation_errors = self._validate_migrated_settings(migrated_settings)
            if validation_errors:
                result.errors.extend(validation_errors)
                return result

            # Save migrated settings
            if self._save_settings(migrated_settings):
                result.success = True
                result.migration_performed = True
                logger.info("MCP settings migration completed successfully")
            else:
                result.errors.append("Failed to save migrated settings")

            return result

        except Exception as e:
            error_msg = f"Migration failed with exception: {e}"
            logger.error(error_msg)
            result.errors.append(error_msg)
            return result

    def rollback_migration(self, backup_path: Path) -> bool:
        """Rollback migration using a backup file.

        Args:
            backup_path: Path to backup file

        Returns:
            True if rollback was successful
        """
        try:
            if not backup_path.exists():
                logger.error(f"Backup file not found: {backup_path}")
                return False

            # Read backup
            with open(backup_path, 'r') as f:
                backup_settings = yaml.safe_load(f)

            # Restore backup
            if self._save_settings(backup_settings):
                logger.info(f"Successfully rolled back migration using backup: {backup_path}")
                return True
            else:
                logger.error("Failed to save backup settings during rollback")
                return False

        except Exception as e:
            logger.error(f"Rollback failed: {e}")
            return False

    def _load_current_settings(self) -> Optional[Dict[str, Any]]:
        """Load current settings from file.

        Returns:
            Settings dictionary or None if failed
        """
        try:
            with open(self.settings_file, 'r') as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            logger.error(f"Failed to load settings: {e}")
            return None

    def _create_backup(self) -> Optional[Path]:
        """Create a backup of current settings.

        Returns:
            Path to backup file or None if failed
        """
        try:
            import datetime
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = self.backup_dir / f"settings_backup_{timestamp}.yaml"

            # Copy current settings to backup
            if self.settings_file.exists():
                import shutil
                shutil.copy2(self.settings_file, backup_path)
                return backup_path
            else:
                logger.warning("No settings file to backup")
                return None

        except Exception as e:
            logger.error(f"Failed to create backup: {e}")
            return None

    def _migrate_settings(self, settings: Dict[str, Any]) -> Dict[str, Any]:
        """Migrate settings to new structured format.

        Args:
            settings: Current settings dictionary

        Returns:
            Migrated settings dictionary
        """
        migrated = settings.copy()

        # Extract old MCP configuration
        old_config = self._extract_old_mcp_config(settings)

        # Create new structured configuration
        mcp_server_configs = self._create_structured_config(old_config)

        # Add new configuration
        migrated["mcp_server_configs"] = mcp_server_configs

        # Keep old fields for backward compatibility but mark them
        migrated["_migration_info"] = {
            "migrated_at": self._get_timestamp(),
            "migration_version": "1.0",
            "original_mcp_config": old_config
        }

        logger.info("Settings migration completed")
        return migrated

    def _extract_old_mcp_config(self, settings: Dict[str, Any]) -> Dict[str, Any]:
        """Extract old MCP configuration from settings.

        Args:
            settings: Current settings dictionary

        Returns:
            Dictionary containing old MCP configuration
        """
        old_config = {}

        # Read-only server configuration
        old_config["read_only"] = {
            "host": settings.get("mcp_read_only_host", "0.0.0.0"),
            "port": settings.get("mcp_read_only_port", 9383),
            "enabled": settings.get("mcp_read_only_enabled", True)
        }

        # Admin server configuration
        old_config["admin"] = {
            "host": settings.get("mcp_admin_host", "127.0.0.1"),
            "port": settings.get("mcp_admin_port", 9384),
            "enabled": settings.get("mcp_admin_enabled", True)
        }

        return old_config

    def _create_structured_config(self, old_config: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """Create new structured MCP configuration.

        Args:
            old_config: Old configuration dictionary

        Returns:
            New structured configuration
        """
        structured_config = {}

        # Read-only server
        read_only_config = old_config.get("read_only", {})
        structured_config["read-only"] = {
            "server_type": "read-only",
            "host": read_only_config.get("host", "0.0.0.0"),
            "port": read_only_config.get("port", 9383),
            "enabled": read_only_config.get("enabled", True)
        }

        # Admin server
        admin_config = old_config.get("admin", {})
        structured_config["admin"] = {
            "server_type": "admin",
            "host": admin_config.get("host", "127.0.0.1"),
            "port": admin_config.get("port", 9384),
            "enabled": admin_config.get("enabled", True)
        }

        return structured_config

    def _validate_migrated_settings(self, settings: Dict[str, Any]) -> List[str]:
        """Validate migrated settings.

        Args:
            settings: Migrated settings dictionary

        Returns:
            List of validation errors
        """
        errors = []

        mcp_configs = settings.get("mcp_server_configs", {})
        if not mcp_configs:
            errors.append("No MCP server configurations found after migration")
            return errors

        # Validate each server configuration
        for server_name, config in mcp_configs.items():
            # Check required fields
            required_fields = ["server_type", "host", "port", "enabled"]
            for field in required_fields:
                if field not in config:
                    errors.append(f"Missing required field '{field}' in {server_name} config")

            # Validate port range
            port = config.get("port")
            if not isinstance(port, int) or port < 1024 or port > 65535:
                errors.append(f"Invalid port {port} for {server_name} server")

            # Validate admin server host
            if config.get("server_type") == "admin":
                host = config.get("host")
                if host not in ["127.0.0.1", "localhost"]:
                    errors.append(f"Admin server must use localhost, got: {host}")

        # Check for port conflicts
        enabled_configs = [c for c in mcp_configs.values() if c.get("enabled", False)]
        ports = [c.get("port") for c in enabled_configs]
        if len(ports) != len(set(ports)):
            errors.append("Port conflicts detected in migrated configuration")

        return errors

    def _save_settings(self, settings: Dict[str, Any]) -> bool:
        """Save settings to file.

        Args:
            settings: Settings dictionary to save

        Returns:
            True if save was successful
        """
        try:
            with open(self.settings_file, 'w') as f:
                yaml.dump(settings, f, default_flow_style=False, sort_keys=True)
            return True
        except Exception as e:
            logger.error(f"Failed to save settings: {e}")
            return False

    def _get_timestamp(self) -> str:
        """Get current timestamp string.

        Returns:
            ISO format timestamp string
        """
        import datetime
        return datetime.datetime.now().isoformat()

    def get_migration_status(self) -> Dict[str, Any]:
        """Get current migration status.

        Returns:
            Migration status information
        """
        status = {
            "migration_needed": self.check_migration_needed(),
            "settings_file_exists": self.settings_file.exists(),
            "backup_dir_exists": self.backup_dir.exists(),
            "config_dir": str(self.config_dir),
            "settings_file": str(self.settings_file)
        }

        if self.settings_file.exists():
            try:
                with open(self.settings_file, 'r') as f:
                    settings = yaml.safe_load(f) or {}

                status["has_structured_config"] = "mcp_server_configs" in settings
                status["has_migration_info"] = "_migration_info" in settings

                if "_migration_info" in settings:
                    status["migration_info"] = settings["_migration_info"]

            except Exception as e:
                status["settings_read_error"] = str(e)

        return status

    def list_backups(self) -> List[Tuple[Path, Dict[str, Any]]]:
        """List available backup files with their metadata.

        Returns:
            List of tuples containing (backup_path, metadata)
        """
        backups = []

        try:
            backup_files = list(self.backup_dir.glob("settings_backup_*.yaml"))
            backup_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)

            for backup_file in backup_files:
                try:
                    stat = backup_file.stat()
                    metadata = {
                        "size": stat.st_size,
                        "created": stat.st_mtime,
                        "name": backup_file.name
                    }
                    backups.append((backup_file, metadata))
                except Exception as e:
                    logger.warning(f"Could not read metadata for backup {backup_file}: {e}")

        except Exception as e:
            logger.error(f"Failed to list backups: {e}")

        return backups