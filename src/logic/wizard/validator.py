"""Wizard validator for input validation across all wizard types.

Provides centralized validation logic for wizard inputs with
type-specific rules and error handling.
"""

import re
import socket
import os
from typing import Dict, Any, List, Optional, Union
from urllib.parse import urlparse
from pathlib import Path


class ValidationResult:
    """Result of a validation operation."""

    def __init__(self, valid: bool, error: Optional[str] = None, suggestions: Optional[List[str]] = None):
        """Initialize validation result.

        Args:
            valid: Whether validation passed
            error: Error message if validation failed
            suggestions: List of suggested corrections
        """
        self.valid = valid
        self.error = error
        self.suggestions = suggestions or []

    def __bool__(self) -> bool:
        """Return validation status."""
        return self.valid

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            "valid": self.valid,
            "error": self.error,
            "suggestions": self.suggestions
        }


class WizardValidator:
    """Centralized validator for wizard inputs with type-specific rules."""

    def __init__(self):
        """Initialize wizard validator."""
        self.common_patterns = {
            "entity_name": re.compile(r"^[a-zA-Z0-9_-]+$"),
            "tag_name": re.compile(r"^[a-zA-Z0-9_-]+$"),
            "email": re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"),
            "version": re.compile(r"^\d+\.\d+(\.\d+)?$")
        }

    async def validate_input(self, value: Any, validation_rules: List[str], context: Optional[Dict[str, Any]] = None) -> ValidationResult:
        """Validate input against a list of validation rules.

        Args:
            value: Input value to validate
            validation_rules: List of validation rule strings
            context: Additional context for validation

        Returns:
            ValidationResult with validation status and error details
        """
        context = context or {}

        for rule in validation_rules:
            result = await self._validate_single_rule(value, rule, context)
            if not result.valid:
                return result

        return ValidationResult(valid=True)

    async def _validate_single_rule(self, value: Any, rule: str, context: Dict[str, Any]) -> ValidationResult:
        """Validate input against a single rule.

        Args:
            value: Input value to validate
            rule: Validation rule string
            context: Additional context for validation

        Returns:
            ValidationResult for this specific rule
        """
        # Required validation
        if rule == "required":
            if not value or (isinstance(value, str) and not value.strip()):
                return ValidationResult(False, "This field is required")

        # Length validations
        elif rule.startswith("max_length:"):
            max_length = int(rule.split(":")[1])
            if isinstance(value, str) and len(value) > max_length:
                return ValidationResult(
                    False,
                    f"Input too long. Maximum {max_length} characters allowed",
                    [f"Truncate to {max_length} characters"]
                )

        elif rule.startswith("min_length:"):
            min_length = int(rule.split(":")[1])
            if isinstance(value, str) and len(value) < min_length:
                return ValidationResult(
                    False,
                    f"Input too short. Minimum {min_length} characters required"
                )

        # Numeric range validations
        elif rule.startswith("integer_range:"):
            try:
                parts = rule.split(":")
                min_val, max_val = int(parts[1]), int(parts[2])
                int_val = int(value)
                if not (min_val <= int_val <= max_val):
                    return ValidationResult(
                        False,
                        f"Value must be between {min_val} and {max_val}",
                        [f"Try a value between {min_val} and {max_val}"]
                    )
            except ValueError:
                return ValidationResult(False, "Please enter a valid integer")

        elif rule.startswith("float_range:"):
            try:
                parts = rule.split(":")
                min_val, max_val = float(parts[1]), float(parts[2])
                float_val = float(value)
                if not (min_val <= float_val <= max_val):
                    return ValidationResult(
                        False,
                        f"Value must be between {min_val} and {max_val}",
                        [f"Try a value between {min_val} and {max_val}"]
                    )
            except ValueError:
                return ValidationResult(False, "Please enter a valid number")

        elif rule == "positive_integer":
            try:
                int_val = int(value)
                if int_val <= 0:
                    return ValidationResult(
                        False,
                        "Value must be a positive integer",
                        ["Enter a number greater than 0"]
                    )
            except ValueError:
                return ValidationResult(False, "Please enter a valid positive integer")

        # Pattern validations
        elif rule == "entity_name":
            if not self.common_patterns["entity_name"].match(value):
                return ValidationResult(
                    False,
                    "Invalid name format. Use only letters, numbers, hyphens, and underscores",
                    ["Remove spaces and special characters", "Use hyphens instead of spaces"]
                )

        elif rule == "tag_format":
            if isinstance(value, str) and value:
                tags = [tag.strip() for tag in value.split(",")]
                for tag in tags:
                    if not self.common_patterns["tag_name"].match(tag):
                        return ValidationResult(
                            False,
                            f"Invalid tag format: '{tag}'. Use only letters, numbers, hyphens, and underscores",
                            ["Remove spaces from tags", "Use hyphens instead of spaces"]
                        )

        # Network validations
        elif rule == "port_number":
            try:
                port = int(value)
                if not (1024 <= port <= 65535):
                    return ValidationResult(
                        False,
                        "Port must be between 1024 and 65535",
                        ["Try 9383 for read-only server", "Try 9384 for admin server"]
                    )

                # Check if port is available
                if not await self._is_port_available(port):
                    alternative = await self._suggest_alternative_port(port)
                    return ValidationResult(
                        False,
                        f"Port {port} is already in use",
                        [f"Try port {alternative}", "Use a different port number"]
                    )

            except ValueError:
                return ValidationResult(False, "Please enter a valid port number")

        elif rule == "url":
            result = self._validate_url(value)
            if not result.valid:
                return result

        elif rule == "file_path":
            result = self._validate_file_path(value)
            if not result.valid:
                return result

        elif rule == "directory_path":
            result = self._validate_directory_path(value)
            if not result.valid:
                return result

        # File pattern validation
        elif rule == "file_pattern":
            result = self._validate_file_pattern(value)
            if not result.valid:
                return result

        # Email validation
        elif rule == "email":
            if not self.common_patterns["email"].match(value):
                return ValidationResult(
                    False,
                    "Invalid email format",
                    ["Use format: user@domain.com"]
                )

        # Version validation
        elif rule == "version":
            if not self.common_patterns["version"].match(value):
                return ValidationResult(
                    False,
                    "Invalid version format",
                    ["Use format: 1.0 or 1.0.0"]
                )

        # Choice validation
        elif rule.startswith("choice:"):
            choices = rule.split(":")[1].split(",")
            if value not in choices:
                return ValidationResult(
                    False,
                    f"Invalid choice. Must be one of: {', '.join(choices)}",
                    [f"Try: {choices[0]}"]
                )

        return ValidationResult(valid=True)

    def _validate_url(self, url: str) -> ValidationResult:
        """Validate URL format and accessibility.

        Args:
            url: URL to validate

        Returns:
            ValidationResult for URL validation
        """
        try:
            parsed = urlparse(url)

            # Check basic URL structure
            if not parsed.scheme:
                return ValidationResult(
                    False,
                    "URL must include protocol (http:// or https://)",
                    ["Add https:// to the beginning"]
                )

            if parsed.scheme not in ["http", "https"]:
                return ValidationResult(
                    False,
                    "URL must use http or https protocol",
                    ["Use https:// instead"]
                )

            if not parsed.netloc:
                return ValidationResult(
                    False,
                    "URL must include domain name",
                    ["Example: https://docs.example.com"]
                )

            return ValidationResult(valid=True)

        except Exception:
            return ValidationResult(
                False,
                "Invalid URL format",
                ["Example: https://docs.example.com"]
            )

    def _validate_file_path(self, path: str) -> ValidationResult:
        """Validate file path exists and is accessible.

        Args:
            path: File path to validate

        Returns:
            ValidationResult for file path validation
        """
        try:
            path_obj = Path(path)

            if not path_obj.exists():
                return ValidationResult(
                    False,
                    f"File does not exist: {path}",
                    ["Check the file path spelling", "Ensure the file exists"]
                )

            if not path_obj.is_file():
                return ValidationResult(
                    False,
                    f"Path is not a file: {path}",
                    ["Specify a file, not a directory"]
                )

            if not os.access(path, os.R_OK):
                return ValidationResult(
                    False,
                    f"File is not readable: {path}",
                    ["Check file permissions"]
                )

            return ValidationResult(valid=True)

        except Exception as e:
            return ValidationResult(
                False,
                f"Invalid file path: {str(e)}",
                ["Use absolute or relative path"]
            )

    def _validate_directory_path(self, path: str) -> ValidationResult:
        """Validate directory path exists and is accessible.

        Args:
            path: Directory path to validate

        Returns:
            ValidationResult for directory path validation
        """
        try:
            path_obj = Path(path)

            if not path_obj.exists():
                return ValidationResult(
                    False,
                    f"Directory does not exist: {path}",
                    ["Check the directory path spelling", "Create the directory first"]
                )

            if not path_obj.is_dir():
                return ValidationResult(
                    False,
                    f"Path is not a directory: {path}",
                    ["Specify a directory, not a file"]
                )

            if not os.access(path, os.R_OK):
                return ValidationResult(
                    False,
                    f"Directory is not readable: {path}",
                    ["Check directory permissions"]
                )

            return ValidationResult(valid=True)

        except Exception as e:
            return ValidationResult(
                False,
                f"Invalid directory path: {str(e)}",
                ["Use absolute or relative path"]
            )

    def _validate_file_pattern(self, pattern: str) -> ValidationResult:
        """Validate file pattern format.

        Args:
            pattern: File pattern to validate

        Returns:
            ValidationResult for file pattern validation
        """
        if not pattern:
            return ValidationResult(valid=True)  # Empty pattern is valid (optional)

        # Split comma-separated patterns
        patterns = [p.strip() for p in pattern.split(",")]

        for p in patterns:
            # Basic file pattern validation
            if not re.match(r"^[\w\*\.\-]+$", p):
                return ValidationResult(
                    False,
                    f"Invalid file pattern: '{p}'. Use wildcards (*), letters, numbers, dots, and hyphens",
                    ["Example: *.pdf,*.md,*.txt"]
                )

            # Check for common mistakes
            if ".." in p:
                return ValidationResult(
                    False,
                    f"Invalid pattern: '{p}'. Avoid double dots",
                    ["Use single dots for extensions"]
                )

        return ValidationResult(valid=True)

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

    async def _suggest_alternative_port(self, preferred_port: int) -> int:
        """Suggest an alternative port if the preferred one is unavailable.

        Args:
            preferred_port: The port that was requested

        Returns:
            Alternative available port
        """
        # Try ports near the preferred port
        for offset in range(1, 10):
            for port in [preferred_port + offset, preferred_port - offset]:
                if 1024 <= port <= 65535 and await self._is_port_available(port):
                    return port

        # Try common alternative ports
        common_ports = [8080, 8081, 8082, 8083, 8084, 8085, 9000, 9001, 9002]
        for port in common_ports:
            if await self._is_port_available(port):
                return port

        # Default fallback
        return 8080

    async def validate_wizard_data(self, wizard_type: str, data: Dict[str, Any]) -> ValidationResult:
        """Validate complete wizard data for a specific wizard type.

        Args:
            wizard_type: Type of wizard ('shelf', 'box', 'mcp')
            data: Complete wizard data to validate

        Returns:
            ValidationResult for the entire wizard data
        """
        if wizard_type == "shelf":
            return await self._validate_shelf_data(data)
        elif wizard_type == "box":
            return await self._validate_box_data(data)
        elif wizard_type == "mcp":
            return await self._validate_mcp_data(data)
        else:
            return ValidationResult(False, f"Unknown wizard type: {wizard_type}")

    async def _validate_shelf_data(self, data: Dict[str, Any]) -> ValidationResult:
        """Validate shelf wizard data.

        Args:
            data: Shelf wizard data

        Returns:
            ValidationResult for shelf data
        """
        # Validate default_box_type
        default_box_type = data.get("default_box_type")
        if default_box_type and default_box_type not in ["drag", "rag", "bag"]:
            return ValidationResult(
                False,
                f"Invalid default box type: {default_box_type}",
                ["Use: drag, rag, or bag"]
            )

        # Validate tags
        tags = data.get("tags", [])
        if tags:
            for tag in tags:
                if not self.common_patterns["tag_name"].match(tag):
                    return ValidationResult(
                        False,
                        f"Invalid tag: '{tag}'. Use only letters, numbers, hyphens, and underscores"
                    )

        return ValidationResult(valid=True)

    async def _validate_box_data(self, data: Dict[str, Any]) -> ValidationResult:
        """Validate box wizard data.

        Args:
            data: Box wizard data

        Returns:
            ValidationResult for box data
        """
        box_type = data.get("box_type")
        if not box_type or box_type not in ["drag", "rag", "bag"]:
            return ValidationResult(
                False,
                f"Invalid box type: {box_type}",
                ["Use: drag, rag, or bag"]
            )

        # Type-specific validation
        if box_type == "drag":
            return await self._validate_drag_box_data(data)
        elif box_type == "rag":
            return await self._validate_rag_box_data(data)
        elif box_type == "bag":
            return await self._validate_bag_box_data(data)

        return ValidationResult(valid=True)

    async def _validate_drag_box_data(self, data: Dict[str, Any]) -> ValidationResult:
        """Validate drag box specific data.

        Args:
            data: Drag box data

        Returns:
            ValidationResult for drag box data
        """
        # Validate crawl depth
        crawl_depth = data.get("crawl_depth")
        if crawl_depth is not None:
            try:
                depth = int(crawl_depth)
                if not (1 <= depth <= 10):
                    return ValidationResult(
                        False,
                        "Crawl depth must be between 1 and 10"
                    )
            except (ValueError, TypeError):
                return ValidationResult(False, "Crawl depth must be an integer")

        # Validate rate limit
        rate_limit = data.get("rate_limit")
        if rate_limit is not None:
            try:
                rate = float(rate_limit)
                if not (0.1 <= rate <= 10.0):
                    return ValidationResult(
                        False,
                        "Rate limit must be between 0.1 and 10.0 requests per second"
                    )
            except (ValueError, TypeError):
                return ValidationResult(False, "Rate limit must be a number")

        return ValidationResult(valid=True)

    async def _validate_rag_box_data(self, data: Dict[str, Any]) -> ValidationResult:
        """Validate rag box specific data.

        Args:
            data: Rag box data

        Returns:
            ValidationResult for rag box data
        """
        # Validate chunk size
        chunk_size = data.get("chunk_size")
        if chunk_size is not None:
            try:
                size = int(chunk_size)
                if not (100 <= size <= 2000):
                    return ValidationResult(
                        False,
                        "Chunk size must be between 100 and 2000"
                    )
            except (ValueError, TypeError):
                return ValidationResult(False, "Chunk size must be an integer")

        # Validate chunk overlap
        chunk_overlap = data.get("chunk_overlap")
        if chunk_overlap is not None:
            try:
                overlap = int(chunk_overlap)
                if not (0 <= overlap <= 50):
                    return ValidationResult(
                        False,
                        "Chunk overlap must be between 0 and 50 percent"
                    )
            except (ValueError, TypeError):
                return ValidationResult(False, "Chunk overlap must be an integer")

        return ValidationResult(valid=True)

    async def _validate_bag_box_data(self, data: Dict[str, Any]) -> ValidationResult:
        """Validate bag box specific data.

        Args:
            data: Bag box data

        Returns:
            ValidationResult for bag box data
        """
        # Validate storage format
        storage_format = data.get("storage_format")
        if storage_format and storage_format not in ["json", "yaml", "raw", "compressed"]:
            return ValidationResult(
                False,
                f"Invalid storage format: {storage_format}",
                ["Use: json, yaml, raw, or compressed"]
            )

        return ValidationResult(valid=True)

    async def _validate_mcp_data(self, data: Dict[str, Any]) -> ValidationResult:
        """Validate MCP wizard data.

        Args:
            data: MCP wizard data

        Returns:
            ValidationResult for MCP data
        """
        # Check that at least one server is enabled
        enable_read_only = data.get("enable_read_only", False)
        enable_admin = data.get("enable_admin", False)

        if not enable_read_only and not enable_admin:
            return ValidationResult(
                False,
                "At least one server (read-only or admin) must be enabled"
            )

        # Check for port conflicts
        read_only_port = data.get("read_only_port")
        admin_port = data.get("admin_port")

        if (enable_read_only and enable_admin and
                read_only_port and admin_port and
                read_only_port == admin_port):
            return ValidationResult(
                False,
                "Read-only and admin servers cannot use the same port"
            )

        return ValidationResult(valid=True)