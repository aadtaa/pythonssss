"""
TCX Parser - A Python library for parsing TCX (Training Center XML) files
and computing altimetry data with professional climb detection.
"""

from .models import Trackpoint, Lap, Activity, TCXData
from .parser import TCXParser, parse_tcx, parse_tcx_string
from .altimetry import (
    calculate_elevation_gain,
    calculate_elevation_loss,
    calculate_total_elevation_change,
    smooth_elevation_data,
    get_altimetry_profile,
    AltimetryStats,
    detect_climbs,
    detect_descents,
    calculate_grades,
)

# Climb classification
from .climb_classifier import (
    Category,
    ClimbClassification,
    classify_climb,
    get_category_color,
    get_category_label,
    get_category_description,
    get_category_rank,
)

# Climb time estimation
from .climb_time_solver import (
    ClimbInput,
    SolverSettings,
    ClimbTimesResult,
    estimate_climb_times,
    estimate_climb_time_at_power,
    format_time,
    calculate_vam,
)

# Advanced climb detection
from .climb_detection import (
    ClimbData,
    detect_climbs_advanced,
    smooth_elevation_advanced,
    remove_elevation_outliers,
    gaussian_filter,
    savgol_filter,
)

# High-level API
from .climb_extractor import (
    RouteData,
    ClimbAnalysis,
    RouteAnalysis,
    RiderSettings,
    extract_elevation_profile,
    extract_coordinates,
    extract_route_data,
    analyze_route,
    analyze_tcx_file,
    extract_climbs_from_profile,
    print_climb_summary,
    print_route_summary,
)

__version__ = "2.0.0"
__all__ = [
    # Models
    "Trackpoint",
    "Lap",
    "Activity",
    "TCXData",
    # Parser
    "TCXParser",
    "parse_tcx",
    "parse_tcx_string",
    # Basic altimetry
    "calculate_elevation_gain",
    "calculate_elevation_loss",
    "calculate_total_elevation_change",
    "smooth_elevation_data",
    "get_altimetry_profile",
    "AltimetryStats",
    "detect_climbs",
    "detect_descents",
    "calculate_grades",
    # Climb classification
    "Category",
    "ClimbClassification",
    "classify_climb",
    "get_category_color",
    "get_category_label",
    "get_category_description",
    "get_category_rank",
    # Climb time estimation
    "ClimbInput",
    "SolverSettings",
    "ClimbTimesResult",
    "estimate_climb_times",
    "estimate_climb_time_at_power",
    "format_time",
    "calculate_vam",
    # Advanced climb detection
    "ClimbData",
    "detect_climbs_advanced",
    "smooth_elevation_advanced",
    "remove_elevation_outliers",
    "gaussian_filter",
    "savgol_filter",
    # High-level API
    "RouteData",
    "ClimbAnalysis",
    "RouteAnalysis",
    "RiderSettings",
    "extract_elevation_profile",
    "extract_coordinates",
    "extract_route_data",
    "analyze_route",
    "analyze_tcx_file",
    "extract_climbs_from_profile",
    "print_climb_summary",
    "print_route_summary",
]
