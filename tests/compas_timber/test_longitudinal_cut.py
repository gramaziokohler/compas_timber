import pytest

from compas.data import json_dumps
from compas.data import json_loads
from compas.geometry import Line
from compas.geometry import Point
from compas.geometry import Plane
from compas.geometry import Frame
from compas.geometry import Vector
from compas.geometry import is_point_on_plane

from compas_timber.elements import Beam
from compas_timber.fabrication import LongitudinalCut
from compas_timber.fabrication import AlignmentType

from compas.tolerance import Tolerance


@pytest.fixture
def tol():
    return Tolerance(unit="MM", absolute=1e-3, relative=1e-3)


def test_longitudinal_cut_from_plane_with_ref_side_index(tol):
    centerline = Line(Point(x=251.4831588479271, y=-248.4761486653297, z=-361.20250690854925), Point(x=754.171905226478, y=240.25911119218435, z=349.45332666519346))
    z_vector = Vector(x=-0.510, y=-0.496, z=0.702)
    cross_section = (60, 100)
    beam = Beam.from_centerline(centerline, cross_section[0], cross_section[1], z_vector)

    # cut the start of the beam
    plane = Plane(point=Point(x=452.495, y=-56.036, z=-25.372), normal=Vector(x=-0.864, y=0.279, z=0.419))
    instance = LongitudinalCut.from_plane_and_beam(plane, beam, ref_side_index=2)

    assert tol.is_close(instance.start_x, 0.0)
    assert tol.is_close(instance.start_y, 18.651)
    assert tol.is_close(instance.inclination, -53.363)
    assert instance.start_limited is False
    assert instance.end_limited is False
    assert tol.is_close(instance.length, 998.293)
    assert instance.depth_limited is False
    assert tol.is_close(instance.depth, 55.601)
    assert tol.is_close(instance.angle_start, 90.0)
    assert tol.is_close(instance.angle_end, 90.0)
    assert tol.is_close(instance.ref_side_index, 2)

    cut_plane = instance.plane_from_params_and_beam(beam)

    # should be the same plane, but point might be different
    assert cut_plane.is_parallel(plane, tol=tol.absolute)
    assert is_point_on_plane(cut_plane.point, plane, tol=tol.absolute)


def test_longitudinal_cut_from_plane_without_ref_side_index(tol):
    centerline = Line(Point(x=251.4831588479271, y=-248.4761486653297, z=-361.20250690854925), Point(x=754.171905226478, y=240.25911119218435, z=349.45332666519346))
    z_vector = Vector(x=-0.510, y=-0.496, z=0.702)
    cross_section = (60, 100)
    beam = Beam.from_centerline(centerline, cross_section[0], cross_section[1], z_vector)

    # cut the start of the beam
    plane = Plane(point=Point(x=452.495, y=-56.036, z=-25.372), normal=Vector(x=-0.864, y=0.279, z=0.419))
    instance = LongitudinalCut.from_plane_and_beam(plane, beam, start_x=10.0, length=300.0)

    assert tol.is_close(instance.start_x, 10.0)
    assert tol.is_close(instance.start_y, 55.601)
    assert tol.is_close(instance.inclination, 36.637)
    assert instance.start_limited is True
    assert instance.end_limited is True
    assert tol.is_close(instance.length, 300.0)
    assert instance.depth_limited is False
    assert tol.is_close(instance.depth, 41.349)
    assert tol.is_close(instance.angle_start, 90.0)
    assert tol.is_close(instance.angle_end, 90.0)
    assert tol.is_close(instance.ref_side_index, 1)

    cut_plane = instance.plane_from_params_and_beam(beam)

    # should be the same plane, but point might be different
    assert cut_plane.is_parallel(plane, tol=tol.absolute)


def test_jack_rafter_cut_from_frame(tol):
    centerline = Line(Point(x=251.4831588479271, y=-248.4761486653297, z=-361.20250690854925), Point(x=754.171905226478, y=240.25911119218435, z=349.45332666519346))
    z_vector = Vector(x=-0.510, y=-0.496, z=0.702)
    cross_section = (60, 100)
    beam = Beam.from_centerline(centerline, cross_section[0], cross_section[1], z_vector)

    # cut the start of the beam
    plane = Plane(point=Point(x=452.495, y=-56.036, z=-25.372), normal=Vector(x=-0.864, y=0.279, z=0.419))
    frame = Frame.from_plane(plane)
    instance = LongitudinalCut.from_plane_and_beam(frame, beam, start_x=10.0, length=300.0)

    assert tol.is_close(instance.start_x, 10.0)
    assert tol.is_close(instance.start_y, 55.601)
    assert tol.is_close(instance.inclination, 36.637)
    assert instance.start_limited is True
    assert instance.end_limited is True
    assert tol.is_close(instance.length, 300.0)
    assert instance.depth_limited is False
    assert tol.is_close(instance.depth, 41.349)
    assert tol.is_close(instance.angle_start, 90.0)
    assert tol.is_close(instance.angle_end, 90.0)
    assert tol.is_close(instance.ref_side_index, 1)

    cut_plane = instance.plane_from_params_and_beam(beam)

    # should be the same plane, but point might be different
    assert cut_plane.is_parallel(Plane.from_frame(frame), tol=tol.absolute)


def test_longitudinal_cut_data(tol):
    instance = LongitudinalCut(
        start_x=214.922,
        start_y=30.0,
        inclination=40.0,
        start_limited=False,
        end_limited=True,
        length=100.0,
        depth_limited=False,
        depth=50.0,
        angle_start=113.344,
        angle_end=66.656,
        tool_position=AlignmentType.CENTER,
        ref_side_index=0,
    )

    copied_instance = json_loads(json_dumps(instance))
    assert copied_instance.start_x == instance.start_x
    assert copied_instance.start_y == instance.start_y
    assert copied_instance.inclination == instance.inclination
    assert copied_instance.start_limited == instance.start_limited
    assert copied_instance.end_limited == instance.end_limited
    assert copied_instance.length == instance.length
    assert copied_instance.depth_limited == instance.depth_limited
    assert copied_instance.depth == instance.depth
    assert copied_instance.angle_start == instance.angle_start
    assert copied_instance.angle_end == instance.angle_end
    assert copied_instance.tool_position == instance.tool_position
    assert copied_instance.ref_side_index == instance.ref_side_index


def test_longitudinal_params_obj():
    instance = LongitudinalCut(
        start_x=214.922,
        start_y=30.0,
        inclination=40.0,
        start_limited=False,
        end_limited=True,
        length=100.0,
        depth_limited=False,
        depth=50.0,
        angle_start=113.344,
        angle_end=66.656,
        tool_position=AlignmentType.CENTER,
        ref_side_index=0,
    )

    params = instance.params.header_attributes
    params.update(instance.params.as_dict())

    assert params["Name"] == "LongitudinalCut"
    assert params["Process"] == "yes"
    assert params["Priority"] == "0"
    assert params["ProcessID"] == "0"
    assert params["ReferencePlaneID"] == "1"
    assert params["ToolPosition"] == "center"

    assert params["StartX"] == "214.922"
    assert params["StartY"] == "30.000"
    assert params["Inclination"] == "40.000"
    assert params["StartLimited"] == "no"
    assert params["EndLimited"] == "yes"
    assert params["Length"] == "100.000"
    assert params["DepthLimited"] == "no"
    assert params["Depth"] == "50.000"
    assert params["AngleStart"] == "113.344"
    assert params["AngleEnd"] == "66.656"
