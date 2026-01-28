"""Tests for TCX parser."""

import pytest
from datetime import datetime

from tcx_parser import TCXParser, TCXData, Activity, Lap, Trackpoint


SAMPLE_TCX = """<?xml version="1.0" encoding="UTF-8"?>
<TrainingCenterDatabase
    xmlns="http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2">
    <Activities>
        <Activity Sport="Running">
            <Id>2024-01-15T08:30:00Z</Id>
            <Lap StartTime="2024-01-15T08:30:00Z">
                <TotalTimeSeconds>1800</TotalTimeSeconds>
                <DistanceMeters>5000</DistanceMeters>
                <Calories>350</Calories>
                <Intensity>Active</Intensity>
                <TriggerMethod>Manual</TriggerMethod>
                <AverageHeartRateBpm><Value>140</Value></AverageHeartRateBpm>
                <MaximumHeartRateBpm><Value>165</Value></MaximumHeartRateBpm>
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
                        <AltitudeMeters>30.0</AltitudeMeters>
                        <DistanceMeters>500</DistanceMeters>
                        <HeartRateBpm><Value>145</Value></HeartRateBpm>
                    </Trackpoint>
                </Track>
            </Lap>
        </Activity>
    </Activities>
</TrainingCenterDatabase>
"""


class TestTCXParser:
    """Tests for TCXParser class."""

    def test_parse_string(self):
        """Test parsing TCX from string."""
        parser = TCXParser()
        data = parser.parse_string(SAMPLE_TCX)

        assert isinstance(data, TCXData)
        assert len(data.activities) == 1

    def test_parse_bytes(self):
        """Test parsing TCX from bytes."""
        parser = TCXParser()
        data = parser.parse(SAMPLE_TCX.encode("utf-8"))

        assert isinstance(data, TCXData)
        assert len(data.activities) == 1

    def test_activity_parsing(self):
        """Test activity fields are parsed correctly."""
        parser = TCXParser()
        data = parser.parse_string(SAMPLE_TCX)
        activity = data.activities[0]

        assert isinstance(activity, Activity)
        assert activity.sport == "Running"
        assert activity.activity_id.year == 2024
        assert activity.activity_id.month == 1
        assert activity.activity_id.day == 15

    def test_lap_parsing(self):
        """Test lap fields are parsed correctly."""
        parser = TCXParser()
        data = parser.parse_string(SAMPLE_TCX)
        lap = data.activities[0].laps[0]

        assert isinstance(lap, Lap)
        assert lap.total_time_seconds == 1800
        assert lap.distance_meters == 5000
        assert lap.calories == 350
        assert lap.intensity == "Active"
        assert lap.trigger_method == "Manual"
        assert lap.average_heart_rate_bpm == 140
        assert lap.maximum_heart_rate_bpm == 165

    def test_trackpoint_parsing(self):
        """Test trackpoint fields are parsed correctly."""
        parser = TCXParser()
        data = parser.parse_string(SAMPLE_TCX)
        trackpoints = data.activities[0].laps[0].trackpoints

        assert len(trackpoints) == 2

        tp1 = trackpoints[0]
        assert isinstance(tp1, Trackpoint)
        assert tp1.latitude == pytest.approx(37.7749)
        assert tp1.longitude == pytest.approx(-122.4194)
        assert tp1.altitude_meters == 10.0
        assert tp1.distance_meters == 0
        assert tp1.heart_rate_bpm == 120

        tp2 = trackpoints[1]
        assert tp2.altitude_meters == 30.0
        assert tp2.distance_meters == 500

    def test_trackpoint_has_position(self):
        """Test trackpoint.has_position property."""
        parser = TCXParser()
        data = parser.parse_string(SAMPLE_TCX)
        tp = data.activities[0].laps[0].trackpoints[0]

        assert tp.has_position is True
        assert tp.has_altitude is True

    def test_activity_properties(self):
        """Test activity computed properties."""
        parser = TCXParser()
        data = parser.parse_string(SAMPLE_TCX)
        activity = data.activities[0]

        assert activity.total_time_seconds == 1800
        assert activity.total_distance_meters == 5000
        assert len(activity.all_trackpoints) == 2

    def test_elevation_properties(self):
        """Test elevation-related properties."""
        parser = TCXParser()
        data = parser.parse_string(SAMPLE_TCX)
        activity = data.activities[0]

        # 10m to 30m = 20m gain
        assert activity.elevation_gain == pytest.approx(20.0)
        assert activity.elevation_loss == pytest.approx(0.0)
        assert activity.min_altitude == 10.0
        assert activity.max_altitude == 30.0


class TestEmptyTCX:
    """Tests for handling empty or minimal TCX files."""

    def test_empty_activities(self):
        """Test parsing TCX with no activities."""
        tcx = """<?xml version="1.0"?>
        <TrainingCenterDatabase xmlns="http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2">
            <Activities></Activities>
        </TrainingCenterDatabase>
        """
        parser = TCXParser()
        data = parser.parse_string(tcx)

        assert len(data.activities) == 0
        assert data.total_elevation_gain == 0
        assert data.total_elevation_loss == 0

    def test_empty_laps(self):
        """Test parsing activity with no laps."""
        tcx = """<?xml version="1.0"?>
        <TrainingCenterDatabase xmlns="http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2">
            <Activities>
                <Activity Sport="Biking">
                    <Id>2024-01-01T00:00:00Z</Id>
                </Activity>
            </Activities>
        </TrainingCenterDatabase>
        """
        parser = TCXParser()
        data = parser.parse_string(tcx)

        assert len(data.activities) == 1
        assert len(data.activities[0].laps) == 0
        assert data.activities[0].total_time_seconds == 0


class TestMultipleLaps:
    """Tests for activities with multiple laps."""

    def test_multiple_laps(self):
        """Test parsing activity with multiple laps."""
        tcx = """<?xml version="1.0"?>
        <TrainingCenterDatabase xmlns="http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2">
            <Activities>
                <Activity Sport="Running">
                    <Id>2024-01-01T00:00:00Z</Id>
                    <Lap StartTime="2024-01-01T00:00:00Z">
                        <TotalTimeSeconds>600</TotalTimeSeconds>
                        <DistanceMeters>1000</DistanceMeters>
                        <Track>
                            <Trackpoint>
                                <Time>2024-01-01T00:00:00Z</Time>
                                <AltitudeMeters>100</AltitudeMeters>
                            </Trackpoint>
                        </Track>
                    </Lap>
                    <Lap StartTime="2024-01-01T00:10:00Z">
                        <TotalTimeSeconds>600</TotalTimeSeconds>
                        <DistanceMeters>1000</DistanceMeters>
                        <Track>
                            <Trackpoint>
                                <Time>2024-01-01T00:10:00Z</Time>
                                <AltitudeMeters>150</AltitudeMeters>
                            </Trackpoint>
                        </Track>
                    </Lap>
                </Activity>
            </Activities>
        </TrainingCenterDatabase>
        """
        parser = TCXParser()
        data = parser.parse_string(tcx)

        activity = data.activities[0]
        assert len(activity.laps) == 2
        assert activity.total_time_seconds == 1200
        assert activity.total_distance_meters == 2000
        assert len(activity.all_trackpoints) == 2
