"""Unit tests for ShelfBox model."""

import pytest
from datetime import datetime
from uuid import uuid4

from src.models.shelf_box import ShelfBox, ShelfBoxValidationError


class TestShelfBoxModel:
    """Test ShelfBox model functionality."""

    def test_shelf_box_creation_defaults(self):
        """Test shelf-box creation with default values."""
        shelf_id = str(uuid4())
        box_id = str(uuid4())

        shelf_box = ShelfBox(shelf_id=shelf_id, box_id=box_id)

        assert shelf_box.shelf_id == shelf_id
        assert shelf_box.box_id == box_id
        assert shelf_box.position is None
        assert isinstance(shelf_box.added_at, datetime)

    def test_shelf_box_creation_with_position(self):
        """Test shelf-box creation with position."""
        shelf_id = str(uuid4())
        box_id = str(uuid4())
        position = 5
        added_time = datetime.utcnow()

        shelf_box = ShelfBox(
            shelf_id=shelf_id,
            box_id=box_id,
            position=position,
            added_at=added_time
        )

        assert shelf_box.shelf_id == shelf_id
        assert shelf_box.box_id == box_id
        assert shelf_box.position == position
        assert shelf_box.added_at == added_time

    def test_shelf_id_validation_empty(self):
        """Test that empty shelf_id is rejected."""
        box_id = str(uuid4())

        with pytest.raises(ShelfBoxValidationError, match="shelf_id cannot be empty"):
            ShelfBox(shelf_id="", box_id=box_id)

        with pytest.raises(ShelfBoxValidationError, match="shelf_id cannot be empty"):
            ShelfBox(shelf_id="   ", box_id=box_id)  # Only whitespace

    def test_box_id_validation_empty(self):
        """Test that empty box_id is rejected."""
        shelf_id = str(uuid4())

        with pytest.raises(ShelfBoxValidationError, match="box_id cannot be empty"):
            ShelfBox(shelf_id=shelf_id, box_id="")

        with pytest.raises(ShelfBoxValidationError, match="box_id cannot be empty"):
            ShelfBox(shelf_id=shelf_id, box_id="   ")  # Only whitespace

    def test_position_validation_negative(self):
        """Test that negative position is rejected."""
        shelf_id = str(uuid4())
        box_id = str(uuid4())

        with pytest.raises(ShelfBoxValidationError, match="position must be non-negative"):
            ShelfBox(shelf_id=shelf_id, box_id=box_id, position=-1)

    def test_position_validation_zero_and_positive(self):
        """Test that zero and positive positions are accepted."""
        shelf_id = str(uuid4())
        box_id = str(uuid4())

        # Zero position should be valid
        shelf_box_0 = ShelfBox(shelf_id=shelf_id, box_id=box_id, position=0)
        assert shelf_box_0.position == 0

        # Positive position should be valid
        shelf_box_pos = ShelfBox(shelf_id=shelf_id, box_id=box_id, position=10)
        assert shelf_box_pos.position == 10

    def test_to_dict(self):
        """Test dictionary conversion."""
        shelf_id = str(uuid4())
        box_id = str(uuid4())
        position = 3
        added_time = datetime(2023, 1, 15, 10, 30, 0)

        shelf_box = ShelfBox(
            shelf_id=shelf_id,
            box_id=box_id,
            position=position,
            added_at=added_time
        )

        data = shelf_box.to_dict()
        expected_keys = {"shelf_id", "box_id", "position", "added_at"}

        assert set(data.keys()) == expected_keys
        assert data["shelf_id"] == shelf_id
        assert data["box_id"] == box_id
        assert data["position"] == position
        assert data["added_at"] == "2023-01-15T10:30:00"  # ISO format

    def test_to_dict_no_position(self):
        """Test dictionary conversion when position is None."""
        shelf_id = str(uuid4())
        box_id = str(uuid4())

        shelf_box = ShelfBox(shelf_id=shelf_id, box_id=box_id)
        data = shelf_box.to_dict()

        assert data["position"] is None

    def test_string_representation(self):
        """Test string representation."""
        shelf_id = "shelf-123"
        box_id = "box-456"

        # Without position
        shelf_box_no_pos = ShelfBox(shelf_id=shelf_id, box_id=box_id)
        str_repr_no_pos = str(shelf_box_no_pos)
        assert "box-456 in shelf-123" in str_repr_no_pos
        assert "position" not in str_repr_no_pos

        # With position
        shelf_box_with_pos = ShelfBox(shelf_id=shelf_id, box_id=box_id, position=5)
        str_repr_with_pos = str(shelf_box_with_pos)
        assert "box-456 in shelf-123" in str_repr_with_pos
        assert "at position 5" in str_repr_with_pos

    def test_repr(self):
        """Test developer representation."""
        shelf_id = "shelf-123"
        box_id = "box-456"
        position = 7

        shelf_box = ShelfBox(shelf_id=shelf_id, box_id=box_id, position=position)
        repr_str = repr(shelf_box)

        assert "ShelfBox(" in repr_str
        assert "shelf_id='shelf-123'" in repr_str
        assert "box_id='box-456'" in repr_str
        assert "position=7" in repr_str

    def test_config_json_encoders(self):
        """Test that datetime objects are properly encoded."""
        shelf_id = str(uuid4())
        box_id = str(uuid4())

        shelf_box = ShelfBox(shelf_id=shelf_id, box_id=box_id)
        data = shelf_box.model_dump(mode='json')

        # Date should be ISO format string
        assert isinstance(data["added_at"], str)
        assert "T" in data["added_at"]  # ISO format indicator

    def test_equality(self):
        """Test shelf-box equality based on content."""
        shelf_id = str(uuid4())
        box_id = str(uuid4())
        added_time = datetime.utcnow()

        shelf_box_1 = ShelfBox(
            shelf_id=shelf_id,
            box_id=box_id,
            position=1,
            added_at=added_time
        )

        shelf_box_2 = ShelfBox(
            shelf_id=shelf_id,
            box_id=box_id,
            position=1,
            added_at=added_time
        )

        shelf_box_3 = ShelfBox(
            shelf_id=shelf_id,
            box_id=box_id,
            position=2,  # Different position
            added_at=added_time
        )

        # Same content should be equal
        assert shelf_box_1 == shelf_box_2

        # Different content should not be equal
        assert shelf_box_1 != shelf_box_3

    def test_different_shelf_same_box(self):
        """Test that same box in different shelves creates different relationships."""
        box_id = str(uuid4())
        shelf_id_1 = str(uuid4())
        shelf_id_2 = str(uuid4())

        shelf_box_1 = ShelfBox(shelf_id=shelf_id_1, box_id=box_id)
        shelf_box_2 = ShelfBox(shelf_id=shelf_id_2, box_id=box_id)

        assert shelf_box_1.box_id == shelf_box_2.box_id
        assert shelf_box_1.shelf_id != shelf_box_2.shelf_id
        assert shelf_box_1 != shelf_box_2

    def test_same_shelf_different_boxes(self):
        """Test that different boxes in same shelf create different relationships."""
        shelf_id = str(uuid4())
        box_id_1 = str(uuid4())
        box_id_2 = str(uuid4())

        shelf_box_1 = ShelfBox(shelf_id=shelf_id, box_id=box_id_1)
        shelf_box_2 = ShelfBox(shelf_id=shelf_id, box_id=box_id_2)

        assert shelf_box_1.shelf_id == shelf_box_2.shelf_id
        assert shelf_box_1.box_id != shelf_box_2.box_id
        assert shelf_box_1 != shelf_box_2

    def test_position_ordering_concept(self):
        """Test the concept of position-based ordering."""
        shelf_id = str(uuid4())
        box_id_1 = str(uuid4())
        box_id_2 = str(uuid4())
        box_id_3 = str(uuid4())

        # Create relationships with different positions
        rel_1 = ShelfBox(shelf_id=shelf_id, box_id=box_id_1, position=1)
        rel_2 = ShelfBox(shelf_id=shelf_id, box_id=box_id_2, position=2)
        rel_3 = ShelfBox(shelf_id=shelf_id, box_id=box_id_3, position=0)

        # Positions should be preserved
        assert rel_1.position == 1
        assert rel_2.position == 2
        assert rel_3.position == 0

        # Create list and sort by position to demonstrate ordering
        relationships = [rel_1, rel_2, rel_3]
        sorted_relationships = sorted(relationships, key=lambda r: r.position or float('inf'))

        assert sorted_relationships[0].position == 0
        assert sorted_relationships[1].position == 1
        assert sorted_relationships[2].position == 2