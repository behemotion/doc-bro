"""Box type enumeration for the Shelf-Box Rhyme System."""

from enum import Enum


class BoxType(str, Enum):
    """
    Box types following the rhyming convention.

    Each type determines how the fill command operates:
    - DRAG: Website crawling (formerly crawling projects)
    - RAG: Document import for RAG/search (formerly data projects)
    - BAG: File storage (formerly storage projects)
    """

    DRAG = "drag"  # Website crawling
    RAG = "rag"    # Document import for RAG
    BAG = "bag"    # File storage

    def __str__(self) -> str:
        """Return the string value."""
        return self.value

    @classmethod
    def from_string(cls, value: str) -> "BoxType":
        """Create BoxType from string value."""
        value_lower = value.lower()
        for box_type in cls:
            if box_type.value == value_lower:
                return box_type
        raise ValueError(f"Invalid box type: {value}. Must be one of: {', '.join([t.value for t in cls])}")

    def get_description(self) -> str:
        """Get human-readable description of the box type."""
        descriptions = {
            BoxType.DRAG: "Website crawling - Extract documentation from web pages",
            BoxType.RAG: "Document import - Upload and index documents for search",
            BoxType.BAG: "File storage - Store and organize files and archives"
        }
        return descriptions[self]

    def get_legacy_equivalent(self) -> str:
        """Get the legacy project type this box type replaces."""
        legacy_mapping = {
            BoxType.DRAG: "crawling",
            BoxType.RAG: "data",
            BoxType.BAG: "storage"
        }
        return legacy_mapping[self]