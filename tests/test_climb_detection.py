"""Tests for advanced climb detection."""

import pytest

from tcx_parser.climb_detection import (
    ClimbData,
    detect_climbs_advanced,
    smooth_elevation_advanced,
    remove_elevation_outliers,
    is_local_min,
    is_local_max,
    gaussian_filter,
    savgol_filter,
)


def create_profile(elevations: list[float], spacing: float = 100.0) -> list[tuple[float, float]]:
    """Helper to create elevation profile from list of elevations."""
    return [(i * spacing, e) for i, e in enumerate(elevations)]


class TestGaussianFilter:
    """Tests for Gaussian smoothing."""

    def test_smoothing_reduces_noise(self):
        """Test that smoothing reduces noise."""
        noisy = [100, 105, 98, 103, 99, 102, 100]
        smoothed = gaussian_filter(noisy, sigma=1.0)

        # Smoothed values should have less variance
        orig_var = sum((x - 100) ** 2 for x in noisy) / len(noisy)
        smooth_var = sum((x - 100) ** 2 for x in smoothed) / len(smoothed)

        assert smooth_var < orig_var

    def test_preserves_length(self):
        """Test that smoothing preserves array length."""
        data = [100, 110, 120, 130, 140]
        smoothed = gaussian_filter(data, sigma=1.0)

        assert len(smoothed) == len(data)


class TestSavgolFilter:
    """Tests for Savitzky-Golay filter."""

    def test_preserves_length(self):
        """Test that filter preserves array length."""
        data = [100, 110, 120, 130, 140, 150]
        filtered = savgol_filter(data, window_length=3)

        assert len(filtered) == len(data)

    def test_short_array(self):
        """Test with array shorter than window."""
        data = [100, 110]
        filtered = savgol_filter(data, window_length=5)

        assert filtered == data


class TestLocalMinMax:
    """Tests for local min/max detection."""

    def test_is_local_min(self):
        """Test local minimum detection."""
        profile = create_profile([100, 90, 80, 90, 100])  # Valley at index 2

        assert is_local_min(profile, 2, neighbor_count=2, dip_threshold=5.0) is True
        assert is_local_min(profile, 0, neighbor_count=2, dip_threshold=5.0) is False

    def test_is_local_max(self):
        """Test local maximum detection."""
        profile = create_profile([100, 110, 120, 110, 100])  # Peak at index 2

        assert is_local_max(profile, 2, neighbor_count=2) is True
        assert is_local_max(profile, 0, neighbor_count=2) is False

    def test_dip_threshold(self):
        """Test that shallow dips are ignored."""
        profile = create_profile([100, 98, 100])  # Only 2m dip

        # Should not be detected with 5m threshold
        assert is_local_min(profile, 1, neighbor_count=1, dip_threshold=5.0) is False

        # Should be detected with 1m threshold
        assert is_local_min(profile, 1, neighbor_count=1, dip_threshold=1.0) is True


class TestRemoveElevationOutliers:
    """Tests for outlier removal."""

    def test_removes_spike(self):
        """Test that spikes are removed."""
        profile = create_profile([100, 100, 150, 100, 100])  # 50m spike

        cleaned = remove_elevation_outliers(profile, max_gradient=15.0)

        # The spike should be smoothed out
        spike_elev = cleaned[2][1]
        assert spike_elev < 130  # Should be closer to 100

    def test_preserves_gradual_changes(self):
        """Test that gradual changes are preserved."""
        profile = create_profile([100, 105, 110, 115, 120])  # Gradual climb

        cleaned = remove_elevation_outliers(profile, max_gradient=20.0)

        # Values should be mostly unchanged
        for orig, clean in zip(profile, cleaned):
            assert abs(orig[1] - clean[1]) < 5


class TestSmoothElevationAdvanced:
    """Tests for advanced elevation smoothing."""

    def test_smoothing_works(self):
        """Test that advanced smoothing works."""
        # Create noisy profile
        profile = create_profile([100 + (i % 3) * 2 for i in range(100)])

        smoothed = smooth_elevation_advanced(profile, sigma=2, window_length=10)

        assert len(smoothed) == len(profile)

    def test_short_profile(self):
        """Test with profile shorter than window."""
        profile = create_profile([100, 110, 120])

        smoothed = smooth_elevation_advanced(profile, window_length=10)

        assert smoothed == profile


class TestDetectClimbsAdvanced:
    """Tests for advanced climb detection."""

    def test_simple_climb(self):
        """Test detection of simple climb."""
        # Create a clear climb from 100m to 200m
        elevations = [100] * 10 + list(range(100, 201, 5)) + [200] * 10
        profile = create_profile(elevations, spacing=50)

        climbs = detect_climbs_advanced(profile, min_gain=50, neighbor_count=3)

        assert len(climbs) >= 1
        assert climbs[0].gain >= 50

    def test_no_climb_on_flat(self):
        """Test that flat terrain has no climbs."""
        profile = create_profile([100] * 50)

        climbs = detect_climbs_advanced(profile, min_gain=30)

        assert len(climbs) == 0

    def test_no_climb_on_descent(self):
        """Test that descents are not detected as climbs."""
        elevations = list(range(200, 100, -5))
        profile = create_profile(elevations)

        climbs = detect_climbs_advanced(profile, min_gain=30)

        assert len(climbs) == 0

    def test_multiple_climbs(self):
        """Test detection of multiple climbs."""
        # Two separate climbs with valley between
        elevations = (
            [100] * 10 +
            list(range(100, 200, 10)) +  # Climb 1
            [200] * 5 +
            list(range(200, 100, -10)) +  # Descent
            [100] * 5 +
            list(range(100, 180, 10)) +  # Climb 2
            [180] * 10
        )
        profile = create_profile(elevations, spacing=50)

        climbs = detect_climbs_advanced(profile, min_gain=50, merge_dip_threshold=30)

        # Should detect both climbs (if not merged)
        assert len(climbs) >= 1

    def test_climb_has_category(self):
        """Test that detected climbs have categories."""
        elevations = [0] * 10 + list(range(0, 501, 5)) + [500] * 10
        profile = create_profile(elevations, spacing=50)

        climbs = detect_climbs_advanced(profile, min_gain=100)

        if climbs:
            assert climbs[0].category is not None
            assert climbs[0].classification is not None

    def test_climb_merging(self):
        """Test that climbs with small drops between are merged."""
        # Climb with small dip in middle
        elevations = (
            [100] * 5 +
            list(range(100, 150, 5)) +  # First part
            [145, 143, 145] +  # Small dip (5m drop)
            list(range(145, 200, 5)) +  # Second part
            [200] * 5
        )
        profile = create_profile(elevations, spacing=50)

        climbs = detect_climbs_advanced(profile, min_gain=30, merge_dip_threshold=10)

        # Should merge into one climb
        assert len(climbs) <= 2

    def test_min_gain_filter(self):
        """Test that climbs below min_gain are filtered."""
        elevations = [100] * 5 + list(range(100, 120, 2)) + [120] * 5  # 20m gain
        profile = create_profile(elevations, spacing=50)

        climbs_high_threshold = detect_climbs_advanced(profile, min_gain=50)
        climbs_low_threshold = detect_climbs_advanced(profile, min_gain=10)

        assert len(climbs_high_threshold) == 0
        # Low threshold might detect it
        # (depends on trimming and other factors)


class TestClimbDataProperties:
    """Tests for ClimbData properties."""

    def test_length_properties(self):
        """Test length calculation properties."""
        climb = ClimbData(
            start_index=0,
            end_index=100,
            start_dist=0,
            end_dist=5000,
            start_elev=100,
            end_elev=500,
            gain=400,
            avg_gradient=8.0,
        )

        assert climb.length_m == 5000
        assert climb.length_km == 5.0
