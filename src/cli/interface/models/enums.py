"""
Enumerations for CLI interface components
"""

from enum import Enum


class LayoutMode(Enum):
    """Layout modes for progress display"""
    FULL_WIDTH = "full_width"
    COMPACT = "compact"


class ProcessingState(Enum):
    """States for embedding/processing operations"""
    INITIALIZING = "initializing"
    PROCESSING = "processing"
    COMPLETE = "complete"
    ERROR = "error"


class CompletionStatus(Enum):
    """Final status of completed operations"""
    SUCCESS = "success"
    PARTIAL_SUCCESS = "partial_success"
    FAILURE = "failure"


class TruncationStrategy(Enum):
    """Strategies for text truncation"""
    MIDDLE = "middle"
    END = "end"
    NONE = "none"
