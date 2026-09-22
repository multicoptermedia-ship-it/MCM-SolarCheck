from mcm_solarcheck.domain.models import PVModule
from mcm_solarcheck.pairing.geometry import PixelTransform, unavailable_transform
from mcm_solarcheck.vision.cross_sensor_assignment import assign_thermal_point_to_rgb_module


def transform(error=2.0):
    return PixelTransform(
        "test", True, 640, 512, 4000, 3000,
        ((5.0,0.0,100.0),(0.0,5.0,50.0),(0.0,0.0,1.0)),
        error,
    )


def module(module_id="M-0001", frame="V-0001", polygon=((500,400),(900,400),(900,800),(500,800))):
    return PVModule(module_id, frame, polygon)


def test_validated_transform_assigns_thermal_point_to_rgb_module():
    result = assign_thermal_point_to_rgb_module(
        thermal_x=100, thermal_y=100, transform=transform(),
        rgb_modules=(module(),), rgb_frame_id="V-0001",
    )
    assert result.rgb_point == (600.0, 550.0)
    assert result.module_id == "M-0001"
    assert result.status == "assigned"


def test_unvalidated_transform_refuses_assignment():
    result = assign_thermal_point_to_rgb_module(
        thermal_x=100, thermal_y=100, transform=unavailable_transform(),
        rgb_modules=(module(),), rgb_frame_id="V-0001",
    )
    assert result.module_id is None
    assert result.status == "transform_unvalidated"


def test_point_near_module_edge_is_ambiguous_using_registration_error():
    result = assign_thermal_point_to_rgb_module(
        thermal_x=80.2, thermal_y=100, transform=transform(error=2.0),
        rgb_modules=(module(),), rgb_frame_id="V-0001",
    )
    assert result.rgb_point == (501.0, 550.0)
    assert result.module_id is None
    assert result.status == "ambiguous_edge"


def test_wrong_rgb_frame_modules_are_not_used():
    result = assign_thermal_point_to_rgb_module(
        thermal_x=100, thermal_y=100, transform=transform(),
        rgb_modules=(module(frame="V-9999"),), rgb_frame_id="V-0001",
    )
    assert result.status == "no_module"


def test_overlapping_modules_are_never_silently_resolved():
    result = assign_thermal_point_to_rgb_module(
        thermal_x=100, thermal_y=100, transform=transform(),
        rgb_modules=(module("M-0001"), module("M-0002")), rgb_frame_id="V-0001",
    )
    assert result.module_id is None
    assert result.status == "ambiguous_overlap"
    assert result.candidates == ("M-0001", "M-0002")


def test_unexpected_thermal_geometry_fails_closed():
 t=PixelTransform("test",True,320,256,4000,3000,((1,0,0),(0,1,0),(0,0,1)),1)
 r=assign_thermal_point_to_rgb_module(thermal_x=10,thermal_y=10,transform=t,rgb_modules=(module(),),rgb_frame_id="V-0001")
 assert r.status=="thermal_geometry_mismatch" and r.module_id is None
