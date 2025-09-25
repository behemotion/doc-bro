"""UV tool compatibility service for lifecycle management."""

import asyncio
import json
import shutil
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import logging
import os
import sys

from packaging import version
import platformdirs

from src.models.installation import InstallationContext, ServiceStatus, PackageMetadata
from src.services.config import ConfigService, InstallationError, ConfigurationError, MigrationError
from src.services.detection import ServiceDetectionService

logger = logging.getLogger(__name__)


class UVToolError(Exception):
    """Base exception for UV tool-related errors."""
    pass


class UVEnvironmentError(UVToolError):
    """UV environment isolation or detection issues."""
    pass


class UVVersionError(UVToolError):
    """UV version compatibility issues."""
    pass


class UVMigrationError(UVToolError):
    """UV tool migration issues."""
    pass


class UVUninstallError(UVToolError):
    """UV tool uninstall issues."""
    pass


class UVCompatibilityService:
    """Service for UV tool lifecycle management and compatibility."""

    def __init__(self):
        """Initialize UV compatibility service."""
        self.config_service = ConfigService()
        self.detection_service = ServiceDetectionService()
        self.min_uv_version = "0.4.0"
        self.supported_install_methods = {"uvx", "uv-tool"}

    async def detect_uv_environment(self) -> Dict[str, Any]:
        """Detect current UV environment and tool installation status."""
        try:
            env_info = {
                "uv_available": False,
                "uv_version": None,
                "uvx_available": False,
                "install_method": None,
                "tool_path": None,
                "environment_isolated": False,
                "python_path": sys.executable,
                "virtual_env": None,
                "uv_cache_dir": None,
                "uv_tool_dir": None,
                "docbro_installed_via_uv": False,
                "installation_integrity": False
            }

            # Check UV availability and version
            uv_info = await self._check_uv_installation()
            env_info.update(uv_info)

            # Check UVX availability
            uvx_info = await self._check_uvx_availability()
            env_info.update(uvx_info)

            # Check DocBro installation method
            docbro_info = await self._check_docbro_installation()
            env_info.update(docbro_info)

            # Check environment isolation
            isolation_info = await self._check_environment_isolation()
            env_info.update(isolation_info)

            # Validate installation integrity
            env_info["installation_integrity"] = await self._validate_installation_integrity()

            logger.info(f"UV environment detected: {env_info}")
            return env_info

        except Exception as e:
            logger.error(f"Failed to detect UV environment: {e}")
            raise UVEnvironmentError(f"UV environment detection failed: {e}")

    async def _check_uv_installation(self) -> Dict[str, Any]:
        """Check UV installation and version."""
        try:
            result = await asyncio.create_subprocess_exec(
                "uv", "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await result.communicate()

            if result.returncode == 0:
                version_output = stdout.decode().strip()
                # Parse version from "uv 0.4.0" format
                version_parts = version_output.split()
                uv_version = version_parts[-1] if version_parts else None

                return {
                    "uv_available": True,
                    "uv_version": uv_version,
                    "uv_cache_dir": await self._get_uv_cache_dir(),
                    "uv_tool_dir": await self._get_uv_tool_dir()
                }
            else:
                return {
                    "uv_available": False,
                    "uv_version": None,
                    "uv_error": stderr.decode().strip() if stderr else "Unknown error"
                }

        except FileNotFoundError:
            return {
                "uv_available": False,
                "uv_version": None,
                "uv_error": "UV not found in PATH"
            }
        except Exception as e:
            return {
                "uv_available": False,
                "uv_version": None,
                "uv_error": str(e)
            }

    async def _check_uvx_availability(self) -> Dict[str, Any]:
        """Check UVX command availability."""
        try:
            result = await asyncio.create_subprocess_exec(
                "uvx", "--help",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await result.communicate()

            return {
                "uvx_available": result.returncode == 0,
                "uvx_error": stderr.decode().strip() if result.returncode != 0 and stderr else None
            }

        except FileNotFoundError:
            return {
                "uvx_available": False,
                "uvx_error": "UVX not found in PATH"
            }
        except Exception as e:
            return {
                "uvx_available": False,
                "uvx_error": str(e)
            }

    async def _check_docbro_installation(self) -> Dict[str, Any]:
        """Check how DocBro is currently installed."""
        try:
            # Check if docbro command is available
            docbro_path = shutil.which("docbro")
            if not docbro_path:
                return {
                    "docbro_installed_via_uv": False,
                    "install_method": None,
                    "tool_path": None
                }

            tool_path = Path(docbro_path)

            # Check if installed via UV tool
            if await self._is_uv_tool_installation(tool_path):
                return {
                    "docbro_installed_via_uv": True,
                    "install_method": "uv-tool",
                    "tool_path": str(tool_path)
                }
            # Check if installed via UVX
            elif await self._is_uvx_installation(tool_path):
                return {
                    "docbro_installed_via_uv": True,
                    "install_method": "uvx",
                    "tool_path": str(tool_path)
                }
            else:
                return {
                    "docbro_installed_via_uv": False,
                    "install_method": "manual",
                    "tool_path": str(tool_path)
                }

        except Exception as e:
            logger.error(f"Error checking DocBro installation: {e}")
            return {
                "docbro_installed_via_uv": False,
                "install_method": None,
                "tool_path": None,
                "error": str(e)
            }

    async def _is_uv_tool_installation(self, tool_path: Path) -> bool:
        """Check if DocBro is installed via uv tool."""
        try:
            result = await asyncio.create_subprocess_exec(
                "uv", "tool", "list",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await result.communicate()

            if result.returncode == 0:
                output = stdout.decode()
                return "docbro" in output and str(tool_path) in output

            return False

        except Exception:
            return False

    async def _is_uvx_installation(self, tool_path: Path) -> bool:
        """Check if DocBro is installed via uvx."""
        # UVX installations typically go to ~/.local/bin
        local_bin = Path.home() / ".local" / "bin"
        return local_bin in tool_path.parents

    async def _check_environment_isolation(self) -> Dict[str, Any]:
        """Check UV tool environment isolation."""
        try:
            # Check if we're in a UV-managed virtual environment
            virtual_env = os.environ.get("VIRTUAL_ENV")
            uv_project = os.environ.get("UV_PROJECT_ENVIRONMENT")

            return {
                "environment_isolated": bool(virtual_env or uv_project),
                "virtual_env": virtual_env,
                "uv_project": uv_project
            }

        except Exception as e:
            return {
                "environment_isolated": False,
                "error": str(e)
            }

    async def _get_uv_cache_dir(self) -> Optional[str]:
        """Get UV cache directory."""
        try:
            # Try environment variable first
            cache_dir = os.environ.get("UV_CACHE_DIR")
            if cache_dir:
                return cache_dir

            # Try UV config
            result = await asyncio.create_subprocess_exec(
                "uv", "cache", "dir",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await result.communicate()

            if result.returncode == 0:
                return stdout.decode().strip()

            return None

        except Exception:
            return None

    async def _get_uv_tool_dir(self) -> Optional[str]:
        """Get UV tool directory."""
        try:
            # UV tools are typically stored in XDG data directory
            uv_data_dir = platformdirs.user_data_dir("uv")
            tool_dir = Path(uv_data_dir) / "tools"

            if tool_dir.exists():
                return str(tool_dir)

            return None

        except Exception:
            return None

    async def _validate_installation_integrity(self) -> bool:
        """Validate DocBro installation integrity."""
        try:
            # Check if docbro command works
            result = await asyncio.create_subprocess_exec(
                "docbro", "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await result.communicate()

            if result.returncode != 0:
                return False

            # Check configuration integrity
            context = self.config_service.load_installation_context()
            if not context:
                return False

            # Check required directories exist
            paths = self.config_service.get_installation_paths()
            for path in paths.values():
                if isinstance(path, Path) and not path.parent.exists():
                    return False

            return True

        except Exception:
            return False

    async def handle_uv_tool_update(
        self,
        target_version: Optional[str] = None,
        preserve_data: bool = True,
        backup_config: bool = True
    ) -> Dict[str, Any]:
        """Handle UV tool update scenario with data preservation."""
        try:
            logger.info(f"Handling UV tool update to version {target_version}")

            # Detect current environment
            env_info = await self.detect_uv_environment()
            if not env_info["docbro_installed_via_uv"]:
                raise UVToolError("DocBro is not installed via UV tool")

            # Create backup if requested
            backup_info = None
            if backup_config:
                backup_info = await self._create_configuration_backup()

            # Preserve user data
            data_backup_info = None
            if preserve_data:
                data_backup_info = await self._preserve_user_data()

            # Perform update based on installation method
            update_result = await self._perform_uv_update(
                env_info["install_method"],
                target_version
            )

            # Restore configuration and data
            if backup_info:
                await self._restore_configuration_backup(backup_info)

            if data_backup_info:
                await self._restore_user_data(data_backup_info)

            # Validate update
            post_update_env = await self.detect_uv_environment()

            result = {
                "success": True,
                "previous_version": env_info.get("uv_version"),
                "updated_version": post_update_env.get("uv_version"),
                "install_method": env_info["install_method"],
                "data_preserved": preserve_data,
                "config_backed_up": backup_config,
                "integrity_check": post_update_env["installation_integrity"]
            }

            logger.info(f"UV tool update completed successfully: {result}")
            return result

        except Exception as e:
            logger.error(f"UV tool update failed: {e}")
            raise UVToolError(f"UV tool update failed: {e}")

    async def _create_configuration_backup(self) -> Dict[str, Any]:
        """Create backup of current configuration."""
        try:
            backup_dir = Path(tempfile.mkdtemp(prefix="docbro-config-backup-"))

            # Backup installation context
            config_paths = self.config_service.get_installation_paths()
            for name, path in config_paths.items():
                if isinstance(path, Path) and path.exists():
                    backup_file = backup_dir / f"{name}.backup"
                    if path.is_file():
                        shutil.copy2(path, backup_file)
                    elif path.is_dir():
                        shutil.copytree(path, backup_file)

            return {
                "backup_dir": str(backup_dir),
                "timestamp": datetime.now().isoformat(),
                "files_backed_up": list(config_paths.keys())
            }

        except Exception as e:
            logger.error(f"Configuration backup failed: {e}")
            raise UVToolError(f"Configuration backup failed: {e}")

    async def _preserve_user_data(self) -> Dict[str, Any]:
        """Preserve user data during update."""
        try:
            data_dir = self.config_service.data_dir
            if not data_dir.exists():
                return {"preserved": False, "reason": "No data directory found"}

            backup_dir = Path(tempfile.mkdtemp(prefix="docbro-data-backup-"))

            # Copy entire data directory
            shutil.copytree(data_dir, backup_dir / "data", dirs_exist_ok=True)

            return {
                "preserved": True,
                "backup_dir": str(backup_dir),
                "data_dir": str(data_dir),
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"User data preservation failed: {e}")
            raise UVToolError(f"User data preservation failed: {e}")

    async def _perform_uv_update(
        self,
        install_method: str,
        target_version: Optional[str]
    ) -> Dict[str, Any]:
        """Perform the actual UV tool update."""
        try:
            if install_method == "uvx":
                return await self._update_via_uvx(target_version)
            elif install_method == "uv-tool":
                return await self._update_via_uv_tool(target_version)
            else:
                raise UVToolError(f"Unsupported install method for update: {install_method}")

        except Exception as e:
            logger.error(f"UV update failed: {e}")
            raise UVToolError(f"UV update failed: {e}")

    async def _update_via_uvx(self, target_version: Optional[str]) -> Dict[str, Any]:
        """Update DocBro via uvx."""
        try:
            # Build install command
            install_source = "git+https://github.com/behemotion/local-doc-bro"
            if target_version:
                install_source += f"@v{target_version}"

            # Upgrade via uvx
            result = await asyncio.create_subprocess_exec(
                "uvx", "install", "--force", install_source,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await result.communicate()

            if result.returncode != 0:
                error_msg = stderr.decode() if stderr else "Unknown error"
                raise UVToolError(f"UVX upgrade failed: {error_msg}")

            return {
                "method": "uvx",
                "command": f"uvx install --force {install_source}",
                "output": stdout.decode(),
                "success": True
            }

        except Exception as e:
            raise UVToolError(f"UVX update failed: {e}")

    async def _update_via_uv_tool(self, target_version: Optional[str]) -> Dict[str, Any]:
        """Update DocBro via uv tool."""
        try:
            # Build install command
            install_source = "git+https://github.com/behemotion/local-doc-bro"
            if target_version:
                install_source += f"@v{target_version}"

            # Upgrade via uv tool
            result = await asyncio.create_subprocess_exec(
                "uv", "tool", "upgrade", "docbro", "--from", install_source,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await result.communicate()

            if result.returncode != 0:
                error_msg = stderr.decode() if stderr else "Unknown error"
                raise UVToolError(f"UV tool upgrade failed: {error_msg}")

            return {
                "method": "uv-tool",
                "command": f"uv tool upgrade docbro --from {install_source}",
                "output": stdout.decode(),
                "success": True
            }

        except Exception as e:
            raise UVToolError(f"UV tool update failed: {e}")

    async def _restore_configuration_backup(self, backup_info: Dict[str, Any]) -> None:
        """Restore configuration from backup."""
        try:
            backup_dir = Path(backup_info["backup_dir"])
            if not backup_dir.exists():
                logger.warning(f"Backup directory not found: {backup_dir}")
                return

            # Restore configuration files
            config_paths = self.config_service.get_installation_paths()
            for name in backup_info["files_backed_up"]:
                if name in config_paths:
                    backup_file = backup_dir / f"{name}.backup"
                    target_path = config_paths[name]

                    if backup_file.exists() and isinstance(target_path, Path):
                        if backup_file.is_file():
                            shutil.copy2(backup_file, target_path)
                        elif backup_file.is_dir():
                            if target_path.exists():
                                shutil.rmtree(target_path)
                            shutil.copytree(backup_file, target_path)

            # Clean up backup
            shutil.rmtree(backup_dir)
            logger.info("Configuration restored from backup")

        except Exception as e:
            logger.error(f"Configuration restore failed: {e}")
            raise UVToolError(f"Configuration restore failed: {e}")

    async def _restore_user_data(self, data_backup_info: Dict[str, Any]) -> None:
        """Restore user data from backup."""
        try:
            if not data_backup_info.get("preserved"):
                return

            backup_dir = Path(data_backup_info["backup_dir"])
            data_dir = Path(data_backup_info["data_dir"])
            backup_data_dir = backup_dir / "data"

            if backup_data_dir.exists():
                if data_dir.exists():
                    # Create timestamped backup of current data
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    current_backup = data_dir.parent / f"data.backup.{timestamp}"
                    shutil.move(str(data_dir), str(current_backup))

                # Restore data
                shutil.copytree(backup_data_dir, data_dir)

            # Clean up backup
            shutil.rmtree(backup_dir)
            logger.info("User data restored from backup")

        except Exception as e:
            logger.error(f"User data restore failed: {e}")
            raise UVToolError(f"User data restore failed: {e}")

    async def handle_clean_uninstall(self, remove_data: bool = False) -> Dict[str, Any]:
        """Handle clean uninstall with proper cleanup."""
        try:
            logger.info(f"Starting clean uninstall (remove_data={remove_data})")

            # Detect current installation
            env_info = await self.detect_uv_environment()

            # Stop any running services
            await self._stop_running_services()

            # Create data backup if requested
            data_backup_info = None
            if not remove_data:
                try:
                    data_backup_info = await self._preserve_user_data()
                except Exception as e:
                    logger.warning(f"Data backup failed during uninstall: {e}")

            # Uninstall based on method
            uninstall_result = await self._perform_uninstall(env_info)

            # Clean up configuration and cache
            cleanup_result = await self._cleanup_installation_files(remove_data)

            result = {
                "success": True,
                "install_method": env_info.get("install_method"),
                "uninstall_method": uninstall_result.get("method"),
                "data_removed": remove_data,
                "data_backed_up": data_backup_info is not None,
                "backup_location": data_backup_info.get("backup_dir") if data_backup_info else None,
                "files_cleaned": cleanup_result.get("files_cleaned", []),
                "directories_cleaned": cleanup_result.get("directories_cleaned", [])
            }

            logger.info(f"Clean uninstall completed: {result}")
            return result

        except Exception as e:
            logger.error(f"Clean uninstall failed: {e}")
            raise UVUninstallError(f"Clean uninstall failed: {e}")

    async def _stop_running_services(self) -> None:
        """Stop any running DocBro services."""
        try:
            # Try to stop MCP server if running
            try:
                result = await asyncio.create_subprocess_exec(
                    "pkill", "-f", "docbro.*serve",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                await result.communicate()
            except Exception:
                pass  # Process might not be running

            logger.info("Stopped running services")

        except Exception as e:
            logger.warning(f"Error stopping services: {e}")

    async def _perform_uninstall(self, env_info: Dict[str, Any]) -> Dict[str, Any]:
        """Perform uninstall based on installation method."""
        try:
            install_method = env_info.get("install_method")

            if install_method == "uvx":
                return await self._uninstall_via_uvx()
            elif install_method == "uv-tool":
                return await self._uninstall_via_uv_tool()
            elif install_method == "manual":
                return await self._uninstall_manual()
            else:
                logger.warning(f"Unknown install method: {install_method}")
                return {"method": "unknown", "success": False}

        except Exception as e:
            raise UVUninstallError(f"Uninstall failed: {e}")

    async def _uninstall_via_uvx(self) -> Dict[str, Any]:
        """Uninstall DocBro via uvx."""
        try:
            result = await asyncio.create_subprocess_exec(
                "uvx", "uninstall", "docbro",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await result.communicate()

            return {
                "method": "uvx",
                "success": result.returncode == 0,
                "output": stdout.decode() if stdout else "",
                "error": stderr.decode() if stderr else ""
            }

        except Exception as e:
            return {
                "method": "uvx",
                "success": False,
                "error": str(e)
            }

    async def _uninstall_via_uv_tool(self) -> Dict[str, Any]:
        """Uninstall DocBro via uv tool."""
        try:
            result = await asyncio.create_subprocess_exec(
                "uv", "tool", "uninstall", "docbro",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await result.communicate()

            return {
                "method": "uv-tool",
                "success": result.returncode == 0,
                "output": stdout.decode() if stdout else "",
                "error": stderr.decode() if stderr else ""
            }

        except Exception as e:
            return {
                "method": "uv-tool",
                "success": False,
                "error": str(e)
            }

    async def _uninstall_manual(self) -> Dict[str, Any]:
        """Handle manual installation uninstall."""
        try:
            # Remove docbro executable if found
            docbro_path = shutil.which("docbro")
            removed_files = []

            if docbro_path:
                try:
                    Path(docbro_path).unlink()
                    removed_files.append(docbro_path)
                except Exception as e:
                    logger.warning(f"Could not remove {docbro_path}: {e}")

            return {
                "method": "manual",
                "success": True,
                "removed_files": removed_files,
                "note": "Manual uninstall - may require additional cleanup"
            }

        except Exception as e:
            return {
                "method": "manual",
                "success": False,
                "error": str(e)
            }

    async def _cleanup_installation_files(self, remove_data: bool = False) -> Dict[str, Any]:
        """Clean up installation files and directories."""
        try:
            cleaned_files = []
            cleaned_directories = []

            # Get paths
            config_dir = self.config_service.config_dir
            cache_dir = self.config_service.cache_dir
            data_dir = self.config_service.data_dir

            # Clean config directory
            if config_dir.exists():
                shutil.rmtree(config_dir)
                cleaned_directories.append(str(config_dir))

            # Clean cache directory
            if cache_dir.exists():
                shutil.rmtree(cache_dir)
                cleaned_directories.append(str(cache_dir))

            # Clean data directory if requested
            if remove_data and data_dir.exists():
                shutil.rmtree(data_dir)
                cleaned_directories.append(str(data_dir))

            return {
                "files_cleaned": cleaned_files,
                "directories_cleaned": cleaned_directories
            }

        except Exception as e:
            logger.error(f"Cleanup failed: {e}")
            raise UVUninstallError(f"Cleanup failed: {e}")

    async def check_uv_version_compatibility(self) -> Dict[str, Any]:
        """Check UV version compatibility with DocBro."""
        try:
            env_info = await self.detect_uv_environment()

            if not env_info["uv_available"]:
                return {
                    "compatible": False,
                    "reason": "UV not available",
                    "required_version": self.min_uv_version,
                    "current_version": None
                }

            current_version = env_info.get("uv_version")
            if not current_version:
                return {
                    "compatible": False,
                    "reason": "Cannot determine UV version",
                    "required_version": self.min_uv_version,
                    "current_version": None
                }

            try:
                is_compatible = version.parse(current_version) >= version.parse(self.min_uv_version)
            except Exception:
                is_compatible = False

            return {
                "compatible": is_compatible,
                "required_version": self.min_uv_version,
                "current_version": current_version,
                "reason": None if is_compatible else f"UV {current_version} < {self.min_uv_version}"
            }

        except Exception as e:
            return {
                "compatible": False,
                "reason": f"Version check failed: {e}",
                "required_version": self.min_uv_version,
                "current_version": None
            }

    async def migrate_between_uv_methods(
        self,
        source_method: str,
        target_method: str
    ) -> Dict[str, Any]:
        """Migrate DocBro between UV installation methods (uvx <-> uv tool)."""
        try:
            logger.info(f"Migrating from {source_method} to {target_method}")

            # Validate migration path
            if source_method not in self.supported_install_methods or target_method not in self.supported_install_methods:
                raise UVMigrationError(f"Unsupported migration: {source_method} -> {target_method}")

            # Detect current installation
            env_info = await self.detect_uv_environment()
            if env_info["install_method"] != source_method:
                raise UVMigrationError(f"Current installation method ({env_info['install_method']}) does not match source ({source_method})")

            # Backup configuration and data
            backup_info = await self._create_configuration_backup()
            data_backup_info = await self._preserve_user_data()

            # Uninstall from source method
            uninstall_result = await self._perform_uninstall(env_info)
            if not uninstall_result.get("success", False):
                raise UVMigrationError(f"Failed to uninstall from {source_method}")

            # Install via target method
            install_result = await self._install_via_method(target_method)
            if not install_result.get("success", False):
                raise UVMigrationError(f"Failed to install via {target_method}")

            # Restore configuration and data
            await self._restore_configuration_backup(backup_info)
            await self._restore_user_data(data_backup_info)

            # Update installation context
            context = self.config_service.load_installation_context()
            if context:
                context.install_method = target_method
                context.install_path = Path(install_result["install_path"])
                self.config_service.save_installation_context(context)

            result = {
                "success": True,
                "source_method": source_method,
                "target_method": target_method,
                "install_path": install_result["install_path"],
                "migration_timestamp": datetime.now().isoformat()
            }

            logger.info(f"Migration completed successfully: {result}")
            return result

        except Exception as e:
            logger.error(f"Migration failed: {e}")
            raise UVMigrationError(f"Migration from {source_method} to {target_method} failed: {e}")

    async def _install_via_method(self, method: str) -> Dict[str, Any]:
        """Install DocBro via specified UV method."""
        try:
            install_source = "git+https://github.com/behemotion/local-doc-bro"

            if method == "uvx":
                result = await asyncio.create_subprocess_exec(
                    "uvx", "install", install_source,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
            elif method == "uv-tool":
                result = await asyncio.create_subprocess_exec(
                    "uv", "tool", "install", install_source,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
            else:
                raise UVMigrationError(f"Unsupported install method: {method}")

            stdout, stderr = await result.communicate()

            if result.returncode != 0:
                error_msg = stderr.decode() if stderr else "Unknown error"
                raise UVMigrationError(f"Installation via {method} failed: {error_msg}")

            # Get install path
            install_path = shutil.which("docbro")
            if not install_path:
                raise UVMigrationError("DocBro command not found after installation")

            return {
                "success": True,
                "method": method,
                "install_path": install_path,
                "output": stdout.decode()
            }

        except Exception as e:
            raise UVMigrationError(f"Installation via {method} failed: {e}")

    async def repair_uv_installation(self) -> Dict[str, Any]:
        """Repair corrupted or broken UV tool installation."""
        try:
            logger.info("Starting UV installation repair")

            # Detect current state
            env_info = await self.detect_uv_environment()

            repair_actions = []

            # Check UV availability
            if not env_info["uv_available"]:
                repair_actions.append("uv_not_available")
                return {
                    "success": False,
                    "reason": "UV not available - cannot repair UV installation",
                    "repair_actions": repair_actions
                }

            # Check DocBro installation integrity
            if not env_info["installation_integrity"]:
                repair_actions.append("reinstall_docbro")

                # Try to reinstall
                if env_info["install_method"] in self.supported_install_methods:
                    try:
                        reinstall_result = await self._install_via_method(env_info["install_method"])
                        if reinstall_result["success"]:
                            repair_actions.append("reinstall_successful")
                        else:
                            repair_actions.append("reinstall_failed")
                    except Exception as e:
                        logger.error(f"Reinstall failed: {e}")
                        repair_actions.append("reinstall_failed")

            # Check and repair configuration
            try:
                self.config_service.load_installation_context()
            except ConfigurationError:
                repair_actions.append("repair_configuration")
                try:
                    repair_result = self.config_service.repair_configuration()
                    if any(repair_result.values()):
                        repair_actions.append("configuration_repaired")
                    else:
                        repair_actions.append("configuration_repair_failed")
                except Exception:
                    repair_actions.append("configuration_repair_failed")

            # Validate final state
            final_env_info = await self.detect_uv_environment()
            repair_successful = final_env_info["installation_integrity"]

            result = {
                "success": repair_successful,
                "repair_actions": repair_actions,
                "initial_state": env_info,
                "final_state": final_env_info,
                "repair_timestamp": datetime.now().isoformat()
            }

            logger.info(f"UV installation repair completed: {result}")
            return result

        except Exception as e:
            logger.error(f"UV installation repair failed: {e}")
            raise UVToolError(f"UV installation repair failed: {e}")

    async def validate_uv_tool_environment(self) -> Dict[str, Any]:
        """Comprehensive validation of UV tool environment."""
        try:
            validation_result = {
                "valid": True,
                "issues": [],
                "warnings": [],
                "recommendations": []
            }

            # Check UV availability and version
            version_check = await self.check_uv_version_compatibility()
            if not version_check["compatible"]:
                validation_result["valid"] = False
                validation_result["issues"].append({
                    "type": "uv_version",
                    "message": f"UV version incompatible: {version_check['reason']}",
                    "current": version_check["current_version"],
                    "required": version_check["required_version"]
                })

            # Check environment detection
            env_info = await self.detect_uv_environment()

            # Check DocBro installation
            if not env_info["docbro_installed_via_uv"]:
                validation_result["warnings"].append({
                    "type": "install_method",
                    "message": f"DocBro not installed via UV (method: {env_info.get('install_method')})"
                })
                validation_result["recommendations"].append(
                    "Consider migrating to UV tool installation for better lifecycle management"
                )

            # Check installation integrity
            if not env_info["installation_integrity"]:
                validation_result["valid"] = False
                validation_result["issues"].append({
                    "type": "integrity",
                    "message": "DocBro installation integrity check failed"
                })

            # Check configuration
            try:
                context = self.config_service.load_installation_context()
                if not context:
                    validation_result["issues"].append({
                        "type": "configuration",
                        "message": "Installation context not found"
                    })
            except Exception as e:
                validation_result["valid"] = False
                validation_result["issues"].append({
                    "type": "configuration",
                    "message": f"Configuration error: {e}"
                })

            # Check required directories
            paths = self.config_service.get_installation_paths()
            for name, path in paths.items():
                if isinstance(path, Path) and name.endswith("_dir"):
                    if not path.exists():
                        validation_result["warnings"].append({
                            "type": "directory",
                            "message": f"Directory missing: {name} ({path})"
                        })

            validation_result["environment_info"] = env_info
            validation_result["validation_timestamp"] = datetime.now().isoformat()

            return validation_result

        except Exception as e:
            logger.error(f"Environment validation failed: {e}")
            return {
                "valid": False,
                "issues": [{
                    "type": "validation_error",
                    "message": f"Validation failed: {e}"
                }],
                "warnings": [],
                "recommendations": [],
                "validation_timestamp": datetime.now().isoformat()
            }