"""
Advanced climb detection with local min/max, trimming, and merging.

This module provides sophisticated climb detection that:
- Identifies local minima and maxima in elevation profiles
- Handles "falsopiano" (false flat) sections
- Trims climb starts/ends to true uphill sections
- Merges climbs separated by small drops
- Classifies climbs using professional categorization
"""

from dataclasses import dataclass, field
from typing import Optional
import math

from .climb_classifier import classify_climb, Category


@dataclass
class ClimbData:
    """Data structure for a detected climb."""
    start_index: int
    end_index: int
    start_dist: float  # meters
    end_dist: float  # meters
    start_elev: float  # meters
    end_elev: float  # meters
    gain: float  # meters
    avg_gradient: float  # percent
    category: Optional[Category] = None
    classification: Optional[dict] = None
    estimated_times: Optional[dict[str, float]] = None

    @property
    def length_m(self) -> float:
        """Length of the climb in meters."""
        return self.end_dist - self.start_dist

    @property
    def length_km(self) -> float:
        """Length of the climb in kilometers."""
        return self.length_m / 1000


def gaussian_kernel(sigma: float) -> list[float]:
    """Generate a Gaussian kernel for smoothing."""
    size = int(math.ceil(sigma * 3)) * 2 + 1
    kernel = []
    total = 0.0

    for i in range(size):
        x = i - size // 2
        value = math.exp(-(x * x) / (2 * sigma * sigma))
        kernel.append(value)
        total += value

    return [k / total for k in kernel]


def gaussian_filter(data: list[float], sigma: float) -> list[float]:
    """Apply Gaussian smoothing to data."""
    if len(data) < 3:
        return list(data)

    kernel = gaussian_kernel(sigma)
    half_size = len(kernel) // 2
    filtered = []

    for i in range(len(data)):
        value = 0.0
        weight_sum = 0.0

        for j, k in enumerate(kernel):
            idx = i + j - half_size
            if 0 <= idx < len(data):
                value += data[idx] * k
                weight_sum += k

        filtered.append(value / weight_sum if weight_sum > 0 else data[i])

    return filtered


def savgol_filter(data: list[float], window_length: int, polyorder: int = 2) -> list[float]:
    """
    Simplified Savitzky-Golay filter (moving average approximation).

    For full polynomial fitting, scipy.signal.savgol_filter is recommended.
    """
    if len(data) < window_length:
        return list(data)

    result = []
    half_window = window_length // 2

    for i in range(len(data)):
        start = max(0, i - half_window)
        end = min(len(data), i + half_window + 1)
        result.append(sum(data[start:end]) / (end - start))

    return result


def smooth_elevation_advanced(
    elevation_profile: list[tuple[float, float]],
    sigma: float = 8.0,
    window_length: int = 50,
    polyorder: int = 8,
) -> list[tuple[float, float]]:
    """
    Apply advanced smoothing to elevation profile.

    Uses a combination of Savitzky-Golay and Gaussian filtering
    to reduce noise while preserving meaningful features.

    Args:
        elevation_profile: List of (distance, elevation) tuples
        sigma: Gaussian filter sigma
        window_length: Savitzky-Golay window length
        polyorder: Savitzky-Golay polynomial order (unused in simplified version)

    Returns:
        Smoothed elevation profile
    """
    if len(elevation_profile) < window_length:
        return list(elevation_profile)

    distances = [p[0] for p in elevation_profile]
    elevations = [p[1] for p in elevation_profile]

    # Apply Savitzky-Golay filter first
    sg_smoothed = savgol_filter(elevations, window_length, polyorder)

    # Then apply Gaussian filter twice
    smoothed = gaussian_filter(sg_smoothed, sigma)
    smoothed = gaussian_filter(smoothed, sigma)

    return [(d, e) for d, e in zip(distances, smoothed)]


def is_local_min(
    points: list[tuple[float, float]],
    index: int,
    neighbor_count: int = 10,
    dip_threshold: float = 10.0,
) -> bool:
    """
    Check if a point is a local minimum.

    A point is a local minimum if it's lower than all neighbors
    and the dip is significant enough.
    """
    if index < 0 or index >= len(points):
        return False

    elevation = points[index][1]
    left_idx = max(0, index - neighbor_count)
    right_idx = min(len(points), index + neighbor_count + 1)

    max_neighbor = max(points[j][1] for j in range(left_idx, right_idx))

    if elevation > max_neighbor:
        return False
    if max_neighbor - elevation < dip_threshold:
        return False

    return True


def is_local_max(
    points: list[tuple[float, float]],
    index: int,
    neighbor_count: int = 10,
) -> bool:
    """Check if a point is a local maximum."""
    if index < 0 or index >= len(points):
        return False

    elevation = points[index][1]
    left_idx = max(0, index - neighbor_count)
    right_idx = min(len(points), index + neighbor_count + 1)

    for j in range(left_idx, right_idx):
        if points[j][1] > elevation:
            return False

    return True


def is_falsopiano(
    points: list[tuple[float, float]],
    index: int,
    neighbor_count: int = 10,
    slope_threshold: float = 0.5,
) -> bool:
    """
    Check if a point is in a "falsopiano" (false flat) section.

    A falsopiano is a relatively flat section where elevation
    changes are minimal.
    """
    if index < 0 or index >= len(points):
        return False

    elevation = points[index][1]
    left_idx = max(0, index - neighbor_count)
    right_idx = min(len(points), index + neighbor_count + 1)

    for j in range(left_idx, right_idx):
        if abs(points[j][1] - elevation) > slope_threshold:
            return False

    return True


def find_index_for_distance(
    points: list[tuple[float, float]],
    start_index: int,
    target_distance: float,
) -> Optional[int]:
    """Find the first index where distance >= target_distance."""
    for k in range(start_index, len(points)):
        if points[k][0] >= target_distance:
            return k
    return None


def average_slope(
    points: list[tuple[float, float]],
    index1: int,
    index2: int,
) -> float:
    """Calculate average slope between two points in percent."""
    dist1, elev1 = points[index1]
    dist2, elev2 = points[index2]
    dist_diff = dist2 - dist1

    if dist_diff <= 0:
        return 0.0

    return ((elev2 - elev1) / dist_diff) * 100


def trim_climb_start(
    points: list[tuple[float, float]],
    start_index: int,
    end_index: int,
    min_slope: float = 3.0,
    trim_distance: float = 150.0,
) -> Optional[int]:
    """
    Trim the start of a climb to where it truly begins ascending.

    Finds the first point where the next `trim_distance` meters
    has at least `min_slope` gradient.
    """
    i = start_index
    if i >= end_index:
        return None

    # Skip initial descent
    while i < end_index and i + 1 < len(points) and points[i + 1][1] < points[i][1]:
        i += 1

    # Find where slope becomes significant
    while i < end_index:
        distance_i = points[i][0]
        i2 = find_index_for_distance(points, i, distance_i + trim_distance)

        if i2 is None or i2 >= end_index:
            return None

        slope = average_slope(points, i, i2)
        if slope >= min_slope:
            return i

        i += 1

    return None


def trim_climb_end(
    points: list[tuple[float, float]],
    start_index: int,
    end_index: int,
    min_slope: float = 3.0,
    trim_distance: float = 150.0,
) -> Optional[int]:
    """
    Trim the end of a climb to where it truly stops ascending.

    Finds the last point where the previous `trim_distance` meters
    has at least `min_slope` gradient.
    """
    j = end_index
    if start_index >= j:
        return None

    # Skip final descent
    while j > start_index and j - 1 >= 0 and points[j - 1][1] > points[j][1]:
        j -= 1

    # Find where slope becomes significant
    while j > start_index:
        distance_j = points[j][0]
        target_distance = distance_j - trim_distance
        j2 = find_index_for_distance(points, start_index, target_distance)

        if j2 is None or j2 <= start_index:
            return None

        slope = average_slope(points, j2, j)
        if slope >= min_slope:
            return j

        j -= 1

    return None


def detect_climbs_advanced(
    elevation_profile: list[tuple[float, float]],
    min_gain: float = 30.0,
    neighbor_count: int = 3,
    dip_threshold: float = 10.0,
    merge_dip_threshold: float = 15.0,
) -> list[ClimbData]:
    """
    Detect climbs using advanced local min/max analysis.

    This algorithm:
    1. Finds local minima and maxima in the elevation profile
    2. Pairs minima with subsequent maxima to identify potential climbs
    3. Trims climb boundaries to true uphill sections
    4. Classifies climbs using professional categorization
    5. Merges nearby climbs if the drop between them is small

    Args:
        elevation_profile: List of (distance_m, elevation_m) tuples
        min_gain: Minimum elevation gain to qualify as a climb (meters)
        neighbor_count: Points to check for local min/max detection
        dip_threshold: Minimum dip depth for local minimum (meters)
        merge_dip_threshold: Maximum drop between climbs to merge (meters)

    Returns:
        List of detected climbs with classification
    """
    n = len(elevation_profile)
    if n < 3:
        return []

    # Find local minima and maxima
    local_mins: list[int] = []
    local_maxs: list[int] = []

    for idx in range(n):
        if is_local_min(elevation_profile, idx, neighbor_count, dip_threshold):
            local_mins.append(idx)
        elif is_falsopiano(elevation_profile, idx, neighbor_count):
            local_mins.append(idx)

        if is_local_max(elevation_profile, idx, neighbor_count):
            local_maxs.append(idx)

    local_mins.sort()
    local_maxs.sort()

    climbs: list[ClimbData] = []
    max_idx_pointer = 0
    last_end_index = -1

    for i in local_mins:
        if i <= last_end_index:
            continue

        dist_i, elev_i = elevation_profile[i]

        # Find next local max
        while max_idx_pointer < len(local_maxs) and local_maxs[max_idx_pointer] <= i:
            max_idx_pointer += 1

        if max_idx_pointer >= len(local_maxs):
            continue

        j = local_maxs[max_idx_pointer]
        dist_j, elev_j = elevation_profile[j]

        if j > i and dist_j > dist_i and elev_j > elev_i:
            dist_diff = dist_j - dist_i
            elev_diff = elev_j - elev_i
            overall_slope = (elev_diff / dist_diff) * 100 if dist_diff > 0 else 0

            # Skip if overall slope is too low
            if overall_slope < 2:
                continue

            # Trim climb boundaries
            new_i = trim_climb_start(elevation_profile, i, j, 3.0, 150.0)
            if new_i is None:
                continue

            new_j = trim_climb_end(elevation_profile, new_i, j, 3.0, 150.0)
            if new_j is None:
                continue

            new_dist_i, new_elev_i = elevation_profile[new_i]
            final_dist_j, final_elev_j = elevation_profile[new_j]
            gain = final_elev_j - new_elev_i

            if gain < min_gain:
                continue

            horizontal_dist = final_dist_j - new_dist_i
            avg_gradient = (gain / horizontal_dist) * 100 if horizontal_dist > 0 else 0

            # Classify the climb
            length_km = horizontal_dist / 1000
            classification = classify_climb(length_km, gain)

            climbs.append(ClimbData(
                start_index=new_i,
                end_index=new_j,
                start_dist=new_dist_i,
                end_dist=final_dist_j,
                start_elev=new_elev_i,
                end_elev=final_elev_j,
                gain=gain,
                avg_gradient=avg_gradient,
                category=classification.category,
                classification={
                    "category": classification.category,
                    "avg_pct": classification.avg_pct,
                    "base": classification.base,
                    "bonus_applied": classification.bonus_applied,
                },
            ))

            last_end_index = new_j

    # Merge climbs if drop between them is small
    climbs.sort(key=lambda c: c.start_index)

    merged_climbs: list[ClimbData] = []
    for climb in climbs:
        if not merged_climbs:
            merged_climbs.append(climb)
            continue

        prev = merged_climbs[-1]
        drop_between = prev.end_elev - climb.start_elev

        if drop_between < merge_dip_threshold:
            # Merge climbs
            prev.end_index = climb.end_index
            prev.end_dist = climb.end_dist
            prev.end_elev = climb.end_elev
            prev.gain = prev.end_elev - prev.start_elev

            dist_diff = prev.end_dist - prev.start_dist
            prev.avg_gradient = (prev.gain / dist_diff) * 100 if dist_diff > 0 else 0

            # Reclassify merged climb
            length_km = dist_diff / 1000
            classification = classify_climb(length_km, prev.gain)
            prev.category = classification.category
            prev.classification = {
                "category": classification.category,
                "avg_pct": classification.avg_pct,
                "base": classification.base,
                "bonus_applied": classification.bonus_applied,
            }
        else:
            merged_climbs.append(climb)

    return merged_climbs


def remove_elevation_outliers(
    profile: list[tuple[float, float]],
    max_gradient: float = 15.0,
) -> list[tuple[float, float]]:
    """
    Remove elevation outliers (e.g., GPS errors in tunnels).

    Detects and interpolates over sudden spikes in elevation data.
    """
    if len(profile) < 5:
        return list(profile)

    result = list(profile)

    for _ in range(3):  # Multiple passes
        temp: list[tuple[float, float]] = [result[0]]

        for i in range(1, len(result) - 1):
            dist, elev = result[i]
            prev_dist, prev_elev = result[i - 1]
            next_dist, next_elev = result[i + 1]

            dist_delta1 = dist - prev_dist
            dist_delta2 = next_dist - dist

            if dist_delta1 <= 0 or dist_delta2 <= 0:
                temp.append((dist, elev))
                continue

            grad1 = abs((elev - prev_elev) / dist_delta1 * 100)
            grad2 = abs((next_elev - elev) / dist_delta2 * 100)

            elev_jump = abs(elev - prev_elev)
            is_spike = (
                (grad1 > max_gradient and grad2 > max_gradient and
                 ((elev > prev_elev and elev > next_elev) or
                  (elev < prev_elev and elev < next_elev))) or
                (elev_jump > 10 and abs(next_elev - elev) > 10 and
                 abs(elev - (prev_elev + next_elev) / 2) > 8)
            )

            if is_spike:
                # Interpolate
                if i >= 2 and i < len(result) - 2:
                    e1 = result[i - 2][1]
                    e2 = prev_elev
                    e3 = next_elev
                    e4 = result[i + 2][1]
                    interp_elev = (e1 + 2 * e2 + 2 * e3 + e4) / 6
                else:
                    interp_elev = prev_elev + (next_elev - prev_elev) * (dist - prev_dist) / (next_dist - prev_dist)
                temp.append((dist, interp_elev))
            else:
                temp.append((dist, elev))

        temp.append(result[-1])
        result = temp

    return result
