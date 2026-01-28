"""Tests for climb time solver."""

import pytest
import math

from tcx_parser.climb_time_solver import (
    ClimbInput,
    SolverSettings,
    air_density,
    solve_velocity_ms,
    estimate_climb_times,
    estimate_climb_time_at_power,
    format_time,
    calculate_vam,
)


class TestAirDensity:
    """Tests for air density calculation."""

    def test_sea_level_standard(self):
        """Test air density at sea level, 15°C (ISA standard)."""
        # At sea level, 15°C, should be close to 1.225 kg/m³
        rho = air_density(15, 0)
        assert rho == pytest.approx(1.229, rel=0.05)

    def test_altitude_reduces_density(self):
        """Test that altitude reduces air density."""
        rho_0 = air_density(20, 0)
        rho_1000 = air_density(20, 1000)
        rho_2000 = air_density(20, 2000)

        assert rho_1000 < rho_0
        assert rho_2000 < rho_1000

    def test_temperature_affects_density(self):
        """Test that higher temperature reduces air density."""
        rho_cold = air_density(0, 0)
        rho_hot = air_density(35, 0)

        assert rho_hot < rho_cold


class TestSolveVelocity:
    """Tests for Newton-Raphson velocity solver."""

    def test_flat_terrain(self):
        """Test velocity on flat terrain."""
        settings = SolverSettings(ftp=250, mass_kg=75)
        v = solve_velocity_ms(200, 0, settings)

        # On flat ground, ~200W should give ~30-35 km/h
        assert 8 < v < 12  # 28-43 km/h

    def test_steep_climb(self):
        """Test velocity on steep climb."""
        settings = SolverSettings(ftp=250, mass_kg=75)
        v = solve_velocity_ms(250, 10, settings)

        # On 10% grade, speed should be much lower
        assert 1 < v < 5  # Very slow

    def test_higher_power_faster(self):
        """Test that higher power gives higher velocity."""
        settings = SolverSettings(ftp=250, mass_kg=75)
        v_low = solve_velocity_ms(150, 5, settings)
        v_high = solve_velocity_ms(300, 5, settings)

        assert v_high > v_low

    def test_headwind_slows(self):
        """Test that headwind reduces velocity."""
        settings_calm = SolverSettings(ftp=250, mass_kg=75, wind_ms=0)
        settings_wind = SolverSettings(ftp=250, mass_kg=75, wind_ms=5)

        v_calm = solve_velocity_ms(200, 3, settings_calm)
        v_wind = solve_velocity_ms(200, 3, settings_wind)

        assert v_wind < v_calm


class TestEstimateClimbTimes:
    """Tests for climb time estimation."""

    def test_basic_climb(self):
        """Test basic climb time estimation."""
        climb = ClimbInput(length_m=5000, gain_m=400)
        settings = SolverSettings(ftp=250, mass_kg=75)

        result = estimate_climb_times(climb, settings)

        assert result.minutes_by_power is not None
        assert len(result.minutes_by_power) > 0

        # All times should be positive
        for power, minutes in result.minutes_by_power.items():
            assert minutes > 0
            assert "W" in power

    def test_higher_power_faster(self):
        """Test that higher power gives faster times."""
        climb = ClimbInput(length_m=5000, gain_m=400)
        settings = SolverSettings(ftp=250, mass_kg=75)

        result = estimate_climb_times(climb, settings)

        # Extract power values and times
        times = [(int(k.replace(" W", "")), v)
                 for k, v in result.minutes_by_power.items()]
        times.sort(key=lambda x: x[0])

        # Higher power should mean less time
        for i in range(len(times) - 1):
            power1, time1 = times[i]
            power2, time2 = times[i + 1]
            assert time2 < time1  # Higher power = less time

    def test_steeper_climb_slower(self):
        """Test that steeper climbs take longer."""
        climb_gentle = ClimbInput(length_m=5000, gain_m=200, avg_gradient_pct=4.0)
        climb_steep = ClimbInput(length_m=5000, gain_m=500, avg_gradient_pct=10.0)
        settings = SolverSettings(ftp=250, mass_kg=75)

        result_gentle = estimate_climb_times(climb_gentle, settings)
        result_steep = estimate_climb_times(climb_steep, settings)

        # Get a common power level
        common_power = list(result_gentle.minutes_by_power.keys())[0]

        assert result_steep.minutes_by_power[common_power] > result_gentle.minutes_by_power[common_power]

    def test_heavier_rider_slower(self):
        """Test that heavier riders are slower on climbs."""
        climb = ClimbInput(length_m=5000, gain_m=400)
        settings_light = SolverSettings(ftp=250, mass_kg=65)
        settings_heavy = SolverSettings(ftp=250, mass_kg=85)

        result_light = estimate_climb_times(climb, settings_light)
        result_heavy = estimate_climb_times(climb, settings_heavy)

        # Compare at same power
        common_power = list(result_light.minutes_by_power.keys())[0]
        assert result_heavy.minutes_by_power[common_power] > result_light.minutes_by_power[common_power]


class TestEstimateClimbTimeAtPower:
    """Tests for single-power time estimation."""

    def test_specific_power(self):
        """Test time at specific power."""
        climb = ClimbInput(length_m=10000, gain_m=800)
        settings = SolverSettings(ftp=250, mass_kg=75)

        time_secs = estimate_climb_time_at_power(climb, 250, settings)

        # Should take between 20-60 minutes
        assert 20 * 60 < time_secs < 60 * 60

    def test_zero_power(self):
        """Test with near-zero power."""
        climb = ClimbInput(length_m=1000, gain_m=100)
        settings = SolverSettings(ftp=250, mass_kg=75)

        time_secs = estimate_climb_time_at_power(climb, 1, settings)

        # Should be very long (capped at 999 minutes)
        assert time_secs >= 999 * 60


class TestFormatTime:
    """Tests for time formatting."""

    def test_minutes_only(self):
        """Test formatting minutes only."""
        assert format_time(1800) == "30m 0s"

    def test_with_seconds(self):
        """Test formatting with seconds."""
        assert format_time(1830) == "30m 30s"

    def test_hours(self):
        """Test formatting with hours."""
        result = format_time(3720)  # 1h 2m 0s
        assert "1h" in result

    def test_infinity(self):
        """Test formatting infinity."""
        assert format_time(999 * 60) == "N/A"


class TestCalculateVAM:
    """Tests for VAM calculation."""

    def test_normal_vam(self):
        """Test normal VAM calculation."""
        # 1000m gain in 1 hour = 1000 m/h VAM
        vam = calculate_vam(1000, 3600)
        assert vam == pytest.approx(1000.0)

    def test_pro_vam(self):
        """Test pro-level VAM."""
        # 1800m in 1.5 hours = 1200 m/h (elite level)
        vam = calculate_vam(1800, 5400)
        assert vam == pytest.approx(1200.0)

    def test_zero_time(self):
        """Test with zero time."""
        vam = calculate_vam(1000, 0)
        assert vam == 0.0

    def test_negative_time(self):
        """Test with negative time."""
        vam = calculate_vam(1000, -100)
        assert vam == 0.0
