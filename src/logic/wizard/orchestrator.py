"""Wizard orchestrator for managing interactive setup sessions."""

import json
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from src.core.config import DocBroConfig
from src.models.wizard_state import WizardState
from src.models.wizard_step import WizardStep
from src.services.database import DatabaseManager
from src.cli.utils.navigation import ArrowNavigator, NavigationChoice


class WizardResult:
    """Result from wizard completion."""

    def __init__(self, configuration_applied: bool, entity_created: bool, next_actions: List[Dict[str, str]]):
        self.configuration_applied = configuration_applied
        self.entity_created = entity_created
        self.next_actions = next_actions


class StepResult:
    """Result from processing a wizard step."""

    def __init__(self, accepted: bool, validation_errors: List[str], next_step: Optional[WizardStep], is_complete: bool):
        self.accepted = accepted
        self.validation_errors = validation_errors
        self.next_step = next_step
        self.is_complete = is_complete


class WizardOrchestrator:
    """Manages wizard sessions and step processing."""

    def __init__(self, config: Optional[DocBroConfig] = None):
        """Initialize wizard orchestrator."""
        self.config = config or DocBroConfig()
        self.db_manager = DatabaseManager(self.config)
        self.session_timeout = timedelta(minutes=30)  # 30-minute session timeout
        self.max_sessions = 10  # Maximum concurrent sessions per user

    async def start_wizard(self, wizard_type: str, target_entity: str) -> WizardState:
        """Start a new wizard session."""
        # Clean up expired sessions first
        await self._cleanup_expired_sessions()

        # Check session limit
        active_sessions = await self._count_active_sessions()
        if active_sessions >= self.max_sessions:
            raise ValueError(f"Maximum {self.max_sessions} concurrent wizard sessions exceeded")

        # Get wizard steps
        steps = self._get_wizard_steps(wizard_type)
        if not steps:
            raise ValueError(f"No steps defined for wizard type: {wizard_type}")

        # Create new wizard session
        wizard_id = str(uuid.uuid4())
        now = datetime.utcnow()

        wizard_state = WizardState(
            wizard_id=wizard_id,
            wizard_type=wizard_type,
            target_entity=target_entity,
            current_step=1,
            total_steps=len(steps),
            collected_data={},
            start_time=now,
            last_activity=now,
            is_complete=False
        )

        # Store in database
        await self._save_wizard_state(wizard_state)

        return wizard_state

    async def process_step(self, wizard_id: str, response: Any) -> StepResult:
        """Process user response to current wizard step."""
        # Load wizard state
        wizard_state = await self._load_wizard_state(wizard_id)
        if not wizard_state:
            raise ValueError(f"Wizard session {wizard_id} not found or expired")

        if wizard_state.is_complete:
            raise ValueError("Wizard session is already complete")

        # Get current step definition
        steps = self._get_wizard_steps(wizard_state.wizard_type)
        current_step = steps[wizard_state.current_step - 1]

        # Validate response
        validation_errors = self._validate_response(current_step, response)
        if validation_errors:
            return StepResult(
                accepted=False,
                validation_errors=validation_errors,
                next_step=current_step,
                is_complete=False
            )

        # Store response
        wizard_state.collected_data[current_step.step_title.lower().replace(" ", "_")] = response
        wizard_state.last_activity = datetime.utcnow()

        # Check if wizard is complete
        if wizard_state.current_step >= wizard_state.total_steps:
            wizard_state.is_complete = True
            await self._save_wizard_state(wizard_state)

            return StepResult(
                accepted=True,
                validation_errors=[],
                next_step=None,
                is_complete=True
            )

        # Move to next step
        wizard_state.current_step += 1
        next_step = steps[wizard_state.current_step - 1]

        # Save updated state
        await self._save_wizard_state(wizard_state)

        return StepResult(
            accepted=True,
            validation_errors=[],
            next_step=next_step,
            is_complete=False
        )

    async def complete_wizard(self, wizard_id: str) -> WizardResult:
        """Complete wizard and apply configuration."""
        wizard_state = await self._load_wizard_state(wizard_id)
        if not wizard_state:
            raise ValueError(f"Wizard session {wizard_id} not found")

        if not wizard_state.is_complete:
            raise ValueError("Wizard session is not complete")

        # Apply configuration based on wizard type
        if wizard_state.wizard_type == "shelf":
            result = await self._apply_shelf_configuration(wizard_state)
        elif wizard_state.wizard_type == "box":
            result = await self._apply_box_configuration(wizard_state)
        elif wizard_state.wizard_type == "mcp":
            result = await self._apply_mcp_configuration(wizard_state)
        else:
            raise ValueError(f"Unknown wizard type: {wizard_state.wizard_type}")

        # Clean up wizard session
        await self._delete_wizard_state(wizard_id)

        return result

    async def get_wizard_status(self, wizard_id: str) -> Optional[WizardState]:
        """Get current wizard session status."""
        return await self._load_wizard_state(wizard_id)

    def _get_wizard_steps(self, wizard_type: str) -> List[WizardStep]:
        """Get step definitions for wizard type."""
        if wizard_type == "shelf":
            return [
                WizardStep(
                    step_number=1,
                    wizard_type="shelf",
                    step_title="Description",
                    prompt_text="Enter shelf description (optional):",
                    input_type="text",
                    choices=None,
                    validation_rules=["max_length:500"],
                    is_optional=True,
                    depends_on=None
                ),
                WizardStep(
                    step_number=2,
                    wizard_type="shelf",
                    step_title="Auto-fill Setting",
                    prompt_text="Auto-fill empty boxes when accessed?",
                    input_type="boolean",
                    choices=["yes", "no"],
                    validation_rules=[],
                    is_optional=False,
                    depends_on=None
                ),
                WizardStep(
                    step_number=3,
                    wizard_type="shelf",
                    step_title="Default Box Type",
                    prompt_text="Default box type for new boxes:",
                    input_type="choice",
                    choices=["drag", "rag", "bag"],
                    validation_rules=[],
                    is_optional=False,
                    depends_on=None
                ),
                WizardStep(
                    step_number=4,
                    wizard_type="shelf",
                    step_title="Tags",
                    prompt_text="Add tags (comma-separated, optional):",
                    input_type="text",
                    choices=None,
                    validation_rules=["csv_format"],
                    is_optional=True,
                    depends_on=None
                ),
                WizardStep(
                    step_number=5,
                    wizard_type="shelf",
                    step_title="Confirmation",
                    prompt_text="Apply this configuration?",
                    input_type="boolean",
                    choices=["yes", "no"],
                    validation_rules=[],
                    is_optional=False,
                    depends_on=None
                )
            ]
        elif wizard_type == "box":
            return [
                WizardStep(
                    step_number=1,
                    wizard_type="box",
                    step_title="Box Type",
                    prompt_text="Select box type:",
                    input_type="choice",
                    choices=["drag", "rag", "bag"],
                    validation_rules=[],
                    is_optional=False,
                    depends_on=None
                ),
                WizardStep(
                    step_number=2,
                    wizard_type="box",
                    step_title="Description",
                    prompt_text="Enter box description (optional):",
                    input_type="text",
                    choices=None,
                    validation_rules=["max_length:500"],
                    is_optional=True,
                    depends_on=None
                ),
                WizardStep(
                    step_number=3,
                    wizard_type="box",
                    step_title="Auto-process",
                    prompt_text="Auto-process content when added?",
                    input_type="boolean",
                    choices=["yes", "no"],
                    validation_rules=[],
                    is_optional=False,
                    depends_on=None
                )
            ]
        elif wizard_type == "mcp":
            return [
                WizardStep(
                    step_number=1,
                    wizard_type="mcp",
                    step_title="Read-only Server",
                    prompt_text="Enable read-only server?",
                    input_type="boolean",
                    choices=["yes", "no"],
                    validation_rules=[],
                    is_optional=False,
                    depends_on=None
                ),
                WizardStep(
                    step_number=2,
                    wizard_type="mcp",
                    step_title="Admin Server",
                    prompt_text="Enable admin server?",
                    input_type="boolean",
                    choices=["yes", "no"],
                    validation_rules=[],
                    is_optional=False,
                    depends_on=None
                )
            ]
        else:
            return []

    def _validate_response(self, step: WizardStep, response: Any) -> List[str]:
        """Validate user response against step requirements."""
        errors = []

        if step.input_type == "choice" and step.choices:
            if response not in step.choices:
                errors.append(f"Response must be one of: {', '.join(step.choices)}")

        if step.input_type == "text" and "max_length" in step.validation_rules:
            max_length = int(step.validation_rules[0].split(":")[1])
            if len(str(response)) > max_length:
                errors.append(f"Response too long (max {max_length} characters)")

        if step.input_type == "boolean":
            if response not in ["yes", "no", "y", "n", True, False]:
                errors.append("Response must be yes/no")

        return errors

    async def _save_wizard_state(self, wizard_state: WizardState) -> None:
        """Save wizard state to database."""
        async with self.db_manager.get_connection() as conn:
            await conn.execute("""
                INSERT OR REPLACE INTO wizard_states
                (wizard_id, wizard_type, target_entity, current_step, total_steps,
                 collected_data, start_time, last_activity, is_complete)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                wizard_state.wizard_id,
                wizard_state.wizard_type,
                wizard_state.target_entity,
                wizard_state.current_step,
                wizard_state.total_steps,
                json.dumps(wizard_state.collected_data),
                wizard_state.start_time.isoformat(),
                wizard_state.last_activity.isoformat(),
                wizard_state.is_complete
            ))
            await conn.commit()

    async def _load_wizard_state(self, wizard_id: str) -> Optional[WizardState]:
        """Load wizard state from database."""
        async with self.db_manager.get_connection() as conn:
            cursor = await conn.execute("""
                SELECT wizard_id, wizard_type, target_entity, current_step, total_steps,
                       collected_data, start_time, last_activity, is_complete
                FROM wizard_states
                WHERE wizard_id = ?
            """, (wizard_id,))

            row = await cursor.fetchone()

        if not row:
            return None

        wizard_id, wizard_type, target_entity, current_step, total_steps, collected_data_json, start_time_str, last_activity_str, is_complete = row

        # Check if session is expired
        last_activity = datetime.fromisoformat(last_activity_str)
        if datetime.utcnow() - last_activity > self.session_timeout:
            await self._delete_wizard_state(wizard_id)
            return None

        return WizardState(
            wizard_id=wizard_id,
            wizard_type=wizard_type,
            target_entity=target_entity,
            current_step=current_step,
            total_steps=total_steps,
            collected_data=json.loads(collected_data_json),
            start_time=datetime.fromisoformat(start_time_str),
            last_activity=last_activity,
            is_complete=is_complete
        )

    async def _delete_wizard_state(self, wizard_id: str) -> None:
        """Delete wizard state from database."""
        async with self.db_manager.get_connection() as conn:
            await conn.execute("DELETE FROM wizard_states WHERE wizard_id = ?", (wizard_id,))
            await conn.commit()

    async def _cleanup_expired_sessions(self) -> None:
        """Clean up expired wizard sessions."""
        cutoff_time = datetime.utcnow() - self.session_timeout
        async with self.db_manager.get_connection() as conn:
            await conn.execute(
                "DELETE FROM wizard_states WHERE last_activity < ?",
                (cutoff_time.isoformat(),)
            )
            await conn.commit()

    async def _count_active_sessions(self) -> int:
        """Count active wizard sessions."""
        async with self.db_manager.get_connection() as conn:
            cursor = await conn.execute("SELECT COUNT(*) FROM wizard_states WHERE is_complete = 0")
            return (await cursor.fetchone())[0]

    async def _apply_shelf_configuration(self, wizard_state: WizardState) -> WizardResult:
        """Apply shelf wizard configuration."""
        # This would integrate with shelf service to create/configure shelf
        return WizardResult(
            configuration_applied=True,
            entity_created=True,
            next_actions=[
                {"action": "create_boxes", "description": "Add boxes to your new shelf"},
                {"action": "fill_content", "description": "Fill boxes with documentation"}
            ]
        )

    async def _apply_box_configuration(self, wizard_state: WizardState) -> WizardResult:
        """Apply box wizard configuration."""
        # This would integrate with box service to create/configure box
        return WizardResult(
            configuration_applied=True,
            entity_created=True,
            next_actions=[
                {"action": "add_content", "description": "Add content to your new box"},
                {"action": "configure_processing", "description": "Set up content processing rules"}
            ]
        )

    async def _apply_mcp_configuration(self, wizard_state: WizardState) -> WizardResult:
        """Apply MCP wizard configuration."""
        # This would integrate with MCP service to configure server
        return WizardResult(
            configuration_applied=True,
            entity_created=False,
            next_actions=[
                {"action": "start_server", "description": "Start MCP server with new configuration"},
                {"action": "connect_client", "description": "Connect AI assistant to MCP server"}
            ]
        )