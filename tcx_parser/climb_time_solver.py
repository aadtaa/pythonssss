"""
Physics-based climb time estimation with Newton-Raphson solver.

This module provides accurate climb time predictions based on:
- Rider power output (FTP-based)
- Aerodynamic drag (CdA)
- Rolling resistance
- Wind conditions
- Air density (temperature and altitude adjusted)
"""

from dataclasses import dataclass, field
from typing import Optional
import math


@dataclass
class ClimbInput:
    """Input data for climb time estimation."""
    length_m: float  # Length in meters
    gain_m: float  # Elevation gain in meters
    avg_gradient_pct: Optional[float] = None  # Average gradient in %


@dataclass
class SolverSettings:
    """Settings for the physics solver."""
    ftp: float  # Functional Threshold Power in watts
    mass_kg: float = 75.0  # Total mass (rider + bike) in kg
    cda: float = 0.3  # Coefficient of drag * frontal area (m²)
    crr: float = 0.004  # Coefficient of rolling resistance
    wind_ms: float = 0.0  # Headwind speed in m/s (positive = headwind)
    temperature_c: float = 20.0  # Temperature in Celsius
    altitude_m: float = 200.0  # Altitude in meters
    transmission: float = 0.96  # Drivetrain efficiency


@dataclass
class ClimbTimesResult:
    """Result of climb time estimation at multiple power levels."""
    minutes_by_power: dict[str, float] = field(default_factory=dict)


# Power duration table: sustainable power as fraction of FTP based on duration
POWER_DURATION_TABLE = [
    {"duration": 1, "fractions": [1.9, 1.8, 1.7, 1.6, 1.5]},
    {"duration": 2, "fractions": [1.75, 1.65, 1.55, 1.45, 1.35]},
    {"duration": 3, "fractions": [1.65, 1.55, 1.45, 1.35, 1.25]},
    {"duration": 5, "fractions": [1.5, 1.4, 1.3, 1.2, 1.1]},
    {"duration": 8, "fractions": [1.35, 1.28, 1.2, 1.12, 1.05]},
    {"duration": 10, "fractions": [1.3, 1.22, 1.15, 1.08, 1.0]},
    {"duration": 12, "fractions": [1.25, 1.18, 1.1, 1.03, 0.96]},
    {"duration": 15, "fractions": [1.2, 1.14, 1.07, 1.0, 0.94]},
    {"duration": 20, "fractions": [1.15, 1.1, 1.03, 0.97, 0.91]},
    {"duration": 25, "fractions": [1.1, 1.05, 0.99, 0.94, 0.89]},
    {"duration": 30, "fractions": [1.07, 1.02, 0.96, 0.91, 0.86]},
    {"duration": 40, "fractions": [1.03, 0.98, 0.93, 0.88, 0.83]},
    {"duration": 50, "fractions": [1.01, 0.96, 0.91, 0.86, 0.81]},
    {"duration": 60, "fractions": [1.0, 0.95, 0.9, 0.85, 0.8]},
    {"duration": 75, "fractions": [0.97, 0.92, 0.87, 0.82, 0.77]},
    {"duration": 90, "fractions": [0.95, 0.9, 0.85, 0.8, 0.75]},
    {"duration": 105, "fractions": [0.93, 0.88, 0.83, 0.78, 0.73]},
    {"duration": 120, "fractions": [0.91, 0.86, 0.81, 0.76, 0.71]},
    {"duration": 150, "fractions": [0.88, 0.83, 0.78, 0.73, 0.68]},
    {"duration": 180, "fractions": [0.85, 0.8, 0.75, 0.7, 0.65]},
    {"duration": 240, "fractions": [0.83, 0.78, 0.73, 0.68, 0.63]},
    {"duration": 300, "fractions": [0.8, 0.75, 0.7, 0.65, 0.6]},
    {"duration": 99999, "fractions": [0.78, 0.73, 0.68, 0.63, 0.58]},
]


def air_density(temperature_c: float, altitude_m: float) -> float:
    """
    Calculate air density based on temperature and altitude.

    Uses simplified atmospheric model.

    Args:
        temperature_c: Temperature in Celsius
        altitude_m: Altitude in meters

    Returns:
        Air density in kg/m³
    """
    return (1.293 - 0.00426 * temperature_c) * math.exp(-altitude_m / 7000.0)


def solve_velocity_ms(
    power_w: float,
    grade_pct: float,
    settings: SolverSettings,
) -> float:
    """
    Solve for steady-state velocity using Newton-Raphson method.

    The power balance equation is:
    P = v * (F_aero + F_gravity + F_rolling)

    Where:
    - F_aero = 0.5 * CdA * rho * (v + wind)²
    - F_gravity = m * g * sin(grade)
    - F_rolling = m * g * cos(grade) * Crr

    Args:
        power_w: Power output in watts
        grade_pct: Grade in percent
        settings: Solver settings

    Returns:
        Velocity in m/s
    """
    rho = air_density(settings.temperature_c, settings.altitude_m)
    aero = 0.5 * settings.cda * rho
    total_weight_n = settings.mass_kg * 9.8
    grade = grade_pct / 100.0
    rolling_res = total_weight_n * (grade + settings.crr)

    # Initial guess
    v = 5.0
    max_iter = 40
    tol = 1e-3

    for _ in range(max_iter):
        total_v = v + settings.wind_ms
        sign = 1 if total_v >= 0 else -1
        aero_force = sign * aero * total_v * total_v

        # f(v) = v * (aero_force + rolling_res) - transmission * power
        f = v * (aero_force + rolling_res) - settings.transmission * power_w

        # f'(v) derivative
        fp = aero * (3 * v + settings.wind_ms) * total_v + (aero_force + rolling_res)

        if not math.isfinite(f) or not math.isfinite(fp) or abs(fp) < 1e-12:
            break

        v_next = v - f / fp

        if not math.isfinite(v_next) or v_next <= 0:
            v = max(0.2, v * 0.5)
        else:
            if abs(v_next - v) < tol:
                return v_next
            v = v_next

    return max(0.1, v)


def model_time_seconds(
    distance_m: float,
    grade_pct: float,
    power_w: float,
    settings: SolverSettings,
) -> float:
    """
    Calculate time to cover distance at given power and grade.

    Args:
        distance_m: Distance in meters
        grade_pct: Grade in percent
        power_w: Power output in watts
        settings: Solver settings

    Returns:
        Time in seconds
    """
    v_ms = solve_velocity_ms(power_w, grade_pct, settings)

    if v_ms <= 0:
        return float("inf")

    return distance_m / v_ms


def pick_fractions_for_climb(distance_m: float, ftp: float) -> list[float]:
    """
    Select appropriate power fractions based on estimated climb duration.

    Args:
        distance_m: Distance in meters
        ftp: FTP in watts

    Returns:
        List of power fractions to use
    """
    rough_minutes = distance_m / (ftp * 0.9) if ftp > 0 else 60

    row = POWER_DURATION_TABLE[-1]
    for r in POWER_DURATION_TABLE:
        if rough_minutes <= r["duration"]:
            row = r
            break

    fractions = sorted(row["fractions"], reverse=True)[:5]
    return fractions


def estimate_climb_times(climb: ClimbInput, settings: SolverSettings) -> ClimbTimesResult:
    """
    Estimate climb times at multiple power levels.

    Args:
        climb: Climb input data (length, gain)
        settings: Solver settings (FTP, mass, etc.)

    Returns:
        ClimbTimesResult with times at various power levels
    """
    distance_m = max(1, climb.length_m)

    if climb.avg_gradient_pct is not None:
        grade_pct = climb.avg_gradient_pct
    else:
        grade_pct = (climb.gain_m / distance_m) * 100

    fractions = pick_fractions_for_climb(distance_m, settings.ftp)
    minutes_by_power: dict[str, float] = {}

    for frac in fractions:
        power_w = round((settings.ftp * frac) / 10) * 10
        secs = model_time_seconds(distance_m, grade_pct, power_w, settings)

        if secs == float("inf"):
            minutes_by_power[f"{power_w} W"] = 999.0
        else:
            minutes_by_power[f"{power_w} W"] = round(secs / 60, 2)

    return ClimbTimesResult(minutes_by_power=minutes_by_power)


def estimate_climb_time_at_power(
    climb: ClimbInput,
    power_w: float,
    settings: SolverSettings,
) -> float:
    """
    Estimate climb time at a specific power output.

    Args:
        climb: Climb input data
        power_w: Power output in watts
        settings: Solver settings

    Returns:
        Time in seconds
    """
    distance_m = max(1, climb.length_m)

    if climb.avg_gradient_pct is not None:
        grade_pct = climb.avg_gradient_pct
    else:
        grade_pct = (climb.gain_m / distance_m) * 100

    secs = model_time_seconds(distance_m, grade_pct, power_w, settings)

    if secs == float("inf"):
        return 999 * 60

    return secs


def format_time(seconds: float) -> str:
    """Format time in seconds to human-readable string."""
    if seconds >= 999 * 60:
        return "N/A"

    minutes = int(seconds // 60)
    secs = int(seconds % 60)

    if minutes >= 60:
        hours = minutes // 60
        mins = minutes % 60
        return f"{hours}h {mins}m {secs}s"

    return f"{minutes}m {secs}s"


def calculate_vam(gain_m: float, time_seconds: float) -> float:
    """
    Calculate VAM (Velocità Ascensionale Media).

    VAM is the average climbing speed in meters per hour.

    Args:
        gain_m: Elevation gain in meters
        time_seconds: Time in seconds

    Returns:
        VAM in m/h
    """
    if time_seconds <= 0:
        return 0.0

    hours = time_seconds / 3600
    return gain_m / hours
