"""Enhanced command routing service for context-aware command execution."""

import logging
from typing import Dict, Any, Optional, List, Callable, Awaitable
from dataclasses import dataclass
from enum import Enum

from src.services.flag_standardizer import FlagStandardizer
from src.services.context_service import ContextService
from src.core.lib_logger import get_component_logger

logger = get_component_logger("command_router")


class CommandType(Enum):
    """Types of commands for routing purposes."""
    ENTITY_COMMAND = "entity"  # Commands that operate on entities (shelf, box)
    ACTION_COMMAND = "action"  # Commands that perform actions (fill, serve)
    META_COMMAND = "meta"      # Commands that manage the system (setup, health)


@dataclass
class CommandContext:
    """Context information for command execution."""
    command_name: str
    subcommand: Optional[str]
    arguments: Dict[str, Any]
    flags: Dict[str, Any]
    command_type: CommandType
    requires_entity: bool = False
    entity_name: Optional[str] = None
    entity_type: Optional[str] = None


@dataclass
class RoutingRule:
    """Rule for routing commands based on context."""
    pattern: str
    handler: str
    requires_context: bool = False
    context_type: Optional[str] = None
    priority: int = 0


class CommandRouter:
    """Enhanced command router with context awareness and flag standardization."""

    def __init__(self):
        self.flag_standardizer = FlagStandardizer()
        self.context_service = ContextService()
        self._routing_rules = self._initialize_routing_rules()
        self._command_handlers: Dict[str, Callable] = {}

    def _initialize_routing_rules(self) -> List[RoutingRule]:
        """Initialize command routing rules."""
        return [
            # Entity inspection commands (context-aware)
            RoutingRule(
                pattern="shelf:inspect",
                handler="handle_shelf_inspect",
                requires_context=True,
                context_type="shelf",
                priority=10
            ),
            RoutingRule(
                pattern="box:inspect",
                handler="handle_box_inspect",
                requires_context=True,
                context_type="box",
                priority=10
            ),

            # Entity creation commands
            RoutingRule(
                pattern="shelf:create",
                handler="handle_shelf_create",
                requires_context=False,
                priority=5
            ),
            RoutingRule(
                pattern="box:create",
                handler="handle_box_create",
                requires_context=False,
                priority=5
            ),

            # Action commands (with context awareness)
            RoutingRule(
                pattern="fill:*",
                handler="handle_fill_command",
                requires_context=True,
                context_type="box",
                priority=8
            ),

            # Service commands
            RoutingRule(
                pattern="serve:*",
                handler="handle_serve_command",
                requires_context=False,
                priority=3
            ),

            # Meta commands
            RoutingRule(
                pattern="setup:*",
                handler="handle_setup_command",
                requires_context=False,
                priority=1
            ),
            RoutingRule(
                pattern="health:*",
                handler="handle_health_command",
                requires_context=False,
                priority=1
            )
        ]

    def register_handler(self, pattern: str, handler: Callable) -> None:
        """Register a command handler for a specific pattern."""
        self._command_handlers[pattern] = handler
        logger.debug(f"Registered handler for pattern: {pattern}")

    async def route_command(self, command_context: CommandContext) -> Dict[str, Any]:
        """Route command to appropriate handler with context awareness."""
        try:
            # Standardize flags first
            standardized_flags = await self._standardize_flags(
                command_context.command_name,
                command_context.flags
            )
            command_context.flags = standardized_flags

            # Find matching routing rule
            matching_rule = self._find_matching_rule(command_context)

            if not matching_rule:
                return {
                    'success': False,
                    'error': f"No routing rule found for command: {command_context.command_name}",
                    'suggestions': self._get_command_suggestions(command_context.command_name)
                }

            # Check if context is required and available
            if matching_rule.requires_context:
                context_result = await self._ensure_context(command_context, matching_rule)
                if not context_result['success']:
                    return context_result

            # Get handler and execute
            handler = self._command_handlers.get(matching_rule.handler)
            if not handler:
                return {
                    'success': False,
                    'error': f"Handler not found: {matching_rule.handler}",
                    'rule': matching_rule.pattern
                }

            # Execute handler
            result = await handler(command_context)
            return result

        except Exception as e:
            logger.error(f"Error routing command {command_context.command_name}: {e}")
            return {
                'success': False,
                'error': str(e),
                'command': command_context.command_name
            }

    def _find_matching_rule(self, command_context: CommandContext) -> Optional[RoutingRule]:
        """Find the best matching routing rule for a command."""
        command_pattern = f"{command_context.command_name}:{command_context.subcommand or '*'}"

        # Sort rules by priority (higher first)
        sorted_rules = sorted(self._routing_rules, key=lambda r: r.priority, reverse=True)

        for rule in sorted_rules:
            if self._pattern_matches(rule.pattern, command_pattern):
                return rule

        return None

    def _pattern_matches(self, rule_pattern: str, command_pattern: str) -> bool:
        """Check if a command pattern matches a routing rule pattern."""
        rule_parts = rule_pattern.split(':')
        command_parts = command_pattern.split(':')

        if len(rule_parts) != len(command_parts):
            return False

        for rule_part, command_part in zip(rule_parts, command_parts):
            if rule_part != '*' and rule_part != command_part:
                return False

        return True

    async def _standardize_flags(self, command: str, flags: Dict[str, Any]) -> Dict[str, Any]:
        """Standardize command flags using FlagStandardizer."""
        try:
            # Get standard flag mappings for this command
            standard_flags = self.flag_standardizer.get_all_flags_for_command(command)

            # Create mapping from both long and short forms to canonical names
            flag_mapping = {}
            for canonical_name, mapping in standard_flags.items():
                flag_mapping[mapping.long_form] = canonical_name
                flag_mapping[mapping.short_form] = canonical_name

            # Standardize the input flags
            standardized = {}
            for flag_name, value in flags.items():
                # Normalize flag name (ensure it starts with -)
                if not flag_name.startswith('-'):
                    flag_name = f"--{flag_name}"

                canonical_name = flag_mapping.get(flag_name, flag_name)
                standardized[canonical_name] = value

            return standardized

        except Exception as e:
            logger.warning(f"Error standardizing flags for {command}: {e}")
            return flags

    async def _ensure_context(self, command_context: CommandContext, rule: RoutingRule) -> Dict[str, Any]:
        """Ensure required context is available for command execution."""
        try:
            if not command_context.entity_name:
                return {
                    'success': False,
                    'error': f"Entity name required for {rule.context_type} context",
                    'suggestion': f"Provide entity name for {command_context.command_name} command"
                }

            # Check entity context
            if rule.context_type == "shelf":
                context = await self.context_service.check_shelf_exists(command_context.entity_name)
            elif rule.context_type == "box":
                context = await self.context_service.check_box_exists(
                    command_context.entity_name,
                    command_context.flags.get('shelf')
                )
            else:
                return {
                    'success': False,
                    'error': f"Unknown context type: {rule.context_type}"
                }

            # Store context in command context for handler use
            command_context.arguments['_context'] = context

            return {'success': True, 'context': context}

        except Exception as e:
            logger.error(f"Error ensuring context: {e}")
            return {
                'success': False,
                'error': f"Context check failed: {str(e)}"
            }

    def _get_command_suggestions(self, command_name: str) -> List[str]:
        """Get command suggestions for unknown commands."""
        available_commands = set()

        for rule in self._routing_rules:
            parts = rule.pattern.split(':')
            if len(parts) > 0:
                available_commands.add(parts[0])

        # Simple similarity matching
        suggestions = []
        for available in available_commands:
            if command_name.lower() in available.lower() or available.lower() in command_name.lower():
                suggestions.append(available)

        return suggestions[:3]  # Return top 3 suggestions

    def get_routing_report(self) -> str:
        """Generate a report of all routing rules and handlers."""
        report = "📋 Command Routing Configuration\n\n"

        report += "🔄 Routing Rules:\n"
        sorted_rules = sorted(self._routing_rules, key=lambda r: r.priority, reverse=True)

        for i, rule in enumerate(sorted_rules, 1):
            report += f"{i}. Pattern: {rule.pattern}\n"
            report += f"   Handler: {rule.handler}\n"
            report += f"   Context: {'Required' if rule.requires_context else 'Optional'}"
            if rule.context_type:
                report += f" ({rule.context_type})"
            report += f"\n   Priority: {rule.priority}\n\n"

        report += "🔧 Registered Handlers:\n"
        for pattern, handler in self._command_handlers.items():
            report += f"- {pattern}: {handler.__name__ if hasattr(handler, '__name__') else str(handler)}\n"

        return report

    def validate_routing_configuration(self) -> List[str]:
        """Validate routing configuration for issues."""
        issues = []

        # Check for missing handlers
        required_handlers = {rule.handler for rule in self._routing_rules}
        registered_handlers = set(self._command_handlers.keys())

        missing_handlers = required_handlers - registered_handlers
        for handler in missing_handlers:
            issues.append(f"Missing handler: {handler}")

        # Check for duplicate patterns
        patterns = [rule.pattern for rule in self._routing_rules]
        duplicate_patterns = set([p for p in patterns if patterns.count(p) > 1])
        for pattern in duplicate_patterns:
            issues.append(f"Duplicate routing pattern: {pattern}")

        # Check for conflicting priorities
        pattern_priorities = {}
        for rule in self._routing_rules:
            if rule.pattern in pattern_priorities:
                if pattern_priorities[rule.pattern] != rule.priority:
                    issues.append(f"Conflicting priorities for pattern: {rule.pattern}")
            else:
                pattern_priorities[rule.pattern] = rule.priority

        return issues

    async def get_command_help(self, command: str) -> Dict[str, Any]:
        """Get help information for a command including standardized flags."""
        try:
            # Get standard flags for command
            flags = self.flag_standardizer.get_all_flags_for_command(command)

            # Find routing rules for command
            matching_rules = [
                rule for rule in self._routing_rules
                if rule.pattern.split(':')[0] == command
            ]

            help_info = {
                'command': command,
                'available_flags': {},
                'routing_rules': [],
                'context_requirements': {}
            }

            # Format flag information
            for flag_name, mapping in flags.items():
                help_info['available_flags'][flag_name] = {
                    'long_form': mapping.long_form,
                    'short_form': mapping.short_form,
                    'type': mapping.flag_type,
                    'description': mapping.description,
                    'choices': mapping.choices,
                    'default': mapping.default_value,
                    'global': mapping.is_global
                }

            # Format routing information
            for rule in matching_rules:
                help_info['routing_rules'].append({
                    'pattern': rule.pattern,
                    'handler': rule.handler,
                    'requires_context': rule.requires_context,
                    'context_type': rule.context_type,
                    'priority': rule.priority
                })

                if rule.requires_context:
                    help_info['context_requirements'][rule.pattern] = {
                        'type': rule.context_type,
                        'required': True
                    }

            return help_info

        except Exception as e:
            logger.error(f"Error getting command help for {command}: {e}")
            return {
                'command': command,
                'error': str(e)
            }