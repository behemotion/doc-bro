"""Contextual header generation for chunks."""

from src.logic.rag.models.chunk import Chunk
from src.logic.rag.models.document import Document


def format_header(
    document_title: str, hierarchy: list[tuple[int, str]], project: str
) -> str:
    """Format a contextual header for a chunk.

    Args:
        document_title: Title of the source document
        hierarchy: List of (level, heading_text) tuples
        project: Project name

    Returns:
        Formatted header string
    """
    parts = [f"Document: {document_title}"]

    if hierarchy:
        # Build section path from hierarchy
        section_path = " > ".join(heading for _, heading in hierarchy[-3:])  # Last 3 levels
        parts.append(f"Section: {section_path}")

    parts.append(f"Project: {project}")

    return "[" + " | ".join(parts) + "]"


def add_contextual_header(
    chunk: Chunk, document: Document, hierarchy: list[tuple[int, str]] | None = None
) -> Chunk:
    """Add contextual header to a chunk.

    Args:
        chunk: Chunk to enhance
        document: Source document
        hierarchy: Optional document hierarchy

    Returns:
        Enhanced chunk with context header
    """
    # Generate header
    hierarchy = hierarchy or []
    header = format_header(document.title, hierarchy, document.project)

    # Prepend header to content
    enhanced_content = f"{header}\n\n{chunk.content}"

    # Update chunk
    chunk.content = enhanced_content
    chunk.context_header = header
    chunk.hierarchy = hierarchy

    return chunk