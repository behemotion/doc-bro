"""
MCP HTTP Transport Layer

Handles HTTP transport for JSON-RPC messages in the MCP protocol.
Provides FastAPI integration for receiving and sending MCP messages.
"""

import logging
from typing import Any

from fastapi import Request, Response
from pydantic import ValidationError

from .handler import ProtocolHandler
from .message import JsonRpcRequest, JsonRpcResponse, McpErrorCode

logger = logging.getLogger(__name__)


class HttpTransport:
    """
    HTTP transport layer for MCP protocol.

    Integrates with FastAPI to handle JSON-RPC over HTTP.
    """

    def __init__(self, handler: ProtocolHandler):
        """
        Initialize HTTP transport.

        Args:
            handler: Protocol handler for processing requests
        """
        self.handler = handler

    async def handle_http_request(self, request: Request) -> Response:
        """
        Handle an HTTP request containing a JSON-RPC message.

        Args:
            request: FastAPI request object

        Returns:
            FastAPI Response with JSON-RPC response
        """
        try:
            # Parse JSON body
            body = await request.json()

            # Validate and parse JSON-RPC request
            try:
                rpc_request = JsonRpcRequest(**body)
            except ValidationError as e:
                # Invalid JSON-RPC request format
                logger.warning(f"Invalid JSON-RPC request: {e}")
                error_response = JsonRpcResponse.error_response(
                    request_id=body.get("id", 0),
                    code=McpErrorCode.INVALID_REQUEST,
                    message="Invalid JSON-RPC request format",
                    data={"validation_errors": e.errors()},
                )
                return self._create_response(error_response)

            # Handle the request
            rpc_response = await self.handler.handle_request(rpc_request)
            return self._create_response(rpc_response)

        except Exception as e:
            # Parse error or other fatal error
            logger.exception(f"Fatal error handling HTTP request: {e}")
            error_response = JsonRpcResponse.error_response(
                request_id=0,
                code=McpErrorCode.PARSE_ERROR,
                message="Failed to parse request",
            )
            return self._create_response(error_response)

    def _create_response(self, rpc_response: JsonRpcResponse) -> Response:
        """
        Create FastAPI Response from JSON-RPC response.

        Args:
            rpc_response: JSON-RPC response object

        Returns:
            FastAPI Response with proper headers
        """
        content = rpc_response.model_dump_json()
        return Response(
            content=content,
            media_type="application/json",
            headers={
                "Content-Type": "application/json",
            },
        )

    async def send_notification(self, method: str, params: dict[str, Any]) -> None:
        """
        Send a notification (no response expected).

        Notifications are used for server-initiated events like list changes.

        Args:
            method: MCP method name
            params: Method parameters
        """
        # Note: Actual sending depends on client connection
        # This is a placeholder for future SSE/WebSocket support
        logger.debug(f"Notification: {method} with params: {params}")
