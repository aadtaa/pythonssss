#!/usr/bin/env python3
"""
Example usage of the TCX parser, altimetry, and climb detection modules.
"""

from tcx_parser import (
    # Parser
    TCXParser,
    # Basic altimetry
    AltimetryStats,
    get_altimetry_profile,
    detect_climbs,
    smooth_elevation_data,
    # Climb classification
    classify_climb,
    get_category_description,
    get_category_color,
    # Climb time estimation
    ClimbInput,
    SolverSettings,
    estimate_climb_times,
    format_time,
    calculate_vam,
    # Advanced detection
    detect_climbs_advanced,
    smooth_elevation_advanced,
    # High-level API
    analyze_route,
    RiderSettings,
    print_route_summary,
)


# Example TCX data with a significant climb
SAMPLE_TCX = """<?xml version="1.0" encoding="UTF-8"?>
<TrainingCenterDatabase
    xmlns="http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2">
    <Activities>
        <Activity Sport="Biking">
            <Id>2024-06-15T07:00:00Z</Id>
            <Lap StartTime="2024-06-15T07:00:00Z">
                <TotalTimeSeconds>7200</TotalTimeSeconds>
                <DistanceMeters>40000</DistanceMeters>
                <Calories>1200</Calories>
                <Intensity>Active</Intensity>
                <TriggerMethod>Manual</TriggerMethod>
                <Track>
                    <Trackpoint>
                        <Time>2024-06-15T07:00:00Z</Time>
                        <Position>
                            <LatitudeDegrees>45.0</LatitudeDegrees>
                            <LongitudeDegrees>6.0</LongitudeDegrees>
                        </Position>
                        <AltitudeMeters>500</AltitudeMeters>
                        <DistanceMeters>0</DistanceMeters>
                    </Trackpoint>
                    <Trackpoint>
                        <Time>2024-06-15T07:10:00Z</Time>
                        <AltitudeMeters>520</AltitudeMeters>
                        <DistanceMeters>2000</DistanceMeters>
                    </Trackpoint>
                    <Trackpoint>
                        <Time>2024-06-15T07:20:00Z</Time>
                        <AltitudeMeters>550</AltitudeMeters>
                        <DistanceMeters>4000</DistanceMeters>
                    </Trackpoint>
                    <Trackpoint>
                        <Time>2024-06-15T07:30:00Z</Time>
                        <AltitudeMeters>600</AltitudeMeters>
                        <DistanceMeters>6000</DistanceMeters>
                    </Trackpoint>
                    <Trackpoint>
                        <Time>2024-06-15T07:40:00Z</Time>
                        <AltitudeMeters>680</AltitudeMeters>
                        <DistanceMeters>8000</DistanceMeters>
                    </Trackpoint>
                    <Trackpoint>
                        <Time>2024-06-15T07:50:00Z</Time>
                        <AltitudeMeters>780</AltitudeMeters>
                        <DistanceMeters>10000</DistanceMeters>
                    </Trackpoint>
                    <Trackpoint>
                        <Time>2024-06-15T08:00:00Z</Time>
                        <AltitudeMeters>900</AltitudeMeters>
                        <DistanceMeters>12000</DistanceMeters>
                    </Trackpoint>
                    <Trackpoint>
                        <Time>2024-06-15T08:10:00Z</Time>
                        <AltitudeMeters>1050</AltitudeMeters>
                        <DistanceMeters>14000</DistanceMeters>
                    </Trackpoint>
                    <Trackpoint>
                        <Time>2024-06-15T08:20:00Z</Time>
                        <AltitudeMeters>1200</AltitudeMeters>
                        <DistanceMeters>16000</DistanceMeters>
                    </Trackpoint>
                    <Trackpoint>
                        <Time>2024-06-15T08:30:00Z</Time>
                        <AltitudeMeters>1100</AltitudeMeters>
                        <DistanceMeters>20000</DistanceMeters>
                    </Trackpoint>
                    <Trackpoint>
                        <Time>2024-06-15T08:40:00Z</Time>
                        <AltitudeMeters>1000</AltitudeMeters>
                        <DistanceMeters>24000</DistanceMeters>
                    </Trackpoint>
                    <Trackpoint>
                        <Time>2024-06-15T08:50:00Z</Time>
                        <AltitudeMeters>800</AltitudeMeters>
                        <DistanceMeters>28000</DistanceMeters>
                    </Trackpoint>
                    <Trackpoint>
                        <Time>2024-06-15T09:00:00Z</Time>
                        <AltitudeMeters>600</AltitudeMeters>
                        <DistanceMeters>32000</DistanceMeters>
                    </Trackpoint>
                    <Trackpoint>
                        <Time>2024-06-15T09:10:00Z</Time>
                        <AltitudeMeters>550</AltitudeMeters>
                        <DistanceMeters>36000</DistanceMeters>
                    </Trackpoint>
                    <Trackpoint>
                        <Time>2024-06-15T09:20:00Z</Time>
                        <AltitudeMeters>500</AltitudeMeters>
                        <DistanceMeters>40000</DistanceMeters>
                    </Trackpoint>
                </Track>
            </Lap>
        </Activity>
    </Activities>
</TrainingCenterDatabase>
"""


def demo_basic_parsing():
    """Demonstrate basic TCX parsing."""
    print("=" * 60)
    print("1. BASIC TCX PARSING")
    print("=" * 60)

    parser = TCXParser()
    tcx_data = parser.parse_string(SAMPLE_TCX)
    activity = tcx_data.activities[0]

    print(f"\nActivity: {activity.sport}")
    print(f"Date: {activity.activity_id}")
    print(f"Distance: {activity.total_distance_meters/1000:.1f} km")
    print(f"Duration: {activity.total_time_seconds/60:.0f} min")
    print(f"Trackpoints: {len(activity.all_trackpoints)}")


def demo_altimetry_stats():
    """Demonstrate altimetry statistics."""
    print("\n" + "=" * 60)
    print("2. ALTIMETRY STATISTICS")
    print("=" * 60)

    parser = TCXParser()
    tcx_data = parser.parse_string(SAMPLE_TCX)
    activity = tcx_data.activities[0]

    trackpoints = activity.all_trackpoints
    altitudes = [tp.altitude_meters for tp in trackpoints if tp.has_altitude]

    stats = AltimetryStats.from_altitudes(altitudes, smoothing=False)

    print(f"\nElevation Range: {stats.min_elevation:.0f}m - {stats.max_elevation:.0f}m")
    print(f"Total Gain: {stats.elevation_gain:.0f}m")
    print(f"Total Loss: {stats.elevation_loss:.0f}m")
    print(f"Net Change: {stats.net_elevation_change:.0f}m")


def demo_climb_classification():
    """Demonstrate climb classification."""
    print("\n" + "=" * 60)
    print("3. CLIMB CLASSIFICATION (2-out-of-3 Rule)")
    print("=" * 60)

    test_climbs = [
        ("Alpe d'Huez", 13.8, 1120),
        ("Mont Ventoux", 21.5, 1617),
        ("Col du Galibier", 18.1, 1245),
        ("Category 3 climb", 5.0, 350),
        ("Category 4 climb", 2.5, 150),
        ("Easy hill", 1.0, 30),
    ]

    print(f"\n{'Climb Name':<20} {'Length':<10} {'Gain':<10} {'Avg%':<8} {'Category':<15}")
    print("-" * 70)

    for name, length_km, gain_m in test_climbs:
        result = classify_climb(length_km, gain_m)
        print(f"{name:<20} {length_km:>6.1f} km  {gain_m:>6.0f} m  {result.avg_pct:>5.1f}%  {result.category:<15}")
        if result.bonus_applied:
            print(f"                     ^ Upgraded from {result.base} (9.5% avg bonus)")


def demo_climb_time_estimation():
    """Demonstrate climb time estimation."""
    print("\n" + "=" * 60)
    print("4. CLIMB TIME ESTIMATION (Physics-Based)")
    print("=" * 60)

    # Simulate Alpe d'Huez
    climb = ClimbInput(
        length_m=13800,
        gain_m=1120,
        avg_gradient_pct=8.1,
    )

    settings = SolverSettings(
        ftp=250,
        mass_kg=75,
        cda=0.35,
        crr=0.004,
        temperature_c=20,
        altitude_m=1000,
    )

    print(f"\nAlpe d'Huez: {climb.length_m/1000:.1f}km, {climb.gain_m:.0f}m @ {climb.avg_gradient_pct:.1f}%")
    print(f"Rider: FTP={settings.ftp}W, Mass={settings.mass_kg}kg")
    print("\nEstimated times by power:")

    result = estimate_climb_times(climb, settings)
    for power, minutes in sorted(result.minutes_by_power.items(), reverse=True):
        secs = minutes * 60
        vam = calculate_vam(climb.gain_m, secs)
        print(f"  {power}: {format_time(secs)} (VAM: {vam:.0f} m/h)")


def demo_advanced_detection():
    """Demonstrate advanced climb detection."""
    print("\n" + "=" * 60)
    print("5. ADVANCED CLIMB DETECTION")
    print("=" * 60)

    parser = TCXParser()
    tcx_data = parser.parse_string(SAMPLE_TCX)
    activity = tcx_data.activities[0]

    trackpoints = activity.all_trackpoints
    profile = [
        (tp.distance_meters, tp.altitude_meters)
        for tp in trackpoints
        if tp.distance_meters is not None and tp.altitude_meters is not None
    ]

    # Smooth and detect
    smoothed = smooth_elevation_advanced(profile)
    climbs = detect_climbs_advanced(smoothed, min_gain=100)

    print(f"\nDetected {len(climbs)} climb(s):")

    for i, climb in enumerate(climbs, 1):
        print(f"\nClimb {i}: {climb.category}")
        print(f"  Start: {climb.start_dist/1000:.1f}km at {climb.start_elev:.0f}m")
        print(f"  End: {climb.end_dist/1000:.1f}km at {climb.end_elev:.0f}m")
        print(f"  Gain: {climb.gain:.0f}m over {climb.length_km:.1f}km")
        print(f"  Average Gradient: {climb.avg_gradient:.1f}%")


def demo_high_level_api():
    """Demonstrate high-level route analysis API."""
    print("\n" + "=" * 60)
    print("6. HIGH-LEVEL ROUTE ANALYSIS")
    print("=" * 60)

    parser = TCXParser()
    tcx_data = parser.parse_string(SAMPLE_TCX)
    activity = tcx_data.activities[0]

    # Analyze with rider settings for time estimation
    rider = RiderSettings(
        ftp=280,
        mass_kg=72,
        cda=0.32,
    )

    analysis = analyze_route(activity, settings=rider, min_gain=100)

    print(f"\nRoute: {analysis.route_data.total_distance_m/1000:.1f}km")
    print(f"Elevation: {analysis.route_data.min_elevation:.0f}m - {analysis.route_data.max_elevation:.0f}m")
    print(f"Total Climbing: {analysis.route_data.total_elevation_gain:.0f}m")
    print(f"\nClimbs Found: {len(analysis.climbs)}")

    for i, climb_analysis in enumerate(analysis.climbs, 1):
        c = climb_analysis.climb
        print(f"\n  [{i}] {climb_analysis.category}")
        print(f"      {c.length_km:.1f}km, {c.gain:.0f}m @ {c.avg_gradient:.1f}%")
        print(f"      {climb_analysis.description}")

        if climb_analysis.estimated_times:
            print("      Estimated times:")
            for power, mins in list(climb_analysis.estimated_times.items())[:3]:
                print(f"        {power}: {mins:.1f} min")


def main():
    """Run all demos."""
    print("\n" + "#" * 60)
    print("#  TCX Parser with Climb Detection - Full Demo")
    print("#" * 60)

    demo_basic_parsing()
    demo_altimetry_stats()
    demo_climb_classification()
    demo_climb_time_estimation()
    demo_advanced_detection()
    demo_high_level_api()

    print("\n" + "=" * 60)
    print("Demo Complete!")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
