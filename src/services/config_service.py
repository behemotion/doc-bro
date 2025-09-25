"""Configuration persistence service for DocBro setup logic.

This service handles saving, loading, and managing setup configurations.
"""

import json
import logging
from typing import Optional, Dict, Any
from pathlib import Path
from datetime import datetime, timezone

from platformdirs import user_config_dir, user_data_dir

from ..models.setup_configuration import SetupConfiguration
from ..models.setup_session import SetupSession


logger = logging.getLogger(__name__)


class ConfigService:
    """Manages setup configuration persistence."""

    def __init__(self):
        """Initialize config service."""
        self.config_dir = Path(user_config_dir("docbro"))
        self.data_dir = Path(user_data_dir("docbro"))
        self.config_file = self.config_dir / "setup-config.json"
        self.session_dir = self.data_dir / "sessions"

        # Ensure directories exist
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.session_dir.mkdir(parents=True, exist_ok=True)

    async def save_configuration(self, config: SetupConfiguration) -> bool:
        """Save setup configuration to disk."""
        try:
            # Update timestamp
            config.update_timestamp()

            # Create backup if existing config exists
            if self.config_file.exists():
                await self.backup_configuration()

            # Write configuration
            with open(self.config_file, 'w') as f:
                json.dump(config.to_dict(), f, indent=2)

            logger.info(f"Configuration saved: {self.config_file}")
            return True

        except Exception as e:
            logger.error(f"Failed to save configuration: {e}")
            return False

    async def load_configuration(self) -> Optional[SetupConfiguration]:
        """Load setup configuration from disk."""
        if not self.config_file.exists():
            return None

        try:
            with open(self.config_file, 'r') as f:
                data = json.load(f)

            config = SetupConfiguration.from_dict(data)
            logger.info(f"Configuration loaded: {self.config_file}")
            return config

        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            return None

    async def backup_configuration(self) -> Optional[Path]:
        """Create backup of current configuration."""
        if not self.config_file.exists():
            return None

        try:
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            backup_file = self.config_dir / f"setup-config.{timestamp}.backup.json"

            with open(self.config_file, 'r') as src, open(backup_file, 'w') as dst:
                dst.write(src.read())

            logger.info(f"Configuration backup created: {backup_file}")
            return backup_file

        except Exception as e:
            logger.error(f"Failed to create backup: {e}")
            return None

    async def save_session(self, session: SetupSession) -> bool:
        """Save setup session to disk."""
        try:
            session_file = self.session_dir / f"{session.session_id}.json"

            with open(session_file, 'w') as f:
                json.dump(session.to_dict(), f, indent=2)

            logger.debug(f"Session saved: {session_file}")
            return True

        except Exception as e:
            logger.error(f"Failed to save session: {e}")
            return False

    async def load_session(self, session_id: str) -> Optional[SetupSession]:
        """Load setup session from disk."""
        try:
            session_file = self.session_dir / f"{session_id}.json"

            if not session_file.exists():
                return None

            with open(session_file, 'r') as f:
                data = json.load(f)

            session = SetupSession.from_dict(data)
            logger.debug(f"Session loaded: {session_file}")
            return session

        except Exception as e:
            logger.error(f"Failed to load session: {e}")
            return None

    async def delete_session(self, session_id: str) -> bool:
        """Delete setup session from disk."""
        try:
            session_file = self.session_dir / f"{session_id}.json"

            if session_file.exists():
                session_file.unlink()
                logger.debug(f"Session deleted: {session_file}")

            return True

        except Exception as e:
            logger.error(f"Failed to delete session: {e}")
            return False

    async def check_existing_setup(self) -> Optional[Dict[str, Any]]:
        """Check if setup has been completed before."""
        config = await self.load_configuration()

        if not config:
            return None

        return {
            "setup_completed": config.is_completed(),
            "setup_mode": config.setup_mode,
            "last_setup_time": config.updated_at.isoformat(),
            "components_configured": config.get_configured_components(),
            "configuration_file": str(self.config_file)
        }

    async def cleanup_corrupted_state(self) -> Dict[str, Any]:
        """Clean up corrupted setup state."""
        try:
            backup_created = False

            # Backup current config if it exists
            if self.config_file.exists():
                backup_file = await self.backup_configuration()
                backup_created = backup_file is not None

            # Clean up session files
            session_files_removed = 0
            for session_file in self.session_dir.glob("*.json"):
                try:
                    session_file.unlink()
                    session_files_removed += 1
                except Exception:
                    pass

            logger.info(f"Cleaned up corrupted state: {session_files_removed} session files removed")

            return {
                "cleanup_successful": True,
                "backup_created": backup_created,
                "session_files_removed": session_files_removed
            }

        except Exception as e:
            logger.error(f"Failed to cleanup corrupted state: {e}")
            return {"cleanup_successful": False, "error": str(e)}