"""Unit tests for BoxType enum."""

import pytest

from src.models.box_type import BoxType


class TestBoxType:
    """Test BoxType enum functionality."""

    def test_enum_values(self):
        """Test that enum has correct values."""
        assert BoxType.DRAG.value == "drag"
        assert BoxType.RAG.value == "rag"
        assert BoxType.BAG.value == "bag"

    def test_string_representation(self):
        """Test string representation of enum values."""
        assert str(BoxType.DRAG) == "drag"
        assert str(BoxType.RAG) == "rag"
        assert str(BoxType.BAG) == "bag"

    def test_from_string_valid(self):
        """Test creating BoxType from valid string values."""
        assert BoxType.from_string("drag") == BoxType.DRAG
        assert BoxType.from_string("rag") == BoxType.RAG
        assert BoxType.from_string("bag") == BoxType.BAG

        # Test case insensitive
        assert BoxType.from_string("DRAG") == BoxType.DRAG
        assert BoxType.from_string("Rag") == BoxType.RAG
        assert BoxType.from_string("BAG") == BoxType.BAG

    def test_from_string_invalid(self):
        """Test that invalid strings raise ValueError."""
        with pytest.raises(ValueError, match="Invalid box type: invalid"):
            BoxType.from_string("invalid")

        with pytest.raises(ValueError, match="Invalid box type: crawling"):
            BoxType.from_string("crawling")  # Old terminology

        with pytest.raises(ValueError, match="Invalid box type: "):
            BoxType.from_string("")

    def test_get_description(self):
        """Test that descriptions are returned for all types."""
        drag_desc = BoxType.DRAG.get_description()
        assert "crawling" in drag_desc.lower()
        assert "web" in drag_desc.lower()

        rag_desc = BoxType.RAG.get_description()
        assert "document" in rag_desc.lower()
        assert "search" in rag_desc.lower()

        bag_desc = BoxType.BAG.get_description()
        assert "storage" in bag_desc.lower()
        assert "file" in bag_desc.lower()

    def test_get_legacy_equivalent(self):
        """Test that legacy equivalents are correct."""
        assert BoxType.DRAG.get_legacy_equivalent() == "crawling"
        assert BoxType.RAG.get_legacy_equivalent() == "data"
        assert BoxType.BAG.get_legacy_equivalent() == "storage"

    def test_enum_iteration(self):
        """Test that all enum values can be iterated."""
        all_types = list(BoxType)
        assert len(all_types) == 3
        assert BoxType.DRAG in all_types
        assert BoxType.RAG in all_types
        assert BoxType.BAG in all_types

    def test_equality(self):
        """Test enum equality comparisons."""
        assert BoxType.DRAG == BoxType.DRAG
        assert BoxType.DRAG != BoxType.RAG
        assert BoxType.RAG != BoxType.BAG

        # String comparison
        assert BoxType.DRAG == "drag"
        assert BoxType.RAG == "rag"
        assert BoxType.BAG == "bag"

    def test_hashable(self):
        """Test that enum values are hashable (can be used as dict keys)."""
        type_dict = {
            BoxType.DRAG: "crawling",
            BoxType.RAG: "documents",
            BoxType.BAG: "storage"
        }

        assert type_dict[BoxType.DRAG] == "crawling"
        assert type_dict[BoxType.RAG] == "documents"
        assert type_dict[BoxType.BAG] == "storage"