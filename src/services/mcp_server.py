"""MCP (Model Context Protocol) server for DocBro."""

import asyncio
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
import uuid
import logging

from fastapi import FastAPI, HTTPException, Depends, WebSocket, WebSocketDisconnect, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from ..lib.config import DocBroConfig
from ..lib.logging import get_component_logger
from ..services.database import DatabaseManager
from ..services.vector_store import VectorStoreService
from ..services.embeddings import EmbeddingService
from ..services.rag import RAGSearchService
from ..models import Project, ProjectStatus


# Security
security = HTTPBearer()


class MCPServer:
    """MCP server for DocBro integration with coding agents."""

    def __init__(self, config: Optional[DocBroConfig] = None):
        """Initialize MCP server."""
        self.config = config or DocBroConfig()
        self.logger = get_component_logger("mcp_server")

        # Services
        self.db_manager: Optional[DatabaseManager] = None
        self.vector_store: Optional[VectorStoreService] = None
        self.embedding_service: Optional[EmbeddingService] = None
        self.rag_service: Optional[RAGSearchService] = None

        # Session management
        self.sessions: Dict[str, Dict[str, Any]] = {}
        self.websocket_connections: Dict[str, WebSocket] = {}

        # Create FastAPI app
        self.app = self._create_app()

    async def initialize_services(self) -> None:
        """Initialize all backend services."""
        try:
            self.db_manager = DatabaseManager(self.config)
            await self.db_manager.initialize()

            self.vector_store = VectorStoreService(self.config)
            await self.vector_store.initialize()

            self.embedding_service = EmbeddingService(self.config)
            await self.embedding_service.initialize()

            self.rag_service = RAGSearchService(
                self.vector_store,
                self.embedding_service,
                self.config
            )

            self.logger.info("MCP services initialized")

        except Exception as e:
            self.logger.error("Failed to initialize MCP services", extra={
                "error": str(e)
            })
            raise

    async def cleanup_services(self) -> None:
        """Clean up all backend services."""
        if self.embedding_service:
            await self.embedding_service.cleanup()
        if self.vector_store:
            await self.vector_store.cleanup()
        if self.db_manager:
            await self.db_manager.cleanup()

        self.logger.info("MCP services cleaned up")

    def _create_app(self) -> FastAPI:
        """Create FastAPI application."""
        app = FastAPI(
            title="DocBro MCP Server",
            description="Model Context Protocol server for DocBro",
            version="1.0.0"
        )

        # Add CORS middleware
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"]
        )

        # Add startup and shutdown events
        @app.on_event("startup")
        async def startup_event():
            await self.initialize_services()

        @app.on_event("shutdown")
        async def shutdown_event():
            await self.cleanup_services()

        # Add routes
        self._add_routes(app)

        return app

    def _add_routes(self, app: FastAPI) -> None:
        """Add API routes to the FastAPI app."""

        # Authentication helper
        async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
            """Verify authentication token."""
            # Simple token validation - in production, use proper JWT
            if credentials.credentials == "valid-test-token":
                return "authenticated"
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token"
            )

        # Health check
        @app.get("/health")
        async def health_check():
            """Health check endpoint."""
            return {
                "status": "healthy",
                "timestamp": datetime.utcnow().isoformat(),
                "services": {
                    "database": self.db_manager is not None,
                    "vector_store": self.vector_store is not None,
                    "embeddings": self.embedding_service is not None
                }
            }

        # MCP Connect endpoint
        @app.post("/mcp/connect", dependencies=[Depends(verify_token)])
        async def mcp_connect(session_data: Dict[str, Any]):
            """Establish MCP connection."""
            session_id = str(uuid.uuid4())
            self.sessions[session_id] = {
                "id": session_id,
                "created_at": datetime.utcnow().isoformat(),
                "data": session_data,
                "active": True
            }

            self.logger.info("MCP session created", extra={
                "session_id": session_id
            })

            return {
                "session_id": session_id,
                "status": "connected",
                "timestamp": datetime.utcnow().isoformat()
            }

        # MCP Projects endpoint
        @app.get("/mcp/projects", dependencies=[Depends(verify_token)])
        async def mcp_projects(
            status: Optional[str] = None,
            limit: int = 100
        ):
            """List available projects."""
            try:
                # Parse status filter
                status_filter = None
                if status:
                    try:
                        status_filter = ProjectStatus(status)
                    except ValueError:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Invalid status: {status}"
                        )

                # Get projects
                projects = await self.db_manager.list_projects(
                    status=status_filter,
                    limit=limit
                )

                # Format response
                return {
                    "projects": [
                        {
                            "name": p.name,
                            "source_url": p.source_url,
                            "status": p.status.value,
                            "last_updated": p.updated_at.isoformat(),
                            "page_count": p.total_pages,
                            "total_size": p.total_size_bytes,
                            "created_at": p.created_at.isoformat(),
                            "outdated": p.is_outdated()
                        }
                        for p in projects
                    ]
                }

            except Exception as e:
                self.logger.error("Failed to list projects", extra={
                    "error": str(e)
                })
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to list projects"
                )

        # MCP Search endpoint
        @app.post("/mcp/search", dependencies=[Depends(verify_token)])
        async def mcp_search(search_request: Dict[str, Any]):
            """Search documentation."""
            try:
                # Extract parameters
                query = search_request.get("query")
                if not query:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Query parameter is required"
                    )

                projects = search_request.get("projects", [])
                limit = min(search_request.get("limit", 10), 100)
                strategy = search_request.get("strategy", "semantic")

                # Perform search
                if projects:
                    # Search specific projects
                    results = await self.rag_service.search_multi_project(
                        query=query,
                        project_names=projects,
                        limit=limit,
                        strategy=strategy
                    )
                else:
                    # Search all projects
                    all_projects = await self.db_manager.list_projects()
                    project_names = [p.name for p in all_projects]
                    results = await self.rag_service.search_multi_project(
                        query=query,
                        project_names=project_names,
                        limit=limit,
                        strategy=strategy
                    )

                # Format response
                return {
                    "query": query,
                    "results": [
                        {
                            "id": r.get("id"),
                            "url": r.get("url"),
                            "title": r.get("title"),
                            "content": r.get("content", "")[:500],  # Limit content length
                            "score": r.get("score"),
                            "project": r.get("project")
                        }
                        for r in results
                    ],
                    "total": len(results)
                }

            except HTTPException:
                raise
            except Exception as e:
                self.logger.error("Search failed", extra={
                    "query": query,
                    "error": str(e)
                })
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Search failed"
                )

        # MCP Project refresh endpoint
        @app.post("/mcp/projects/refresh", dependencies=[Depends(verify_token)])
        async def mcp_project_refresh(refresh_request: Dict[str, Any]):
            """Refresh a project."""
            project_name = refresh_request.get("project_name")
            if not project_name:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Project name is required"
                )

            # Get project
            project = await self.db_manager.get_project_by_name(project_name)
            if not project:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Project '{project_name}' not found"
                )

            # TODO: Trigger crawl refresh
            return {
                "project_name": project_name,
                "status": "refresh_started",
                "message": "Project refresh not fully implemented yet"
            }

        # WebSocket endpoint for real-time updates
        @app.websocket("/mcp/ws/{session_id}")
        async def websocket_endpoint(websocket: WebSocket, session_id: str):
            """WebSocket connection for real-time updates."""
            await websocket.accept()
            self.websocket_connections[session_id] = websocket

            try:
                # Send initial connection message
                await websocket.send_json({
                    "type": "connection",
                    "status": "connected",
                    "session_id": session_id,
                    "timestamp": datetime.utcnow().isoformat()
                })

                # Handle incoming messages
                while True:
                    data = await websocket.receive_text()
                    message = json.loads(data)

                    # Process message based on type
                    if message.get("type") == "ping":
                        await websocket.send_json({
                            "type": "pong",
                            "timestamp": datetime.utcnow().isoformat()
                        })
                    elif message.get("type") == "search":
                        # Perform search and send results
                        query = message.get("query")
                        if query:
                            # Simplified search for WebSocket
                            await websocket.send_json({
                                "type": "search_results",
                                "query": query,
                                "results": [],
                                "timestamp": datetime.utcnow().isoformat()
                            })

            except WebSocketDisconnect:
                del self.websocket_connections[session_id]
                self.logger.info("WebSocket disconnected", extra={
                    "session_id": session_id
                })
            except Exception as e:
                self.logger.error("WebSocket error", extra={
                    "session_id": session_id,
                    "error": str(e)
                })
                del self.websocket_connections[session_id]

    def get_app(self) -> FastAPI:
        """Get FastAPI application instance."""
        return self.app

    async def send_update(self, session_id: str, message: Dict[str, Any]) -> None:
        """Send update to a connected WebSocket client."""
        if session_id in self.websocket_connections:
            ws = self.websocket_connections[session_id]
            try:
                await ws.send_json(message)
            except Exception as e:
                self.logger.error("Failed to send WebSocket update", extra={
                    "session_id": session_id,
                    "error": str(e)
                })


def create_app(config: Optional[DocBroConfig] = None) -> FastAPI:
    """Create MCP server FastAPI application."""
    server = MCPServer(config)
    return server.get_app()


def run_mcp_server(
    host: str = "0.0.0.0",
    port: int = 8000,
    config: Optional[DocBroConfig] = None
) -> None:
    """Run MCP server."""
    app = create_app(config)

    # Run with uvicorn
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info"
    )


if __name__ == "__main__":
    run_mcp_server()