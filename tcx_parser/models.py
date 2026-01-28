"""
Data models for TCX file structures.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Trackpoint:
    """Represents a single trackpoint in a TCX file."""

    time: datetime
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    altitude_meters: Optional[float] = None
    distance_meters: Optional[float] = None
    heart_rate_bpm: Optional[int] = None
    cadence: Optional[int] = None
    speed: Optional[float] = None
    power_watts: Optional[int] = None

    @property
    def has_position(self) -> bool:
        """Check if trackpoint has GPS position data."""
        return self.latitude is not None and self.longitude is not None

    @property
    def has_altitude(self) -> bool:
        """Check if trackpoint has altitude data."""
        return self.altitude_meters is not None


@dataclass
class Lap:
    """Represents a lap in a TCX activity."""

    start_time: datetime
    total_time_seconds: float
    distance_meters: float
    maximum_speed: Optional[float] = None
    calories: Optional[int] = None
    average_heart_rate_bpm: Optional[int] = None
    maximum_heart_rate_bpm: Optional[int] = None
    intensity: str = "Active"
    cadence: Optional[int] = None
    trigger_method: str = "Manual"
    trackpoints: list[Trackpoint] = field(default_factory=list)

    @property
    def elevation_gain(self) -> float:
        """Calculate elevation gain for this lap."""
        from .altimetry import calculate_elevation_gain
        altitudes = [tp.altitude_meters for tp in self.trackpoints if tp.has_altitude]
        return calculate_elevation_gain(altitudes)

    @property
    def elevation_loss(self) -> float:
        """Calculate elevation loss for this lap."""
        from .altimetry import calculate_elevation_loss
        altitudes = [tp.altitude_meters for tp in self.trackpoints if tp.has_altitude]
        return calculate_elevation_loss(altitudes)


@dataclass
class Activity:
    """Represents an activity (workout) in a TCX file."""

    sport: str
    activity_id: datetime
    laps: list[Lap] = field(default_factory=list)
    notes: Optional[str] = None
    creator_name: Optional[str] = None
    creator_version: Optional[str] = None

    @property
    def total_time_seconds(self) -> float:
        """Total duration of the activity in seconds."""
        return sum(lap.total_time_seconds for lap in self.laps)

    @property
    def total_distance_meters(self) -> float:
        """Total distance of the activity in meters."""
        return sum(lap.distance_meters for lap in self.laps)

    @property
    def all_trackpoints(self) -> list[Trackpoint]:
        """Get all trackpoints from all laps."""
        trackpoints = []
        for lap in self.laps:
            trackpoints.extend(lap.trackpoints)
        return trackpoints

    @property
    def elevation_gain(self) -> float:
        """Calculate total elevation gain for the activity."""
        from .altimetry import calculate_elevation_gain
        altitudes = [tp.altitude_meters for tp in self.all_trackpoints if tp.has_altitude]
        return calculate_elevation_gain(altitudes)

    @property
    def elevation_loss(self) -> float:
        """Calculate total elevation loss for the activity."""
        from .altimetry import calculate_elevation_loss
        altitudes = [tp.altitude_meters for tp in self.all_trackpoints if tp.has_altitude]
        return calculate_elevation_loss(altitudes)

    @property
    def min_altitude(self) -> Optional[float]:
        """Minimum altitude in the activity."""
        altitudes = [tp.altitude_meters for tp in self.all_trackpoints if tp.has_altitude]
        return min(altitudes) if altitudes else None

    @property
    def max_altitude(self) -> Optional[float]:
        """Maximum altitude in the activity."""
        altitudes = [tp.altitude_meters for tp in self.all_trackpoints if tp.has_altitude]
        return max(altitudes) if altitudes else None


@dataclass
class TCXData:
    """Container for all data parsed from a TCX file."""

    activities: list[Activity] = field(default_factory=list)

    @property
    def all_trackpoints(self) -> list[Trackpoint]:
        """Get all trackpoints from all activities."""
        trackpoints = []
        for activity in self.activities:
            trackpoints.extend(activity.all_trackpoints)
        return trackpoints

    @property
    def total_elevation_gain(self) -> float:
        """Total elevation gain across all activities."""
        return sum(activity.elevation_gain for activity in self.activities)

    @property
    def total_elevation_loss(self) -> float:
        """Total elevation loss across all activities."""
        return sum(activity.elevation_loss for activity in self.activities)
