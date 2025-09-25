"""Critical decisions handling service for installation processes.

This service manages critical decision points during installation, providing
methods to retrieve pending decisions and submit user choices. It integrates
with the InstallationWizardService to handle decision resolution workflow.
"""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
import logging

from src.models.installation import CriticalDecisionPoint
from src.services.config import ConfigService
from src.services.installation_wizard import InstallationWizardService

logger = logging.getLogger(__name__)


class DecisionHandlerError(Exception):
    """Base exception for decision handler errors."""
    pass


class DecisionNotFoundError(DecisionHandlerError):
    """Exception raised when a decision is not found."""
    pass


class InvalidDecisionError(DecisionHandlerError):
    """Exception raised when a decision format is invalid."""
    pass


class DecisionHandler:
    """Service for managing critical installation decisions.

    This service provides methods to retrieve pending critical decision points
    and handle user decision submissions during the installation process.
    """

    def __init__(self):
        """Initialize decision handler."""
        self.config_service = ConfigService()
        self.installation_wizard: Optional[InstallationWizardService] = None

    def _get_installation_wizard(self) -> InstallationWizardService:
        """Get installation wizard service instance.

        Returns:
            InstallationWizardService instance
        """
        if not self.installation_wizard:
            self.installation_wizard = InstallationWizardService()
        return self.installation_wizard

    async def get_installation_decisions(self, installation_id: str) -> List[Dict[str, Any]]:
        """Get critical decisions for an installation.

        Args:
            installation_id: UUID of the installation process

        Returns:
            List of critical decision points as dictionaries

        Raises:
            DecisionHandlerError: If installation not found or invalid
        """
        try:
            # Validate installation ID format
            uuid.UUID(installation_id)
        except (ValueError, TypeError):
            raise DecisionHandlerError(f"Invalid installation ID format: {installation_id}")

        try:
            # Load installation decisions from storage
            decisions_path = self._get_decisions_path(installation_id)

            if not decisions_path.exists():
                # Check if installation exists at all
                wizard = self._get_installation_wizard()
                profile = await wizard.load_installation_profile()

                if not profile or str(profile.id) != installation_id:
                    # Return empty list for non-existent installations
                    logger.info(f"No installation found for ID {installation_id}")
                    return []

                # Installation exists but no decisions yet
                return []

            # Load decisions from file
            with open(decisions_path, 'r') as f:
                decisions_data = json.load(f)

            # Validate and convert to CriticalDecisionPoint models
            decisions = []
            for decision_data in decisions_data.get('decisions', []):
                try:
                    decision = CriticalDecisionPoint.model_validate(decision_data)
                    decisions.append(decision.model_dump())
                except Exception as e:
                    logger.warning(f"Invalid decision data: {e}")
                    continue

            logger.info(f"Retrieved {len(decisions)} decisions for installation {installation_id}")
            return decisions

        except DecisionHandlerError:
            raise
        except Exception as e:
            logger.error(f"Failed to get installation decisions: {e}")
            raise DecisionHandlerError(f"Cannot retrieve decisions: {str(e)}")

    async def submit_installation_decision(
        self,
        installation_id: str,
        decision_data: Dict[str, Any]
    ) -> bool:
        """Submit user choice for a critical decision.

        Args:
            installation_id: UUID of the installation process
            decision_data: Dictionary containing decision_id and user_choice

        Returns:
            True if decision was successfully submitted

        Raises:
            DecisionHandlerError: If submission fails
            DecisionNotFoundError: If decision not found
            InvalidDecisionError: If decision format is invalid
        """
        try:
            # Validate installation ID format
            uuid.UUID(installation_id)
        except (ValueError, TypeError):
            raise DecisionHandlerError(f"Invalid installation ID format: {installation_id}")

        # Validate decision data format
        if not isinstance(decision_data, dict):
            raise InvalidDecisionError("Decision data must be a dictionary")

        if 'decision_id' not in decision_data:
            raise InvalidDecisionError("Missing required field: decision_id")

        if 'user_choice' not in decision_data:
            raise InvalidDecisionError("Missing required field: user_choice")

        decision_id = decision_data['decision_id']
        user_choice = decision_data['user_choice']

        try:
            # Load current decisions
            decisions_path = self._get_decisions_path(installation_id)

            if not decisions_path.exists():
                raise DecisionNotFoundError(f"No decisions found for installation {installation_id}")

            with open(decisions_path, 'r') as f:
                decisions_data = json.load(f)

            # Find and update the decision
            decision_found = False
            for decision_item in decisions_data.get('decisions', []):
                if decision_item.get('decision_id') == decision_id:
                    # Update the decision with user choice
                    decision_item['user_choice'] = user_choice
                    decision_item['resolved'] = True
                    decision_item['timestamp'] = datetime.now().isoformat()
                    decision_found = True
                    break

            if not decision_found:
                raise DecisionNotFoundError(f"Decision {decision_id} not found")

            # Validate the updated decision
            try:
                updated_decision = CriticalDecisionPoint.model_validate(decision_item)

                # Validate user choice against options
                await self._validate_user_choice(updated_decision, user_choice)

            except Exception as e:
                raise InvalidDecisionError(f"Invalid decision update: {str(e)}")

            # Save updated decisions
            self.config_service.ensure_directories()
            with open(decisions_path, 'w') as f:
                json.dump(decisions_data, f, indent=2)

            logger.info(f"Decision {decision_id} resolved for installation {installation_id}")

            # Notify installation wizard of decision resolution
            await self._notify_decision_resolved(installation_id, decision_id, user_choice)

            return True

        except (DecisionNotFoundError, InvalidDecisionError):
            raise
        except Exception as e:
            logger.error(f"Failed to submit installation decision: {e}")
            raise DecisionHandlerError(f"Cannot submit decision: {str(e)}")

    async def save_installation_decisions(
        self,
        installation_id: str,
        decisions: List[CriticalDecisionPoint]
    ) -> None:
        """Save critical decisions for an installation.

        Args:
            installation_id: UUID of the installation process
            decisions: List of critical decision points

        Raises:
            DecisionHandlerError: If save operation fails
        """
        try:
            # Validate installation ID format
            uuid.UUID(installation_id)
        except (ValueError, TypeError):
            raise DecisionHandlerError(f"Invalid installation ID format: {installation_id}")

        try:
            decisions_path = self._get_decisions_path(installation_id)
            self.config_service.ensure_directories()

            # Convert decisions to dict format
            decisions_data = {
                'installation_id': installation_id,
                'created_at': datetime.now().isoformat(),
                'decisions': [decision.model_dump() for decision in decisions]
            }

            # Save to file
            with open(decisions_path, 'w') as f:
                json.dump(decisions_data, f, indent=2)

            logger.info(f"Saved {len(decisions)} decisions for installation {installation_id}")

        except Exception as e:
            logger.error(f"Failed to save installation decisions: {e}")
            raise DecisionHandlerError(f"Cannot save decisions: {str(e)}")

    async def remove_installation_decisions(self, installation_id: str) -> None:
        """Remove decisions for an installation.

        Args:
            installation_id: UUID of the installation process
        """
        try:
            decisions_path = self._get_decisions_path(installation_id)
            if decisions_path.exists():
                decisions_path.unlink()
                logger.info(f"Removed decisions for installation {installation_id}")
        except Exception as e:
            logger.error(f"Failed to remove installation decisions: {e}")

    def _get_decisions_path(self, installation_id: str) -> Path:
        """Get path to decisions file for installation.

        Args:
            installation_id: UUID of the installation process

        Returns:
            Path to the decisions JSON file
        """
        return self.config_service.config_dir / "installations" / f"{installation_id}_decisions.json"

    async def _validate_user_choice(
        self,
        decision: CriticalDecisionPoint,
        user_choice: Union[str, Dict[str, Any]]
    ) -> None:
        """Validate user choice against decision options.

        Args:
            decision: The critical decision point
            user_choice: User's selected choice

        Raises:
            InvalidDecisionError: If choice is invalid
        """
        # Extract choice ID
        choice_id = user_choice
        if isinstance(user_choice, dict):
            choice_id = user_choice.get('id')

        if not choice_id:
            raise InvalidDecisionError("User choice must specify an option ID")

        # Check if choice ID is valid
        valid_options = [option['id'] for option in decision.options]
        if choice_id not in valid_options:
            raise InvalidDecisionError(f"Invalid choice '{choice_id}'. Valid options: {valid_options}")

        # Apply validation pattern if provided
        if decision.validation_pattern and isinstance(user_choice, dict):
            custom_value = user_choice.get('value') or user_choice.get('path') or user_choice.get('port')
            if custom_value:
                import re
                if not re.match(decision.validation_pattern, str(custom_value)):
                    raise InvalidDecisionError(
                        f"Custom value '{custom_value}' doesn't match pattern '{decision.validation_pattern}'"
                    )

    async def _notify_decision_resolved(
        self,
        installation_id: str,
        decision_id: str,
        user_choice: Union[str, Dict[str, Any]]
    ) -> None:
        """Notify installation wizard that a decision has been resolved.

        Args:
            installation_id: UUID of the installation process
            decision_id: ID of the resolved decision
            user_choice: User's selected choice
        """
        try:
            # This could trigger continuation of the installation process
            # For now, just log the resolution
            logger.info(
                f"Decision resolved - Installation: {installation_id}, "
                f"Decision: {decision_id}, Choice: {user_choice}"
            )

            # In a full implementation, this could:
            # - Resume the installation wizard if waiting for this decision
            # - Apply the decision to configuration
            # - Trigger next phase of installation

        except Exception as e:
            logger.error(f"Failed to notify decision resolution: {e}")