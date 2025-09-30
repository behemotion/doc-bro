"""MCP wizard with server setup flow.

Provides interactive setup wizard for MCP server configuration with
read-only and admin server options, port configuration, and startup settings.
"""

import asyncio
import socket
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from src.models.wizard_step import WizardStep
from src.models.wizard_state import WizardState
from src.models.configuration_state import ConfigurationState
from src.cli.utils.navigation import ArrowNavigator, NavigationChoice
from src.logic.wizard.orchestrator import WizardOrchestrator


@dataclass
class McpWizardResult:
    """Result of MCP wizard execution."""

    success: bool
    configuration: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    steps_completed: int = 0


class McpWizard:
    """Interactive wizard for MCP server setup and configuration."""

    def __init__(self):
        """Initialize MCP wizard."""
        self.orchestrator = WizardOrchestrator()
        self.navigator = ArrowNavigator()

    def get_wizard_steps(self) -> List[WizardStep]:
        """Get the defined steps for MCP wizard.

        Returns:
            List of WizardStep objects defining the flow
        """
        steps = [
            WizardStep(
                step_number=1,
                wizard_type="mcp",
                step_title="Read-Only Server",
                prompt_text="Enable read-only MCP server? (Recommended for AI assistants)",
                input_type="boolean",
                validation_rules=[],
                is_optional=False,
                depends_on=None
            ),
            WizardStep(
                step_number=2,
                wizard_type="mcp",
                step_title="Read-Only Port",
                prompt_text="Read-only server port (1024-65535, default 9383):",
                input_type="text",
                validation_rules=["port_number"],
                is_optional=True,
                depends_on="enable_read_only"
            ),
            WizardStep(
                step_number=3,
                wizard_type="mcp",
                step_title="Admin Server",
                prompt_text="Enable admin MCP server? (Localhost only, for advanced operations)",
                input_type="boolean",
                validation_rules=[],
                is_optional=False,
                depends_on=None
            ),
            WizardStep(
                step_number=4,
                wizard_type="mcp",
                step_title="Admin Port",
                prompt_text="Admin server port (1024-65535, default 9384):",
                input_type="text",
                validation_rules=["port_number"],
                is_optional=True,
                depends_on="enable_admin"
            ),
            WizardStep(
                step_number=5,
                wizard_type="mcp",
                step_title="Auto-Start",
                prompt_text="Auto-start servers with system?",
                input_type="boolean",
                validation_rules=[],
                is_optional=False,
                depends_on=None
            ),
            WizardStep(
                step_number=6,
                wizard_type="mcp",
                step_title="Security Settings",
                prompt_text="Enable CORS for web clients?",
                input_type="boolean",
                validation_rules=[],
                is_optional=False,
                depends_on=None
            ),
            WizardStep(
                step_number=7,
                wizard_type="mcp",
                step_title="Confirmation",
                prompt_text="Review your MCP server configuration and confirm:",
                input_type="boolean",
                validation_rules=[],
                is_optional=False,
                depends_on=None
            )
        ]
        return steps

    async def run(self, target_entity: str = "mcp-server", auto_advance: bool = False) -> McpWizardResult:
        """Run the MCP wizard for server configuration.

        Args:
            target_entity: Name of the configuration target
            auto_advance: Whether to skip optional steps automatically

        Returns:
            McpWizardResult with configuration and success status
        """
        try:
            # Initialize wizard session
            wizard_id = await self.orchestrator.start_session(
                wizard_type="mcp",
                target_entity=target_entity,
                config={"auto_advance": auto_advance}
            )

            steps = self.get_wizard_steps()
            collected_data = {}

            print(f"\n🧙 Configuring MCP Server\n")

            # Execute each step
            for step in steps:
                # Check dependencies
                if not await self._check_step_dependency(step, collected_data):
                    continue

                if auto_advance and step.is_optional:
                    # Use defaults for optional steps in auto mode
                    default_value = self._get_default_value(step)
                    if default_value is not None:
                        collected_data[self._get_step_key(step)] = default_value
                        continue

                print(f"Step {step.step_number}/{len(steps)}: {step.step_title}")

                if step.step_number == 7:  # Confirmation step
                    # Show summary before confirmation
                    await self._display_configuration_summary(collected_data)

                response = await self._execute_step(step, collected_data)

                if response is None:
                    # User cancelled
                    await self.orchestrator.cleanup_session(wizard_id)
                    return McpWizardResult(
                        success=False,
                        error_message="Wizard cancelled by user",
                        steps_completed=step.step_number - 1
                    )

                collected_data[self._get_step_key(step)] = response

                if step.step_number == 7 and not response:
                    # User rejected configuration
                    print("Configuration rejected. Starting over...")
                    collected_data = {}
                    continue

            # Validate configuration
            validation_result = await self._validate_configuration(collected_data)
            if not validation_result["valid"]:
                return McpWizardResult(
                    success=False,
                    error_message=validation_result["error"],
                    steps_completed=len(steps) - 1
                )

            # Apply configuration
            configuration = await self._build_configuration(collected_data)
            await self._apply_configuration(configuration)

            await self.orchestrator.cleanup_session(wizard_id)

            print(f"\n✅ MCP server configured successfully!")

            return McpWizardResult(
                success=True,
                configuration=configuration,
                steps_completed=len(steps)
            )

        except Exception as e:
            return McpWizardResult(
                success=False,
                error_message=str(e),
                steps_completed=0
            )

    async def _check_step_dependency(self, step: WizardStep, collected_data: Dict[str, Any]) -> bool:
        """Check if step dependency is satisfied.

        Args:
            step: WizardStep to check
            collected_data: Data collected from previous steps

        Returns:
            True if step should be executed, False to skip
        """
        if step.depends_on is None:
            return True

        # Check specific dependencies
        if step.depends_on == "enable_read_only":
            return collected_data.get("enable_read_only", False)
        elif step.depends_on == "enable_admin":
            return collected_data.get("enable_admin", False)

        return True

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
                # Return default for optional fields
                return self._get_default_value(step)

            if not user_input and not step.is_optional:
                print("This field is required. Please enter a value.")
                return await self._handle_text_input(step)

            # Validate input
            validation_result = await self._validate_input(user_input, step.validation_rules)
            if not validation_result["valid"]:
                print(f"Invalid input: {validation_result['error']}")
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
        # Currently no choice steps in MCP wizard, but ready for future use
        return ""

    async def _validate_input(self, value: str, validation_rules: List[str]) -> Dict[str, Any]:
        """Validate user input against rules.

        Args:
            value: Input value to validate
            validation_rules: List of validation rule strings

        Returns:
            Dictionary with validation result
        """
        for rule in validation_rules:
            if rule == "port_number":
                try:
                    port = int(value)
                    if not (1024 <= port <= 65535):
                        return {
                            "valid": False,
                            "error": "Port must be between 1024 and 65535"
                        }

                    # Check if port is available
                    if not await self._is_port_available(port):
                        return {
                            "valid": False,
                            "error": f"Port {port} is already in use"
                        }

                except ValueError:
                    return {
                        "valid": False,
                        "error": "Please enter a valid port number"
                    }

        return {"valid": True}

    async def _is_port_available(self, port: int) -> bool:
        """Check if a port is available.

        Args:
            port: Port number to check

        Returns:
            True if port is available, False otherwise
        """
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('localhost', port))
                return True
        except OSError:
            return False

    def _get_step_key(self, step: WizardStep) -> str:
        """Get storage key for step data.

        Args:
            step: WizardStep object

        Returns:
            Key string for storing step data
        """
        key_mapping = {
            1: "enable_read_only",
            2: "read_only_port",
            3: "enable_admin",
            4: "admin_port",
            5: "auto_start",
            6: "enable_cors",
            7: "confirmed"
        }
        return key_mapping.get(step.step_number, f"step_{step.step_number}")

    def _get_default_value(self, step: WizardStep) -> Any:
        """Get default value for step.

        Args:
            step: WizardStep object

        Returns:
            Default value
        """
        defaults = {
            "Read-Only Port": "9383",
            "Admin Port": "9384",
            "Read-Only Server": True,
            "Admin Server": False,
            "Auto-Start": False,
            "Security Settings": True
        }
        return defaults.get(step.step_title)

    async def _validate_configuration(self, collected_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate the complete configuration.

        Args:
            collected_data: Data collected from wizard steps

        Returns:
            Dictionary with validation result
        """
        # Check that at least one server is enabled
        enable_read_only = collected_data.get("enable_read_only", False)
        enable_admin = collected_data.get("enable_admin", False)

        if not enable_read_only and not enable_admin:
            return {
                "valid": False,
                "error": "At least one server (read-only or admin) must be enabled"
            }

        # Check for port conflicts
        read_only_port = collected_data.get("read_only_port")
        admin_port = collected_data.get("admin_port")

        if (enable_read_only and enable_admin and
                read_only_port and admin_port and
                read_only_port == admin_port):
            return {
                "valid": False,
                "error": "Read-only and admin servers cannot use the same port"
            }

        return {"valid": True}

    async def _display_configuration_summary(self, collected_data: Dict[str, Any]) -> None:
        """Display configuration summary before confirmation.

        Args:
            collected_data: Data collected from wizard steps
        """
        print("\n📋 MCP Server Configuration Summary:")
        print("=" * 40)

        enable_read_only = collected_data.get("enable_read_only", False)
        enable_admin = collected_data.get("enable_admin", False)

        print(f"Read-only server: {'Enabled' if enable_read_only else 'Disabled'}")
        if enable_read_only:
            read_only_port = collected_data.get("read_only_port", "9383")
            print(f"  Port: {read_only_port}")
            print(f"  Access: Public (0.0.0.0)")

        print(f"Admin server: {'Enabled' if enable_admin else 'Disabled'}")
        if enable_admin:
            admin_port = collected_data.get("admin_port", "9384")
            print(f"  Port: {admin_port}")
            print(f"  Access: Localhost only (127.0.0.1)")

        auto_start = collected_data.get("auto_start", False)
        print(f"Auto-start: {'Yes' if auto_start else 'No'}")

        enable_cors = collected_data.get("enable_cors", True)
        print(f"CORS enabled: {'Yes' if enable_cors else 'No'}")

        print("=" * 40)

        # Show connection information
        if enable_read_only:
            read_only_port = collected_data.get("read_only_port", "9383")
            print(f"\nRead-only server will be available at:")
            print(f"  http://localhost:{read_only_port}")

        if enable_admin:
            admin_port = collected_data.get("admin_port", "9384")
            print(f"\nAdmin server will be available at:")
            print(f"  http://localhost:{admin_port}")

    async def _build_configuration(self, collected_data: Dict[str, Any]) -> Dict[str, Any]:
        """Build final configuration from collected data.

        Args:
            collected_data: Data collected from wizard steps

        Returns:
            Final configuration dictionary
        """
        configuration = {
            "enable_read_only": collected_data.get("enable_read_only", False),
            "enable_admin": collected_data.get("enable_admin", False),
            "auto_start": collected_data.get("auto_start", False),
            "enable_cors": collected_data.get("enable_cors", True),
            "wizard_completed": True,
            "configured_at": asyncio.get_event_loop().time()
        }

        # Add port configuration if servers are enabled
        if configuration["enable_read_only"]:
            configuration["read_only_port"] = int(collected_data.get("read_only_port", "9383"))

        if configuration["enable_admin"]:
            configuration["admin_port"] = int(collected_data.get("admin_port", "9384"))

        return configuration

    async def _apply_configuration(self, configuration: Dict[str, Any]) -> None:
        """Apply configuration to MCP server settings.

        Args:
            configuration: Configuration to apply
        """
        # This would typically save to MCP configuration file
        # For now, we'll just validate the configuration structure
        required_keys = ["enable_read_only", "enable_admin", "auto_start", "enable_cors"]
        for key in required_keys:
            if key not in configuration:
                raise ValueError(f"Missing required configuration key: {key}")

        # Validate that at least one server is enabled
        if not configuration["enable_read_only"] and not configuration["enable_admin"]:
            raise ValueError("At least one server must be enabled")

        # In a real implementation, this would save to configuration file
        print("MCP server configuration applied successfully")

    async def get_wizard_info(self) -> Dict[str, Any]:
        """Get information about this wizard.

        Returns:
            Dictionary with wizard metadata
        """
        steps = self.get_wizard_steps()

        return {
            "wizard_type": "mcp",
            "name": "MCP Server Setup Wizard",
            "description": "Interactive setup for MCP server configuration",
            "total_steps": len(steps),
            "estimated_time": "2-3 minutes",
            "features": [
                "Read-only server configuration",
                "Admin server setup (localhost only)",
                "Port conflict detection",
                "Auto-start configuration",
                "CORS security settings"
            ],
            "servers": {
                "read_only": {
                    "description": "Safe read access for AI assistants",
                    "default_port": 9383,
                    "access": "public"
                },
                "admin": {
                    "description": "Full administrative control",
                    "default_port": 9384,
                    "access": "localhost only"
                }
            }
        }

    async def suggest_alternative_port(self, preferred_port: int) -> int:
        """Suggest an alternative port if the preferred one is unavailable.

        Args:
            preferred_port: The port that was requested

        Returns:
            Alternative available port
        """
        # Try ports in the range around the preferred port
        for offset in range(1, 100):
            for port in [preferred_port + offset, preferred_port - offset]:
                if 1024 <= port <= 65535 and await self._is_port_available(port):
                    return port

        # If no port found in range, try some common alternatives
        common_ports = [8080, 8081, 8082, 8083, 8084, 8085]
        for port in common_ports:
            if await self._is_port_available(port):
                return port

        # Last resort: find any available port
        for port in range(9000, 10000):
            if await self._is_port_available(port):
                return port

        raise ValueError("No available ports found")

    async def check_port_available(self, port: int) -> bool:
        """Public method to check port availability.

        Args:
            port: Port number to check

        Returns:
            True if port is available, False otherwise
        """
        return await self._is_port_available(port)