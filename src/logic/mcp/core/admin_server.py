"""Admin MCP server FastAPI application."""

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
import logging

from src.logic.mcp.models.response import McpResponse
from src.logic.mcp.models.command_execution import CommandExecutionRequest, AllowedCommand
from src.logic.mcp.services.admin import AdminMcpService
from src.logic.mcp.services.command_executor import CommandExecutor

logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="DocBro MCP Admin Server",
    version="1.0.0",
    description="MCP server providing full administrative control over DocBro operations"
)

# Services
command_executor = None
admin_service = None


def initialize_services():
    """Initialize services for the admin server."""
    global command_executor, admin_service
    command_executor = CommandExecutor()
    admin_service = AdminMcpService(command_executor)


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    initialize_services()
    logger.info("Admin MCP server started")


@app.post("/mcp/v1/execute_command")
async def execute_command(request: Request):
    """Execute DocBro CLI command."""
    try:
        body = await request.json()
        method = body.get("method")
        params = body.get("params", {})

        if method != "execute_command":
            raise HTTPException(status_code=400, detail="Invalid method")

        # Create command execution request
        cmd_request = CommandExecutionRequest(
            command=AllowedCommand(params.get("command")),
            arguments=params.get("arguments", []),
            options=params.get("options", {}),
            timeout=params.get("timeout", 30)
        )

        response = await admin_service.execute_command(cmd_request)
        return JSONResponse(content=response.to_dict())

    except Exception as e:
        logger.error(f"Error executing command: {e}")
        error_response = McpResponse.error_response(f"Command execution failed: {str(e)}")
        return JSONResponse(content=error_response.to_dict(), status_code=500)


@app.post("/mcp/v1/project_create")
async def project_create(request: Request):
    """Create a new project."""
    try:
        body = await request.json()
        params = body.get("params", {})

        response = await admin_service.project_create(
            name=params.get("name"),
            project_type=params.get("type"),
            description=params.get("description"),
            settings=params.get("settings")
        )
        return JSONResponse(content=response.to_dict())

    except Exception as e:
        logger.error(f"Error creating project: {e}")
        error_response = McpResponse.error_response(f"Project creation failed: {str(e)}")
        return JSONResponse(content=error_response.to_dict(), status_code=500)


@app.get("/mcp/v1/health")
async def health_check():
    """Health check endpoint."""
    try:
        import subprocess
        import json

        result = subprocess.run(
            ["uv", "run", "docbro", "health", "--json"],
            capture_output=True,
            text=True,
            timeout=10
        )

        health_data = {}
        if result.returncode == 0:
            try:
                health_data = json.loads(result.stdout)
            except json.JSONDecodeError:
                health_data = {"raw_output": result.stdout}

        response = McpResponse.success_response(
            data={
                "server_type": "admin",
                "status": "healthy" if result.returncode == 0 else "degraded",
                "docbro_health": health_data,
                "security_status": {
                    "localhost_only": True,
                    "port": 9384
                }
            }
        )

        return JSONResponse(content=response.to_dict())

    except Exception as e:
        logger.error(f"Error in health check: {e}")
        error_response = McpResponse.error_response(f"Health check failed: {str(e)}")
        return JSONResponse(content=error_response.to_dict(), status_code=500)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=9384)