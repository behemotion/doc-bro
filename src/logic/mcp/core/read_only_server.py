"""Read-only MCP server FastAPI application."""

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
import logging
from typing import Dict, Any, Optional, List

from src.logic.mcp.models.response import McpResponse
from src.logic.mcp.services.read_only import ReadOnlyMcpService
from src.services.project import ProjectService
from src.services.search import SearchService

logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="DocBro MCP Read-Only Server",
    version="1.0.0",
    description="MCP server providing read-only access to DocBro projects and documentation"
)


# Dependency injection - these would be properly initialized in production
project_service = None  # Will be injected
search_service = None   # Will be injected
read_only_service = None  # Will be injected


def initialize_services():
    """Initialize services for the read-only server."""
    global project_service, search_service, read_only_service

    # In production, these would be properly initialized with configuration
    from src.services.project import ProjectService
    from src.services.search import SearchService

    project_service = ProjectService()
    search_service = SearchService()
    read_only_service = ReadOnlyMcpService(project_service, search_service)


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    initialize_services()
    logger.info("Read-only MCP server started")


@app.post("/mcp/v1/list_projects")
async def list_projects(request: Request):
    """List all DocBro projects with optional filtering."""
    try:
        # Parse request body
        body = await request.json()
        method = body.get("method")
        params = body.get("params", {})

        if method != "list_projects":
            raise HTTPException(status_code=400, detail="Invalid method")

        # Extract parameters
        status_filter = params.get("status_filter")
        limit = params.get("limit")

        # Validate limit
        if limit is not None and (limit < 1 or limit > 100):
            raise HTTPException(status_code=422, detail="Limit must be between 1 and 100")

        # Call service
        response = await read_only_service.list_projects(
            status_filter=status_filter,
            limit=limit
        )

        return JSONResponse(content=response.to_dict())

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in list_projects: {e}")
        error_response = McpResponse.error_response(f"Internal server error: {str(e)}")
        return JSONResponse(content=error_response.to_dict(), status_code=500)


@app.post("/mcp/v1/search_projects")
async def search_projects(request: Request):
    """Search projects using embeddings."""
    try:
        # Parse request body
        body = await request.json()
        method = body.get("method")
        params = body.get("params", {})

        if method != "search_projects":
            raise HTTPException(status_code=400, detail="Invalid method")

        # Extract and validate parameters
        query = params.get("query")
        if not query:
            raise HTTPException(status_code=422, detail="Query parameter is required")

        project_names = params.get("project_names")
        limit = params.get("limit", 10)

        # Validate limit
        if limit < 1 or limit > 50:
            raise HTTPException(status_code=422, detail="Limit must be between 1 and 50")

        # Call service
        response = await read_only_service.search_projects(
            query=query,
            project_names=project_names,
            limit=limit
        )

        return JSONResponse(content=response.to_dict())

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in search_projects: {e}")
        error_response = McpResponse.error_response(f"Internal server error: {str(e)}")
        return JSONResponse(content=error_response.to_dict(), status_code=500)


@app.post("/mcp/v1/get_project_files")
async def get_project_files(request: Request):
    """Get project file information based on project type."""
    try:
        # Parse request body
        body = await request.json()
        method = body.get("method")
        params = body.get("params", {})

        if method != "get_project_files":
            raise HTTPException(status_code=400, detail="Invalid method")

        # Extract and validate parameters
        project_name = params.get("project_name")
        if not project_name:
            raise HTTPException(status_code=422, detail="Project name is required")

        file_path = params.get("file_path")
        include_content = params.get("include_content", False)

        # Call service
        response = await read_only_service.get_project_files(
            project_name=project_name,
            file_path=file_path,
            include_content=include_content
        )

        return JSONResponse(content=response.to_dict())

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_project_files: {e}")
        error_response = McpResponse.error_response(f"Internal server error: {str(e)}")
        return JSONResponse(content=error_response.to_dict(), status_code=500)


@app.get("/mcp/v1/health")
async def health_check():
    """Health check endpoint using DocBro health command."""
    try:
        # Execute health check using existing DocBro health command
        import subprocess
        import json

        result = subprocess.run(
            ["uv", "run", "docbro", "health", "--json"],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode == 0:
            try:
                health_data = json.loads(result.stdout)
            except json.JSONDecodeError:
                health_data = {"raw_output": result.stdout}

            response = McpResponse.success_response(
                data={
                    "server_type": "read-only",
                    "status": "healthy",
                    "docbro_health": health_data
                }
            )
        else:
            response = McpResponse.success_response(
                data={
                    "server_type": "read-only",
                    "status": "degraded",
                    "docbro_health": {
                        "error": result.stderr,
                        "exit_code": result.returncode
                    }
                }
            )

        return JSONResponse(content=response.to_dict())

    except Exception as e:
        logger.error(f"Error in health check: {e}")
        error_response = McpResponse.error_response(f"Health check failed: {str(e)}")
        return JSONResponse(content=error_response.to_dict(), status_code=500)


@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    """Handle 404 errors for undefined endpoints."""
    error_response = McpResponse.error_response("Endpoint not found")
    return JSONResponse(content=error_response.to_dict(), status_code=404)


@app.exception_handler(422)
async def validation_error_handler(request: Request, exc):
    """Handle validation errors."""
    error_response = McpResponse.error_response(f"Validation error: {str(exc)}")
    return JSONResponse(content=error_response.to_dict(), status_code=422)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9383)