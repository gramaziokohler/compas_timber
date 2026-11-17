import math
import xml.etree.ElementTree as ET

import pytest
from compas.data import json_dumps
from compas.data import json_loads
from compas.geometry import Box
from compas.geometry import Frame
from compas_brep import Brep

from compas_timber.elements import Beam
from compas_timber.fabrication.btlx import BTLxWriter
from compas_timber.fabrication.profile_cambered import ProfileCambered
from compas_timber.fabrication.profile_front import ProfileFront
from compas_timber.fabrication.profile_head import ProfileArc
from compas_timber.fabrication.profile_head import ProfileHead
from compas_timber.fabrication.round_arch import RoundArch

LENGTH, WIDTH, HEIGHT = 1000.0, 100.0, 200.0


def cut(processing):
    """Returns the beam with the processing, the geometry and the removed area of the profile."""
    beam = Beam(Frame.worldXY(), LENGTH, WIDTH, HEIGHT)
    beam.add_features([processing])
    geometry = beam.compute_elementgeometry(include_features=True)
    assert not beam.debug_info
    return beam, geometry, (LENGTH * WIDTH * HEIGHT - geometry.volume) / beam.get_dimensions_relative_to_side(processing.ref_side_index)[0]


def removed_depth(beam, geometry, ref_side_index, x):
    """The depth of the material missing at x, in the half of the beam next to the reference side."""
    side = beam.ref_sides[ref_side_index]
    width, height = beam.get_dimensions_relative_to_side(ref_side_index)
    thickness = 0.02
    probe = Box(thickness, width, height / 2.0, Frame(side.point + side.xaxis * x + side.yaxis * (width / 2.0) - side.zaxis * (height / 4.0), side.xaxis, side.yaxis))
    material = sum(piece.volume for piece in Brep.from_boolean_intersection(geometry, Brep.from_box(probe)))
    return height / 2.0 - material / (thickness * width)


@pytest.mark.parametrize(
    "cls,kwargs",
    [
        (ProfileFront, {"orientation": "middle"}),
        (ProfileFront, {"start_x": 100001.0}),
        (ProfileFront, {"arc_shape": "flat"}),
        (ProfileFront, {"depth": -1.0}),
        (ProfileFront, {"depth": 1001.0}),
        (ProfileFront, {"start_rotation": 91.0}),
        (ProfileFront, {"start_rotation": -91.0}),
        (ProfileFront, {"rotation1": 181.0}),
        (ProfileFront, {"radius1": 1001.0}),
        (ProfileFront, {"rotation2": -1.0}),
        (ProfileFront, {"radius2": -1.0}),
        (ProfileCambered, {"orientation": "middle"}),
        (ProfileCambered, {"start_x": -100001.0}),
        (ProfileCambered, {"length": -1.0}),
        (ProfileCambered, {"length": 100001.0}),
        (ProfileCambered, {"start_depth": 1001.0}),
        (ProfileCambered, {"max_depth": -1.0}),
        (ProfileCambered, {"min_depth": 1001.0}),
        (ProfileCambered, {"end_depth": -1.0}),
        (ProfileCambered, {"premill": "square"}),
        (RoundArch, {"start_x": 100001.0}),
        (RoundArch, {"length": -1.0}),
        (RoundArch, {"camber": 1001.0}),
        (RoundArch, {"arc_shape": "flat"}),
        (RoundArch, {"premill": "square"}),
        (ProfileHead, {"orientation": "middle"}),
        (ProfileHead, {"start_x": 100001.0}),
        (ProfileHead, {"lap_length": -1.0}),
        (ProfileHead, {"lap_height": 1001.0}),
        (ProfileArc, {"radius": 1001.0}),
        (ProfileArc, {"length": -1.0}),
        (ProfileArc, {"camber": 1001.0}),
        (ProfileArc, {"displacement": -1.0}),
        (ProfileArc, {"arc_shape": "flat"}),
    ],
)
def test_limits_are_rejected(cls, kwargs):
    with pytest.raises(ValueError):
        cls(**kwargs)


def test_profile_front_params():
    assert dict(ProfileFront().params.as_dict()) == {
        "Orientation": "start",
        "StartX": "0.000",
        "ArcShape": "convex",
        "Depth": "0.000",
        "StartRotation": "0.000",
        "Rotation1": "90.000",
        "Radius1": "250.000",
        "Rotation2": "90.000",
        "Radius2": "250.000",
    }
    assert list(ProfileFront().params.as_dict()) == ["Orientation", "StartX", "ArcShape", "Depth", "StartRotation", "Rotation1", "Radius1", "Rotation2", "Radius2"]


def test_profile_cambered_params():
    params = ProfileCambered(orientation="end", start_x=10.0, length=300.0, premill="round").params.as_dict()
    assert list(params.items()) == [
        ("Orientation", "end"),
        ("StartX", "10.000"),
        ("Length", "300.000"),
        ("StartDepth", "40.000"),
        ("MaxDepth", "60.000"),
        ("MinDepth", "10.000"),
        ("EndDepth", "40.000"),
        ("Premill", "round"),
    ]


def test_round_arch_params():
    assert list(RoundArch().params.as_dict().items()) == [("StartX", "0.000"), ("Length", "500.000"), ("Camber", "30.000"), ("ArcShape", "concave"), ("Premill", "angular")]


def test_profile_head_params():
    params = ProfileHead().params.as_dict()
    assert list(params) == ["Orientation", "StartX", "Arc1", "LapLength", "LapHeight"]
    assert (params["Orientation"], params["StartX"], params["LapLength"], params["LapHeight"]) == ("start", "0.000", "10.000", "10.000")


def test_profile_arc_xml():
    arc = ProfileArc(length=30.0, height=20.0, camber=5.0, arc_shape="concave", lap_length=1.0, lap_height=2.0, displacement=3.0)
    processing = ProfileHead(arc1=ProfileArc(), arc2=arc)

    arc1 = BTLxWriter()._element_from_complex_param(processing.arc1)
    arc2 = BTLxWriter()._element_from_complex_param(processing.arc2)

    assert ET.tostring(arc1, encoding="unicode") == '<Arc1 ArcShape="convex" LapLength="10.000" LapHeight="10.000" Displacement="10.000"><QuarterArc Radius="50.000" /></Arc1>'
    assert ET.tostring(arc2, encoding="unicode") == (
        '<Arc2 ArcShape="concave" LapLength="1.000" LapHeight="2.000" Displacement="3.000"><Segment Length="30.000" Height="20.000" Camber="5.000" /></Arc2>'
    )
    assert ProfileArc.from_xml(arc2).__data__ == arc.__data__
    assert ProfileArc.from_xml(arc1).__data__ == ProfileArc().__data__


def test_same_arc_for_both_steps_keeps_both_element_names():
    arc = ProfileArc()
    processing = ProfileHead(arc1=arc, arc2=arc)
    assert (processing.arc1.tag, processing.arc2.tag) == ("Arc1", "Arc2")


@pytest.mark.parametrize(
    "processing,names",
    [
        (ProfileFront(start_x=10.0, depth=2.0, radius1=3.0, radius2=4.0, start_rotation=10.0, rotation1=20.0, rotation2=30.0), ("start_x", "depth", "radius1", "radius2")),
        (
            ProfileCambered(start_x=10.0, length=2.0, start_depth=3.0, max_depth=4.0, min_depth=1.0, end_depth=2.0),
            ("start_x", "length", "start_depth", "max_depth", "min_depth", "end_depth"),
        ),
        (RoundArch(start_x=10.0, length=2.0, camber=3.0), ("start_x", "length", "camber")),
        (ProfileHead(start_x=10.0, lap_length=2.0, lap_height=3.0), ("start_x", "lap_length", "lap_height")),
    ],
)
def test_scale(processing, names):
    scaled = processing.scaled(2.0)
    for name in names:
        assert getattr(scaled, name) == 2.0 * getattr(processing, name)
    for name in ("start_rotation", "rotation1", "rotation2"):
        assert getattr(scaled, name, None) == getattr(processing, name, None)


def test_scale_profile_arcs():
    processing = ProfileHead(arc1=ProfileArc(radius=10.0), arc2=ProfileArc(length=1.0, height=2.0, camber=3.0, lap_length=4.0, lap_height=5.0, displacement=6.0))
    scaled = processing.scaled(2.0)
    assert scaled.arc1.radius == 20.0 and scaled.arc1.lap_length == 20.0
    assert (scaled.arc2.length, scaled.arc2.height, scaled.arc2.camber) == (2.0, 4.0, 6.0)
    assert (scaled.arc2.lap_length, scaled.arc2.lap_height, scaled.arc2.displacement) == (8.0, 10.0, 12.0)
    assert scaled.arc2.radius is None
    assert processing.arc1.radius == 10.0


@pytest.mark.parametrize(
    "processing",
    [
        ProfileFront(
            orientation="end", start_x=10.0, arc_shape="concave", depth=2.0, start_rotation=5.0, rotation1=20.0, radius1=3.0, rotation2=30.0, radius2=4.0, ref_side_index=2
        ),
        ProfileCambered(orientation="end", start_x=10.0, length=20.0, premill="round", ref_side_index=1),
        RoundArch(start_x=10.0, length=2.0, camber=3.0, arc_shape="convex", premill="round", ref_side_index=3),
    ],
)
def test_json_round_trip(processing):
    assert json_loads(json_dumps(processing)).__data__ == processing.__data__


def test_profile_head_json_round_trip():
    processing = ProfileHead(start_x=5.0, arc1=ProfileArc(radius=20.0), arc2=ProfileArc(length=1.0, height=2.0, camber=3.0, arc_shape="concave"), ref_side_index=1)
    restored = json_loads(json_dumps(processing))
    assert restored.arc1.__data__ == processing.arc1.__data__
    assert restored.arc2.__data__ == processing.arc2.__data__
    assert restored.arc2.tag == "Arc2"
    assert restored.start_x == 5.0


def segment_area(length, camber):
    radius = (length**2 / 4.0 + camber**2) / (2.0 * camber)
    angle = 4.0 * math.atan(2.0 * camber / length)
    return radius**2 * (angle - math.sin(angle)) / 2.0


def test_round_arch_concave():
    beam, geometry, area = cut(RoundArch(start_x=500.0, length=400.0, camber=30.0))
    assert area == pytest.approx(segment_area(400.0, 30.0))
    assert removed_depth(beam, geometry, 0, 500.0) == pytest.approx(30.0, abs=1e-3)
    assert removed_depth(beam, geometry, 0, 250.0) == pytest.approx(0.0, abs=1e-6)
    assert removed_depth(beam, geometry, 2, 500.0) == pytest.approx(0.0, abs=1e-6)


def test_round_arch_convex_angular_premill_is_normal_to_the_arc():
    beam, geometry, area = cut(RoundArch(start_x=500.0, length=400.0, camber=30.0, arc_shape="convex"))
    slope = math.tan(2.0 * math.atan(2.0 * 30.0 / 400.0))
    assert area == pytest.approx(400.0 * 30.0 - segment_area(400.0, 30.0) + 30.0**2 * slope)
    assert removed_depth(beam, geometry, 0, 500.0) == pytest.approx(0.0, abs=1e-3)
    assert removed_depth(beam, geometry, 0, 300.5) > 25.0
    assert removed_depth(beam, geometry, 0, 699.5) > 25.0
    assert removed_depth(beam, geometry, 0, 280.0) == pytest.approx(0.0, abs=1e-6)


def test_round_arch_convex_round_premill_is_a_wall():
    _, _, area = cut(RoundArch(start_x=500.0, length=400.0, camber=30.0, arc_shape="convex", premill="round"))
    assert area == pytest.approx(400.0 * 30.0 - segment_area(400.0, 30.0))


def test_round_arch_on_another_side():
    beam, geometry, area = cut(RoundArch(start_x=300.0, length=100.0, camber=20.0, ref_side_index=1))
    assert area == pytest.approx(segment_area(100.0, 20.0))
    assert removed_depth(beam, geometry, 1, 300.0) == pytest.approx(20.0, abs=1e-3)
    assert removed_depth(beam, geometry, 3, 300.0) == pytest.approx(0.0, abs=1e-6)


def test_round_arch_without_camber_leaves_the_beam():
    _, _, area = cut(RoundArch(start_x=300.0, length=100.0, camber=0.0))
    assert area == pytest.approx(0.0, abs=1e-6)


@pytest.mark.parametrize("orientation,start_x", [("start", 100.0), ("end", 900.0)])
def test_profile_cambered_reaches_the_depths(orientation, start_x):
    # with equal start and end the curve is odd around its middle, which puts the extrema at 1/2 -+ sqrt(3)/6 of the length
    length = 300.0
    processing = ProfileCambered(orientation=orientation, start_x=start_x, length=length, start_depth=40.0, max_depth=60.0, min_depth=20.0, end_depth=40.0)
    beam, geometry, area = cut(processing)

    slope = 20.0 * 36.0 / math.sqrt(3.0) / 2.0 / length  # of 40 + k t (t - 1/2) (t - 1), at t = 1
    assert area == pytest.approx(100.0 * 40.0 + length * 40.0 + 40.0**2 * slope / 2.0)

    def x(distance):
        return start_x + distance if orientation == "start" else start_x - distance

    assert removed_depth(beam, geometry, 0, x(-50.0)) == pytest.approx(40.0, abs=1e-3)
    assert removed_depth(beam, geometry, 0, x(length * (0.5 - math.sqrt(3.0) / 6.0))) == pytest.approx(60.0, abs=1e-3)
    assert removed_depth(beam, geometry, 0, x(length * (0.5 + math.sqrt(3.0) / 6.0))) == pytest.approx(20.0, abs=1e-3)
    assert removed_depth(beam, geometry, 0, x(length * 0.5)) == pytest.approx(40.0, abs=1e-3)
    assert removed_depth(beam, geometry, 0, x(length + 100.0)) == pytest.approx(0.0, abs=1e-6)


def test_profile_cambered_round_premill_is_a_wall():
    processing = ProfileCambered(start_x=100.0, length=300.0, start_depth=40.0, max_depth=60.0, min_depth=20.0, end_depth=40.0, premill="round")
    beam, geometry, area = cut(processing)
    assert area == pytest.approx(100.0 * 40.0 + 300.0 * 40.0)
    assert removed_depth(beam, geometry, 0, 401.0) == pytest.approx(0.0, abs=1e-6)


def test_profile_cambered_asymmetric_depths():
    processing = ProfileCambered(start_x=100.0, length=300.0, start_depth=5.0, max_depth=50.0, min_depth=10.0, end_depth=45.0, premill="round")
    beam, geometry, _ = cut(processing)
    depths = [removed_depth(beam, geometry, 0, 100.0 + 300.0 * i / 30.0 + 0.1) for i in range(30)]
    assert max(depths) == pytest.approx(50.0, abs=0.3)
    assert min(depths[max(range(30), key=depths.__getitem__) :]) == pytest.approx(10.0, abs=0.3)
    assert removed_depth(beam, geometry, 0, 100.1) == pytest.approx(5.0, abs=1.0)
    assert removed_depth(beam, geometry, 0, 399.9) == pytest.approx(45.0, abs=1.0)


@pytest.mark.parametrize("kwargs", [{"length": 0.0}, {"length": 100.0, "start_depth": 70.0}, {"length": 100.0, "end_depth": 5.0}, {"length": 100.0, "min_depth": 60.0}])
def test_profile_cambered_impossible_depths_are_reported(kwargs):
    beam = Beam(Frame.worldXY(), LENGTH, WIDTH, HEIGHT)
    beam.add_features([ProfileCambered(**kwargs)])
    assert beam.compute_elementgeometry(include_features=True).volume == pytest.approx(LENGTH * WIDTH * HEIGHT)
    assert len(beam.debug_info) == 1


@pytest.mark.parametrize("orientation,start_x", [("start", 100.0), ("end", 900.0)])
def test_profile_front_two_arcs_ending_on_the_reference_side(orientation, start_x):
    processing = ProfileFront(orientation=orientation, start_x=start_x, depth=20.0, radius1=50.0, radius2=20.0)
    beam, geometry, area = cut(processing)
    assert area == pytest.approx(100.0 * 70.0 + 50.0 * 70.0 - math.pi * 50.0**2 / 4.0 + math.pi * 20.0**2 / 4.0)

    def x(distance):
        return start_x + distance if orientation == "start" else start_x - distance

    assert removed_depth(beam, geometry, 0, x(-50.0)) == pytest.approx(70.0, abs=1e-3)  # the start of the first arc continues along its radius
    assert removed_depth(beam, geometry, 0, x(50.0)) == pytest.approx(20.0, abs=1e-3)  # where `depth` is measured
    assert removed_depth(beam, geometry, 0, x(90.0)) == pytest.approx(0.0, abs=1e-6)
    assert removed_depth(beam, geometry, 2, x(-50.0)) == pytest.approx(0.0, abs=1e-6)


def test_profile_front_start_rotation_tilts_the_radius_the_profile_continues_along():
    processing = ProfileFront(start_x=100.0, depth=20.0, start_rotation=30.0, radius1=60.0, rotation1=60.0, rotation2=0.0, radius2=0.0)
    beam, geometry, _ = cut(processing)
    start_x, start_z = 160.0 - 60.0 * math.cos(math.radians(30.0)), -80.0 + 60.0 * math.sin(math.radians(30.0))
    assert removed_depth(beam, geometry, 0, 50.0) == pytest.approx(-start_z - (start_x - 50.0) * math.tan(math.radians(30.0)), abs=1e-2)
    assert removed_depth(beam, geometry, 0, 10.0) == pytest.approx(0.0, abs=1e-6)  # it leaves the reference side before the end of the beam
    assert removed_depth(beam, geometry, 0, 159.5) == pytest.approx(20.0, abs=1e-2)  # the top of the circle, where the arc ends
    assert removed_depth(beam, geometry, 0, 161.0) == pytest.approx(0.0, abs=1e-6)  # and continues along the radius


def test_profile_front_without_second_arc_continues_along_the_radius():
    processing = ProfileFront(start_x=100.0, depth=20.0, radius1=60.0, rotation1=120.0, radius2=0.0, rotation2=0.0)
    beam, geometry, area = cut(processing)
    center_x, center_z = 160.0, -80.0
    x = center_x + 60.0 * math.cos(math.radians(60.0)) + 10.0  # beyond the end of the arc, along the radius at 60 degrees
    assert removed_depth(beam, geometry, 0, x) == pytest.approx(-center_z - (x - center_x) * math.tan(math.radians(60.0)), abs=1e-2)
    third = math.pi * 60.0**2 / 3.0
    assert area == pytest.approx(100.0 * 80.0 + 60.0 * 80.0 + 80.0**2 / math.tan(math.radians(60.0)) / 2.0 - third)


def test_profile_front_concave():
    beam, geometry, area = cut(ProfileFront(start_x=100.0, depth=20.0, arc_shape="concave", radius1=60.0, radius2=0.0, rotation2=0.0))
    assert area == pytest.approx(100.0 * HEIGHT + 60.0 * 20.0 + math.pi * 60.0**2 / 4.0)
    assert removed_depth(beam, geometry, 0, 100.5) == pytest.approx(80.0, abs=0.1)
    assert removed_depth(beam, geometry, 0, 159.0) == pytest.approx(20.0 + math.sqrt(60.0**2 - 59.0**2), abs=0.1)
    assert removed_depth(beam, geometry, 0, 161.0) == pytest.approx(0.0, abs=1e-6)


def test_profile_front_without_arcs_is_reported():
    beam = Beam(Frame.worldXY(), LENGTH, WIDTH, HEIGHT)
    beam.add_features([ProfileFront(radius1=0.0, radius2=0.0)])
    beam.compute_elementgeometry(include_features=True)
    assert len(beam.debug_info) == 1


@pytest.mark.parametrize("orientation,start_x", [("start", 100.0), ("end", 900.0)])
def test_profile_head_quarter_arc(orientation, start_x):
    beam, geometry, area = cut(ProfileHead(orientation=orientation, start_x=start_x, arc1=ProfileArc(radius=50.0)))
    assert area == pytest.approx(100.0 * HEIGHT + 10.0 * 70.0 + 10.0 * 60.0 + 50.0 * 60.0 - math.pi * 50.0**2 / 4.0 + 10.0 * 10.0)

    def x(distance):
        return start_x + distance if orientation == "start" else start_x - distance

    assert removed_depth(beam, geometry, 0, x(5.0)) == pytest.approx(70.0, abs=1e-3)  # lap
    assert removed_depth(beam, geometry, 0, x(15.0)) == pytest.approx(60.0, abs=1e-3)  # displacement
    assert removed_depth(beam, geometry, 0, x(75.0)) == pytest.approx(10.0, abs=1e-3)  # lap of the arc
    assert removed_depth(beam, geometry, 0, x(85.0)) == pytest.approx(0.0, abs=1e-6)
    assert removed_depth(beam, geometry, 2, x(5.0)) == pytest.approx(0.0, abs=1e-6)


def test_profile_head_concave_quarter_arc_bulges_into_the_material():
    beam, geometry, area = cut(ProfileHead(start_x=100.0, arc1=ProfileArc(radius=50.0, arc_shape="concave")))
    assert area == pytest.approx(100.0 * HEIGHT + 10.0 * 70.0 + 10.0 * 60.0 + 10.0 * 50.0 + math.pi * 50.0**2 / 4.0 + 10.0 * 10.0)
    # the arc starts level: 40 past its start it is still deep
    assert removed_depth(beam, geometry, 0, 160.0) == pytest.approx(60.0 - 50.0 + math.sqrt(50.0**2 - 40.0**2), abs=1e-2)


@pytest.mark.parametrize("shape,sign", [("convex", -1.0), ("concave", 1.0)])
def test_profile_head_two_steps_with_a_segment(shape, sign):
    arc2 = ProfileArc(length=60.0, height=30.0, camber=5.0, arc_shape=shape, lap_length=4.0, lap_height=6.0, displacement=8.0)
    arc1 = ProfileArc(radius=20.0, arc_shape="concave", lap_length=2.0, lap_height=3.0, displacement=1.0)
    _, _, area = cut(ProfileHead(start_x=100.0, arc1=arc1, arc2=arc2, lap_length=7.0, lap_height=9.0))

    depth2 = 30.0 + 6.0  # above the second arc
    depth1 = depth2 + 20.0 + 3.0  # above the first arc
    depth0 = depth1 + 9.0
    expected = 100.0 * HEIGHT + 7.0 * depth0
    expected += 1.0 * depth1 + 20.0 * (depth1 - 20.0) + math.pi * 20.0**2 / 4.0 + 2.0 * (depth1 - 20.0)
    expected += 8.0 * depth2 + 60.0 * (6.0 + 15.0) + sign * segment_area(math.hypot(60.0, 30.0), 5.0) + 4.0 * 6.0
    assert area == pytest.approx(expected)


def test_profile_head_on_another_side():
    beam, geometry, area = cut(ProfileHead(start_x=100.0, arc1=ProfileArc(radius=20.0), ref_side_index=3))
    assert removed_depth(beam, geometry, 3, 105.0) == pytest.approx(40.0, abs=1e-3)
    assert removed_depth(beam, geometry, 1, 105.0) == pytest.approx(0.0, abs=1e-6)
