"""Unit tests for JSON-RPC message models."""

import pytest
from pydantic import ValidationError

from src.logic.mcp.protocol.message import (
    JsonRpcError,
    JsonRpcNotification,
    JsonRpcRequest,
    JsonRpcResponse,
    McpErrorCode,
)


class TestMcpErrorCode:
    """Test error code enum."""

    def test_error_codes_have_correct_values(self):
        """Verify error codes match JSON-RPC spec."""
        assert McpErrorCode.PARSE_ERROR == -32700
        assert McpErrorCode.INVALID_REQUEST == -32600
        assert McpErrorCode.METHOD_NOT_FOUND == -32601
        assert McpErrorCode.INVALID_PARAMS == -32602
        assert McpErrorCode.INTERNAL_ERROR == -32603
        assert McpErrorCode.SERVER_NOT_INITIALIZED == -32002


class TestJsonRpcError:
    """Test JSON-RPC error object."""

    def test_create_error_from_code(self):
        """Test creating error from standard code."""
        error = JsonRpcError.from_code(McpErrorCode.METHOD_NOT_FOUND)
        assert error.code == -32601
        assert error.message == "Method not found"
        assert error.data is None

    def test_create_error_with_custom_message(self):
        """Test creating error with custom message."""
        error = JsonRpcError.from_code(
            McpErrorCode.INVALID_PARAMS,
            message="Missing required field",
        )
        assert error.code == -32602
        assert error.message == "Missing required field"

    def test_create_error_with_data(self):
        """Test creating error with additional data."""
        data = {"field": "name", "reason": "required"}
        error = JsonRpcError.from_code(
            McpErrorCode.INVALID_PARAMS,
            data=data,
        )
        assert error.code == -32602
        assert error.data == data


class TestJsonRpcRequest:
    """Test JSON-RPC request message."""

    def test_create_valid_request(self):
        """Test creating valid JSON-RPC request."""
        request = JsonRpcRequest(
            id=1,
            method="test_method",
            params={"arg": "value"},
        )
        assert request.jsonrpc == "2.0"
        assert request.id == 1
        assert request.method == "test_method"
        assert request.params == {"arg": "value"}

    def test_request_without_params(self):
        """Test creating request without params."""
        request = JsonRpcRequest(
            id="test-123",
            method="ping",
        )
        assert request.params is None

    def test_request_with_string_id(self):
        """Test request with string ID."""
        request = JsonRpcRequest(
            id="abc-123",
            method="test",
        )
        assert request.id == "abc-123"

    def test_invalid_jsonrpc_version(self):
        """Test that invalid version is rejected."""
        with pytest.raises(ValidationError):
            JsonRpcRequest(
                id=1,
                method="test",
                jsonrpc="1.0",
            )


class TestJsonRpcNotification:
    """Test JSON-RPC notification message."""

    def test_create_notification(self):
        """Test creating notification."""
        notification = JsonRpcNotification(
            method="tools/list_changed",
            params={"reason": "update"},
        )
        assert notification.jsonrpc == "2.0"
        assert notification.method == "tools/list_changed"
        assert notification.params == {"reason": "update"}

    def test_notification_without_params(self):
        """Test notification without params."""
        notification = JsonRpcNotification(method="initialized")
        assert notification.params is None


class TestJsonRpcResponse:
    """Test JSON-RPC response message."""

    def test_create_success_response(self):
        """Test creating success response."""
        response = JsonRpcResponse.success(
            request_id=1,
            result={"data": "value"},
        )
        assert response.jsonrpc == "2.0"
        assert response.id == 1
        assert response.result == {"data": "value"}
        assert response.error is None

    def test_create_error_response(self):
        """Test creating error response."""
        response = JsonRpcResponse.error_response(
            request_id=1,
            code=McpErrorCode.METHOD_NOT_FOUND,
            message="Method does not exist",
        )
        assert response.id == 1
        assert response.result is None
        assert response.error is not None
        assert response.error.code == -32601
        assert response.error.message == "Method does not exist"

    def test_response_cannot_have_both_result_and_error(self):
        """Test that response cannot have both result and error."""
        with pytest.raises(ValidationError):
            JsonRpcResponse(
                id=1,
                result={"data": "value"},
                error=JsonRpcError.from_code(McpErrorCode.INTERNAL_ERROR),
            )

    def test_response_must_have_result_or_error(self):
        """Test that response must have either result or error."""
        with pytest.raises(ValidationError):
            JsonRpcResponse(id=1)
