"""Tests for altimetry calculations."""

import pytest
import numpy as np

from tcx_parser.altimetry import (
    calculate_elevation_gain,
    calculate_elevation_loss,
    calculate_total_elevation_change,
    smooth_elevation_data,
    get_altimetry_profile,
    calculate_grades,
    detect_climbs,
    detect_descents,
    AltimetryStats,
)


class TestElevationGain:
    """Tests for elevation gain calculation."""

    def test_simple_gain(self):
        """Test basic elevation gain calculation."""
        altitudes = [100, 110, 120, 130]
        gain = calculate_elevation_gain(altitudes)
        assert gain == pytest.approx(30.0)

    def test_no_gain(self):
        """Test with no elevation gain (all descending)."""
        altitudes = [130, 120, 110, 100]
        gain = calculate_elevation_gain(altitudes)
        assert gain == pytest.approx(0.0)

    def test_mixed_terrain(self):
        """Test with mixed uphill and downhill."""
        altitudes = [100, 150, 120, 180]  # +50, -30, +60 = 110 gain
        gain = calculate_elevation_gain(altitudes)
        assert gain == pytest.approx(110.0)

    def test_with_threshold(self):
        """Test elevation gain with threshold filter."""
        altitudes = [100, 101, 102, 110]  # +1, +1, +8 = 10 total
        gain_no_threshold = calculate_elevation_gain(altitudes, threshold=0)
        gain_with_threshold = calculate_elevation_gain(altitudes, threshold=2)

        assert gain_no_threshold == pytest.approx(10.0)
        assert gain_with_threshold == pytest.approx(8.0)

    def test_empty_list(self):
        """Test with empty altitude list."""
        assert calculate_elevation_gain([]) == 0.0

    def test_single_point(self):
        """Test with single altitude point."""
        assert calculate_elevation_gain([100]) == 0.0

    def test_flat_terrain(self):
        """Test with flat terrain (no change)."""
        altitudes = [100, 100, 100, 100]
        assert calculate_elevation_gain(altitudes) == 0.0


class TestElevationLoss:
    """Tests for elevation loss calculation."""

    def test_simple_loss(self):
        """Test basic elevation loss calculation."""
        altitudes = [130, 120, 110, 100]
        loss = calculate_elevation_loss(altitudes)
        assert loss == pytest.approx(30.0)

    def test_no_loss(self):
        """Test with no elevation loss (all ascending)."""
        altitudes = [100, 110, 120, 130]
        loss = calculate_elevation_loss(altitudes)
        assert loss == pytest.approx(0.0)

    def test_mixed_terrain(self):
        """Test with mixed uphill and downhill."""
        altitudes = [100, 150, 120, 180]  # -30 loss
        loss = calculate_elevation_loss(altitudes)
        assert loss == pytest.approx(30.0)

    def test_with_threshold(self):
        """Test elevation loss with threshold filter."""
        altitudes = [110, 109, 108, 100]  # -1, -1, -8 = 10 total
        loss_no_threshold = calculate_elevation_loss(altitudes, threshold=0)
        loss_with_threshold = calculate_elevation_loss(altitudes, threshold=2)

        assert loss_no_threshold == pytest.approx(10.0)
        assert loss_with_threshold == pytest.approx(8.0)


class TestTotalElevationChange:
    """Tests for combined elevation change calculation."""

    def test_total_change(self):
        """Test calculating both gain and loss."""
        altitudes = [100, 150, 120, 180, 160]  # +50, -30, +60, -20
        gain, loss = calculate_total_elevation_change(altitudes)

        assert gain == pytest.approx(110.0)
        assert loss == pytest.approx(50.0)


class TestSmoothElevationData:
    """Tests for elevation data smoothing."""

    def test_moving_average(self):
        """Test moving average smoothing."""
        altitudes = [100, 102, 98, 101, 99]
        smoothed = smooth_elevation_data(altitudes, window_size=3, method="moving_average")

        assert len(smoothed) == len(altitudes)
        # Smoothed values should be between min and max
        assert np.all(smoothed >= 98)
        assert np.all(smoothed <= 102)

    def test_short_array(self):
        """Test smoothing with array shorter than window."""
        altitudes = [100, 110]
        smoothed = smooth_elevation_data(altitudes, window_size=5)

        # Should return original array
        np.testing.assert_array_almost_equal(smoothed, altitudes)

    def test_invalid_method(self):
        """Test with invalid smoothing method."""
        with pytest.raises(ValueError):
            smooth_elevation_data([100, 110, 120], method="invalid")


class TestAltimetryStats:
    """Tests for AltimetryStats class."""

    def test_from_altitudes(self):
        """Test creating stats from altitudes."""
        altitudes = [100, 150, 120, 180, 160]
        stats = AltimetryStats.from_altitudes(altitudes, smoothing=False)

        assert stats.min_elevation == 100
        assert stats.max_elevation == 180
        assert stats.start_elevation == 100
        assert stats.end_elevation == 160
        assert stats.net_elevation_change == 60
        assert stats.elevation_range == 80
        assert stats.elevation_gain == pytest.approx(110.0)
        assert stats.elevation_loss == pytest.approx(50.0)
        assert stats.total_elevation_change == pytest.approx(160.0)

    def test_empty_altitudes(self):
        """Test stats with empty altitudes."""
        stats = AltimetryStats.from_altitudes([])

        assert stats.elevation_gain == 0.0
        assert stats.elevation_loss == 0.0
        assert stats.min_elevation == 0.0
        assert stats.max_elevation == 0.0


class TestAltimetryProfile:
    """Tests for altimetry profile generation."""

    def test_get_profile(self):
        """Test getting altimetry profile."""
        altitudes = [100, 120, 110, 130]
        distances = [0, 1000, 2000, 3000]

        profile = get_altimetry_profile(altitudes, distances, smooth=False)

        assert profile["altitudes"] == altitudes
        assert profile["distances"] == distances
        assert len(profile["grades"]) == 3
        assert profile["stats"] is not None

    def test_empty_profile(self):
        """Test profile with empty data."""
        profile = get_altimetry_profile([], [])

        assert profile["altitudes"] == []
        assert profile["stats"] is None


class TestCalculateGrades:
    """Tests for grade calculation."""

    def test_simple_grades(self):
        """Test basic grade calculation."""
        altitudes = [100, 110, 100]
        distances = [0, 100, 200]

        grades = calculate_grades(altitudes, distances)

        # +10m over 100m = 10%, -10m over 100m = -10%
        assert len(grades) == 2
        assert grades[0] == pytest.approx(10.0)
        assert grades[1] == pytest.approx(-10.0)

    def test_zero_distance(self):
        """Test grade with zero distance (should handle gracefully)."""
        altitudes = [100, 110]
        distances = [0, 0]  # Zero distance

        grades = calculate_grades(altitudes, distances)
        assert grades[0] == 0.0


class TestDetectClimbs:
    """Tests for climb detection."""

    def test_detect_climb(self):
        """Test detecting a significant climb."""
        # Create a clear climb: 0m to 100m over 1000m distance
        altitudes = list(range(0, 101, 10))  # 0, 10, 20, ..., 100
        distances = list(range(0, 1001, 100))  # 0, 100, 200, ..., 1000

        climbs = detect_climbs(altitudes, distances, min_gain=50, min_grade=5)

        assert len(climbs) >= 1
        assert climbs[0]["elevation_gain"] >= 50

    def test_no_climb(self):
        """Test with flat terrain."""
        altitudes = [100, 100, 100, 100]
        distances = [0, 100, 200, 300]

        climbs = detect_climbs(altitudes, distances, min_gain=50, min_grade=5)
        assert len(climbs) == 0

    def test_descent_not_climb(self):
        """Test that descents are not detected as climbs."""
        altitudes = [100, 80, 60, 40]
        distances = [0, 100, 200, 300]

        climbs = detect_climbs(altitudes, distances, min_gain=10, min_grade=2)
        assert len(climbs) == 0


class TestDetectDescents:
    """Tests for descent detection."""

    def test_detect_descent(self):
        """Test detecting a significant descent."""
        altitudes = [100, 90, 80, 70, 60, 50, 40, 30, 20, 10, 0]
        distances = list(range(0, 1001, 100))

        descents = detect_descents(altitudes, distances, min_loss=50, min_grade=5)

        assert len(descents) >= 1
        assert descents[0]["elevation_loss"] >= 50
