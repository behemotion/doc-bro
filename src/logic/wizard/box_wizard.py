"""Box wizard with type-aware configuration.

Provides interactive setup wizard for box configuration with
type-specific steps and validation based on box type (drag/rag/bag).
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
class BoxWizardResult:
    """Result of box wizard execution."""

    success: bool
    configuration: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    steps_completed: int = 0
    box_type: Optional[str] = None


class BoxWizard:
    """Interactive wizard for box setup and configuration with type awareness."""

    def __init__(self):
        """Initialize box wizard."""
        self.orchestrator = WizardOrchestrator()
        self.navigator = ArrowNavigator()

    def get_wizard_steps(self, box_type: Optional[str] = None) -> List[WizardStep]:
        """Get the defined steps for box wizard based on type.

        Args:
            box_type: Type of box ('drag', 'rag', 'bag') or None for type selection

        Returns:
            List of WizardStep objects defining the flow
        """
        steps = []

        # Step 1: Box type confirmation (if not provided)
        if box_type is None:
            steps.append(WizardStep(
                step_number=1,
                wizard_type="box",
                step_title="Box Type Selection",
                prompt_text="Choose the type of box to create:",
                input_type="choice",
                choices=["drag", "rag", "bag"],
                validation_rules=["required"],
                is_optional=False,
                depends_on=None
            ))
            step_offset = 1
        else:
            step_offset = 0

        # Step 2: Description
        steps.append(WizardStep(
            step_number=1 + step_offset,
            wizard_type="box",
            step_title="Box Description",
            prompt_text="Enter a description for this box (optional):",
            input_type="text",
            validation_rules=["max_length:500"],
            is_optional=True,
            depends_on=None
        ))

        # Step 3: Auto-process setting
        steps.append(WizardStep(
            step_number=2 + step_offset,
            wizard_type="box",
            step_title="Auto-Processing",
            prompt_text="Automatically process content when it's added?",
            input_type="boolean",
            validation_rules=[],
            is_optional=False,
            depends_on=None
        ))

        # Type-specific steps
        if box_type == "drag" or box_type is None:
            steps.extend(self._get_drag_specific_steps(3 + step_offset))
        elif box_type == "rag":
            steps.extend(self._get_rag_specific_steps(3 + step_offset))
        elif box_type == "bag":
            steps.extend(self._get_bag_specific_steps(3 + step_offset))

        # Final confirmation step
        final_step_num = len(steps) + 1
        steps.append(WizardStep(
            step_number=final_step_num,
            wizard_type="box",
            step_title="Confirmation",
            prompt_text="Review your configuration and confirm:",
            input_type="boolean",
            validation_rules=[],
            is_optional=False,
            depends_on=None
        ))

        return steps

    def _get_drag_specific_steps(self, start_step: int) -> List[WizardStep]:
        """Get drag box specific wizard steps.

        Args:
            start_step: Starting step number

        Returns:
            List of drag-specific WizardStep objects
        """
        return [
            WizardStep(
                step_number=start_step,
                wizard_type="box",
                step_title="Crawl Depth",
                prompt_text="Maximum crawl depth (1-10, default 3):",
                input_type="text",
                validation_rules=["integer_range:1:10"],
                is_optional=True,
                depends_on=None
            ),
            WizardStep(
                step_number=start_step + 1,
                wizard_type="box",
                step_title="Rate Limiting",
                prompt_text="Requests per second (0.1-10.0, default 1.0):",
                input_type="text",
                validation_rules=["float_range:0.1:10.0"],
                is_optional=True,
                depends_on=None
            ),
            WizardStep(
                step_number=start_step + 2,
                wizard_type="box",
                step_title="Page Limit",
                prompt_text="Maximum pages to crawl (default: unlimited):",
                input_type="text",
                validation_rules=["positive_integer"],
                is_optional=True,
                depends_on=None
            )
        ]

    def _get_rag_specific_steps(self, start_step: int) -> List[WizardStep]:
        """Get rag box specific wizard steps.

        Args:
            start_step: Starting step number

        Returns:
            List of rag-specific WizardStep objects
        """
        return [
            WizardStep(
                step_number=start_step,
                wizard_type="box",
                step_title="File Patterns",
                prompt_text="File patterns to include (comma-separated, e.g., *.pdf,*.md):",
                input_type="text",
                validation_rules=["file_pattern"],
                is_optional=True,
                depends_on=None
            ),
            WizardStep(
                step_number=start_step + 1,
                wizard_type="box",
                step_title="Chunk Size",
                prompt_text="Text chunk size (100-2000, default 500):",
                input_type="text",
                validation_rules=["integer_range:100:2000"],
                is_optional=True,
                depends_on=None
            ),
            WizardStep(
                step_number=start_step + 2,
                wizard_type="box",
                step_title="Chunk Overlap",
                prompt_text="Chunk overlap percentage (0-50, default 10):",
                input_type="text",
                validation_rules=["integer_range:0:50"],
                is_optional=True,
                depends_on=None
            )
        ]

    def _get_bag_specific_steps(self, start_step: int) -> List[WizardStep]:
        """Get bag box specific wizard steps.

        Args:
            start_step: Starting step number

        Returns:
            List of bag-specific WizardStep objects
        """
        return [
            WizardStep(
                step_number=start_step,
                wizard_type="box",
                step_title="Storage Format",
                prompt_text="Choose storage format:",
                input_type="choice",
                choices=["json", "yaml", "raw", "compressed"],
                validation_rules=["required"],
                is_optional=False,
                depends_on=None
            ),
            WizardStep(
                step_number=start_step + 1,
                wizard_type="box",
                step_title="Compression",
                prompt_text="Enable compression for stored data?",
                input_type="boolean",
                validation_rules=[],
                is_optional=False,
                depends_on=None
            ),
            WizardStep(
                step_number=start_step + 2,
                wizard_type="box",
                step_title="Indexing",
                prompt_text="Create searchable index for stored data?",
                input_type="boolean",
                validation_rules=[],
                is_optional=False,
                depends_on=None
            )
        ]

    async def run(self, box_name: str, box_type: Optional[str] = None, auto_advance: bool = False) -> BoxWizardResult:
        """Run the box wizard for the specified box.

        Args:
            box_name: Name of the box to configure
            box_type: Type of box ('drag', 'rag', 'bag') or None to prompt
            auto_advance: Whether to skip optional steps automatically

        Returns:
            BoxWizardResult with configuration and success status
        """
        try:
            # Initialize wizard session
            wizard_id = await self.orchestrator.start_session(
                wizard_type="box",
                target_entity=box_name,
                config={"auto_advance": auto_advance, "box_type": box_type}
            )

            collected_data = {}
            determined_box_type = box_type

            print(f"\n🧙 Setting up box '{box_name}'\n")

            # If box type not provided, get it first
            if determined_box_type is None:
                type_step = WizardStep(
                    step_number=1,
                    wizard_type="box",
                    step_title="Box Type Selection",
                    prompt_text="Choose the type of box to create:",
                    input_type="choice",
                    choices=["drag", "rag", "bag"],
                    validation_rules=["required"],
                    is_optional=False,
                    depends_on=None
                )

                print("Step 1: Box Type Selection")
                determined_box_type = await self._execute_step(type_step, collected_data)

                if determined_box_type is None:
                    await self.orchestrator.cleanup_session(wizard_id)
                    return BoxWizardResult(
                        success=False,
                        error_message="Wizard cancelled by user",
                        steps_completed=0
                    )

                collected_data["box_type"] = determined_box_type

            steps = self.get_wizard_steps(determined_box_type)

            # Execute remaining steps
            for step in steps:
                if step.step_title == "Box Type Selection":
                    continue  # Already handled

                if auto_advance and step.is_optional:
                    # Skip optional steps in auto mode with defaults
                    default_value = self._get_default_value(step, determined_box_type)
                    if default_value is not None:
                        collected_data[self._get_step_key(step)] = default_value
                        continue

                print(f"Step {step.step_number}: {step.step_title}")

                if step.step_title == "Confirmation":
                    # Show summary before confirmation
                    await self._display_configuration_summary(collected_data, determined_box_type)

                response = await self._execute_step(step, collected_data)

                if response is None:
                    # User cancelled
                    await self.orchestrator.cleanup_session(wizard_id)
                    return BoxWizardResult(
                        success=False,
                        error_message="Wizard cancelled by user",
                        steps_completed=step.step_number - 1,
                        box_type=determined_box_type
                    )

                collected_data[self._get_step_key(step)] = response

                if step.step_title == "Confirmation" and not response:
                    # User rejected configuration
                    print("Configuration rejected. Starting over...")
                    collected_data = {"box_type": determined_box_type}
                    continue

            # Apply configuration
            configuration = await self._build_configuration(collected_data, determined_box_type)
            await self._apply_configuration(box_name, configuration, determined_box_type)

            await self.orchestrator.cleanup_session(wizard_id)

            print(f"\n✅ Box '{box_name}' configured successfully!")

            return BoxWizardResult(
                success=True,
                configuration=configuration,
                steps_completed=len(steps),
                box_type=determined_box_type
            )

        except Exception as e:
            return BoxWizardResult(
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
        """Handle text input step with validation.

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
                description = self._get_choice_description(step.step_title, choice)
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

    def _get_choice_description(self, step_title: str, choice: str) -> str:
        """Get description for a choice option based on step context.

        Args:
            step_title: Title of the current step
            choice: Choice value

        Returns:
            Description string
        """
        if step_title == "Box Type Selection":
            descriptions = {
                "drag": "Website crawler - for crawling documentation sites",
                "rag": "Document processor - for uploading files and documents",
                "bag": "Data storage - for storing raw data and content"
            }
            return descriptions.get(choice, "")

        elif step_title == "Storage Format":
            descriptions = {
                "json": "JSON format - structured and readable",
                "yaml": "YAML format - human-readable",
                "raw": "Raw format - preserve original structure",
                "compressed": "Compressed format - space efficient"
            }
            return descriptions.get(choice, "")

        return ""

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

            elif rule.startswith("integer_range:"):
                try:
                    min_val, max_val = map(int, rule.split(":")[1:3])
                    int_val = int(value)
                    if not (min_val <= int_val <= max_val):
                        print(f"Value must be between {min_val} and {max_val}.")
                        return False
                except ValueError:
                    print("Please enter a valid integer.")
                    return False

            elif rule.startswith("float_range:"):
                try:
                    min_val, max_val = map(float, rule.split(":")[1:3])
                    float_val = float(value)
                    if not (min_val <= float_val <= max_val):
                        print(f"Value must be between {min_val} and {max_val}.")
                        return False
                except ValueError:
                    print("Please enter a valid number.")
                    return False

            elif rule == "positive_integer":
                try:
                    int_val = int(value)
                    if int_val <= 0:
                        print("Value must be a positive integer.")
                        return False
                except ValueError:
                    print("Please enter a valid positive integer.")
                    return False

            elif rule == "file_pattern":
                # Basic file pattern validation
                if value and not all(c.isalnum() or c in "*.,-_" for c in value):
                    print("Invalid file pattern. Use wildcards (*), letters, numbers, and common punctuation.")
                    return False

        return True

    def _get_step_key(self, step: WizardStep) -> str:
        """Get storage key for step data based on step title.

        Args:
            step: WizardStep object

        Returns:
            Key string for storing step data
        """
        title_to_key = {
            "Box Type Selection": "box_type",
            "Box Description": "description",
            "Auto-Processing": "auto_process",
            "Crawl Depth": "crawl_depth",
            "Rate Limiting": "rate_limit",
            "Page Limit": "max_pages",
            "File Patterns": "file_patterns",
            "Chunk Size": "chunk_size",
            "Chunk Overlap": "chunk_overlap",
            "Storage Format": "storage_format",
            "Compression": "compression",
            "Indexing": "indexing",
            "Confirmation": "confirmed"
        }
        return title_to_key.get(step.step_title, f"step_{step.step_number}")

    def _get_default_value(self, step: WizardStep, box_type: str) -> Any:
        """Get default value for optional step based on box type.

        Args:
            step: WizardStep object
            box_type: Type of box

        Returns:
            Default value or None
        """
        defaults = {
            "drag": {
                "Crawl Depth": "3",
                "Rate Limiting": "1.0",
                "Page Limit": ""
            },
            "rag": {
                "File Patterns": "*.pdf,*.md,*.txt",
                "Chunk Size": "500",
                "Chunk Overlap": "10"
            },
            "bag": {
                "Storage Format": "json",
                "Compression": True,
                "Indexing": True
            }
        }

        return defaults.get(box_type, {}).get(step.step_title)

    async def _display_configuration_summary(self, collected_data: Dict[str, Any], box_type: str) -> None:
        """Display configuration summary before confirmation.

        Args:
            collected_data: Data collected from wizard steps
            box_type: Type of box being configured
        """
        print(f"\n📋 {box_type.title()} Box Configuration Summary:")
        print("=" * 40)

        print(f"Box Type: {box_type.title()}")

        description = collected_data.get("description", "")
        if description:
            print(f"Description: {description}")
        else:
            print("Description: (none)")

        auto_process = collected_data.get("auto_process", False)
        print(f"Auto-process content: {'Yes' if auto_process else 'No'}")

        # Type-specific configuration
        if box_type == "drag":
            print(f"Crawl depth: {collected_data.get('crawl_depth', '3')}")
            print(f"Rate limit: {collected_data.get('rate_limit', '1.0')} req/sec")
            max_pages = collected_data.get('max_pages', '')
            print(f"Max pages: {max_pages if max_pages else 'unlimited'}")

        elif box_type == "rag":
            patterns = collected_data.get('file_patterns', '')
            print(f"File patterns: {patterns if patterns else '(default)'}")
            print(f"Chunk size: {collected_data.get('chunk_size', '500')}")
            print(f"Chunk overlap: {collected_data.get('chunk_overlap', '10')}%")

        elif box_type == "bag":
            print(f"Storage format: {collected_data.get('storage_format', 'json')}")
            compression = collected_data.get('compression', True)
            print(f"Compression: {'Yes' if compression else 'No'}")
            indexing = collected_data.get('indexing', True)
            print(f"Indexing: {'Yes' if indexing else 'No'}")

        print("=" * 40)

    async def _build_configuration(self, collected_data: Dict[str, Any], box_type: str) -> Dict[str, Any]:
        """Build final configuration from collected data.

        Args:
            collected_data: Data collected from wizard steps
            box_type: Type of box

        Returns:
            Final configuration dictionary
        """
        base_config = {
            "box_type": box_type,
            "description": collected_data.get("description", ""),
            "auto_process": collected_data.get("auto_process", False),
            "wizard_completed": True,
            "configured_at": asyncio.get_event_loop().time()
        }

        # Add type-specific configuration
        if box_type == "drag":
            base_config.update({
                "crawl_depth": int(collected_data.get("crawl_depth", "3")),
                "rate_limit": float(collected_data.get("rate_limit", "1.0")),
                "max_pages": int(collected_data["max_pages"]) if collected_data.get("max_pages") else None
            })

        elif box_type == "rag":
            patterns_str = collected_data.get("file_patterns", "")
            patterns = [p.strip() for p in patterns_str.split(",") if p.strip()] if patterns_str else []

            base_config.update({
                "file_patterns": patterns,
                "chunk_size": int(collected_data.get("chunk_size", "500")),
                "chunk_overlap": int(collected_data.get("chunk_overlap", "10"))
            })

        elif box_type == "bag":
            base_config.update({
                "storage_format": collected_data.get("storage_format", "json"),
                "compression": collected_data.get("compression", True),
                "indexing": collected_data.get("indexing", True)
            })

        return base_config

    async def _apply_configuration(self, box_name: str, configuration: Dict[str, Any], box_type: str) -> None:
        """Apply configuration to the box.

        Args:
            box_name: Name of the box to configure
            configuration: Configuration to apply
            box_type: Type of box
        """
        # This would typically save to database
        # For now, we'll just validate the configuration structure
        required_keys = ["box_type", "description", "auto_process"]
        for key in required_keys:
            if key not in configuration:
                raise ValueError(f"Missing required configuration key: {key}")

        # Create configuration state
        config_state = ConfigurationState(
            is_configured=True,
            has_content=False,  # New box starts empty
            configuration_version="1.0",
            setup_completed_at=None,  # Will be set by service
            needs_migration=False
        )

        # In a real implementation, this would save to database
        print(f"Configuration applied to {box_type} box '{box_name}'")

    async def get_wizard_info(self, box_type: Optional[str] = None) -> Dict[str, Any]:
        """Get information about this wizard.

        Args:
            box_type: Box type for type-specific info

        Returns:
            Dictionary with wizard metadata
        """
        steps = self.get_wizard_steps(box_type)

        info = {
            "wizard_type": "box",
            "name": "Box Setup Wizard",
            "description": "Interactive setup for box configuration",
            "total_steps": len(steps),
            "estimated_time": "3-5 minutes",
            "supports_types": ["drag", "rag", "bag"]
        }

        if box_type:
            info["configured_for"] = box_type
            if box_type == "drag":
                info["features"] = [
                    "Crawl depth configuration",
                    "Rate limiting settings",
                    "Page limit controls"
                ]
            elif box_type == "rag":
                info["features"] = [
                    "File pattern filtering",
                    "Text chunking configuration",
                    "Overlap optimization"
                ]
            elif box_type == "bag":
                info["features"] = [
                    "Storage format selection",
                    "Compression options",
                    "Indexing configuration"
                ]

        return info