"""Method router for request delegation."""

from typing import Dict, Callable, Any
from src.logic.mcp.models.server_type import McpServerType
from src.logic.mcp.models.method import McpMethodDefinition


class MethodRouter:
    """Routes MCP method calls to appropriate handlers."""

    def __init__(self):
        """Initialize method router."""
        self.read_only_methods: Dict[str, Callable] = {}
        self.admin_methods: Dict[str, Callable] = {}

    def register_read_only_method(self, name: str, handler: Callable):
        """Register a read-only method handler."""
        self.read_only_methods[name] = handler

    def register_admin_method(self, name: str, handler: Callable):
        """Register an admin method handler."""
        self.admin_methods[name] = handler

    def get_handler(self, method_name: str, server_type: McpServerType) -> Callable:
        """Get handler for a method on specific server type."""
        if server_type == McpServerType.READ_ONLY:
            return self.read_only_methods.get(method_name)
        elif server_type == McpServerType.ADMIN:
            return self.admin_methods.get(method_name)
        return None

    def is_method_available(self, method_name: str, server_type: McpServerType) -> bool:
        """Check if method is available on server type."""
        return self.get_handler(method_name, server_type) is not None