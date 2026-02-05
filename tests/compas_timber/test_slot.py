import pytest
from collections import OrderedDict

from compas.geometry import Frame
from compas.geometry import Point
from compas.geometry import Line
from compas.geometry import Vector
from compas.geometry import Polyhedron

from compas_timber.elements import Beam
from compas_timber.fabrication import Slot
from compas_timber.fabrication import OrientationType
from compas_timber.fabrication import MachiningLimits

from compas.tolerance import TOL


@pytest.fixture
def beam():
    width = 60.0
    height = 120.0
    centerline = Line(Point(x=80.4429082858, y=26.8976400207, z=0.0), Point(x=542.848108719, y=26.8976400207, z=0.0))
    return Beam.from_centerline(centerline, width, height)


@pytest.fixture
def tol():
    TOL.absolute = 0.001
    TOL.relative = 0.01


def test_horizontal_slot_negative_angle(beam):
    slot_frame = Frame(
        point=Point(x=137.660612947, y=90.7489233758, z=55.0906953863),
        xaxis=Vector(x=-0.0214020667979, y=-0.833730649845, z=-0.551756427281),
        yaxis=Vector(x=-0.999699702481, y=0.0244348873403, z=0.00185503105829),
    )
    # TODO: add test for integer values. shouldn't be an issue but it is
    slot_depth = 100.0
    slot_thickness = 10.0
    expected_values = OrderedDict(
        [
            ("Name", "Slot"),
            ("Process", "yes"),
            ("Priority", "0"),
            ("ProcessID", "0"),
            ("ReferencePlaneID", "5"),
            ("Orientation", "start"),
            ("StartX", "0.000"),
            ("StartY", "91.882"),
            ("StartDepth", "0.000"),
            ("Angle", "-33.482"),
            ("Inclination", "88.760"),
            ("Length", "71.937"),
            ("Depth", "100.000"),
            ("Thickness", "10.000"),
            ("AngleRefPoint", "90.000"),
            ("AngleOppPoint", "90.000"),
            ("AddAngleOppPoint", "0.000"),
            (
                "MachiningLimits",
                {"FaceLimitedStart": "yes", "FaceLimitedEnd": "yes", "FaceLimitedFront": "yes", "FaceLimitedBack": "yes", "FaceLimitedTop": "yes", "FaceLimitedBottom": "yes"},
            ),
        ]
    )

    slot = Slot.from_plane_and_beam(slot_frame, beam, slot_depth, slot_thickness)
    params = slot.params.header_attributes
    params.update(slot.params.as_dict())
    assert params == expected_values


def test_horizontal_slot_positive_angle(beam):
    slot_frame = Frame(
        point=Point(x=137.660612947, y=-46.3620774824, z=59.0575029514),
        xaxis=Vector(x=-0.0214020667979, y=0.785041613815, z=-0.619073191243),
        yaxis=Vector(x=-0.999699702481, y=-0.00941182448018, z=0.0226257026303),
    )

    slot_depth = 100.0
    slot_thickness = 10.0
    expected_values = OrderedDict(
        [
            ("Name", "Slot"),
            ("Process", "yes"),
            ("Priority", "0"),
            ("ProcessID", "0"),
            ("ReferencePlaneID", "5"),
            ("Orientation", "start"),
            ("StartX", "0.000"),
            ("StartY", "38.455"),
            ("StartDepth", "0.000"),
            ("Angle", "38.273"),
            ("Inclination", "88.896"),
            ("Length", "76.427"),
            ("Depth", "100.000"),
            ("Thickness", "10.000"),
            ("AngleRefPoint", "90.000"),
            ("AngleOppPoint", "90.000"),
            ("AddAngleOppPoint", "0.000"),
            (
                "MachiningLimits",
                {"FaceLimitedStart": "yes", "FaceLimitedEnd": "yes", "FaceLimitedFront": "yes", "FaceLimitedBack": "yes", "FaceLimitedTop": "yes", "FaceLimitedBottom": "yes"},
            ),
        ]
    )

    slot = Slot.from_plane_and_beam(slot_frame, beam, slot_depth, slot_thickness)

    params = slot.params.header_attributes
    params.update(slot.params.as_dict())
    assert params == expected_values


def test_vertical_slot_positive_angle(beam):
    slot_frame = Frame(
        point=Point(x=137.660612947, y=7.41234277630, z=91.0737369193),
        xaxis=Vector(x=-0.0214020667979, y=0.145153961857, z=-0.989177577028),
        yaxis=Vector(x=-0.999699702481, y=0.00870466402682, z=0.0229070662403),
    )

    slot_depth = 100.0
    slot_thickness = 10.0
    expected_values = OrderedDict(
        [
            ("Name", "Slot"),
            ("Process", "yes"),
            ("Priority", "0"),
            ("ProcessID", "0"),
            ("ReferencePlaneID", "5"),
            ("Orientation", "start"),
            ("StartX", "26.666"),
            ("StartY", "0.000"),
            ("StartDepth", "0.000"),
            ("Angle", "81.667"),
            ("Inclination", "89.309"),
            ("Length", "121.281"),
            ("Depth", "100.000"),
            ("Thickness", "10.000"),
            ("AngleRefPoint", "90.000"),
            ("AngleOppPoint", "90.000"),
            ("AddAngleOppPoint", "0.000"),
            (
                "MachiningLimits",
                {"FaceLimitedStart": "yes", "FaceLimitedEnd": "yes", "FaceLimitedFront": "yes", "FaceLimitedBack": "yes", "FaceLimitedTop": "yes", "FaceLimitedBottom": "yes"},
            ),
        ]
    )

    slot = Slot.from_plane_and_beam(slot_frame, beam, slot_depth, slot_thickness)

    params = slot.params.header_attributes
    params.update(slot.params.as_dict())
    assert params == expected_values


def test_vertical_slot_negative_angle(beam):
    slot_frame = Frame(
        point=Point(x=137.660612947, y=35.2371162149, z=90.8851505187),
        xaxis=Vector(x=-0.0214020667979, y=-0.183445400082, z=-0.982796894951),
        yaxis=Vector(x=-0.999699702481, y=0.0156622878516, z=0.0188466866799),
    )

    slot_depth = 100.0
    slot_thickness = 10.0
    expected_values = OrderedDict(
        [
            ("Name", "Slot"),
            ("Process", "yes"),
            ("Priority", "0"),
            ("ProcessID", "0"),
            ("ReferencePlaneID", "5"),
            ("Orientation", "start"),
            ("StartX", "26.739"),
            ("StartY", "120.000"),
            ("StartDepth", "0.000"),
            ("Angle", "-79.412"),
            ("Inclination", "89.304"),
            ("Length", "122.078"),
            ("Depth", "100.000"),
            ("Thickness", "10.000"),
            ("AngleRefPoint", "90.000"),
            ("AngleOppPoint", "90.000"),
            ("AddAngleOppPoint", "0.000"),
            (
                "MachiningLimits",
                {"FaceLimitedStart": "yes", "FaceLimitedEnd": "yes", "FaceLimitedFront": "yes", "FaceLimitedBack": "yes", "FaceLimitedTop": "yes", "FaceLimitedBottom": "yes"},
            ),
        ]
    )

    slot = Slot.from_plane_and_beam(slot_frame, beam, slot_depth, slot_thickness)

    params = slot.params.header_attributes
    params.update(slot.params.as_dict())
    assert params == expected_values


def test_slot_scaled():
    slot = Slot(orientation=OrientationType.START, start_x=14.23, start_y=0.22, start_depth=42.0, angle=23.5, inclination=95.2, length=100.0, depth=10.0, thickness=5.0)

    scaled_slot = slot.scaled(2.0)

    assert scaled_slot.orientation == slot.orientation
    assert scaled_slot.start_x == slot.start_x * 2.0
    assert scaled_slot.start_y == slot.start_y * 2.0
    assert scaled_slot.start_depth == slot.start_depth * 2.0
    assert scaled_slot.angle == slot.angle
    assert scaled_slot.inclination == slot.inclination
    assert scaled_slot.length == slot.length * 2.0
    assert scaled_slot.depth == slot.depth * 2.0
    assert scaled_slot.thickness == slot.thickness * 2.0
    assert scaled_slot.ref_side_index == slot.ref_side_index


def test_slot_apply_points(tol):
    beam = Beam.from_centerline(Line(Point(0, 0, 0), Point(100, 0, 0)), width=30, height=50)
    ml = MachiningLimits()
    slot = slot = Slot(
        orientation=OrientationType.START,
        start_x=10,
        start_y=12,
        start_depth=40,
        angle=25.0,
        inclination=80.0,
        length=10,
        depth=23,
        thickness=5,
        angle_ref_point=110.0,
        angle_opp_point=65.0,
        add_angle_opp_point=10.0,
        machining_limits=ml.limits,
        ref_side_index=2,
    )

    origin_point = slot._origin_point(beam)
    origin_frame = slot._origin_frame(beam)
    p1 = slot._find_p1(origin_point, origin_frame)
    slot_frame = slot._compute_slot_frame(p1, origin_frame)
    p4 = slot._find_p4(p1, slot_frame)
    p3 = slot._find_p3(p1, p4, slot_frame)
    p2 = slot._find_p2(p1, p3, p4, slot_frame)

    assert origin_point == Point(x=0.000, y=-15.000, z=25.000)
    assert origin_frame == Frame(point=Point(x=0.000, y=-15.000, z=25.000), xaxis=Vector(x=1.000, y=0.000, z=0.000), yaxis=Vector(x=0.000, y=1.000, z=-0.000))
    assert slot_frame == Frame(point=Point(x=10.000, y=-3.000, z=-15.000), xaxis=Vector(x=0.985, y=-0.174, z=0.000), yaxis=Vector(x=0.073, y=0.416, z=0.906))
    assert p1 == Point(x=10.000, y=-3.000, z=-15.000)
    assert p2 == Point(x=11.263, y=4.165, z=0.601)
    assert p3 == Point(x=40.292, y=-8.586, z=-15.516)
    assert p4 == Point(x=32.036, y=-10.478, z=-22.587)


def test_slot_apply_frames(tol):
    beam = Beam.from_centerline(Line(Point(0, 0, 0), Point(100, 0, 0)), width=30, height=50)
    ml = MachiningLimits()
    slot = slot = Slot(
        orientation=OrientationType.START,
        start_x=10,
        start_y=12,
        start_depth=40,
        angle=25.0,
        inclination=80.0,
        length=10,
        depth=23,
        thickness=5,
        angle_ref_point=110.0,
        angle_opp_point=65.0,
        add_angle_opp_point=10.0,
        machining_limits=ml.limits,
        ref_side_index=2,
    )

    origin_point = slot._origin_point(beam)
    origin_frame = slot._origin_frame(beam)
    p1 = slot._find_p1(origin_point, origin_frame)
    slot_frame = slot._compute_slot_frame(p1, origin_frame)
    p4 = slot._find_p4(p1, slot_frame)
    p3 = slot._find_p3(p1, p4, slot_frame)
    top_frame = slot._top_frame(beam, slot_frame, p3)
    bottom_frame = slot._bottom_frame(beam, slot_frame, p3)
    start_frame = slot._start_frame(beam, slot_frame, p3)
    end_frame = slot._end_frame(beam, slot_frame, p3)
    front_frame = slot._front_frame(beam, slot_frame)
    back_frame = slot._back_frame(beam, slot_frame)

    assert top_frame == Frame(point=Point(x=16.510, y=1.860, z=-2.311), xaxis=Vector(x=0.157, y=0.893, z=-0.423), yaxis=Vector(x=-0.816, y=0.358, z=0.453))
    assert bottom_frame == Frame(point=Point(x=10.000, y=-3.000, z=-15.000), xaxis=Vector(x=0.157, y=0.893, z=-0.423), yaxis=Vector(x=0.900, y=-0.306, z=-0.310))
    assert start_frame == Frame(point=Point(x=0.000, y=0.000, z=0.000), xaxis=Vector(x=0.000, y=-1.000, z=0.000), yaxis=Vector(x=0.000, y=0.000, z=1.000))
    assert end_frame == Frame(point=Point(x=40.292, y=-8.586, z=-15.516), xaxis=Vector(x=0.157, y=0.893, z=-0.423), yaxis=Vector(x=0.748, y=0.172, z=0.641))
    assert front_frame == Frame(point=Point(x=9.607, y=-5.231, z=-13.943), xaxis=Vector(x=0.985, y=-0.174, z=0.000), yaxis=Vector(x=0.073, y=0.416, z=0.906))
    assert back_frame == Frame(point=Point(x=10.393, y=-0.769, z=-16.057), xaxis=Vector(x=0.985, y=-0.174, z=0.000), yaxis=Vector(x=-0.073, y=-0.416, z=-0.906))

    # with start_depth == 0
    beam = Beam.from_centerline(Line(Point(0, 0, 0), Point(100, 0, 0)), width=30, height=50)
    ml = MachiningLimits()
    slot = slot = Slot(
        orientation=OrientationType.START,
        start_x=10,
        start_y=12,
        start_depth=0,
        angle=25.0,
        inclination=80.0,
        length=10,
        depth=23,
        thickness=5,
        angle_ref_point=110.0,
        angle_opp_point=65.0,
        add_angle_opp_point=10.0,
        machining_limits=ml,
        ref_side_index=2,
    )

    origin_point = slot._origin_point(beam)
    origin_frame = slot._origin_frame(beam)
    p1 = slot._find_p1(origin_point, origin_frame)
    slot_frame = slot._compute_slot_frame(p1, origin_frame)
    p4 = slot._find_p4(p1, slot_frame)
    p3 = slot._find_p3(p1, p4, slot_frame)
    top_frame = slot._top_frame(beam, slot_frame, p3)
    bottom_frame = slot._bottom_frame(beam, slot_frame, p3)
    start_frame = slot._start_frame(beam, slot_frame, p3)
    end_frame = slot._end_frame(beam, slot_frame, p3)
    front_frame = slot._front_frame(beam, slot_frame)
    back_frame = slot._back_frame(beam, slot_frame)

    assert top_frame == Frame(point=Point(x=0.000, y=-15.000, z=25.000), xaxis=Vector(x=1.000, y=0.000, z=0.000), yaxis=Vector(x=0.000, y=1.000, z=-0.000))
    assert bottom_frame == Frame(point=Point(x=9.484, y=-8.586, z=-5.292), xaxis=Vector(x=-0.423, y=0.893, z=-0.157), yaxis=Vector(x=0.641, y=0.172, z=-0.748))
    assert start_frame == Frame(point=Point(x=10.000, y=-3.000, z=25.000), xaxis=Vector(x=-0.423, y=0.893, z=-0.157), yaxis=Vector(x=-0.310, y=-0.306, z=-0.900))
    assert end_frame == Frame(point=Point(x=22.689, y=1.860, z=18.490), xaxis=Vector(x=-0.423, y=0.893, z=-0.157), yaxis=Vector(x=0.453, y=0.358, z=0.816))
    assert front_frame == Frame(point=Point(x=11.057, y=-5.231, z=25.393), xaxis=Vector(x=0.000, y=-0.174, z=-0.985), yaxis=Vector(x=0.906, y=0.416, z=-0.073))
    assert back_frame == Frame(point=Point(x=8.943, y=-0.769, z=24.607), xaxis=Vector(x=0.000, y=-0.174, z=-0.985), yaxis=Vector(x=-0.906, y=-0.416, z=0.073))


def test_slot_volume_subtracting_polyhedron(beam, tol):
    beam = Beam.from_centerline(Line(Point(0, 0, 0), Point(100, 0, 0)), width=30, height=50)
    ml = MachiningLimits()
    slot = slot = Slot(
        orientation=OrientationType.START,
        start_x=10,
        start_y=12,
        start_depth=40,
        angle=25.0,
        inclination=80.0,
        length=10,
        depth=23,
        thickness=5,
        angle_ref_point=110.0,
        angle_opp_point=65.0,
        add_angle_opp_point=10.0,
        machining_limits=ml,
        ref_side_index=2,
    )

    polyhedron = slot.volume_from_params_and_beam(beam)
    comparing_polyhdron = Polyhedron(
        vertices=[
            ["0.000", "-1.971", "-10.636"],
            ["31.643", "-12.709", "-21.530"],
            ["39.899", "-10.817", "-14.459"],
            ["0.000", "6.708", "7.693"],
            ["0.000", "2.758", "-12.478"],
            ["32.430", "-8.247", "-23.644"],
            ["40.686", "-6.354", "-16.572"],
            ["0.000", "11.516", "6.017"],
        ],
        faces=[[0, 1, 2, 3], [4, 7, 6, 5], [0, 4, 5, 1], [3, 2, 6, 7], [1, 5, 6, 2], [0, 3, 7, 4]],
    )

    vertices_points = [Point(*vertex) for vertex in polyhedron.vertices]
    comparing_vertices_points = [Point(*vertex) for vertex in comparing_polyhdron.vertices]

    assert polyhedron.faces == comparing_polyhdron.faces
    assert vertices_points == comparing_vertices_points
