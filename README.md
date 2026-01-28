# TCX Parser

A Python library for parsing TCX (Training Center XML) files and computing altimetry data.

## Features

- **TCX Parsing**: Parse Garmin TCX files with support for activities, laps, and trackpoints
- **Altimetry Analysis**: Calculate elevation gain, loss, and comprehensive statistics
- **Climb Detection**: Automatically detect significant climbs and descents
- **Data Smoothing**: Multiple smoothing algorithms to reduce GPS noise
- **Grade Calculation**: Compute gradient percentages between points

## Installation

```bash
pip install -r requirements.txt
```

## Quick Start

```python
from tcx_parser import TCXParser, AltimetryStats

# Parse a TCX file
parser = TCXParser()
data = parser.parse("activity.tcx")

# Get activity info
activity = data.activities[0]
print(f"Sport: {activity.sport}")
print(f"Distance: {activity.total_distance_meters}m")
print(f"Elevation Gain: {activity.elevation_gain}m")

# Get detailed altimetry stats
trackpoints = activity.all_trackpoints
altitudes = [tp.altitude_meters for tp in trackpoints if tp.has_altitude]
stats = AltimetryStats.from_altitudes(altitudes)

print(f"Min Elevation: {stats.min_elevation}m")
print(f"Max Elevation: {stats.max_elevation}m")
print(f"Total Gain: {stats.elevation_gain}m")
print(f"Total Loss: {stats.elevation_loss}m")
```

## API Reference

### TCXParser

Parse TCX files from file paths, strings, or bytes:

```python
from tcx_parser import TCXParser

parser = TCXParser()
data = parser.parse("file.tcx")           # From file
data = parser.parse(xml_bytes)            # From bytes
data = parser.parse_string(xml_string)    # From string
```

### Altimetry Functions

```python
from tcx_parser import (
    calculate_elevation_gain,
    calculate_elevation_loss,
    smooth_elevation_data,
    get_altimetry_profile,
    detect_climbs,
)

# Calculate elevation changes
gain = calculate_elevation_gain(altitudes, threshold=2.0)
loss = calculate_elevation_loss(altitudes)

# Smooth noisy GPS data
smoothed = smooth_elevation_data(altitudes, window_size=5, method="moving_average")

# Get complete altimetry profile
profile = get_altimetry_profile(altitudes, distances, smooth=True)

# Detect climbs
climbs = detect_climbs(altitudes, distances, min_gain=50, min_grade=3.0)
```

## Data Models

- `TCXData`: Container for all parsed activities
- `Activity`: Single workout (sport, laps, trackpoints)
- `Lap`: Segment within an activity
- `Trackpoint`: Individual GPS point with time, position, altitude, heart rate, etc.
- `AltimetryStats`: Comprehensive elevation statistics

## Running Tests

```bash
pytest tests/
```

## Example

See `example.py` for a complete demonstration of all features.
