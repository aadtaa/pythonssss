"""
TCX (Training Center XML) file parser.
"""

from datetime import datetime
from pathlib import Path
from typing import Union

from lxml import etree
from dateutil.parser import parse as parse_datetime

from .models import Trackpoint, Lap, Activity, TCXData


class TCXParser:
    """
    Parser for TCX (Training Center XML) files.

    TCX is an XML-based file format used by Garmin and other fitness devices
    to store workout data including GPS tracks, heart rate, cadence, etc.
    """

    # TCX namespace
    NAMESPACES = {
        "tcx": "http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2",
        "ae": "http://www.garmin.com/xmlschemas/ActivityExtension/v2",
    }

    def __init__(self):
        self._tree: etree._ElementTree | None = None
        self._root: etree._Element | None = None

    def parse(self, source: Union[str, Path, bytes]) -> TCXData:
        """
        Parse a TCX file from a file path or bytes.

        Args:
            source: File path (string or Path) or raw XML bytes

        Returns:
            TCXData object containing all parsed activities
        """
        if isinstance(source, (str, Path)):
            self._tree = etree.parse(str(source))
            self._root = self._tree.getroot()
        else:
            self._root = etree.fromstring(source)

        return self._parse_tcx()

    def parse_string(self, xml_string: str) -> TCXData:
        """
        Parse TCX data from an XML string.

        Args:
            xml_string: TCX XML content as string

        Returns:
            TCXData object containing all parsed activities
        """
        return self.parse(xml_string.encode("utf-8"))

    def _parse_tcx(self) -> TCXData:
        """Parse the root TCX element."""
        data = TCXData()

        # Find all activities
        activities_elem = self._root.find("tcx:Activities", self.NAMESPACES)
        if activities_elem is not None:
            for activity_elem in activities_elem.findall("tcx:Activity", self.NAMESPACES):
                activity = self._parse_activity(activity_elem)
                data.activities.append(activity)

        return data

    def _parse_activity(self, elem: etree._Element) -> Activity:
        """Parse an Activity element."""
        sport = elem.get("Sport", "Unknown")

        # Parse activity ID (timestamp)
        id_elem = elem.find("tcx:Id", self.NAMESPACES)
        activity_id = parse_datetime(id_elem.text) if id_elem is not None else datetime.now()

        activity = Activity(sport=sport, activity_id=activity_id)

        # Parse notes
        notes_elem = elem.find("tcx:Notes", self.NAMESPACES)
        if notes_elem is not None and notes_elem.text:
            activity.notes = notes_elem.text

        # Parse creator info
        creator_elem = elem.find("tcx:Creator", self.NAMESPACES)
        if creator_elem is not None:
            name_elem = creator_elem.find("tcx:Name", self.NAMESPACES)
            if name_elem is not None and name_elem.text:
                activity.creator_name = name_elem.text
            version_elem = creator_elem.find("tcx:Version", self.NAMESPACES)
            if version_elem is not None:
                major = version_elem.findtext("tcx:VersionMajor", "0", self.NAMESPACES)
                minor = version_elem.findtext("tcx:VersionMinor", "0", self.NAMESPACES)
                activity.creator_version = f"{major}.{minor}"

        # Parse laps
        for lap_elem in elem.findall("tcx:Lap", self.NAMESPACES):
            lap = self._parse_lap(lap_elem)
            activity.laps.append(lap)

        return activity

    def _parse_lap(self, elem: etree._Element) -> Lap:
        """Parse a Lap element."""
        start_time = parse_datetime(elem.get("StartTime"))

        # Required fields
        total_time = float(elem.findtext("tcx:TotalTimeSeconds", "0", self.NAMESPACES))
        distance = float(elem.findtext("tcx:DistanceMeters", "0", self.NAMESPACES))

        lap = Lap(
            start_time=start_time,
            total_time_seconds=total_time,
            distance_meters=distance,
        )

        # Optional fields
        max_speed = elem.findtext("tcx:MaximumSpeed", None, self.NAMESPACES)
        if max_speed:
            lap.maximum_speed = float(max_speed)

        calories = elem.findtext("tcx:Calories", None, self.NAMESPACES)
        if calories:
            lap.calories = int(calories)

        intensity = elem.findtext("tcx:Intensity", None, self.NAMESPACES)
        if intensity:
            lap.intensity = intensity

        cadence = elem.findtext("tcx:Cadence", None, self.NAMESPACES)
        if cadence:
            lap.cadence = int(cadence)

        trigger = elem.findtext("tcx:TriggerMethod", None, self.NAMESPACES)
        if trigger:
            lap.trigger_method = trigger

        # Heart rate
        hr_elem = elem.find("tcx:AverageHeartRateBpm", self.NAMESPACES)
        if hr_elem is not None:
            value = hr_elem.findtext("tcx:Value", None, self.NAMESPACES)
            if value:
                lap.average_heart_rate_bpm = int(float(value))

        hr_max_elem = elem.find("tcx:MaximumHeartRateBpm", self.NAMESPACES)
        if hr_max_elem is not None:
            value = hr_max_elem.findtext("tcx:Value", None, self.NAMESPACES)
            if value:
                lap.maximum_heart_rate_bpm = int(float(value))

        # Parse track/trackpoints
        track_elem = elem.find("tcx:Track", self.NAMESPACES)
        if track_elem is not None:
            for tp_elem in track_elem.findall("tcx:Trackpoint", self.NAMESPACES):
                trackpoint = self._parse_trackpoint(tp_elem)
                lap.trackpoints.append(trackpoint)

        return lap

    def _parse_trackpoint(self, elem: etree._Element) -> Trackpoint:
        """Parse a Trackpoint element."""
        time_str = elem.findtext("tcx:Time", None, self.NAMESPACES)
        time = parse_datetime(time_str) if time_str else datetime.now()

        trackpoint = Trackpoint(time=time)

        # Position (GPS coordinates)
        position_elem = elem.find("tcx:Position", self.NAMESPACES)
        if position_elem is not None:
            lat = position_elem.findtext("tcx:LatitudeDegrees", None, self.NAMESPACES)
            lon = position_elem.findtext("tcx:LongitudeDegrees", None, self.NAMESPACES)
            if lat:
                trackpoint.latitude = float(lat)
            if lon:
                trackpoint.longitude = float(lon)

        # Altitude
        altitude = elem.findtext("tcx:AltitudeMeters", None, self.NAMESPACES)
        if altitude:
            trackpoint.altitude_meters = float(altitude)

        # Distance
        distance = elem.findtext("tcx:DistanceMeters", None, self.NAMESPACES)
        if distance:
            trackpoint.distance_meters = float(distance)

        # Heart rate
        hr_elem = elem.find("tcx:HeartRateBpm", self.NAMESPACES)
        if hr_elem is not None:
            value = hr_elem.findtext("tcx:Value", None, self.NAMESPACES)
            if value:
                trackpoint.heart_rate_bpm = int(float(value))

        # Cadence
        cadence = elem.findtext("tcx:Cadence", None, self.NAMESPACES)
        if cadence:
            trackpoint.cadence = int(cadence)

        # Extensions (speed, power, etc.)
        self._parse_extensions(elem, trackpoint)

        return trackpoint

    def _parse_extensions(self, elem: etree._Element, trackpoint: Trackpoint) -> None:
        """Parse trackpoint extensions (speed, power, etc.)."""
        extensions_elem = elem.find("tcx:Extensions", self.NAMESPACES)
        if extensions_elem is None:
            return

        # ActivityExtension (Garmin)
        tpx_elem = extensions_elem.find("ae:TPX", self.NAMESPACES)
        if tpx_elem is not None:
            speed = tpx_elem.findtext("ae:Speed", None, self.NAMESPACES)
            if speed:
                trackpoint.speed = float(speed)

            watts = tpx_elem.findtext("ae:Watts", None, self.NAMESPACES)
            if watts:
                trackpoint.power_watts = int(float(watts))

            # RunCadence is stored separately from cycling cadence
            run_cadence = tpx_elem.findtext("ae:RunCadence", None, self.NAMESPACES)
            if run_cadence and trackpoint.cadence is None:
                trackpoint.cadence = int(run_cadence)


def parse_tcx(source: Union[str, Path, bytes]) -> TCXData:
    """
    Convenience function to parse a TCX file.

    Args:
        source: File path (string or Path) or raw XML bytes

    Returns:
        TCXData object containing all parsed activities
    """
    parser = TCXParser()
    return parser.parse(source)


def parse_tcx_string(xml_string: str) -> TCXData:
    """
    Convenience function to parse TCX from a string.

    Args:
        xml_string: TCX XML content as string

    Returns:
        TCXData object containing all parsed activities
    """
    parser = TCXParser()
    return parser.parse_string(xml_string)
