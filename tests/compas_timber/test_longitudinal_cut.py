import pytest

from compas.data import json_dumps
from compas.data import json_loads
from compas.geometry import Line
from compas.geometry import Point
from compas.geometry import Plane
from compas.geometry import Frame
from compas.geometry import Vector
from compas.geometry import is_point_on_plane
from compas.geometry import Transformation

from compas_timber.elements import Beam
from compas_timber.fabrication import LongitudinalCut
from compas_timber.fabrication import AlignmentType

from compas_timber.fabrication.longitudinal_cut import LongitudinalCutProxy

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


def test_longitudinal_cut_transforms_with_beam(tol):
    centerline = Line(Point(x=251.4831588479271, y=-248.4761486653297, z=-361.20250690854925), Point(x=754.171905226478, y=240.25911119218435, z=349.45332666519346))
    z_vector = Vector(x=-0.510, y=-0.496, z=0.702)
    cross_section = (60, 100)
    beam_a = Beam.from_centerline(centerline, cross_section[0], cross_section[1], z_vector)
    beam_b = Beam.from_centerline(centerline, cross_section[0], cross_section[1], z_vector)

    # cut the beam
    plane = Plane(point=Point(x=452.495, y=-56.036, z=-25.372), normal=Vector(x=-0.864, y=0.279, z=0.419))
    instance_a = LongitudinalCut.from_plane_and_beam(plane, beam_a, ref_side_index=2)
    instance_b = LongitudinalCut.from_plane_and_beam(plane, beam_b, ref_side_index=2)

    transformation = Transformation.from_frame(Frame(Point(1000, 555, -69), Vector(1, 4, 5), Vector(6, 1, -3)))
    beam_b.transform(transformation)

    # properties should be the same after transformation
    assert tol.is_close(instance_a.start_x, instance_b.start_x)
    assert tol.is_close(instance_a.start_y, instance_b.start_y)
    assert tol.is_close(instance_a.inclination, instance_b.inclination)
    assert instance_a.start_limited == instance_b.start_limited
    assert instance_a.end_limited == instance_b.end_limited
    assert tol.is_close(instance_a.length, instance_b.length)
    assert instance_a.depth_limited == instance_b.depth_limited
    assert tol.is_close(instance_a.depth, instance_b.depth)
    assert tol.is_close(instance_a.angle_start, instance_b.angle_start)
    assert tol.is_close(instance_a.angle_end, instance_b.angle_end)
    assert tol.is_close(instance_a.ref_side_index, instance_b.ref_side_index)

    # planes should transform correctly
    cut_plane_a = instance_a.plane_from_params_and_beam(beam_a)
    cut_plane_b = instance_b.plane_from_params_and_beam(beam_b)

    cut_plane_a.transform(transformation)

    assert tol.is_allclose(cut_plane_a.normal, plane.normal.transformed(transformation))
    assert tol.is_allclose(cut_plane_a.normal, cut_plane_b.normal)
    assert tol.is_allclose(cut_plane_a.point, cut_plane_b.point)


def test_longitudinal_cut_proxy_transforms_with_beam(tol):
    centerline = Line(Point(x=251.4831588479271, y=-248.4761486653297, z=-361.20250690854925), Point(x=754.171905226478, y=240.25911119218435, z=349.45332666519346))
    z_vector = Vector(x=-0.510, y=-0.496, z=0.702)
    cross_section = (60, 100)
    beam_a = Beam.from_centerline(centerline, cross_section[0], cross_section[1], z_vector)
    beam_b = Beam.from_centerline(centerline, cross_section[0], cross_section[1], z_vector)

    # cut the beam
    plane = Plane(point=Point(x=452.495, y=-56.036, z=-25.372), normal=Vector(x=-0.864, y=0.279, z=0.419))
    instance_a = LongitudinalCutProxy(plane, beam_a, ref_side_index=2)
    instance_b = LongitudinalCutProxy(plane, beam_b, ref_side_index=2)

    transformation = Transformation.from_frame(Frame(Point(1000, 555, -69), Vector(1, 4, 5), Vector(6, 1, -3)))
    beam_b.transform(transformation)

    # unproxify to get the actual LongitudinalCut instances
    long_cut_a = instance_a.unproxified()
    long_cut_b = instance_b.unproxified()

    # properties should be the same after transformation
    assert tol.is_close(long_cut_a.start_x, long_cut_b.start_x)
    assert tol.is_close(long_cut_a.start_y, long_cut_b.start_y)
    assert tol.is_close(long_cut_a.inclination, long_cut_b.inclination)
    assert long_cut_a.start_limited == long_cut_b.start_limited
    assert long_cut_a.end_limited == long_cut_b.end_limited
    assert tol.is_close(long_cut_a.length, long_cut_b.length)
    assert long_cut_a.depth_limited == long_cut_b.depth_limited
    assert tol.is_close(long_cut_a.depth, long_cut_b.depth)
    assert tol.is_close(long_cut_a.angle_start, long_cut_b.angle_start)
    assert tol.is_close(long_cut_a.angle_end, long_cut_b.angle_end)
    assert tol.is_close(long_cut_a.ref_side_index, long_cut_b.ref_side_index)

    # planes should transform correctly
    cut_plane_a = long_cut_a.plane_from_params_and_beam(beam_a)
    cut_plane_b = long_cut_b.plane_from_params_and_beam(beam_b)

    cut_plane_a.transform(transformation)

    assert tol.is_allclose(cut_plane_a.normal, plane.normal.transformed(transformation))
    assert tol.is_allclose(cut_plane_a.normal, cut_plane_b.normal)
    assert tol.is_allclose(cut_plane_a.point, cut_plane_b.point)
