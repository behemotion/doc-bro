"""
MCP Protocol Handler

Routes JSON-RPC requests to appropriate MCP method handlers.
Manages initialization state and method dispatch.
"""

import logging
from typing import Any, Awaitable, Callable, Optional

from .capabilities import (
    InitializeRequest,
    InitializeResponse,
    ServerCapabilities,
    ServerInfo,
)
from .message import JsonRpcRequest, JsonRpcResponse, McpErrorCode

logger = logging.getLogger(__name__)


class ProtocolHandler:
    """
    MCP protocol handler for routing requests to method implementations.

    Manages server initialization state and dispatches JSON-RPC requests
    to registered method handlers.
    """

    def __init__(
        self,
        server_name: str,
        server_version: str,
        capabilities: ServerCapabilities,
    ):
        """
        Initialize protocol handler.

        Args:
            server_name: Name of the MCP server
            server_version: Version of the MCP server
            capabilities: Server capabilities to advertise
        """
        self.server_name = server_name
        self.server_version = server_version
        self.capabilities = capabilities
        self.is_initialized = False

        # Method handler registry
        self._handlers: dict[str, Callable[[dict], Awaitable[Any]]] = {}

        # Register built-in methods
        self.register_method("initialize", self._handle_initialize)
        self.register_method("initialized", self._handle_initialized)
        self.register_method("ping", self._handle_ping)

    def register_method(
        self,
        method_name: str,
        handler: Callable[[dict], Awaitable[Any]],
    ) -> None:
        """
        Register a method handler.

        Args:
            method_name: Name of the MCP method
            handler: Async function to handle the method
        """
        self._handlers[method_name] = handler
        logger.debug(f"Registered handler for method: {method_name}")

    async def handle_request(self, request: JsonRpcRequest) -> JsonRpcResponse:
        """
        Handle an incoming JSON-RPC request.

        Args:
            request: The JSON-RPC request to handle

        Returns:
            JsonRpcResponse with result or error
        """
        method = request.method

        # Check if server is initialized (except for initialize/ping)
        if not self.is_initialized and method not in ["initialize", "ping"]:
            return JsonRpcResponse.error_response(
                request_id=request.id,
                code=McpErrorCode.SERVER_NOT_INITIALIZED,
                message="Server must be initialized before calling methods",
            )

        # Check if method exists
        if method not in self._handlers:
            return JsonRpcResponse.error_response(
                request_id=request.id,
                code=McpErrorCode.METHOD_NOT_FOUND,
                message=f"Method '{method}' not found",
            )

        # Execute method handler
        try:
            handler = self._handlers[method]
            params = request.params or {}
            result = await handler(params)
            return JsonRpcResponse.success(request.id, result)

        except ValueError as e:
            # Invalid parameters
            logger.warning(f"Invalid params for {method}: {e}")
            return JsonRpcResponse.error_response(
                request_id=request.id,
                code=McpErrorCode.INVALID_PARAMS,
                message=str(e),
            )

        except Exception as e:
            # Internal error
            logger.exception(f"Error handling {method}: {e}")
            return JsonRpcResponse.error_response(
                request_id=request.id,
                code=McpErrorCode.INTERNAL_ERROR,
                message=f"Internal error: {str(e)}",
            )

    async def _handle_initialize(self, params: dict) -> dict:
        """
        Handle initialize request.

        Performs MCP handshake and exchanges capabilities.
        """
        try:
            # Parse initialize request
            init_request = InitializeRequest(**params)

            # Create initialize response
            response = InitializeResponse.create(
                server_name=self.server_name,
                server_version=self.server_version,
                capabilities=self.capabilities,
                protocol_version=init_request.protocol_version,
            )

            # Mark server as initialized
            self.is_initialized = True
            logger.info(
                f"Server initialized: {self.server_name} v{self.server_version}"
            )

            return response.model_dump(by_alias=True)

        except Exception as e:
            logger.error(f"Initialization failed: {e}")
            raise ValueError(f"Invalid initialize params: {e}")

    async def _handle_initialized(self, params: dict) -> dict:
        """
        Handle initialized notification.

        Client confirms successful initialization.
        """
        logger.info("Client confirmed initialization")
        return {}  # Initialized is a notification, no return value expected

    async def _handle_ping(self, params: dict) -> dict:
        """
        Handle ping request.

        Simple keep-alive check.
        """
        return {}

    def reset(self) -> None:
        """Reset initialization state (useful for testing)."""
        self.is_initialized = False
        logger.debug("Protocol handler reset")
