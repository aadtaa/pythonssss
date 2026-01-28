"""
TCX Parser - A Python library for parsing TCX (Training Center XML) files
and computing altimetry data.
"""

from .models import Trackpoint, Lap, Activity, TCXData
from .parser import TCXParser
from .altimetry import (
    calculate_elevation_gain,
    calculate_elevation_loss,
    calculate_total_elevation_change,
    smooth_elevation_data,
    get_altimetry_profile,
    AltimetryStats,
)

__version__ = "1.0.0"
__all__ = [
    "Trackpoint",
    "Lap",
    "Activity",
    "TCXData",
    "TCXParser",
    "calculate_elevation_gain",
    "calculate_elevation_loss",
    "calculate_total_elevation_change",
    "smooth_elevation_data",
    "get_altimetry_profile",
    "AltimetryStats",
]
