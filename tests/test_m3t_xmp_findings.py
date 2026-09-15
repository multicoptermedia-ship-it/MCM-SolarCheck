from pathlib import Path

from mcm_solarcheck.domain.models import ThermalFrame
from mcm_solarcheck.importers.m3t_xmp import parse_m3t_xmp
from mcm_solarcheck.thermal.analysis import RawAnomalyCandidate
from mcm_solarcheck.thermal.findings import candidate_to_finding


def test_parses_known_m3t_xmp_fields():
    xmp = b'''<?xpacket begin="x"?><x:xmpmeta xmlns:x="adobe:ns:meta/">
    <rdf:Description tiff:Make="DJI" tiff:Model="M3T"
      drone-dji:ImageSource="InfraredCamera" drone-dji:GpsStatus="RTK"
      drone-dji:AltitudeType="RtkAlt" drone-dji:GpsLatitude="+51.056223618"
      drone-dji:GpsLongitude="+6.560170321" drone-dji:AbsoluteAltitude="+112.998"
      drone-dji:GimbalRollDegree="+0.00" drone-dji:GimbalYawDegree="+98.00"
      drone-dji:GimbalPitchDegree="-89.90" drone-dji:FlightRollDegree="-8.80"
      drone-dji:FlightYawDegree="+93.30" drone-dji:FlightPitchDegree="+3.10"
      drone-dji:RtkStdLon="0.00793" drone-dji:RtkStdLat="0.01086"
      drone-dji:RtkStdHgt="0.02012" drone-dji:RtkDiffAge="1.60000"
      drone-dji:UTCAtExposure="2025-08-25T10:14:57.431152" />
    </x:xmpmeta>'''
    result = parse_m3t_xmp(xmp)
    assert result.camera_make == "DJI"
    assert result.camera_model == "M3T"
    assert result.image_source == "InfraredCamera"
    assert result.position.latitude == 51.056223618
    assert result.position.longitude == 6.560170321
    assert result.position.altitude_m == 112.998
    assert result.camera_pose.pitch_deg == -89.90
    assert result.rtk.status == "RTK"
    assert result.rtk.std_lat_m == 0.01086
    assert result.timestamp_utc.isoformat().startswith("2025-08-25T10:14:57.431152")


def test_candidate_becomes_reviewable_finding_without_fake_ground_projection():
    metadata = parse_m3t_xmp(b'''<?xpacket begin="x"?><x:xmpmeta xmlns:x="adobe:ns:meta/">
    <rdf:Description tiff:Model="M3T" drone-dji:GpsStatus="RTK"
      drone-dji:GpsLatitude="51.0" drone-dji:GpsLongitude="6.5"
      drone-dji:RtkStdLat="0.01" /> </x:xmpmeta>''')
    frame = ThermalFrame(
        frame_id="T-0001",
        source_file=Path("DJI_0001_T.JPG"),
        position=metadata.position,
        rtk=metadata.rtk,
        thermal_width=640,
        thermal_height=512,
        thermal_source="DJI M3T raw",
    )
    candidate = RawAnomalyCandidate(12, 34, 20500, 700.0, 20400.0)
    finding = candidate_to_finding(candidate, frame, rank=1)
    assert finding.finding_id == "T-0001:raw:0001"
    assert finding.pixel_x == 12
    assert finding.pixel_y == 34
    assert finding.position == frame.position
    assert finding.temperature_c is None
    assert finding.metadata["coordinate_scope"] == "frame"
    assert finding.metadata["temperature_status"] == "uncalibrated_raw"
