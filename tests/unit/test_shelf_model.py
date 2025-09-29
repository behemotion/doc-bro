"""Unit tests for Shelf model."""

import pytest
from datetime import datetime
from uuid import UUID

from src.models.shelf import Shelf, ShelfValidationError


class TestShelfModel:
    """Test Shelf model functionality."""

    def test_shelf_creation_defaults(self):
        """Test shelf creation with default values."""
        shelf = Shelf(name="test shelf")

        assert shelf.name == "test shelf"
        assert isinstance(UUID(shelf.id), UUID)  # Valid UUID
        assert shelf.is_default is False
        assert shelf.is_deletable is True
        assert isinstance(shelf.created_at, datetime)
        assert isinstance(shelf.updated_at, datetime)
        assert shelf.box_count == 0
        assert shelf.boxes == []

    def test_shelf_creation_custom_values(self):
        """Test shelf creation with custom values."""
        now = datetime.utcnow()
        shelf = Shelf(
            id="custom-id",
            name="Custom Shelf",
            is_default=True,
            is_deletable=False,
            created_at=now,
            updated_at=now,
            box_count=5
        )

        assert shelf.id == "custom-id"
        assert shelf.name == "Custom Shelf"
        assert shelf.is_default is True
        assert shelf.is_deletable is False
        assert shelf.created_at == now
        assert shelf.updated_at == now
        assert shelf.box_count == 5

    def test_name_validation_valid(self):
        """Test valid shelf names."""
        valid_names = [
            "simple",
            "with spaces",
            "with-hyphens",
            "with_underscores",
            "Mixed123",
            "shelf 1",
            "a" * 100  # Max length
        ]

        for name in valid_names:
            shelf = Shelf(name=name)
            assert shelf.name == name

    def test_name_validation_invalid_empty(self):
        """Test that empty names are rejected."""
        with pytest.raises(ShelfValidationError, match="Shelf name cannot be empty"):
            Shelf(name="")

        with pytest.raises(ShelfValidationError, match="Shelf name cannot be empty"):
            Shelf(name="   ")  # Only whitespace

    def test_name_validation_invalid_length(self):
        """Test that names exceeding max length are rejected."""
        long_name = "a" * 101  # Exceeds MAX_NAME_LENGTH
        with pytest.raises(ShelfValidationError, match="cannot exceed 100 characters"):
            Shelf(name=long_name)

    def test_name_validation_invalid_characters(self):
        """Test that names with invalid characters are rejected."""
        invalid_names = [
            "shelf@name",
            "shelf#name",
            "shelf$name",
            "shelf%name",
            "shelf!name",
            "shelf/name",
            "shelf\\name",
            "shelf|name"
        ]

        for name in invalid_names:
            with pytest.raises(ShelfValidationError, match="can only contain letters, numbers"):
                Shelf(name=name)

    def test_name_validation_reserved_names(self):
        """Test that reserved names are rejected."""
        reserved_names = ["default", "system", "temp", "tmp", "test"]

        for name in reserved_names:
            with pytest.raises(ShelfValidationError, match=f"'{name}' is a reserved shelf name"):
                Shelf(name=name)

            # Test case insensitive
            with pytest.raises(ShelfValidationError, match=f"'{name.upper()}' is a reserved shelf name"):
                Shelf(name=name.upper())

    def test_name_trimming(self):
        """Test that shelf names are trimmed of whitespace."""
        shelf = Shelf(name="  spaced name  ")
        assert shelf.name == "spaced name"

    def test_timestamp_validation(self):
        """Test that updated_at is adjusted if before created_at."""
        earlier = datetime(2023, 1, 1)
        later = datetime(2023, 1, 2)

        shelf = Shelf(name="test", created_at=later, updated_at=earlier)
        assert shelf.updated_at == shelf.created_at  # Should be adjusted

    def test_to_dict_basic(self):
        """Test basic dictionary conversion."""
        shelf = Shelf(
            id="test-id",
            name="Test Shelf",
            is_default=True,
            is_deletable=False,
            box_count=3
        )

        data = shelf.to_dict()
        expected_keys = {
            "id", "name", "is_default", "is_deletable",
            "created_at", "updated_at", "box_count"
        }

        assert set(data.keys()) == expected_keys
        assert data["id"] == "test-id"
        assert data["name"] == "Test Shelf"
        assert data["is_default"] is True
        assert data["is_deletable"] is False
        assert data["box_count"] == 3

    def test_to_dict_with_boxes(self):
        """Test dictionary conversion including boxes."""
        shelf = Shelf(name="Test Shelf", boxes=["box1", "box2"])

        data_without_boxes = shelf.to_dict(include_boxes=False)
        assert "boxes" not in data_without_boxes

        data_with_boxes = shelf.to_dict(include_boxes=True)
        assert "boxes" in data_with_boxes
        assert data_with_boxes["boxes"] == ["box1", "box2"]

    def test_to_summary(self):
        """Test summary generation."""
        shelf = Shelf(
            name="Test Shelf",
            is_default=True,
            box_count=5
        )

        summary = shelf.to_summary()
        expected_keys = {"name", "is_default", "box_count", "created_at"}

        assert set(summary.keys()) == expected_keys
        assert summary["name"] == "Test Shelf"
        assert summary["is_default"] is True
        assert summary["box_count"] == 5

    def test_string_representation(self):
        """Test string representation."""
        # Regular shelf
        shelf1 = Shelf(name="Regular Shelf", box_count=3)
        str_repr1 = str(shelf1)
        assert "Regular Shelf" in str_repr1
        assert "3 boxes" in str_repr1
        assert "default" not in str_repr1
        assert "protected" not in str_repr1

        # Default shelf
        shelf2 = Shelf(name="Default Shelf", is_default=True, box_count=1)
        str_repr2 = str(shelf2)
        assert "Default Shelf" in str_repr2
        assert "(default)" in str_repr2

        # Protected (non-deletable) shelf
        shelf3 = Shelf(name="Protected Shelf", is_deletable=False, box_count=2)
        str_repr3 = str(shelf3)
        assert "Protected Shelf" in str_repr3
        assert "(protected)" in str_repr3

    def test_repr(self):
        """Test developer representation."""
        shelf = Shelf(
            id="test-id",
            name="Test Shelf",
            is_default=True,
            box_count=3
        )

        repr_str = repr(shelf)
        assert "Shelf(" in repr_str
        assert "id='test-id'" in repr_str
        assert "name='Test Shelf'" in repr_str
        assert "is_default=True" in repr_str
        assert "box_count=3" in repr_str

    def test_config_json_encoders(self):
        """Test that datetime objects are properly encoded."""
        shelf = Shelf(name="Test Shelf")
        data = shelf.model_dump(mode='json')

        # Dates should be ISO format strings
        assert isinstance(data["created_at"], str)
        assert isinstance(data["updated_at"], str)
        assert "T" in data["created_at"]  # ISO format indicator

    def test_equality(self):
        """Test shelf equality based on content."""
        shelf1 = Shelf(id="same-id", name="Same Name")
        shelf2 = Shelf(id="same-id", name="Same Name")
        shelf3 = Shelf(id="different-id", name="Same Name")

        # Pydantic models compare by content, not just ID
        assert shelf1 == shelf2
        assert shelf1 != shelf3  # Different ID

    def test_immutable_constants(self):
        """Test that class constants are accessible."""
        assert Shelf.MAX_NAME_LENGTH == 100
        assert "default" in Shelf.RESERVED_NAMES
        assert "system" in Shelf.RESERVED_NAMES
        assert len(Shelf.RESERVED_NAMES) == 5