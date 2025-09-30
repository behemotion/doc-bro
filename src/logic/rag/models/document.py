"""Document model for RAG operations."""

from pydantic import BaseModel, Field


class Document(BaseModel):
    """Simple document model for RAG processing."""

    id: str = Field(description="Unique document identifier")
    content: str = Field(description="Document text content")
    title: str = Field(default="", description="Document title")
    url: str = Field(default="", description="Source URL")
    project: str = Field(default="", description="Project name")
    metadata: dict[str, str] = Field(default_factory=dict, description="Additional metadata")

    class Config:
        """Pydantic v2 configuration."""

        json_schema_extra = {
            "example": {
                "id": "doc-123",
                "content": "Docker is a containerization platform...",
                "title": "Docker Getting Started",
                "url": "https://docs.docker.com/get-started/",
                "project": "docker-docs",
                "metadata": {"author": "Docker Inc", "version": "v1.0"},
            }
        }