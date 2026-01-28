"""
High-level climb extraction API with smoothing, detection, and time estimation.

This module provides a simplified interface for:
- Extracting elevation profiles from TCX data
- Detecting climbs with advanced algorithms
- Estimating climb times at various power levels
- Complete route analysis
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Union

from .models import TCXData, Activity, Trackpoint
from .parser import TCXParser
from .climb_classifier import (
    classify_climb,
    Category,
    ClimbClassification,
    get_category_color,
    get_category_description,
    get_category_rank,
)
from .climb_detection import (
    ClimbData,
    detect_climbs_advanced,
    smooth_elevation_advanced,
    remove_elevation_outliers,
)
from .climb_time_solver import (
    ClimbInput,
    SolverSettings,
    ClimbTimesResult,
    estimate_climb_times,
    estimate_climb_time_at_power,
    format_time,
    calculate_vam,
)


@dataclass
class RouteData:
    """Complete route data extracted from activity."""
    elevation_profile: list[tuple[float, float]]  # (distance_m, elevation_m)
    coordinates: list[tuple[float, float]]  # (lat, lon)
    total_distance_m: float
    total_elevation_gain: float
    total_elevation_loss: float
    min_elevation: float
    max_elevation: float


@dataclass
class ClimbAnalysis:
    """Complete analysis of a detected climb."""
    climb: ClimbData
    category: Category
    classification: ClimbClassification
    estimated_times: Optional[dict[str, float]] = None
    color: str = ""
    description: str = ""

    def __post_init__(self):
        if not self.color:
            self.color = get_category_color(self.category)
        if not self.description:
            self.description = get_category_description(self.category)


@dataclass
class RouteAnalysis:
    """Complete route analysis with all detected climbs."""
    route_data: RouteData
    climbs: list[ClimbAnalysis] = field(default_factory=list)
    smoothed_profile: list[tuple[float, float]] = field(default_factory=list)

    @property
    def total_climbing(self) -> float:
        """Total elevation gain from all detected climbs."""
        return sum(c.climb.gain for c in self.climbs)

    @property
    def hardest_climb(self) -> Optional[ClimbAnalysis]:
        """The hardest climb by category."""
        if not self.climbs:
            return None
        return max(self.climbs, key=lambda c: get_category_rank(c.category))

    @property
    def longest_climb(self) -> Optional[ClimbAnalysis]:
        """The longest climb by distance."""
        if not self.climbs:
            return None
        return max(self.climbs, key=lambda c: c.climb.length_m)

    @property
    def steepest_climb(self) -> Optional[ClimbAnalysis]:
        """The steepest climb by average gradient."""
        if not self.climbs:
            return None
        return max(self.climbs, key=lambda c: c.climb.avg_gradient)


@dataclass
class RiderSettings:
    """Rider settings for time estimation."""
    ftp: float  # Functional Threshold Power in watts
    mass_kg: float = 75.0  # Total mass (rider + bike)
    cda: float = 0.3  # Drag coefficient * frontal area
    crr: float = 0.004  # Rolling resistance coefficient
    wind_ms: float = 0.0  # Headwind (positive = headwind)
    temperature_c: float = 20.0  # Temperature in Celsius
    altitude_m: float = 200.0  # Base altitude in meters


def extract_elevation_profile(activity: Activity) -> list[tuple[float, float]]:
    """
    Extract elevation profile from an activity.

    Args:
        activity: TCX Activity object

    Returns:
        List of (distance_m, elevation_m) tuples
    """
    profile: list[tuple[float, float]] = []

    for tp in activity.all_trackpoints:
        if tp.distance_meters is not None and tp.altitude_meters is not None:
            profile.append((tp.distance_meters, tp.altitude_meters))

    return profile


def extract_coordinates(activity: Activity) -> list[tuple[float, float]]:
    """
    Extract GPS coordinates from an activity.

    Args:
        activity: TCX Activity object

    Returns:
        List of (latitude, longitude) tuples
    """
    coords: list[tuple[float, float]] = []

    for tp in activity.all_trackpoints:
        if tp.has_position:
            coords.append((tp.latitude, tp.longitude))

    return coords


def extract_route_data(activity: Activity) -> RouteData:
    """
    Extract complete route data from an activity.

    Args:
        activity: TCX Activity object

    Returns:
        RouteData with elevation profile and statistics
    """
    profile = extract_elevation_profile(activity)
    coords = extract_coordinates(activity)

    if not profile:
        return RouteData(
            elevation_profile=[],
            coordinates=coords,
            total_distance_m=0,
            total_elevation_gain=0,
            total_elevation_loss=0,
            min_elevation=0,
            max_elevation=0,
        )

    elevations = [p[1] for p in profile]

    # Calculate elevation gain/loss
    gain = 0.0
    loss = 0.0
    for i in range(1, len(elevations)):
        diff = elevations[i] - elevations[i - 1]
        if diff > 0:
            gain += diff
        else:
            loss += abs(diff)

    return RouteData(
        elevation_profile=profile,
        coordinates=coords,
        total_distance_m=profile[-1][0] if profile else 0,
        total_elevation_gain=gain,
        total_elevation_loss=loss,
        min_elevation=min(elevations),
        max_elevation=max(elevations),
    )


def estimate_climb_times_for_climb(
    climb: ClimbData,
    settings: RiderSettings,
) -> dict[str, float]:
    """
    Estimate climb times at various power levels.

    Args:
        climb: Detected climb data
        settings: Rider settings

    Returns:
        Dictionary mapping power label to time in minutes
    """
    climb_input = ClimbInput(
        length_m=max(0, climb.end_dist - climb.start_dist),
        gain_m=max(0, climb.gain),
        avg_gradient_pct=climb.avg_gradient,
    )

    solver_settings = SolverSettings(
        ftp=settings.ftp,
        mass_kg=settings.mass_kg,
        cda=settings.cda,
        crr=settings.crr,
        wind_ms=settings.wind_ms,
        temperature_c=settings.temperature_c,
        altitude_m=settings.altitude_m,
    )

    result = estimate_climb_times(climb_input, solver_settings)
    return result.minutes_by_power


def analyze_route(
    activity: Activity,
    settings: Optional[RiderSettings] = None,
    min_gain: float = 30.0,
    smooth: bool = True,
) -> RouteAnalysis:
    """
    Perform complete route analysis with climb detection.

    Args:
        activity: TCX Activity object
        settings: Optional rider settings for time estimation
        min_gain: Minimum elevation gain for climb detection
        smooth: Whether to smooth elevation data

    Returns:
        RouteAnalysis with all detected climbs
    """
    route_data = extract_route_data(activity)

    if not route_data.elevation_profile:
        return RouteAnalysis(route_data=route_data)

    # Clean and smooth elevation data
    profile = route_data.elevation_profile
    if smooth:
        profile = remove_elevation_outliers(profile)
        profile = smooth_elevation_advanced(profile)

    # Detect climbs
    climb_data_list = detect_climbs_advanced(profile, min_gain=min_gain)

    # Analyze each climb
    climbs: list[ClimbAnalysis] = []
    for climb_data in climb_data_list:
        classification = classify_climb(climb_data.length_km, climb_data.gain)

        analysis = ClimbAnalysis(
            climb=climb_data,
            category=classification.category,
            classification=classification,
        )

        # Estimate times if settings provided
        if settings is not None:
            analysis.estimated_times = estimate_climb_times_for_climb(climb_data, settings)

        climbs.append(analysis)

    return RouteAnalysis(
        route_data=route_data,
        climbs=climbs,
        smoothed_profile=profile,
    )


def analyze_tcx_file(
    source: Union[str, Path, bytes],
    settings: Optional[RiderSettings] = None,
    min_gain: float = 30.0,
) -> list[RouteAnalysis]:
    """
    Analyze a TCX file and detect climbs in all activities.

    Args:
        source: File path or bytes of TCX data
        settings: Optional rider settings for time estimation
        min_gain: Minimum elevation gain for climb detection

    Returns:
        List of RouteAnalysis for each activity in the file
    """
    parser = TCXParser()
    tcx_data = parser.parse(source)

    analyses: list[RouteAnalysis] = []
    for activity in tcx_data.activities:
        analysis = analyze_route(activity, settings, min_gain)
        analyses.append(analysis)

    return analyses


def extract_climbs_from_profile(
    elevation_profile: list[tuple[float, float]],
    settings: Optional[RiderSettings] = None,
    min_gain: float = 30.0,
    smooth: bool = True,
) -> list[ClimbAnalysis]:
    """
    Extract and analyze climbs from an elevation profile.

    Args:
        elevation_profile: List of (distance_m, elevation_m) tuples
        settings: Optional rider settings for time estimation
        min_gain: Minimum elevation gain for climb detection
        smooth: Whether to smooth elevation data

    Returns:
        List of analyzed climbs
    """
    if not elevation_profile:
        return []

    profile = list(elevation_profile)
    if smooth:
        profile = remove_elevation_outliers(profile)
        profile = smooth_elevation_advanced(profile)

    climb_data_list = detect_climbs_advanced(profile, min_gain=min_gain)

    climbs: list[ClimbAnalysis] = []
    for climb_data in climb_data_list:
        classification = classify_climb(climb_data.length_km, climb_data.gain)

        analysis = ClimbAnalysis(
            climb=climb_data,
            category=classification.category,
            classification=classification,
        )

        if settings is not None:
            analysis.estimated_times = estimate_climb_times_for_climb(climb_data, settings)

        climbs.append(analysis)

    return climbs


def print_climb_summary(analysis: ClimbAnalysis) -> None:
    """Print a formatted summary of a climb."""
    c = analysis.climb
    print(f"\n{'='*50}")
    print(f"Climb: {analysis.category}")
    print(f"{'='*50}")
    print(f"Distance: {c.start_dist/1000:.2f} km - {c.end_dist/1000:.2f} km")
    print(f"Length: {c.length_km:.2f} km")
    print(f"Elevation: {c.start_elev:.0f} m - {c.end_elev:.0f} m")
    print(f"Gain: {c.gain:.0f} m")
    print(f"Average Gradient: {c.avg_gradient:.1f}%")
    print(f"Description: {analysis.description}")

    if analysis.estimated_times:
        print(f"\nEstimated times:")
        for power, minutes in sorted(analysis.estimated_times.items(), reverse=True):
            secs = minutes * 60
            print(f"  {power}: {format_time(secs)}")


def print_route_summary(analysis: RouteAnalysis) -> None:
    """Print a formatted summary of route analysis."""
    r = analysis.route_data
    print(f"\n{'#'*60}")
    print(f"ROUTE SUMMARY")
    print(f"{'#'*60}")
    print(f"Total Distance: {r.total_distance_m/1000:.2f} km")
    print(f"Elevation Range: {r.min_elevation:.0f} m - {r.max_elevation:.0f} m")
    print(f"Total Gain: {r.total_elevation_gain:.0f} m")
    print(f"Total Loss: {r.total_elevation_loss:.0f} m")
    print(f"\nDetected Climbs: {len(analysis.climbs)}")

    if analysis.hardest_climb:
        print(f"Hardest Climb: {analysis.hardest_climb.category} "
              f"({analysis.hardest_climb.climb.gain:.0f}m @ "
              f"{analysis.hardest_climb.climb.avg_gradient:.1f}%)")

    for climb_analysis in analysis.climbs:
        print_climb_summary(climb_analysis)
