"""Unit tests for contextual header formatting.

Tests verify:
- Header format with document title, section hierarchy, and project
- Hierarchy truncation (last 3 levels)
- Header prepending to chunk content
- Empty hierarchy handling
"""

import pytest
from src.logic.rag.utils.contextual_headers import format_header, add_contextual_header
from src.logic.rag.models.chunk import Chunk
from src.logic.rag.models.document import Document


class TestContextualHeaders:
    """Test contextual header formatting."""

    def test_format_header_basic(self):
        """Test basic header formatting with all components."""
        header = format_header(
            document_title="Docker Guide",
            hierarchy=[(1, "Installation"), (2, "Linux")],
            project="docker-docs"
        )

        assert "Document: Docker Guide" in header
        assert "Section: Installation > Linux" in header
        assert "Project: docker-docs" in header
        assert header.startswith("[")
        assert header.endswith("]")
        assert " | " in header

    def test_format_header_empty_hierarchy(self):
        """Test header formatting with empty hierarchy."""
        header = format_header(
            document_title="Docker Guide",
            hierarchy=[],
            project="docker-docs"
        )

        assert "Document: Docker Guide" in header
        assert "Section:" not in header
        assert "Project: docker-docs" in header

    def test_format_header_hierarchy_truncation(self):
        """Test that only last 3 hierarchy levels are included."""
        hierarchy = [
            (1, "Level1"),
            (2, "Level2"),
            (3, "Level3"),
            (4, "Level4"),
            (5, "Level5")
        ]

        header = format_header(
            document_title="Test Doc",
            hierarchy=hierarchy,
            project="test-project"
        )

        # Should only include last 3 levels
        assert "Level3 > Level4 > Level5" in header
        assert "Level1" not in header
        assert "Level2" not in header

    def test_format_header_single_level_hierarchy(self):
        """Test header with single hierarchy level."""
        header = format_header(
            document_title="API Reference",
            hierarchy=[(1, "Authentication")],
            project="api-docs"
        )

        assert "Section: Authentication" in header
        assert ">" not in header.split("Section:")[1].split("|")[0]

    def test_format_header_special_characters(self):
        """Test header formatting with special characters."""
        header = format_header(
            document_title="Docker & Kubernetes: A Guide",
            hierarchy=[(1, "Setup & Configuration"), (2, "TLS/SSL")],
            project="devops-docs"
        )

        assert "Docker & Kubernetes: A Guide" in header
        assert "Setup & Configuration > TLS/SSL" in header

    def test_add_contextual_header_basic(self):
        """Test adding contextual header to chunk."""
        document = Document(
            id="doc-1",
            title="Docker Guide",
            content="Docker content",
            url="https://example.com/docker",
            project="docker-docs"
        )

        chunk = Chunk(
            id="chunk-1",
            content="Docker is a containerization platform.",
            title="Docker Guide",
            url="https://example.com/docker",
            project="docker-docs",
            chunk_index=0,
            parent_id="doc-1"
        )

        hierarchy = [(1, "Introduction"), (2, "Overview")]

        enhanced_chunk = add_contextual_header(chunk, document, hierarchy)

        # Verify header was added
        assert enhanced_chunk.context_header is not None
        assert "Document: Docker Guide" in enhanced_chunk.context_header
        assert "Introduction > Overview" in enhanced_chunk.context_header
        assert "Project: docker-docs" in enhanced_chunk.context_header

        # Verify content was prepended
        assert enhanced_chunk.content.startswith("[")
        assert "Docker is a containerization platform." in enhanced_chunk.content

        # Verify hierarchy was stored
        assert enhanced_chunk.hierarchy == hierarchy

    def test_add_contextual_header_no_hierarchy(self):
        """Test adding header without hierarchy."""
        document = Document(
            id="doc-1",
            title="API Docs",
            content="API content",
            url="https://example.com/api",
            project="api-docs"
        )

        chunk = Chunk(
            id="chunk-1",
            content="API endpoint description.",
            title="API Docs",
            url="https://example.com/api",
            project="api-docs",
            chunk_index=0,
            parent_id="doc-1"
        )

        enhanced_chunk = add_contextual_header(chunk, document, None)

        assert enhanced_chunk.context_header is not None
        assert "Document: API Docs" in enhanced_chunk.context_header
        assert "Section:" not in enhanced_chunk.context_header
        assert "Project: api-docs" in enhanced_chunk.context_header

    def test_add_contextual_header_preserves_original(self):
        """Test that original chunk content is preserved."""
        document = Document(
            id="doc-1",
            title="Test Doc",
            content="Test content",
            url="https://example.com",
            project="test"
        )

        original_content = "This is the original chunk content."
        chunk = Chunk(
            id="chunk-1",
            content=original_content,
            title="Test Doc",
            url="https://example.com",
            project="test",
            chunk_index=0,
            parent_id="doc-1"
        )

        enhanced_chunk = add_contextual_header(chunk, document, [])

        # Original content should be present (after header and newlines)
        assert original_content in enhanced_chunk.content

    def test_header_format_consistency(self):
        """Test that header format is consistent across chunks."""
        document = Document(
            id="doc-1",
            title="Guide",
            content="Content",
            url="https://example.com",
            project="docs"
        )

        hierarchy = [(1, "Section 1")]

        # Note: add_contextual_header modifies chunk in place, so headers are identical
        header1 = format_header(document.title, hierarchy, document.project)
        header2 = format_header(document.title, hierarchy, document.project)

        # Headers should be identical for same inputs
        assert header1 == header2

    def test_header_length_reasonable(self):
        """Test that headers don't become too long."""
        hierarchy = [(i, f"Very Long Section Name Number {i}") for i in range(1, 11)]

        header = format_header(
            document_title="Test Document",
            hierarchy=hierarchy,
            project="test-project"
        )

        # With truncation to last 3 levels, header should be reasonable
        assert len(header) < 300  # Reasonable limit

    def test_header_newline_separation(self):
        """Test that header is separated from content by newlines."""
        document = Document(
            id="doc-1",
            title="Doc",
            content="Content",
            url="https://example.com",
            project="test"
        )

        chunk = Chunk(
            id="chunk-1",
            content="Chunk content",
            title="Doc",
            url="https://example.com",
            project="test",
            chunk_index=0,
            parent_id="doc-1"
        )

        enhanced_chunk = add_contextual_header(chunk, document, [])

        # Should have header, then two newlines, then original content
        parts = enhanced_chunk.content.split("\n\n", 1)
        assert len(parts) == 2
        assert parts[0].startswith("[")
        assert parts[0].endswith("]")
        assert parts[1] == "Chunk content"

    def test_hierarchy_stored_in_chunk(self):
        """Test that hierarchy is stored in chunk metadata."""
        document = Document(
            id="doc-1",
            title="Doc",
            content="Content",
            url="https://example.com",
            project="test"
        )

        chunk = Chunk(
            id="chunk-1",
            content="Content for testing hierarchy storage",
            title="Doc",
            url="https://example.com",
            project="test",
            chunk_index=0,
            parent_id="doc-1",
            hierarchy=[]  # Initialize with empty hierarchy
        )

        hierarchy = [(1, "Intro"), (2, "Overview")]
        enhanced_chunk = add_contextual_header(chunk, document, hierarchy)

        # Verify hierarchy is stored
        assert len(enhanced_chunk.hierarchy) == 2
        assert enhanced_chunk.hierarchy[0] == (1, "Intro")
        assert enhanced_chunk.hierarchy[1] == (2, "Overview")