"""
Altimetry calculations for elevation data from TCX files.

This module provides functions to analyze elevation data including:
- Elevation gain/loss calculations
- Elevation smoothing to reduce GPS noise
- Altimetry profile generation
- Statistical analysis of elevation data
"""

from dataclasses import dataclass
from typing import Optional, Sequence

import numpy as np


@dataclass
class AltimetryStats:
    """Statistics for elevation data."""

    elevation_gain: float
    elevation_loss: float
    min_elevation: float
    max_elevation: float
    start_elevation: float
    end_elevation: float
    net_elevation_change: float
    total_elevation_change: float
    avg_elevation: float
    elevation_range: float

    @classmethod
    def from_altitudes(
        cls,
        altitudes: Sequence[float],
        threshold: float = 0.0,
        smoothing: bool = True,
        window_size: int = 5,
    ) -> "AltimetryStats":
        """
        Calculate altimetry statistics from a sequence of altitudes.

        Args:
            altitudes: Sequence of altitude values in meters
            threshold: Minimum elevation change to count (filters noise)
            smoothing: Whether to smooth data before calculations
            window_size: Window size for smoothing

        Returns:
            AltimetryStats object with all calculated statistics
        """
        if not altitudes:
            return cls(
                elevation_gain=0.0,
                elevation_loss=0.0,
                min_elevation=0.0,
                max_elevation=0.0,
                start_elevation=0.0,
                end_elevation=0.0,
                net_elevation_change=0.0,
                total_elevation_change=0.0,
                avg_elevation=0.0,
                elevation_range=0.0,
            )

        alt_array = np.array(altitudes, dtype=float)

        if smoothing and len(alt_array) >= window_size:
            smoothed = smooth_elevation_data(alt_array, window_size=window_size)
        else:
            smoothed = alt_array

        gain = calculate_elevation_gain(smoothed, threshold=threshold)
        loss = calculate_elevation_loss(smoothed, threshold=threshold)

        return cls(
            elevation_gain=gain,
            elevation_loss=loss,
            min_elevation=float(np.min(alt_array)),
            max_elevation=float(np.max(alt_array)),
            start_elevation=float(alt_array[0]),
            end_elevation=float(alt_array[-1]),
            net_elevation_change=float(alt_array[-1] - alt_array[0]),
            total_elevation_change=gain + loss,
            avg_elevation=float(np.mean(alt_array)),
            elevation_range=float(np.max(alt_array) - np.min(alt_array)),
        )


def calculate_elevation_gain(
    altitudes: Sequence[float],
    threshold: float = 0.0,
) -> float:
    """
    Calculate total elevation gain from a sequence of altitudes.

    Elevation gain is the sum of all positive elevation changes.

    Args:
        altitudes: Sequence of altitude values in meters
        threshold: Minimum elevation change to count (filters small variations/noise)

    Returns:
        Total elevation gain in meters
    """
    if len(altitudes) < 2:
        return 0.0

    alt_array = np.array(altitudes, dtype=float)
    diffs = np.diff(alt_array)

    # Apply threshold filter
    gains = diffs[diffs > threshold]

    return float(np.sum(gains)) if len(gains) > 0 else 0.0


def calculate_elevation_loss(
    altitudes: Sequence[float],
    threshold: float = 0.0,
) -> float:
    """
    Calculate total elevation loss from a sequence of altitudes.

    Elevation loss is the sum of all negative elevation changes (returned as positive).

    Args:
        altitudes: Sequence of altitude values in meters
        threshold: Minimum elevation change to count (filters small variations/noise)

    Returns:
        Total elevation loss in meters (positive value)
    """
    if len(altitudes) < 2:
        return 0.0

    alt_array = np.array(altitudes, dtype=float)
    diffs = np.diff(alt_array)

    # Apply threshold filter (for losses, check if diff is less than -threshold)
    losses = diffs[diffs < -threshold]

    return float(np.abs(np.sum(losses))) if len(losses) > 0 else 0.0


def calculate_total_elevation_change(
    altitudes: Sequence[float],
    threshold: float = 0.0,
) -> tuple[float, float]:
    """
    Calculate both elevation gain and loss.

    Args:
        altitudes: Sequence of altitude values in meters
        threshold: Minimum elevation change to count

    Returns:
        Tuple of (elevation_gain, elevation_loss) in meters
    """
    gain = calculate_elevation_gain(altitudes, threshold)
    loss = calculate_elevation_loss(altitudes, threshold)
    return gain, loss


def smooth_elevation_data(
    altitudes: Sequence[float],
    window_size: int = 5,
    method: str = "moving_average",
) -> np.ndarray:
    """
    Smooth elevation data to reduce GPS noise.

    GPS altitude data is notoriously noisy. This function applies smoothing
    to get more realistic elevation profiles.

    Args:
        altitudes: Sequence of altitude values in meters
        window_size: Size of the smoothing window (must be odd for some methods)
        method: Smoothing method - 'moving_average', 'gaussian', or 'savgol'

    Returns:
        Smoothed altitude array
    """
    alt_array = np.array(altitudes, dtype=float)

    if len(alt_array) < window_size:
        return alt_array

    if method == "moving_average":
        # Simple moving average
        kernel = np.ones(window_size) / window_size
        # Use 'same' mode to keep array length, with edge handling
        smoothed = np.convolve(alt_array, kernel, mode="same")

        # Fix edge effects by using original values at edges
        half_window = window_size // 2
        smoothed[:half_window] = alt_array[:half_window]
        smoothed[-half_window:] = alt_array[-half_window:]

        return smoothed

    elif method == "gaussian":
        # Gaussian smoothing
        try:
            from scipy.ndimage import gaussian_filter1d

            sigma = window_size / 4  # Approximate relationship
            return gaussian_filter1d(alt_array, sigma=sigma)
        except ImportError:
            # Fall back to moving average if scipy not available
            return smooth_elevation_data(altitudes, window_size, method="moving_average")

    elif method == "savgol":
        # Savitzky-Golay filter (best for preserving peaks)
        try:
            from scipy.signal import savgol_filter

            # Window must be odd
            if window_size % 2 == 0:
                window_size += 1
            # Polynomial order (typically 2 or 3)
            polyorder = min(3, window_size - 1)
            return savgol_filter(alt_array, window_size, polyorder)
        except ImportError:
            return smooth_elevation_data(altitudes, window_size, method="moving_average")

    else:
        raise ValueError(f"Unknown smoothing method: {method}")


def get_altimetry_profile(
    altitudes: Sequence[float],
    distances: Optional[Sequence[float]] = None,
    smooth: bool = True,
    window_size: int = 5,
) -> dict:
    """
    Generate a complete altimetry profile from elevation data.

    Args:
        altitudes: Sequence of altitude values in meters
        distances: Optional sequence of cumulative distances in meters
        smooth: Whether to smooth the elevation data
        window_size: Window size for smoothing

    Returns:
        Dictionary containing:
        - altitudes: Original altitude values
        - smoothed_altitudes: Smoothed altitude values (if smooth=True)
        - distances: Distance values (or indices if not provided)
        - stats: AltimetryStats object
        - grades: Gradient percentages between points
    """
    if not altitudes:
        return {
            "altitudes": [],
            "smoothed_altitudes": [],
            "distances": [],
            "stats": None,
            "grades": [],
        }

    alt_array = np.array(altitudes, dtype=float)

    if smooth and len(alt_array) >= window_size:
        smoothed = smooth_elevation_data(alt_array, window_size=window_size)
    else:
        smoothed = alt_array

    # Use provided distances or create index-based distances
    if distances is not None:
        dist_array = np.array(distances, dtype=float)
    else:
        dist_array = np.arange(len(alt_array), dtype=float)

    # Calculate grades (gradient percentages)
    grades = calculate_grades(smoothed, dist_array)

    # Calculate statistics
    stats = AltimetryStats.from_altitudes(altitudes, smoothing=smooth, window_size=window_size)

    return {
        "altitudes": alt_array.tolist(),
        "smoothed_altitudes": smoothed.tolist(),
        "distances": dist_array.tolist(),
        "stats": stats,
        "grades": grades.tolist(),
    }


def calculate_grades(
    altitudes: Sequence[float],
    distances: Sequence[float],
) -> np.ndarray:
    """
    Calculate grade (gradient) percentages between consecutive points.

    Grade = (elevation change / horizontal distance) * 100

    Args:
        altitudes: Sequence of altitude values in meters
        distances: Sequence of cumulative distance values in meters

    Returns:
        Array of grade percentages (length = len(altitudes) - 1)
    """
    alt_array = np.array(altitudes, dtype=float)
    dist_array = np.array(distances, dtype=float)

    if len(alt_array) < 2:
        return np.array([])

    elevation_diffs = np.diff(alt_array)
    distance_diffs = np.diff(dist_array)

    # Avoid division by zero
    with np.errstate(divide="ignore", invalid="ignore"):
        grades = np.where(
            distance_diffs > 0,
            (elevation_diffs / distance_diffs) * 100,
            0.0,
        )

    return grades


def detect_climbs(
    altitudes: Sequence[float],
    distances: Sequence[float],
    min_gain: float = 50.0,
    min_grade: float = 3.0,
) -> list[dict]:
    """
    Detect significant climbs in the elevation data.

    A climb is defined as a sustained uphill section with minimum
    elevation gain and average grade.

    Args:
        altitudes: Sequence of altitude values in meters
        distances: Sequence of cumulative distance values in meters
        min_gain: Minimum elevation gain to qualify as a climb (meters)
        min_grade: Minimum average grade to qualify as a climb (percent)

    Returns:
        List of dictionaries describing each climb with:
        - start_index, end_index
        - start_distance, end_distance
        - start_elevation, end_elevation
        - elevation_gain
        - distance
        - average_grade
    """
    if len(altitudes) < 2:
        return []

    alt_array = np.array(altitudes, dtype=float)
    dist_array = np.array(distances, dtype=float)

    # Smooth data first
    smoothed = smooth_elevation_data(alt_array, window_size=5)

    climbs = []
    i = 0

    while i < len(smoothed) - 1:
        # Look for start of uphill
        if smoothed[i + 1] > smoothed[i]:
            start_idx = i
            end_idx = i + 1

            # Continue while going uphill (allowing small dips)
            accumulated_gain = smoothed[end_idx] - smoothed[start_idx]
            local_min = smoothed[start_idx]

            while end_idx < len(smoothed) - 1:
                next_alt = smoothed[end_idx + 1]
                current_alt = smoothed[end_idx]

                # Track local minimum for calculating true gain
                if current_alt < local_min:
                    local_min = current_alt

                # Allow small descents (up to 10m) within a climb
                if next_alt < current_alt - 10:
                    break

                end_idx += 1
                accumulated_gain = smoothed[end_idx] - local_min

            # Check if this qualifies as a significant climb
            total_gain = smoothed[end_idx] - smoothed[start_idx]
            total_distance = dist_array[end_idx] - dist_array[start_idx]

            if total_distance > 0:
                avg_grade = (total_gain / total_distance) * 100

                if total_gain >= min_gain and avg_grade >= min_grade:
                    climbs.append({
                        "start_index": start_idx,
                        "end_index": end_idx,
                        "start_distance": float(dist_array[start_idx]),
                        "end_distance": float(dist_array[end_idx]),
                        "start_elevation": float(alt_array[start_idx]),
                        "end_elevation": float(alt_array[end_idx]),
                        "elevation_gain": float(total_gain),
                        "distance": float(total_distance),
                        "average_grade": float(avg_grade),
                    })

            i = end_idx
        else:
            i += 1

    return climbs


def detect_descents(
    altitudes: Sequence[float],
    distances: Sequence[float],
    min_loss: float = 50.0,
    min_grade: float = 3.0,
) -> list[dict]:
    """
    Detect significant descents in the elevation data.

    Args:
        altitudes: Sequence of altitude values in meters
        distances: Sequence of cumulative distance values in meters
        min_loss: Minimum elevation loss to qualify as a descent (meters)
        min_grade: Minimum average grade to qualify as a descent (percent)

    Returns:
        List of dictionaries describing each descent (similar format to climbs)
    """
    # Invert altitudes and use climb detection
    inverted = [-a for a in altitudes]
    climbs = detect_climbs(inverted, distances, min_gain=min_loss, min_grade=min_grade)

    # Convert back to descent format
    descents = []
    for climb in climbs:
        descents.append({
            "start_index": climb["start_index"],
            "end_index": climb["end_index"],
            "start_distance": climb["start_distance"],
            "end_distance": climb["end_distance"],
            "start_elevation": -climb["end_elevation"],  # Swap and invert
            "end_elevation": -climb["start_elevation"],
            "elevation_loss": climb["elevation_gain"],
            "distance": climb["distance"],
            "average_grade": climb["average_grade"],
        })

    return descents
