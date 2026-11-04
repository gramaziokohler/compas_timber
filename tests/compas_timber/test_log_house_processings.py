import math

import pytest
from compas.data import json_dumps
from compas.data import json_loads
from compas.geometry import Frame
from compas.geometry import Point
from compas.tolerance import TOL
from compas.tolerance import Tolerance

from compas_timber.btlx import BTLxReader
from compas_timber.elements import Beam
from compas_timber.fabrication import BTLxWriter
from compas_timber.fabrication.btlx import OrientationType
from compas_timber.fabrication.hip_valley_rafter_notch import HipValleyRafterNotch
from compas_timber.fabrication.log_house_front import LogHouseFront
from compas_timber.fabrication.log_house_half_lap import LogHouseHalfLap
from compas_timber.fabrication.log_house_joint import LogHouseJoint
from compas_timber.fabrication.log_house_joint import LogLapPositionType
from compas_timber.model import TimberModel

LENGTH, WIDTH, HEIGHT = 1000.0, 100.0, 200.0
BEAM_VOLUME = LENGTH * WIDTH * HEIGHT
START, END = OrientationType.START, OrientationType.END


def _apply(processing):
    """Returns the beam, its machined geometry and the removed volume."""
    beam = Beam(Frame.worldXY(), LENGTH, WIDTH, HEIGHT)
    beam.add_features([processing])
    geometry = beam.compute_elementgeometry(include_features=True)
    assert not beam.debug_info
    assert geometry.is_solid
    return beam, geometry, BEAM_VOLUME - geometry.volume


def _is_solid_at(beam, geometry, x, y, depth, ref_side_index=0):
    return geometry.contains(beam.ref_sides[ref_side_index].to_world_coordinates(Point(x, y, -depth)))


def _assert_close(actual, expected):
    assert TOL.is_close(actual, expected, rtol=1e-6, atol=1e-3), (actual, expected)


@pytest.mark.parametrize(
    "cls, kwargs",
    [
        (LogHouseHalfLap, {"orientation": "middle"}),
        (LogHouseHalfLap, {"start_x": 100000.1}),
        (LogHouseHalfLap, {"angle": 0.0}),
        (LogHouseHalfLap, {"length": -1.0}),
        (LogHouseHalfLap, {"depth_ref_side": 50000.1}),
        (LogHouseHalfLap, {"depth_opp_side": -0.1}),
        (LogHouseFront, {"orientation": "middle"}),
        (LogHouseFront, {"start_depth": -0.1}),
        (LogHouseFront, {"angle": 180.0}),
        (LogHouseFront, {"length": -1.0}),
        (LogHouseFront, {"depth_ref_edge": -0.1}),
        (LogHouseFront, {"depth_opp_edge": 50000.1}),
        (LogHouseFront, {"ref_side_only": "yes"}),
        (LogHouseJoint, {"start_x": -100000.1}),
        (LogHouseJoint, {"side_laps_limited": "no"}),
        (LogHouseJoint, {"depth_side_laps": -0.1}),
        (LogHouseJoint, {"lap_position": "sideways"}),
        (LogHouseJoint, {"length_opp_edge": 50000.1}),
        (LogHouseJoint, {"arc_radius": -1.0}),
        (LogHouseJoint, {"arc_depth": -50000.1}),
        (LogHouseJoint, {"arc_center": -0.1}),
        (HipValleyRafterNotch, {"orientation": "middle"}),
        (HipValleyRafterNotch, {"start_y": 50000.1}),
        (HipValleyRafterNotch, {"start_depth": -0.1}),
        (HipValleyRafterNotch, {"angle_ref_edge": 0.0}),
        (HipValleyRafterNotch, {"angle_opp_edge": 180.0}),
        (HipValleyRafterNotch, {"inclination": 180.1}),
        (HipValleyRafterNotch, {"width_counter_part_ref_edge": -0.1}),
        (HipValleyRafterNotch, {"rafter_nail_hole": 1}),
    ],
)
def test_limits_are_rejected(cls, kwargs):
    with pytest.raises(ValueError):
        cls(**kwargs)


def test_params_half_lap():
    processing = LogHouseHalfLap(orientation=END, start_x=12.5, angle=60.0, length=100.0, depth_ref_side=15.0, depth_opp_side=25.0, ref_side_index=2)
    assert processing.params.header_attributes["ReferencePlaneID"] == "3"
    assert processing.params.as_dict() == {
        "Orientation": "end",
        "StartX": "12.500",
        "Angle": "60.000",
        "Length": "100.000",
        "DepthRefSide": "15.000",
        "DepthOppSide": "25.000",
    }


def test_params_front():
    assert LogHouseFront(ref_side_only=True).params.as_dict() == {
        "Orientation": "start",
        "StartX": "0.000",
        "StartDepth": "20.000",
        "Angle": "90.000",
        "Length": "120.000",
        "DepthRefEdge": "20.000",
        "DepthOppEdge": "20.000",
        "RefSideOnly": "yes",
    }


def test_params_joint_in_schema_order_and_without_unset_depth():
    params = LogHouseJoint(lap_position=LogLapPositionType.FORWARD, arc_ref_edge_end=True).params.as_dict()
    assert list(params.items()) == [
        ("StartX", "0.000"),
        ("SideLapsLimited", "no"),
        ("LapPosition", "forward"),
        ("LengthRefSide", "100.000"),
        ("DepthRefSide", "10.000"),
        ("LengthOppSide", "100.000"),
        ("DepthOppSide", "10.000"),
        ("LengthRefEdge", "100.000"),
        ("DepthRefEdge", "10.000"),
        ("LengthOppEdge", "100.000"),
        ("DepthOppEdge", "10.000"),
        ("Drillhole", "no"),
        ("ArcRefEdgeStart", "no"),
        ("ArcRefEdgeEnd", "yes"),
        ("ArcOppEdgeStart", "no"),
        ("ArcOppEdgeEnd", "no"),
        ("ArcRadius", "120.000"),
        ("ArcDepth", "60.000"),
        ("ArcCenter", "120.000"),
    ]
    assert LogHouseJoint(depth_side_laps=80.0).params.as_dict()["DepthSideLaps"] == "80.000"


def test_params_hip_valley_rafter_notch():
    assert list(HipValleyRafterNotch(rafter_nail_hole=True).params.as_dict().items()) == [
        ("Orientation", "start"),
        ("StartX", "0.000"),
        ("StartY", "0.000"),
        ("StartDepth", "20.000"),
        ("AngleRefEdge", "45.000"),
        ("AngleOppEdge", "45.000"),
        ("Inclination", "30.000"),
        ("WidthCounterPartRefEdgeLimited", "no"),
        ("WidthCounterPartRefEdge", "120.000"),
        ("WidthCounterPartOppEdgeLimited", "no"),
        ("WidthCounterPartOppEdge", "120.000"),
        ("RafterNailHole", "yes"),
    ]


@pytest.mark.parametrize(
    "processing, lengths, others",
    [
        (LogHouseHalfLap(), ("start_x", "length", "depth_ref_side", "depth_opp_side"), ("angle",)),
        (LogHouseFront(), ("start_x", "start_depth", "length", "depth_ref_edge", "depth_opp_edge"), ("angle",)),
        (LogHouseJoint(depth_side_laps=80.0), ("start_x", "depth_side_laps", "length_ref_side", "depth_opp_edge", "arc_radius", "arc_depth", "arc_center"), ()),
        (HipValleyRafterNotch(), ("start_x", "start_y", "start_depth", "width_counter_part_ref_edge", "width_counter_part_opp_edge"), ("angle_ref_edge", "inclination")),
    ],
)
def test_scale_and_json_round_trip(processing, lengths, others):
    scaled = processing.scaled(2.0)
    for name in lengths:
        assert getattr(scaled, name) == 2.0 * getattr(processing, name)
    for name in others:
        assert getattr(scaled, name) == getattr(processing, name)
    assert json_loads(json_dumps(processing)).__data__ == processing.__data__


def test_scale_keeps_unset_depth_side_laps():
    assert LogHouseJoint().scaled(2.0).depth_side_laps is None


def test_btlx_round_trip(tmp_path):
    processings = [
        LogHouseHalfLap(orientation=END, start_x=300.0, angle=60.0, length=80.0, depth_ref_side=15.0, depth_opp_side=25.0, ref_side_index=2),
        LogHouseFront(start_x=50.0, start_depth=10.0, length=100.0, depth_ref_edge=30.0, depth_opp_edge=20.0, ref_side_only=True, ref_side_index=1),
        LogHouseJoint(start_x=600.0, side_laps_limited=True, depth_side_laps=120.0, lap_position=LogLapPositionType.FORWARD, arc_ref_edge_start=True, drillhole=True),
        LogHouseJoint(start_x=700.0),
        HipValleyRafterNotch(orientation=END, start_x=800.0, start_y=50.0, angle_ref_edge=130.0, width_counter_part_ref_edge_limited=True, rafter_nail_hole=True),
    ]
    beam = Beam(Frame.worldXY(), LENGTH, WIDTH, HEIGHT)
    beam.add_features(processings)
    model = TimberModel(tolerance=Tolerance(unit="MM", absolute=1e-3, relative=1e-3))
    model.add_element(beam)
    path = str(tmp_path / "log_house.btlx")
    BTLxWriter().write(model, path)

    reader = BTLxReader()
    features = list(reader.read(path).elements())[0].features
    assert not reader.errors
    assert [type(feature) for feature in features] == [type(processing) for processing in processings]
    assert [feature.__data__ for feature in features] == [processing.__data__ for processing in processings]


def test_half_lap_removes_a_notch_from_both_sides():
    beam, geometry, removed = _apply(LogHouseHalfLap(start_x=500.0, length=120.0, depth_ref_side=20.0, depth_opp_side=30.0))
    _assert_close(removed, 120.0 * WIDTH * 50.0)
    assert not _is_solid_at(beam, geometry, 445.0, 50.0, 10.0)
    assert _is_solid_at(beam, geometry, 435.0, 50.0, 10.0)
    assert _is_solid_at(beam, geometry, 500.0, 50.0, 25.0)
    assert _is_solid_at(beam, geometry, 500.0, 50.0, HEIGHT - 35.0)
    assert not _is_solid_at(beam, geometry, 500.0, 50.0, HEIGHT - 25.0)


@pytest.mark.parametrize("orientation, lean", [(START, -1.0), (END, 1.0)])
def test_half_lap_angle_is_measured_from_the_orientation_end(orientation, lean):
    beam, geometry, removed = _apply(LogHouseHalfLap(orientation=orientation, start_x=500.0, angle=60.0, length=120.0, depth_ref_side=20.0, depth_opp_side=0.0))
    _assert_close(removed, 120.0 / math.sin(math.radians(60.0)) * WIDTH * 20.0)
    half_length = 60.0 / math.sin(math.radians(60.0))
    at_opp_edge = 500.0 + lean * WIDTH / math.tan(math.radians(60.0))
    assert not _is_solid_at(beam, geometry, 500.0 + half_length - 1.0, 0.5, 10.0)  # centered on start_x at the reference edge
    assert _is_solid_at(beam, geometry, 500.0 + half_length + 1.0, 0.5, 10.0)
    assert not _is_solid_at(beam, geometry, at_opp_edge, WIDTH - 0.5, 10.0)
    assert _is_solid_at(beam, geometry, at_opp_edge + 2.0 * lean * half_length, WIDTH - 0.5, 10.0)


def test_half_lap_on_a_narrow_side():
    beam, geometry, removed = _apply(LogHouseHalfLap(start_x=500.0, length=120.0, depth_ref_side=20.0, depth_opp_side=0.0, ref_side_index=1))
    _assert_close(removed, 120.0 * HEIGHT * 20.0)
    assert not _is_solid_at(beam, geometry, 500.0, 50.0, 10.0, ref_side_index=1)
    assert _is_solid_at(beam, geometry, 500.0, 50.0, 10.0, ref_side_index=3)


def test_front_trims_and_lowers_the_start():
    processing = LogHouseFront(start_x=100.0, length=120.0, start_depth=10.0, depth_ref_edge=40.0, depth_opp_edge=20.0)
    beam, geometry, removed = _apply(processing)
    _assert_close(removed, 100.0 * WIDTH * HEIGHT + 2.0 * 120.0 * WIDTH * 30.0)  # 30.0 is the average of the corners 10, 40, 20 and 50
    assert not _is_solid_at(beam, geometry, 95.0, 50.0, 100.0)
    assert _is_solid_at(beam, geometry, 105.0, 50.0, 100.0)
    assert not _is_solid_at(beam, geometry, 101.0, 0.5, 9.0)  # start_depth
    assert _is_solid_at(beam, geometry, 101.0, 0.5, 12.0)
    assert not _is_solid_at(beam, geometry, 101.0, WIDTH - 0.5, 19.0)  # depth_opp_edge
    assert _is_solid_at(beam, geometry, 101.0, WIDTH - 0.5, 21.0)
    assert not _is_solid_at(beam, geometry, 219.0, 0.5, 38.0)  # depth_ref_edge
    assert _is_solid_at(beam, geometry, 221.0, 0.5, 5.0)  # past the shoulder
    assert not _is_solid_at(beam, geometry, 101.0, 0.5, HEIGHT - 9.0)  # the opposite side is lowered the same
    assert _is_solid_at(beam, geometry, 101.0, 0.5, HEIGHT - 12.0)


def test_front_trims_the_end_at_an_angle():
    processing = LogHouseFront(orientation=END, start_x=900.0, angle=60.0, length=120.0, start_depth=10.0, depth_ref_edge=40.0, depth_opp_edge=20.0, ref_side_only=True)
    beam, geometry, removed = _apply(processing)
    run = WIDTH / math.tan(math.radians(60.0))
    trim = (2.0 * 100.0 - run) / 2.0 * WIDTH * HEIGHT
    _assert_close(removed, trim + 120.0 / math.sin(math.radians(60.0)) * WIDTH * 30.0)
    assert not _is_solid_at(beam, geometry, 902.0, 0.5, 100.0)
    assert _is_solid_at(beam, geometry, 898.0, 0.5, 100.0)
    assert _is_solid_at(beam, geometry, 900.0 + run - 2.0, WIDTH - 0.5, 100.0)  # the wall leans towards the end
    assert not _is_solid_at(beam, geometry, 900.0 + run + 2.0, WIDTH - 0.5, 100.0)
    assert not _is_solid_at(beam, geometry, 899.0, 0.5, 9.0)
    assert _is_solid_at(beam, geometry, 899.0, 0.5, HEIGHT - 5.0)  # ref_side_only


def test_front_without_depths_only_trims():
    assert TOL.is_close(_apply(LogHouseFront(start_x=100.0, start_depth=0.0, depth_ref_edge=0.0, depth_opp_edge=0.0))[2], 100.0 * WIDTH * HEIGHT)


def test_joint_symmetric_through_laps():
    beam, geometry, removed = _apply(LogHouseJoint(start_x=500.0))
    notches = 2.0 * 100.0 * WIDTH * 10.0
    laps = 2.0 * 100.0 * 10.0 * HEIGHT
    overlaps = 4.0 * 100.0 * 10.0 * 10.0
    _assert_close(removed, notches + laps - overlaps)
    assert not _is_solid_at(beam, geometry, 500.0, 50.0, 5.0)
    assert not _is_solid_at(beam, geometry, 500.0, 50.0, HEIGHT - 5.0)
    assert _is_solid_at(beam, geometry, 500.0, 50.0, 100.0)
    assert not _is_solid_at(beam, geometry, 500.0, 5.0, 100.0)
    assert not _is_solid_at(beam, geometry, 500.0, WIDTH - 5.0, 100.0)
    assert _is_solid_at(beam, geometry, 500.0, 15.0, 100.0)


def test_joint_limited_laps_stop_at_their_depth():
    beam, geometry, removed = _apply(LogHouseJoint(start_x=500.0, side_laps_limited=True, depth_side_laps=120.0))
    _assert_close(removed, 2.0 * 100.0 * WIDTH * 10.0 + 2.0 * 100.0 * 10.0 * 120.0 - 2.0 * 100.0 * 10.0 * 10.0)
    assert not _is_solid_at(beam, geometry, 500.0, 5.0, 115.0)
    assert _is_solid_at(beam, geometry, 500.0, 5.0, 125.0)


def test_joint_limited_laps_without_depth_are_reported():
    beam = Beam(Frame.worldXY(), LENGTH, WIDTH, HEIGHT)
    beam.add_features([LogHouseJoint(start_x=500.0, side_laps_limited=True)])
    beam.compute_elementgeometry(include_features=True)
    assert beam.debug_info


@pytest.mark.parametrize(
    "position, ref_range, opp_range",
    [
        (LogLapPositionType.SYMMETRIC, (425.0, 575.0), (425.0, 575.0)),
        (LogLapPositionType.FORWARD, (450.0, 600.0), (400.0, 550.0)),
        (LogLapPositionType.BACKWARD, (400.0, 550.0), (450.0, 600.0)),
    ],
)
def test_joint_lap_position(position, ref_range, opp_range):
    beam, geometry, _ = _apply(LogHouseJoint(start_x=500.0, lap_position=position, length_ref_edge=150.0, length_opp_edge=150.0))
    for y, (lap_start, lap_end) in ((5.0, ref_range), (WIDTH - 5.0, opp_range)):
        assert _is_solid_at(beam, geometry, lap_start - 1.0, y, 100.0)
        assert not _is_solid_at(beam, geometry, lap_start + 1.0, y, 100.0)
        assert not _is_solid_at(beam, geometry, lap_end - 1.0, y, 100.0)
        assert _is_solid_at(beam, geometry, lap_end + 1.0, y, 100.0)
    assert not _is_solid_at(beam, geometry, 549.0, 50.0, 5.0)  # the notches stay centered
    assert _is_solid_at(beam, geometry, 551.0, 50.0, 5.0)


@pytest.mark.parametrize(
    "arc, wall, outwards, y",
    [
        ("arc_ref_edge_start", 455.0, -1.0, 5.0),
        ("arc_ref_edge_end", 545.0, 1.0, 5.0),
        ("arc_opp_edge_start", 455.0, -1.0, WIDTH - 5.0),
        ("arc_opp_edge_end", 545.0, 1.0, WIDTH - 5.0),
    ],
)
def test_joint_arc_widens_one_wall_of_one_lap(arc, wall, outwards, y):
    # the arc is the 3-4-5 triangle from the center on the far side of start_x to where it meets the wall
    processing = LogHouseJoint(
        start_x=500.0,
        length_ref_side=60.0,
        length_opp_side=60.0,
        length_ref_edge=90.0,
        length_opp_edge=90.0,
        arc_radius=125.0,
        arc_depth=100.0,
        arc_center=30.0,
        **{arc: True},
    )
    beam, geometry, removed = _apply(processing)
    radius, depth, offset = 125.0, 100.0, 75.0
    quarter = 0.5 * depth * offset + 0.5 * radius**2 * math.asin(depth / radius) - offset * depth
    _assert_close(removed, 2.0 * 60.0 * WIDTH * 10.0 + 2.0 * 90.0 * 10.0 * HEIGHT - 4.0 * 60.0 * 10.0 * 10.0 + 2.0 * quarter * 10.0)
    assert not _is_solid_at(beam, geometry, wall + outwards * 40.0, y, 20.0)  # widest at the sides
    assert not _is_solid_at(beam, geometry, wall + outwards * 40.0, y, HEIGHT - 20.0)
    assert _is_solid_at(beam, geometry, wall + outwards * 2.0, y, 100.0)  # the arcs meet on the wall
    assert _is_solid_at(beam, geometry, wall + outwards * 55.0, y, 20.0)
    other = WIDTH - y
    assert _is_solid_at(beam, geometry, wall + outwards * 40.0, other, 20.0)


def test_hip_notch_chevron_in_a_flat_floor():
    processing = HipValleyRafterNotch(
        start_x=300.0,
        start_y=50.0,
        start_depth=30.0,
        inclination=0.0,
        width_counter_part_ref_edge_limited=True,
        width_counter_part_ref_edge=60.0,
        width_counter_part_opp_edge_limited=True,
        width_counter_part_opp_edge=60.0,
    )
    beam, geometry, removed = _apply(processing)
    _assert_close(removed, 60.0 / math.sin(math.radians(45.0)) * WIDTH * 30.0)
    assert _is_solid_at(beam, geometry, 295.0, 50.0, 10.0)  # the tip points towards the start
    assert not _is_solid_at(beam, geometry, 305.0, 50.0, 10.0)
    assert _is_solid_at(beam, geometry, 305.0, 50.0, 35.0)  # below the floor
    assert _is_solid_at(beam, geometry, 345.0, 1.0, 10.0)
    assert not _is_solid_at(beam, geometry, 355.0, 1.0, 10.0)
    assert _is_solid_at(beam, geometry, 345.0, WIDTH - 1.0, 10.0)
    assert not _is_solid_at(beam, geometry, 355.0, WIDTH - 1.0, 10.0)
    assert not _is_solid_at(beam, geometry, 430.0, 1.0, 10.0)
    assert _is_solid_at(beam, geometry, 440.0, 1.0, 10.0)
    assert not _is_solid_at(beam, geometry, 380.0, 50.0, 10.0)
    assert _is_solid_at(beam, geometry, 390.0, 50.0, 10.0)  # past the inner corner of the chevron


def test_valley_notch_opens_the_other_way():
    processing = HipValleyRafterNotch(
        start_x=300.0,
        start_y=50.0,
        start_depth=30.0,
        angle_ref_edge=135.0,
        angle_opp_edge=135.0,
        inclination=0.0,
        width_counter_part_ref_edge_limited=True,
        width_counter_part_ref_edge=60.0,
        width_counter_part_opp_edge_limited=True,
        width_counter_part_opp_edge=60.0,
    )
    beam, geometry, removed = _apply(processing)
    _assert_close(removed, 60.0 / math.sin(math.radians(45.0)) * WIDTH * 30.0)
    assert _is_solid_at(beam, geometry, 295.0, 50.0, 10.0)
    assert not _is_solid_at(beam, geometry, 305.0, 50.0, 10.0)
    assert _is_solid_at(beam, geometry, 245.0, 1.0, 10.0)
    assert not _is_solid_at(beam, geometry, 255.0, 1.0, 10.0)
    assert not _is_solid_at(beam, geometry, 380.0, 50.0, 10.0)  # the tip of the second wall
    assert _is_solid_at(beam, geometry, 390.0, 50.0, 10.0)


def _straight_notch_area(depth, width, inclination):
    """The area of the section along the part of a notch across the part, by the shoelace formula."""
    sin, cos, tan = math.sin(inclination), math.cos(inclination), math.tan(inclination)
    near = (-depth * tan, 0.0)
    apex = (0.0, -depth)
    rising = (width * cos, -depth + width * sin)
    far = (rising[0] + rising[1] * tan, 0.0)
    points = [near, far, rising, apex]
    return 0.5 * abs(sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(points, points[1:] + points[:1])))


@pytest.mark.parametrize("orientation, start_x, rising", [(START, 300.0, 1.0), (END, 700.0, -1.0)])
def test_notch_floor_rises_and_walls_are_perpendicular_to_it(orientation, start_x, rising):
    inclination = math.radians(20.0)
    processing = HipValleyRafterNotch(
        orientation=orientation,
        start_x=start_x,
        start_y=50.0,
        start_depth=30.0,
        angle_ref_edge=90.0,
        angle_opp_edge=90.0,
        inclination=20.0,
        width_counter_part_ref_edge_limited=True,
        width_counter_part_ref_edge=60.0,
        width_counter_part_opp_edge_limited=True,
        width_counter_part_opp_edge=60.0,
    )
    beam, geometry, removed = _apply(processing)
    _assert_close(removed, _straight_notch_area(30.0, 60.0, inclination) * WIDTH)

    def along(floor, above):
        """The x and depth of a point, given in the floor's coordinates."""
        x = start_x + rising * (floor * math.cos(inclination) - above * math.sin(inclination))
        return x, 30.0 - floor * math.sin(inclination) - above * math.cos(inclination)

    for floor, above, is_solid in ((2.0, 2.0, False), (2.0, -2.0, True), (-2.0, 2.0, True), (58.0, 2.0, False), (62.0, 2.0, True), (58.0, -2.0, True)):
        x, depth = along(floor, above)
        assert _is_solid_at(beam, geometry, x, 50.0, depth) == is_solid


def test_notch_widths_apply_to_their_arm():
    kwargs = {"start_x": 300.0, "start_y": 50.0, "start_depth": 30.0, "inclination": 0.0}
    processing = HipValleyRafterNotch(
        width_counter_part_ref_edge_limited=True, width_counter_part_ref_edge=30.0, width_counter_part_opp_edge_limited=True, width_counter_part_opp_edge=60.0, **kwargs
    )
    beam, geometry, _ = _apply(processing)
    assert not _is_solid_at(beam, geometry, 390.0, 1.0, 10.0)
    assert _is_solid_at(beam, geometry, 397.0, 1.0, 10.0)  # 50.0 + 30.0 * sqrt(2) along the reference edge
    assert not _is_solid_at(beam, geometry, 430.0, WIDTH - 1.0, 10.0)
    assert _is_solid_at(beam, geometry, 440.0, WIDTH - 1.0, 10.0)


def test_notch_unlimited_width_opens_to_where_the_floor_leaves_the_part():
    _, _, removed = _apply(HipValleyRafterNotch(start_x=300.0, start_y=50.0, start_depth=30.0, angle_ref_edge=90.0, angle_opp_edge=90.0, inclination=30.0))
    inclination = math.radians(30.0)
    wedge = 0.5 * 30.0 * (30.0 / math.tan(inclination) + 30.0 * math.tan(inclination))
    _assert_close(removed, wedge * WIDTH)


def test_notch_in_line_arms_of_different_width_keep_the_step():
    processing = HipValleyRafterNotch(
        start_x=300.0,
        start_y=50.0,
        start_depth=30.0,
        angle_ref_edge=90.0,
        angle_opp_edge=90.0,
        inclination=0.0,
        width_counter_part_ref_edge_limited=True,
        width_counter_part_ref_edge=30.0,
        width_counter_part_opp_edge_limited=True,
        width_counter_part_opp_edge=60.0,
    )
    _, _, removed = _apply(processing)
    _assert_close(removed, (30.0 + 60.0) * 50.0 * 30.0)


def test_notch_on_the_opposite_side():
    processing = HipValleyRafterNotch(start_x=300.0, start_y=50.0, start_depth=30.0, inclination=0.0, ref_side_index=2)
    beam, geometry, _ = _apply(processing)
    assert not _is_solid_at(beam, geometry, 320.0, 50.0, 10.0, ref_side_index=2)
    assert _is_solid_at(beam, geometry, 320.0, 50.0, 10.0, ref_side_index=0)
