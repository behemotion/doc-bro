"""Shelf wizard with step definitions and flow management.

Provides interactive setup wizard for shelf configuration with
step-by-step user guidance and validation.
"""

import asyncio
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from src.models.wizard_step import WizardStep
from src.models.wizard_state import WizardState
from src.models.configuration_state import ConfigurationState
from src.cli.utils.navigation import ArrowNavigator, NavigationChoice
from src.logic.wizard.orchestrator import WizardOrchestrator


@dataclass
class ShelfWizardResult:
    """Result of shelf wizard execution."""

    success: bool
    configuration: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    steps_completed: int = 0


class ShelfWizard:
    """Interactive wizard for shelf setup and configuration."""

    def __init__(self):
        """Initialize shelf wizard."""
        self.orchestrator = WizardOrchestrator()
        self.navigator = ArrowNavigator()

    def get_wizard_steps(self) -> List[WizardStep]:
        """Get the defined steps for shelf wizard.

        Returns:
            List of WizardStep objects defining the flow
        """
        steps = [
            WizardStep(
                step_number=1,
                wizard_type="shelf",
                step_title="Shelf Description",
                prompt_text="Enter a description for this shelf (optional):",
                input_type="text",
                validation_rules=["max_length:500"],
                is_optional=True,
                depends_on=None
            ),
            WizardStep(
                step_number=2,
                wizard_type="shelf",
                step_title="Auto-Fill Setting",
                prompt_text="Automatically fill empty boxes when they are accessed?",
                input_type="boolean",
                validation_rules=[],
                is_optional=False,
                depends_on=None
            ),
            WizardStep(
                step_number=3,
                wizard_type="shelf",
                step_title="Default Box Type",
                prompt_text="Choose the default box type for new boxes in this shelf:",
                input_type="choice",
                choices=["drag", "rag", "bag"],
                validation_rules=["required"],
                is_optional=False,
                depends_on=None
            ),
            WizardStep(
                step_number=4,
                wizard_type="shelf",
                step_title="Tags",
                prompt_text="Add tags for this shelf (comma-separated, optional):",
                input_type="text",
                validation_rules=["tag_format"],
                is_optional=True,
                depends_on=None
            ),
            WizardStep(
                step_number=5,
                wizard_type="shelf",
                step_title="Confirmation",
                prompt_text="Review your configuration and confirm:",
                input_type="boolean",
                validation_rules=[],
                is_optional=False,
                depends_on=None
            )
        ]
        return steps

    async def run(self, shelf_name: str, auto_advance: bool = False) -> ShelfWizardResult:
        """Run the shelf wizard for the specified shelf.

        Args:
            shelf_name: Name of the shelf to configure
            auto_advance: Whether to skip optional steps automatically

        Returns:
            ShelfWizardResult with configuration and success status
        """
        try:
            # Initialize wizard session
            wizard_id = await self.orchestrator.start_session(
                wizard_type="shelf",
                target_entity=shelf_name,
                config={"auto_advance": auto_advance}
            )

            steps = self.get_wizard_steps()
            collected_data = {}

            print(f"\n🧙 Setting up shelf '{shelf_name}'\n")

            # Execute each step
            for step in steps:
                if auto_advance and step.is_optional:
                    # Skip optional steps in auto mode
                    continue

                print(f"Step {step.step_number}/{len(steps)}: {step.step_title}")

                if step.step_number == 5:  # Confirmation step
                    # Show summary before confirmation
                    await self._display_configuration_summary(collected_data)

                response = await self._execute_step(step, collected_data)

                if response is None:
                    # User cancelled
                    await self.orchestrator.cleanup_session(wizard_id)
                    return ShelfWizardResult(
                        success=False,
                        error_message="Wizard cancelled by user",
                        steps_completed=step.step_number - 1
                    )

                collected_data[self._get_step_key(step)] = response

                if step.step_number == 5 and not response:
                    # User rejected configuration
                    print("Configuration rejected. Starting over...")
                    collected_data = {}
                    continue

            # Apply configuration
            configuration = await self._build_configuration(collected_data)
            await self._apply_configuration(shelf_name, configuration)

            await self.orchestrator.cleanup_session(wizard_id)

            print(f"\n✅ Shelf '{shelf_name}' configured successfully!")

            return ShelfWizardResult(
                success=True,
                configuration=configuration,
                steps_completed=len(steps)
            )

        except Exception as e:
            return ShelfWizardResult(
                success=False,
                error_message=str(e),
                steps_completed=0
            )

    async def _execute_step(self, step: WizardStep, collected_data: Dict[str, Any]) -> Any:
        """Execute a single wizard step.

        Args:
            step: WizardStep to execute
            collected_data: Data collected from previous steps

        Returns:
            User response or None if cancelled
        """
        print(f"{step.prompt_text}")

        if step.input_type == "text":
            return await self._handle_text_input(step)

        elif step.input_type == "boolean":
            return await self._handle_boolean_input(step)

        elif step.input_type == "choice":
            return await self._handle_choice_input(step)

        else:
            raise ValueError(f"Unknown input type: {step.input_type}")

    async def _handle_text_input(self, step: WizardStep) -> Optional[str]:
        """Handle text input step.

        Args:
            step: WizardStep configuration

        Returns:
            User input string or None if cancelled
        """
        try:
            user_input = input("> ").strip()

            if not user_input and step.is_optional:
                return ""

            if not user_input and not step.is_optional:
                print("This field is required. Please enter a value.")
                return await self._handle_text_input(step)

            # Validate input
            if not await self._validate_input(user_input, step.validation_rules):
                print("Invalid input. Please try again.")
                return await self._handle_text_input(step)

            return user_input

        except KeyboardInterrupt:
            return None

    async def _handle_boolean_input(self, step: WizardStep) -> Optional[bool]:
        """Handle boolean input step.

        Args:
            step: WizardStep configuration

        Returns:
            Boolean value or None if cancelled
        """
        try:
            while True:
                response = input("> (y/n): ").strip().lower()

                if response in ['y', 'yes', 'true', '1']:
                    return True
                elif response in ['n', 'no', 'false', '0']:
                    return False
                else:
                    print("Please enter 'y' for yes or 'n' for no.")

        except KeyboardInterrupt:
            return None

    async def _handle_choice_input(self, step: WizardStep) -> Optional[str]:
        """Handle choice input step using arrow navigation.

        Args:
            step: WizardStep configuration

        Returns:
            Selected choice or None if cancelled
        """
        try:
            if not step.choices:
                raise ValueError("Choice step must have choices defined")

            # Create navigation choices with descriptions
            nav_choices = []
            for choice in step.choices:
                description = self._get_choice_description(choice)
                nav_choices.append(NavigationChoice(
                    value=choice,
                    label=choice.title(),
                    description=description
                ))

            result = self.navigator.navigate_choices(
                prompt="Use arrows to select:",
                choices=nav_choices,
                default=0
            )

            return result.value if result else None

        except KeyboardInterrupt:
            return None

    def _get_choice_description(self, choice: str) -> str:
        """Get description for a choice option.

        Args:
            choice: Choice value

        Returns:
            Description string
        """
        descriptions = {
            "drag": "Website crawler - for crawling documentation sites",
            "rag": "Document processor - for uploading files and documents",
            "bag": "Data storage - for storing raw data and content"
        }
        return descriptions.get(choice, "")

    async def _validate_input(self, value: str, validation_rules: List[str]) -> bool:
        """Validate user input against rules.

        Args:
            value: Input value to validate
            validation_rules: List of validation rule strings

        Returns:
            True if valid, False otherwise
        """
        for rule in validation_rules:
            if rule.startswith("max_length:"):
                max_length = int(rule.split(":")[1])
                if len(value) > max_length:
                    print(f"Input too long. Maximum {max_length} characters allowed.")
                    return False

            elif rule == "required":
                if not value.strip():
                    print("This field is required.")
                    return False

            elif rule == "tag_format":
                # Validate tag format (alphanumeric, hyphens, underscores)
                if value:
                    tags = [tag.strip() for tag in value.split(",")]
                    for tag in tags:
                        if not tag.replace("-", "").replace("_", "").isalnum():
                            print(f"Invalid tag format: '{tag}'. Use only letters, numbers, hyphens, and underscores.")
                            return False

        return True

    def _get_step_key(self, step: WizardStep) -> str:
        """Get storage key for step data.

        Args:
            step: WizardStep object

        Returns:
            Key string for storing step data
        """
        key_mapping = {
            1: "description",
            2: "auto_fill",
            3: "default_box_type",
            4: "tags",
            5: "confirmed"
        }
        return key_mapping.get(step.step_number, f"step_{step.step_number}")

    async def _display_configuration_summary(self, collected_data: Dict[str, Any]) -> None:
        """Display configuration summary before confirmation.

        Args:
            collected_data: Data collected from wizard steps
        """
        print("\n📋 Configuration Summary:")
        print("=" * 30)

        description = collected_data.get("description", "")
        if description:
            print(f"Description: {description}")
        else:
            print("Description: (none)")

        auto_fill = collected_data.get("auto_fill", False)
        print(f"Auto-fill empty boxes: {'Yes' if auto_fill else 'No'}")

        default_type = collected_data.get("default_box_type", "")
        print(f"Default box type: {default_type.title()}")

        tags = collected_data.get("tags", "")
        if tags:
            tag_list = [tag.strip() for tag in tags.split(",")]
            print(f"Tags: {', '.join(tag_list)}")
        else:
            print("Tags: (none)")

        print("=" * 30)

    async def _build_configuration(self, collected_data: Dict[str, Any]) -> Dict[str, Any]:
        """Build final configuration from collected data.

        Args:
            collected_data: Data collected from wizard steps

        Returns:
            Final configuration dictionary
        """
        tags_str = collected_data.get("tags", "")
        tags = [tag.strip() for tag in tags_str.split(",") if tag.strip()] if tags_str else []

        configuration = {
            "description": collected_data.get("description", ""),
            "auto_fill": collected_data.get("auto_fill", False),
            "default_box_type": collected_data.get("default_box_type", "drag"),
            "tags": tags,
            "wizard_completed": True,
            "configured_at": asyncio.get_event_loop().time()
        }

        return configuration

    async def _apply_configuration(self, shelf_name: str, configuration: Dict[str, Any]) -> None:
        """Apply configuration to the shelf.

        Args:
            shelf_name: Name of the shelf to configure
            configuration: Configuration to apply
        """
        # This would typically save to database
        # For now, we'll just validate the configuration structure
        required_keys = ["description", "auto_fill", "default_box_type", "tags"]
        for key in required_keys:
            if key not in configuration:
                raise ValueError(f"Missing required configuration key: {key}")

        # Create configuration state
        config_state = ConfigurationState(
            is_configured=True,
            has_content=False,  # New shelf starts empty
            configuration_version="1.0",
            setup_completed_at=None,  # Will be set by service
            needs_migration=False
        )

        # In a real implementation, this would save to database
        print(f"Configuration applied to shelf '{shelf_name}'")

    async def get_wizard_info(self) -> Dict[str, Any]:
        """Get information about this wizard.

        Returns:
            Dictionary with wizard metadata
        """
        steps = self.get_wizard_steps()

        return {
            "wizard_type": "shelf",
            "name": "Shelf Setup Wizard",
            "description": "Interactive setup for shelf configuration",
            "total_steps": len(steps),
            "estimated_time": "2-3 minutes",
            "features": [
                "Custom description and tagging",
                "Auto-fill behavior configuration",
                "Default box type selection",
                "Configuration validation"
            ]
        }