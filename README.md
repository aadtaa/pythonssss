# TCX Parser

A Python library for parsing TCX (Training Center XML) files with professional climb detection and altimetry analysis.

## Features

- **TCX Parsing**: Parse Garmin TCX files with support for activities, laps, and trackpoints
- **Altimetry Analysis**: Calculate elevation gain, loss, and comprehensive statistics
- **Professional Climb Classification**: 2-out-of-3 rule categorization (HC, Cat 1-4)
- **Physics-Based Time Estimation**: Newton-Raphson solver for accurate climb time predictions
- **Advanced Climb Detection**: Local min/max analysis, trimming, merging
- **GPS Noise Reduction**: Multiple smoothing algorithms (Gaussian, Savitzky-Golay)

## Installation

```bash
pip install -r requirements.txt
```

## Quick Start

```python
from tcx_parser import TCXParser, analyze_route, RiderSettings

# Parse and analyze a TCX file
parser = TCXParser()
data = parser.parse("activity.tcx")

# Analyze with rider settings for time estimation
rider = RiderSettings(ftp=250, mass_kg=75)
analysis = analyze_route(data.activities[0], settings=rider)

# Print results
print(f"Climbs found: {len(analysis.climbs)}")
for climb in analysis.climbs:
    print(f"  {climb.category}: {climb.climb.gain}m @ {climb.climb.avg_gradient:.1f}%")
```

## Climb Classification

Uses the professional 2-out-of-3 rule based on length, elevation gain, and average gradient:

```python
from tcx_parser import classify_climb

# Classify Alpe d'Huez
result = classify_climb(length_km=13.8, gain_m=1120)
print(f"Category: {result.category}")  # HC or Cat 1
print(f"Average: {result.avg_pct}%")   # 8.1%
```

| Category | Typical Gain | Typical Length | Typical Avg% |
|----------|-------------|----------------|--------------|
| HC | 1300m+ | 20km+ | 8%+ |
| Cat 1 | 900m+ | 12km+ | 7%+ |
| Cat 2 | 600m+ | 8km+ | 6%+ |
| Cat 3 | 350m+ | 5km+ | 5%+ |
| Cat 4 | 100-200m | 1.2-2.5km | 4-7%+ |

## Climb Time Estimation

Physics-based time estimation using Newton-Raphson solver:

```python
from tcx_parser import ClimbInput, SolverSettings, estimate_climb_times, format_time

climb = ClimbInput(length_m=13800, gain_m=1120, avg_gradient_pct=8.1)
settings = SolverSettings(ftp=250, mass_kg=75)

result = estimate_climb_times(climb, settings)
for power, minutes in result.minutes_by_power.items():
    print(f"{power}: {format_time(minutes * 60)}")
```

Factors considered:
- Rider power output (FTP-based)
- Total mass (rider + bike)
- Aerodynamic drag (CdA)
- Rolling resistance
- Wind conditions
- Air density (temperature/altitude adjusted)

## Advanced Detection

```python
from tcx_parser import detect_climbs_advanced, smooth_elevation_advanced

# Smooth elevation data
profile = [(dist, elev), ...]
smoothed = smooth_elevation_advanced(profile)

# Detect climbs with professional categorization
climbs = detect_climbs_advanced(smoothed, min_gain=50)
```

## API Reference

### Core Modules

| Module | Purpose |
|--------|---------|
| `parser.py` | TCX file parsing |
| `altimetry.py` | Basic elevation calculations |
| `climb_classifier.py` | Professional categorization (2-out-of-3 rule) |
| `climb_time_solver.py` | Physics-based time estimation |
| `climb_detection.py` | Advanced detection algorithms |
| `climb_extractor.py` | High-level API |

### Key Functions

```python
# Classification
classify_climb(length_km, gain_m) -> ClimbClassification

# Time estimation
estimate_climb_times(climb, settings) -> ClimbTimesResult
estimate_climb_time_at_power(climb, power_w, settings) -> float

# Detection
detect_climbs_advanced(profile, min_gain=30) -> list[ClimbData]

# High-level
analyze_route(activity, settings=None, min_gain=30) -> RouteAnalysis
analyze_tcx_file(source, settings=None) -> list[RouteAnalysis]
```

## Running Tests

```bash
pytest tests/ -v
```

## Example

See `example.py` for a complete demonstration:

```bash
python example.py
```

## License

MIT
