"""Tests for climb classifier."""

import pytest

from tcx_parser.climb_classifier import (
    classify_climb,
    get_category_color,
    get_category_description,
    get_category_rank,
    avg_pct,
    pass_2of3,
    Threshold,
)


class TestAvgPct:
    """Tests for average gradient calculation."""

    def test_normal_gradient(self):
        """Test normal gradient calculation."""
        # 500m gain over 10km = 5%
        result = avg_pct(10.0, 500)
        assert result == pytest.approx(5.0)

    def test_steep_gradient(self):
        """Test steep gradient calculation."""
        # 1000m gain over 10km = 10%
        result = avg_pct(10.0, 1000)
        assert result == pytest.approx(10.0)

    def test_zero_length(self):
        """Test with zero length."""
        result = avg_pct(0, 500)
        assert result == 0.0

    def test_negative_length(self):
        """Test with negative length."""
        result = avg_pct(-5, 500)
        assert result == 0.0


class TestPass2of3:
    """Tests for 2-out-of-3 rule."""

    def test_all_three_pass(self):
        """Test when all three criteria pass."""
        threshold = Threshold(gain=500, length=10, avg=5)
        assert pass_2of3(threshold, 15, 600, 6) is True

    def test_two_pass(self):
        """Test when exactly two criteria pass."""
        threshold = Threshold(gain=500, length=10, avg=5)
        # Length and avg pass, gain doesn't
        assert pass_2of3(threshold, 12, 400, 6) is True

    def test_one_passes(self):
        """Test when only one criterion passes."""
        threshold = Threshold(gain=500, length=10, avg=5)
        assert pass_2of3(threshold, 8, 400, 4) is False

    def test_none_pass(self):
        """Test when no criteria pass."""
        threshold = Threshold(gain=500, length=10, avg=5)
        assert pass_2of3(threshold, 5, 200, 3) is False


class TestClassifyClimb:
    """Tests for climb classification."""

    def test_hc_climb(self):
        """Test HC (Hors Catégorie) classification."""
        # 25km, 1500m gain = 6% avg (passes 2 of 3 for HC)
        result = classify_climb(25.0, 1500)
        assert result.category == "HC"

    def test_cat1_climb(self):
        """Test Category 1 classification."""
        # 15km, 1000m gain = 6.67% avg
        result = classify_climb(15.0, 1000)
        assert result.category == "Cat 1"

    def test_cat2_climb(self):
        """Test Category 2 classification."""
        # 10km, 700m gain = 7% avg
        result = classify_climb(10.0, 700)
        assert result.category == "Cat 2"

    def test_cat3_climb(self):
        """Test Category 3 classification."""
        # 6km, 400m gain = 6.67% avg
        result = classify_climb(6.0, 400)
        assert result.category == "Cat 3"

    def test_cat4_climb(self):
        """Test Category 4 classification."""
        # 3km, 250m gain = 8.33% avg
        result = classify_climb(3.0, 250)
        assert result.category == "Cat 4"

    def test_unclassified_climb(self):
        """Test unclassified (too easy) climb."""
        # 1km, 30m gain = 3% avg
        result = classify_climb(1.0, 30)
        assert result.category == "Unclassified"

    def test_bonus_applied(self):
        """Test 9.5% average bonus upgrade."""
        # A climb that would be Cat 2 but gets upgraded to Cat 1
        # 8km, 800m gain = 10% avg (very steep)
        result = classify_climb(8.0, 800)
        assert result.avg_pct == pytest.approx(10.0)
        # Should get bonus because avg >= 9.5%
        if result.base != "HC":
            assert result.bonus_applied is True

    def test_short_steep_climb(self):
        """Test ultra-short steep climb."""
        # 1km, 130m gain = 13% avg (short and very steep)
        result = classify_climb(1.0, 130)
        assert result.category == "Cat 4"

    def test_classification_fields(self):
        """Test that all classification fields are populated."""
        result = classify_climb(10.0, 500)
        assert result.category is not None
        assert result.avg_pct is not None
        assert result.base is not None
        assert result.bonus_applied is not None


class TestCategoryHelpers:
    """Tests for category helper functions."""

    def test_get_category_color(self):
        """Test color retrieval for categories."""
        assert get_category_color("HC") == "#D04972"
        assert get_category_color("Cat 1") == "#C15A85"
        assert get_category_color("Cat 4") == "#5594D7"
        assert get_category_color("Unclassified") == "#66B6E5"

    def test_get_category_description(self):
        """Test description retrieval."""
        desc = get_category_description("HC")
        assert "Hors Catégorie" in desc

    def test_get_category_rank(self):
        """Test category ranking."""
        assert get_category_rank("Unclassified") == 0
        assert get_category_rank("Cat 4") == 1
        assert get_category_rank("Cat 3") == 2
        assert get_category_rank("Cat 2") == 3
        assert get_category_rank("Cat 1") == 4
        assert get_category_rank("HC") == 5


class TestRealWorldClimbs:
    """Tests based on famous real-world climbs."""

    def test_alpe_dhuez(self):
        """Test Alpe d'Huez classification (13.8km, 1120m, 8.1%)."""
        result = classify_climb(13.8, 1120)
        # Should be at least Cat 1, possibly HC
        assert get_category_rank(result.category) >= 4

    def test_mont_ventoux(self):
        """Test Mont Ventoux classification (21.5km, 1617m, 7.5%)."""
        result = classify_climb(21.5, 1617)
        assert result.category == "HC"

    def test_col_du_tourmalet(self):
        """Test Col du Tourmalet classification (17.2km, 1268m, 7.4%)."""
        result = classify_climb(17.2, 1268)
        assert result.category == "HC"

    def test_lacets_de_montvernier(self):
        """Test Lacets de Montvernier (3.4km, 482m, 14%)."""
        result = classify_climb(3.4, 482)
        # Short but very steep
        assert get_category_rank(result.category) >= 2
