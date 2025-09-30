"""Unit tests for MCP protocol handler."""

import pytest

from src.logic.mcp.protocol.capabilities import ServerCapabilities
from src.logic.mcp.protocol.handler import ProtocolHandler
from src.logic.mcp.protocol.message import JsonRpcRequest, McpErrorCode


class TestProtocolHandler:
    """Test protocol handler."""

    @pytest.fixture
    def handler(self):
        """Create protocol handler for testing."""
        capabilities = ServerCapabilities.default_read_only()
        return ProtocolHandler(
            server_name="test-server",
            server_version="1.0.0",
            capabilities=capabilities,
        )

    @pytest.mark.asyncio
    async def test_initialize_request(self, handler):
        """Test handling initialize request."""
        request = JsonRpcRequest(
            id=1,
            method="initialize",
            params={
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "test-client", "version": "1.0.0"},
            },
        )

        response = await handler.handle_request(request)

        assert response.id == 1
        assert response.error is None
        assert response.result is not None
        assert handler.is_initialized is True

    @pytest.mark.asyncio
    async def test_ping_request(self, handler):
        """Test handling ping request."""
        request = JsonRpcRequest(id=1, method="ping")
        response = await handler.handle_request(request)

        assert response.id == 1
        assert response.error is None
        assert response.result == {}

    @pytest.mark.asyncio
    async def test_method_not_found(self, handler):
        """Test method not found error."""
        # Initialize first
        init_request = JsonRpcRequest(
            id=0,
            method="initialize",
            params={
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "test", "version": "1.0"},
            },
        )
        await handler.handle_request(init_request)

        # Try invalid method
        request = JsonRpcRequest(id=1, method="invalid_method")
        response = await handler.handle_request(request)

        assert response.id == 1
        assert response.result is None
        assert response.error is not None
        assert response.error.code == McpErrorCode.METHOD_NOT_FOUND

    @pytest.mark.asyncio
    async def test_server_not_initialized_error(self, handler):
        """Test server not initialized error."""
        request = JsonRpcRequest(id=1, method="tools/list")
        response = await handler.handle_request(request)

        assert response.id == 1
        assert response.result is None
        assert response.error is not None
        assert response.error.code == McpErrorCode.SERVER_NOT_INITIALIZED

    @pytest.mark.asyncio
    async def test_register_custom_method(self, handler):
        """Test registering custom method."""
        # Initialize first
        init_request = JsonRpcRequest(
            id=0,
            method="initialize",
            params={
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "test", "version": "1.0"},
            },
        )
        await handler.handle_request(init_request)

        # Register custom method
        async def custom_handler(params: dict):
            return {"custom": "response"}

        handler.register_method("custom/method", custom_handler)

        # Call custom method
        request = JsonRpcRequest(id=1, method="custom/method")
        response = await handler.handle_request(request)

        assert response.id == 1
        assert response.error is None
        assert response.result == {"custom": "response"}

    @pytest.mark.asyncio
    async def test_invalid_params_error(self, handler):
        """Test invalid params error."""
        # Initialize with bad params
        request = JsonRpcRequest(
            id=1,
            method="initialize",
            params={"invalid": "params"},
        )
        response = await handler.handle_request(request)

        assert response.id == 1
        assert response.result is None
        assert response.error is not None
        assert response.error.code == McpErrorCode.INVALID_PARAMS

    @pytest.mark.asyncio
    async def test_internal_error_handling(self, handler):
        """Test internal error handling."""
        # Initialize first
        init_request = JsonRpcRequest(
            id=0,
            method="initialize",
            params={
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "test", "version": "1.0"},
            },
        )
        await handler.handle_request(init_request)

        # Register method that raises exception
        async def failing_handler(params: dict):
            raise RuntimeError("Intentional error")

        handler.register_method("failing/method", failing_handler)

        # Call failing method
        request = JsonRpcRequest(id=1, method="failing/method")
        response = await handler.handle_request(request)

        assert response.id == 1
        assert response.result is None
        assert response.error is not None
        assert response.error.code == McpErrorCode.INTERNAL_ERROR

    def test_reset_handler(self, handler):
        """Test resetting handler state."""
        handler.is_initialized = True
        handler.reset()
        assert handler.is_initialized is False
