"""Unit tests for RerankWeights validation.

Tests verify:
- Weight range validation (0.0-1.0)
- Weight sum validation (~1.0)
- Default weight configuration
- Custom weight configurations
- Floating point tolerance handling
"""

import pytest
from pydantic import ValidationError
from src.logic.rag.models.strategy_config import RerankWeights


class TestRerankWeights:
    """Test RerankWeights validation."""

    def test_default_weights(self):
        """Test default weight configuration."""
        weights = RerankWeights()

        assert weights.vector_score == 0.5
        assert weights.term_overlap == 0.3
        assert weights.title_match == 0.1
        assert weights.freshness == 0.1

        # Default weights should sum to 1.0
        assert weights.validate_sum()

    def test_custom_weights_valid(self):
        """Test custom weights that sum to 1.0."""
        weights = RerankWeights(
            vector_score=0.6,
            term_overlap=0.2,
            title_match=0.1,
            freshness=0.1
        )

        assert weights.vector_score == 0.6
        assert weights.term_overlap == 0.2
        assert weights.validate_sum()

    def test_weights_sum_validation_pass(self):
        """Test weights that sum to approximately 1.0 pass validation."""
        # Exactly 1.0
        weights1 = RerankWeights(
            vector_score=0.4,
            term_overlap=0.3,
            title_match=0.2,
            freshness=0.1
        )
        assert weights1.validate_sum()

        # Within tolerance (0.995)
        weights2 = RerankWeights(
            vector_score=0.395,
            term_overlap=0.3,
            title_match=0.2,
            freshness=0.1
        )
        assert weights2.validate_sum()

        # Within tolerance (1.005)
        weights3 = RerankWeights(
            vector_score=0.405,
            term_overlap=0.3,
            title_match=0.2,
            freshness=0.1
        )
        assert weights3.validate_sum()

    def test_weights_sum_validation_fail(self):
        """Test weights that don't sum to ~1.0 fail validation."""
        # Sum = 0.5 (too low)
        weights1 = RerankWeights(
            vector_score=0.2,
            term_overlap=0.1,
            title_match=0.1,
            freshness=0.1
        )
        assert not weights1.validate_sum()

        # Sum = 1.5 (too high)
        weights2 = RerankWeights(
            vector_score=0.5,
            term_overlap=0.5,
            title_match=0.3,
            freshness=0.2
        )
        assert not weights2.validate_sum()

    def test_weight_range_validation_lower_bound(self):
        """Test that weights below 0.0 are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            RerankWeights(vector_score=-0.1)

        assert "greater than or equal to 0" in str(exc_info.value)

    def test_weight_range_validation_upper_bound(self):
        """Test that weights above 1.0 are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            RerankWeights(term_overlap=1.5)

        assert "less than or equal to 1" in str(exc_info.value)

    def test_weight_boundary_values(self):
        """Test boundary values (0.0 and 1.0)."""
        # All zeros (valid range, invalid sum)
        weights_zeros = RerankWeights(
            vector_score=0.0,
            term_overlap=0.0,
            title_match=0.0,
            freshness=0.0
        )
        assert not weights_zeros.validate_sum()

        # One weight is 1.0, rest are 0.0 (valid)
        weights_one = RerankWeights(
            vector_score=1.0,
            term_overlap=0.0,
            title_match=0.0,
            freshness=0.0
        )
        assert weights_one.validate_sum()

    def test_floating_point_tolerance(self):
        """Test floating point tolerance in sum validation."""
        # Sum = 0.999 (within tolerance)
        weights1 = RerankWeights(
            vector_score=0.499,
            term_overlap=0.3,
            title_match=0.1,
            freshness=0.1
        )
        assert weights1.validate_sum()

        # Sum = 1.001 (within tolerance)
        weights2 = RerankWeights(
            vector_score=0.501,
            term_overlap=0.3,
            title_match=0.1,
            freshness=0.1
        )
        assert weights2.validate_sum()

        # Sum = 0.98 (outside tolerance)
        weights3 = RerankWeights(
            vector_score=0.48,
            term_overlap=0.3,
            title_match=0.1,
            freshness=0.1
        )
        assert not weights3.validate_sum()

    def test_equal_weights_distribution(self):
        """Test equal distribution of weights."""
        weights = RerankWeights(
            vector_score=0.25,
            term_overlap=0.25,
            title_match=0.25,
            freshness=0.25
        )

        assert weights.validate_sum()
        assert all(w == 0.25 for w in [
            weights.vector_score,
            weights.term_overlap,
            weights.title_match,
            weights.freshness
        ])

    def test_extreme_weight_distribution(self):
        """Test extreme but valid weight distributions."""
        # Heavily favor vector score
        weights1 = RerankWeights(
            vector_score=0.97,
            term_overlap=0.01,
            title_match=0.01,
            freshness=0.01
        )
        assert weights1.validate_sum()

        # Heavily favor term overlap
        weights2 = RerankWeights(
            vector_score=0.01,
            term_overlap=0.97,
            title_match=0.01,
            freshness=0.01
        )
        assert weights2.validate_sum()

    def test_weights_serialization(self):
        """Test weights can be serialized/deserialized."""
        weights = RerankWeights(
            vector_score=0.6,
            term_overlap=0.2,
            title_match=0.1,
            freshness=0.1
        )

        # Serialize to dict
        weights_dict = weights.model_dump()
        assert weights_dict["vector_score"] == 0.6
        assert weights_dict["term_overlap"] == 0.2

        # Deserialize from dict
        weights_restored = RerankWeights(**weights_dict)
        assert weights_restored.vector_score == weights.vector_score
        assert weights_restored.validate_sum()

    def test_partial_weight_specification(self):
        """Test specifying only some weights (others use defaults)."""
        weights = RerankWeights(vector_score=0.7)

        assert weights.vector_score == 0.7
        assert weights.term_overlap == 0.3  # Default
        assert weights.title_match == 0.1  # Default
        assert weights.freshness == 0.1  # Default

        # Should fail sum validation (0.7 + 0.3 + 0.1 + 0.1 = 1.2)
        assert not weights.validate_sum()

    def test_weight_precision(self):
        """Test weight precision handling."""
        weights = RerankWeights(
            vector_score=0.333333,
            term_overlap=0.333333,
            title_match=0.333333,
            freshness=0.000001
        )

        # Sum = 0.999999 (within tolerance)
        assert weights.validate_sum()

    def test_immutable_after_creation(self):
        """Test that weights can be modified after creation."""
        weights = RerankWeights()

        # Pydantic v2 models are mutable by default
        weights.vector_score = 0.8
        assert weights.vector_score == 0.8

        # But validation should still work
        assert not weights.validate_sum()  # Now sum is 1.3