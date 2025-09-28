"""Short key validation and management for CLI commands.

Provides context-aware short key mapping with automatic conflict resolution.
Short keys are scoped to their command context rather than being globally unique.
"""

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ShortKeyMapping:
    """Represents a short key mapping for a CLI option."""
    long_option: str
    short_key: str
    command_context: str  # e.g., "project.create", "upload.files"
    description: str | None = None


class ContextualShortKeyManager:
    """Manages short key mappings with command context awareness."""

    def __init__(self):
        # Store mappings by context
        self.context_mappings: dict[str, dict[str, str]] = {}
        # Reverse mapping for validation
        self.reverse_mappings: dict[str, dict[str, str]] = {}
        # Global options that apply to all contexts
        self.global_options = {
            "--help": "-h",
            "--verbose": "-v",
            "--quiet": "-q",
            "--force": "-f",
            "--confirm": "-c"
        }
        self._initialize_default_mappings()

    def _initialize_default_mappings(self):
        """Initialize default contextual mappings for all commands."""

        # Project command contexts
        self.register_context("project", {
            # Shared across project subcommands
            "--name": "-n",
            "--type": "-t"
        })

        self.register_context("project.create", {
            "--description": "-d",
            "--settings": "-s"
        })

        self.register_context("project.list", {
            "--status": "-s",  # Can reuse -s since --settings not in this context
            "--limit": "-l",
            "--detailed": "-d"  # Can reuse -d since --description not in this context
        })

        self.register_context("project.remove", {
            "--backup": "-b"
        })

        self.register_context("project.show", {
            "--detailed": "-d"
        })

        self.register_context("project.update", {
            "--settings": "-s",
            "--description": "-d"
        })

        # Upload command contexts
        self.register_context("upload", {
            "--project": "-p"
        })

        self.register_context("upload.files", {
            "--source": "-s",  # Can use -s since no --settings in upload context
            "--username": "-u",
            "--recursive": "-r",
            "--exclude": "-e",
            "--dry-run": "-d",  # Can use -d since no --description in upload context
            "--overwrite": "-o",
            "--progress": "-pr"  # Two-char when single char would conflict
        })

        self.register_context("upload.status", {
            "--operation": "-o",  # Can reuse -o since --overwrite not in this context
            "--active": "-a"
        })

    def register_context(self, context: str, mappings: dict[str, str]):
        """Register short key mappings for a specific command context."""
        if context not in self.context_mappings:
            self.context_mappings[context] = {}
            self.reverse_mappings[context] = {}

        for long_opt, short_key in mappings.items():
            self.add_mapping(context, long_opt, short_key)

    def add_mapping(
        self,
        context: str,
        long_option: str,
        short_key: str,
        allow_override: bool = False
    ) -> bool:
        """Add a single mapping with conflict detection."""
        # Initialize context if needed
        if context not in self.context_mappings:
            self.context_mappings[context] = {}
            self.reverse_mappings[context] = {}

        # Check for conflicts in this context
        if not allow_override:
            if short_key in self.reverse_mappings[context]:
                existing_long = self.reverse_mappings[context][short_key]
                if existing_long != long_option:
                    logger.warning(
                        f"Short key conflict in context '{context}': "
                        f"'{short_key}' already maps to '{existing_long}', "
                        f"cannot map to '{long_option}'"
                    )
                    return False

        # Add the mapping
        self.context_mappings[context][long_option] = short_key
        self.reverse_mappings[context][short_key] = long_option
        return True

    def get_short_key(
        self,
        long_option: str,
        context: str,
        check_parents: bool = True
    ) -> str | None:
        """Get short key for an option in a specific context.

        Args:
            long_option: The long form option (e.g., "--name")
            context: The command context (e.g., "project.create")
            check_parents: Whether to check parent contexts and global options

        Returns:
            The short key if found, None otherwise
        """
        # Check global options first
        if long_option in self.global_options:
            return self.global_options[long_option]

        # Check specific context
        if context in self.context_mappings:
            if long_option in self.context_mappings[context]:
                return self.context_mappings[context][long_option]

        # Check parent contexts if requested
        if check_parents and '.' in context:
            parent_context = context.rsplit('.', 1)[0]
            return self.get_short_key(long_option, parent_context, check_parents=True)

        return None

    def validate_context(self, context: str) -> tuple[bool, list[str]]:
        """Validate all mappings in a context for conflicts.

        Returns:
            Tuple of (is_valid, list_of_issues)
        """
        issues = []

        if context not in self.context_mappings:
            return True, []

        # Check for internal conflicts
        seen_short_keys = {}
        for long_opt, short_key in self.context_mappings[context].items():
            if short_key in seen_short_keys:
                issues.append(
                    f"Duplicate short key '{short_key}' in context '{context}': "
                    f"maps to both '{seen_short_keys[short_key]}' and '{long_opt}'"
                )
            seen_short_keys[short_key] = long_opt

        # Check for conflicts with global options
        for long_opt, short_key in self.context_mappings[context].items():
            for global_long, global_short in self.global_options.items():
                if short_key == global_short and long_opt != global_long:
                    issues.append(
                        f"Context '{context}' short key '{short_key}' for '{long_opt}' "
                        f"conflicts with global option '{global_long}'"
                    )

        return len(issues) == 0, issues

    def suggest_short_key(
        self,
        long_option: str,
        context: str,
        preferred_chars: list[str] | None = None
    ) -> str:
        """Suggest a non-conflicting short key for an option.

        Args:
            long_option: The long form option
            context: The command context
            preferred_chars: Preferred characters to try first

        Returns:
            A suggested short key that doesn't conflict
        """
        # Get all used short keys in this context
        used_keys = set()

        # Add global short keys
        used_keys.update(self.global_options.values())

        # Add context-specific keys
        if context in self.reverse_mappings:
            used_keys.update(self.reverse_mappings[context].keys())

        # Add parent context keys if applicable
        if '.' in context:
            parent_context = context.rsplit('.', 1)[0]
            if parent_context in self.reverse_mappings:
                used_keys.update(self.reverse_mappings[parent_context].keys())

        # Generate candidate characters
        candidates = []

        # Use preferred characters if provided
        if preferred_chars:
            candidates.extend(preferred_chars)

        # Add characters from the option name
        option_name = long_option.lstrip('-')
        candidates.append(option_name[0].lower())  # First letter

        # Add other letters from the option name
        for char in option_name[1:]:
            if char.isalpha() and char.lower() not in candidates:
                candidates.append(char.lower())

        # Try single character options first
        for char in candidates:
            short_key = f"-{char}"
            if short_key not in used_keys:
                return short_key

        # Try two-character options
        for i, char1 in enumerate(candidates):
            for char2 in candidates[i:]:
                short_key = f"-{char1}{char2}"
                if short_key not in used_keys:
                    return short_key

        # Fallback: use first two characters of option name
        if len(option_name) >= 2:
            short_key = f"-{option_name[:2].lower()}"
            counter = 1
            while short_key in used_keys:
                short_key = f"-{option_name[0].lower()}{counter}"
                counter += 1
            return short_key

        # Last resort: use first letter with number
        char = option_name[0].lower()
        counter = 1
        while f"-{char}{counter}" in used_keys:
            counter += 1
        return f"-{char}{counter}"

    def get_context_help(self, context: str) -> str:
        """Generate help text showing all options and their short keys for a context."""
        lines = []

        # Add header
        lines.append(f"Options for {context}:")
        lines.append("")

        # Collect all applicable options
        all_options = {}

        # Add global options
        all_options.update(self.global_options)

        # Add parent context options if applicable
        if '.' in context:
            parent_context = context.rsplit('.', 1)[0]
            if parent_context in self.context_mappings:
                all_options.update(self.context_mappings[parent_context])

        # Add context-specific options
        if context in self.context_mappings:
            all_options.update(self.context_mappings[context])

        # Format options
        for long_opt in sorted(all_options.keys()):
            short_key = self.get_short_key(long_opt, context)
            if short_key:
                lines.append(f"  {long_opt:<20} {short_key:<6}")

        return "\n".join(lines)

    def get_all_contexts(self) -> list[str]:
        """Get list of all registered contexts."""
        contexts = list(self.context_mappings.keys())
        contexts.sort()
        return contexts

    def validate_all_contexts(self) -> dict[str, list[str]]:
        """Validate all contexts and return any issues found."""
        all_issues = {}

        for context in self.get_all_contexts():
            is_valid, issues = self.validate_context(context)
            if not is_valid:
                all_issues[context] = issues

        return all_issues


# Singleton instance for application-wide use
short_key_manager = ContextualShortKeyManager()


def get_short_key(long_option: str, command: str, subcommand: str | None = None) -> str:
    """Convenience function to get short key for an option.

    Args:
        long_option: The long form option (e.g., "--name")
        command: The main command (e.g., "project")
        subcommand: The subcommand if any (e.g., "create")

    Returns:
        The short key or the original long option if no mapping exists
    """
    context = command
    if subcommand:
        context = f"{command}.{subcommand}"

    short_key = short_key_manager.get_short_key(long_option, context)
    return short_key or long_option


def validate_command_options(
    command: str,
    subcommand: str | None,
    options: dict[str, str]
) -> tuple[bool, list[str]]:
    """Validate that command options don't have conflicts.

    Args:
        command: The main command
        subcommand: The subcommand if any
        options: Dict mapping long options to short keys

    Returns:
        Tuple of (is_valid, list_of_issues)
    """
    context = command
    if subcommand:
        context = f"{command}.{subcommand}"

    # Register the options temporarily
    temp_manager = ContextualShortKeyManager()
    temp_manager.register_context(context, options)

    # Validate
    return temp_manager.validate_context(context)
