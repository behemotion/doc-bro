"""
EmbeddingStatus model for embedding display component
"""

from typing import Optional
from pydantic import BaseModel, Field, field_validator, ConfigDict
from .enums import ProcessingState


class EmbeddingStatus(BaseModel):
    """Display component for embedding model and project context"""

    model_name: str = Field(..., min_length=1, description="Name of embedding model")
    project_name: str = Field(..., min_length=1, description="Target project identifier")
    processing_state: ProcessingState = Field(default=ProcessingState.INITIALIZING, description="Current embedding phase")
    error_message: Optional[str] = Field(default=None, description="Error text if processing fails")

    @field_validator('project_name')
    @classmethod
    def validate_project_name(cls, v):
        """Validate project name contains only valid characters"""
        if not all(c.isalnum() or c in '-_.' for c in v):
            raise ValueError("Project name must contain only alphanumeric characters, hyphens, underscores, and dots")
        return v

    @field_validator('error_message')
    @classmethod
    def validate_error_message(cls, v):
        """Ensure error message is reasonable length"""
        if v is not None and len(v) > 200:
            return v[:197] + "..."
        return v

    def get_status_text(self) -> str:
        """Get formatted status text for display"""
        if self.error_message:
            return f"[ERROR: {self.error_message}]"

        state_text = {
            ProcessingState.INITIALIZING: "initializing",
            ProcessingState.PROCESSING: "processing",
            ProcessingState.COMPLETE: "complete",
            ProcessingState.ERROR: "error"
        }

        return f"[{state_text[self.processing_state]}]"

    def is_error_state(self) -> bool:
        """Check if current state indicates an error"""
        return self.processing_state == ProcessingState.ERROR or self.error_message is not None

    model_config = ConfigDict(validate_assignment=True)