"""Entire new multi-ZIP RGB intake: synthetic JPEG/XMP, typo suffix and privacy."""
from io import BytesIO
import json
from zipfile import ZipFile

import pytest
from PIL import Image

from mcm_solarcheck.services.rgb_flight_zip_series import read_private_rgb_zip_series
from mcm_solarcheck.services.rgb_flight_zip_series_cli import main


def _image(number):
    output=BytesIO()
    Image.new("RGB",(400,300),(120,80,number)).save(output,format="JPEG")
    xmp=(f'''<?xpacket begin=" "/><x:xmpmeta xmlns:x="adobe:ns:meta/"
        xmlns:drone-dji="http://www.dji.com/drone-dji/1.0/"
        drone-dji:GpsLatitude="50.9999" drone-dji:GpsLongitude="7.2222"
        drone-dji:AbsoluteAltitude="+111.22"
        drone-dji:GimbalYawDegree="2.0" drone-dji:GimbalPitchDegree="-90.0"
        drone-dji:GimbalRollDegree="0.0" drone-dji:FlightYawDegree="3.0"
        drone-dji:FlightPitchDegree="0.0" drone-dji:FlightRollDegree="0.0"
        drone-dji:GpsStatus="50"
        drone-dji:RtkStdLat="0.02" drone-dji:RtkStdLon="0.02"
        drone-dji:RtkStdHgt="0.04"
        drone-dji:DewarpData="0,0,0"/></x:xmpmeta>''').encode("utf-8")
    segment=bytes((0xFF,0xE1))+(len(xmp)+2).to_bytes(2,"big")+xmp
    # Return a legal JPEG with an additional metadata APP1 segment.
    return output.getvalue()[:2]+segment+output.getvalue()[2:]


def _archive(path,counters):
    with ZipFile(path,"w") as z:
        for i in counters:
            z.writestr(f"flight/DJI_20260825112000_{i:04d}_V.JPG",_image(i))
        z.writestr("flight/README.txt",b"metadata file")


def test_rgb_tip_is_zip_and_entire_series_is_deduplicated_and_private(tmp_path,capsys):
    a=tmp_path/"RGB1(1).zip"
    b=tmp_path/"RGB2.tip"
    c=tmp_path/"RGB4.zip"
    _archive(a,(121,122))
    _archive(b,(123,124))
    _archive(c,(125,))
    before={p:p.read_bytes() for p in (a,b,c)}
    series=read_private_rgb_zip_series((a,b,c))
    report=series.privacy_safe_summary()
    assert report["archive_count"]==3
    assert report["unique_rgb_frames"]==5
    assert report["discarded_non_rgb_entries"]==3
    assert report["frames_with_gnss_coordinates"]==5
    assert report["frames_with_gnss_altitude"]==5
    assert report["frames_with_complete_gimbal_angles"]==5
    assert report["frames_with_rtk_standard_deviations"]==5
    assert report["frames_with_dewarp_metadata"]==5
    assert not report["rgb_orthophoto_created"]
    assert [x.frame_id for x in series.frames]==[
        "V-0121","V-0122","V-0123","V-0124","V-0125"
    ]
    reports=tmp_path/"reports"
    reports.mkdir()
    output=reports/"private-report.json"
    assert main([
        "--rgb-archive",str(a),"--rgb-archive",str(b),
        "--rgb-archive",str(c),"--report",str(output),
    ])==0
    out=output.read_text()
    assert json.loads(out)["unique_rgb_frames"]==5
    for private in ("50.9999","7.2222","20260825112000","DJI_","RGB1"):
        assert private not in out
        assert private not in capsys.readouterr().out
    assert {p:p.read_bytes() for p in (a,b,c)}==before


def test_duplicate_same_rgb_between_zips_never_conflated(tmp_path):
    a,b=tmp_path/"a.zip",tmp_path/"b.tip"
    _archive(a,(121,122))
    _archive(b,(122,123))
    with pytest.raises(ValueError,match="duplicate"):
        read_private_rgb_zip_series((a,b))


def test_nonzip_tip_and_unsafe_entry_are_rejected(tmp_path):
    a=tmp_path/"wrong.tip"
    a.write_bytes(b"not a zip")
    with pytest.raises(ValueError,match="invalid RGB ZIP bytes"):
        read_private_rgb_zip_series((a,))
    b=tmp_path/"unsafe.zip"
    with ZipFile(b,"w") as z:
        z.writestr("../DJI_20260825112000_0121_V.JPG",_image(121))
    with pytest.raises(ValueError,match="unsafe member path"):
        read_private_rgb_zip_series((b,))


def test_invalid_gnss_data_blocks_partial_series(tmp_path):
    a=tmp_path/"GPS.zip"
    data=_image(121).replace(b"50.9999",b"99.9999")
    with ZipFile(a,"w") as z:
        z.writestr("DJI_20260825112000_0121_V.JPG",data)
    with pytest.raises(ValueError,match="GNSS position"):
        read_private_rgb_zip_series((a,))


def test_duplicate_archive_path_and_cancellation(tmp_path):
    a=tmp_path/"one.zip"
    _archive(a,(120,121))
    with pytest.raises(ValueError,match="unique"):
        read_private_rgb_zip_series((a,a))
    with pytest.raises(RuntimeError,match="cancelled"):
        read_private_rgb_zip_series((a,),should_cancel=lambda:True)
