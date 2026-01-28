#!/usr/bin/env python3
"""
Example usage of the TCX parser and altimetry module.
"""

from tcx_parser import (
    TCXParser,
    AltimetryStats,
    get_altimetry_profile,
    detect_climbs,
    smooth_elevation_data,
)


# Example TCX data (minimal valid TCX)
SAMPLE_TCX = """<?xml version="1.0" encoding="UTF-8"?>
<TrainingCenterDatabase
    xmlns="http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2"
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
    <Activities>
        <Activity Sport="Running">
            <Id>2024-01-15T08:30:00Z</Id>
            <Lap StartTime="2024-01-15T08:30:00Z">
                <TotalTimeSeconds>1800</TotalTimeSeconds>
                <DistanceMeters>5000</DistanceMeters>
                <Calories>350</Calories>
                <Intensity>Active</Intensity>
                <TriggerMethod>Manual</TriggerMethod>
                <Track>
                    <Trackpoint>
                        <Time>2024-01-15T08:30:00Z</Time>
                        <Position>
                            <LatitudeDegrees>37.7749</LatitudeDegrees>
                            <LongitudeDegrees>-122.4194</LongitudeDegrees>
                        </Position>
                        <AltitudeMeters>10.0</AltitudeMeters>
                        <DistanceMeters>0</DistanceMeters>
                        <HeartRateBpm><Value>120</Value></HeartRateBpm>
                    </Trackpoint>
                    <Trackpoint>
                        <Time>2024-01-15T08:35:00Z</Time>
                        <Position>
                            <LatitudeDegrees>37.7760</LatitudeDegrees>
                            <LongitudeDegrees>-122.4180</LongitudeDegrees>
                        </Position>
                        <AltitudeMeters>25.0</AltitudeMeters>
                        <DistanceMeters>500</DistanceMeters>
                        <HeartRateBpm><Value>135</Value></HeartRateBpm>
                    </Trackpoint>
                    <Trackpoint>
                        <Time>2024-01-15T08:40:00Z</Time>
                        <Position>
                            <LatitudeDegrees>37.7775</LatitudeDegrees>
                            <LongitudeDegrees>-122.4160</LongitudeDegrees>
                        </Position>
                        <AltitudeMeters>45.0</AltitudeMeters>
                        <DistanceMeters>1000</DistanceMeters>
                        <HeartRateBpm><Value>145</Value></HeartRateBpm>
                    </Trackpoint>
                    <Trackpoint>
                        <Time>2024-01-15T08:45:00Z</Time>
                        <Position>
                            <LatitudeDegrees>37.7785</LatitudeDegrees>
                            <LongitudeDegrees>-122.4140</LongitudeDegrees>
                        </Position>
                        <AltitudeMeters>60.0</AltitudeMeters>
                        <DistanceMeters>1500</DistanceMeters>
                        <HeartRateBpm><Value>155</Value></HeartRateBpm>
                    </Trackpoint>
                    <Trackpoint>
                        <Time>2024-01-15T08:50:00Z</Time>
                        <Position>
                            <LatitudeDegrees>37.7795</LatitudeDegrees>
                            <LongitudeDegrees>-122.4120</LongitudeDegrees>
                        </Position>
                        <AltitudeMeters>50.0</AltitudeMeters>
                        <DistanceMeters>2000</DistanceMeters>
                        <HeartRateBpm><Value>150</Value></HeartRateBpm>
                    </Trackpoint>
                    <Trackpoint>
                        <Time>2024-01-15T08:55:00Z</Time>
                        <Position>
                            <LatitudeDegrees>37.7800</LatitudeDegrees>
                            <LongitudeDegrees>-122.4100</LongitudeDegrees>
                        </Position>
                        <AltitudeMeters>35.0</AltitudeMeters>
                        <DistanceMeters>2500</DistanceMeters>
                        <HeartRateBpm><Value>140</Value></HeartRateBpm>
                    </Trackpoint>
                </Track>
            </Lap>
        </Activity>
    </Activities>
</TrainingCenterDatabase>
"""


def main():
    """Demonstrate TCX parsing and altimetry features."""
    print("=" * 60)
    print("TCX Parser & Altimetry Demo")
    print("=" * 60)

    # Parse the TCX data
    parser = TCXParser()
    tcx_data = parser.parse_string(SAMPLE_TCX)

    # Get the first activity
    activity = tcx_data.activities[0]

    print(f"\nActivity: {activity.sport}")
    print(f"Date: {activity.activity_id}")
    print(f"Laps: {len(activity.laps)}")
    print(f"Total Distance: {activity.total_distance_meters:.0f} m")
    print(f"Total Time: {activity.total_time_seconds:.0f} s")

    # Get all trackpoints
    trackpoints = activity.all_trackpoints
    print(f"\nTrackpoints: {len(trackpoints)}")

    # Extract altitude and distance data
    altitudes = [tp.altitude_meters for tp in trackpoints if tp.has_altitude]
    distances = [tp.distance_meters for tp in trackpoints if tp.distance_meters is not None]

    print("\n" + "-" * 40)
    print("Altimetry Analysis")
    print("-" * 40)

    # Calculate elevation statistics
    stats = AltimetryStats.from_altitudes(altitudes, smoothing=False)
    print(f"\nElevation Statistics:")
    print(f"  Min Elevation: {stats.min_elevation:.1f} m")
    print(f"  Max Elevation: {stats.max_elevation:.1f} m")
    print(f"  Elevation Range: {stats.elevation_range:.1f} m")
    print(f"  Start Elevation: {stats.start_elevation:.1f} m")
    print(f"  End Elevation: {stats.end_elevation:.1f} m")
    print(f"  Elevation Gain: {stats.elevation_gain:.1f} m")
    print(f"  Elevation Loss: {stats.elevation_loss:.1f} m")
    print(f"  Net Change: {stats.net_elevation_change:.1f} m")
    print(f"  Average Elevation: {stats.avg_elevation:.1f} m")

    # Using the Activity's built-in properties
    print(f"\nActivity Properties:")
    print(f"  Total Elevation Gain: {activity.elevation_gain:.1f} m")
    print(f"  Total Elevation Loss: {activity.elevation_loss:.1f} m")
    print(f"  Min Altitude: {activity.min_altitude:.1f} m")
    print(f"  Max Altitude: {activity.max_altitude:.1f} m")

    # Get full altimetry profile
    print("\n" + "-" * 40)
    print("Altimetry Profile")
    print("-" * 40)

    profile = get_altimetry_profile(altitudes, distances, smooth=True)

    print("\nElevation points:")
    for i, (dist, alt, grade) in enumerate(
        zip(profile["distances"], profile["altitudes"], profile["grades"] + [0])
    ):
        print(f"  {dist:>6.0f}m: {alt:>5.1f}m (grade: {grade:>+5.1f}%)")

    # Detect climbs (with lower thresholds for this small dataset)
    print("\n" + "-" * 40)
    print("Climb Detection")
    print("-" * 40)

    climbs = detect_climbs(altitudes, distances, min_gain=20.0, min_grade=2.0)

    if climbs:
        for i, climb in enumerate(climbs, 1):
            print(f"\nClimb {i}:")
            print(f"  Distance: {climb['start_distance']:.0f}m - {climb['end_distance']:.0f}m")
            print(f"  Elevation: {climb['start_elevation']:.1f}m - {climb['end_elevation']:.1f}m")
            print(f"  Gain: {climb['elevation_gain']:.1f}m")
            print(f"  Length: {climb['distance']:.0f}m")
            print(f"  Average Grade: {climb['average_grade']:.1f}%")
    else:
        print("No significant climbs detected.")

    # Demonstrate smoothing
    print("\n" + "-" * 40)
    print("Elevation Smoothing Comparison")
    print("-" * 40)

    # Create noisy data for demonstration
    import numpy as np

    noisy_altitudes = [a + np.random.uniform(-2, 2) for a in altitudes]

    print("\nOriginal vs Smoothed altitudes:")
    smoothed = smooth_elevation_data(noisy_altitudes, window_size=3)
    for i, (orig, noisy, smooth) in enumerate(zip(altitudes, noisy_altitudes, smoothed)):
        print(f"  Point {i}: Original={orig:.1f}m, Noisy={noisy:.1f}m, Smoothed={smooth:.1f}m")

    print("\n" + "=" * 60)
    print("Demo Complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
