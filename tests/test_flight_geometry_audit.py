"""Synthetic XMP-only tests: no real roof images or coordinates in GitHub."""
from io import BytesIO
from zipfile import ZipFile

from PIL import Image

from mcm_solarcheck.services.flight_geometry_audit import audit_dji_flight_geometry


def _jpeg(source, status, altitude):
    image = Image.new("RGB", (16, 12))
    buffer = BytesIO()
    image.save(buffer, format="JPEG")
    raw = buffer.getvalue()
    xmp = (
        '<x:xmpmeta xmlns:x="adobe:ns:meta/" xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">'
        '<rdf:RDF><rdf:Description xmlns:d="http://www.dji.com/drone-dji/1.0/" '
        f'd:ImageSource="{source}" d:GpsStatus="{status}" d:AltitudeType="{altitude}" '
        'd:GimbalPitchDegree="-40" d:GimbalRollDegree="0" d:GimbalYawDegree="70" '
        'd:GpsLatitude="1" d:GpsLongitude="2"/></rdf:RDF></x:xmpmeta>'
    ).encode()
    segment = b"\xff\xe1" + (len(xmp) + 31).to_bytes(2, "big") + b"http://ns.adobe.com/xap/1.0/\x00" + xmp
    return raw[:2] + segment + raw[2:]


def test_mismatched_reference_conventions_are_flagged(tmp_path):
    path = tmp_path / "flight.zip"
    with ZipFile(path, "w") as archive:
        archive.writestr("DJI_20260725154422_0001_V.JPG", _jpeg("ZoomCamera", "Normal", "GpsFusionAlt"))
        archive.writestr("DJI_20260725154422_0001_T.JPG", _jpeg("InfraredCamera", "RTK", "RtkAlt"))
    audit = audit_dji_flight_geometry(path)
    assert audit.rgb_count == audit.thermal_count == 1
    assert audit.rgb_sources == ("ZoomCamera",)
    assert audit.thermal_sources == ("InfraredCamera",)
    assert any("differ" in message for message in audit.diagnostics)
    assert audit.ready_for_metric_orthophoto is False
