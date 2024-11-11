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
from compas_timber._fabrication import JackRafterCut
from compas_timber._fabrication import OrientationType

from compas.tolerance import Tolerance


@pytest.fixture
def tol():
    return Tolerance(unit="MM", absolute=1e-3, relative=1e-3)


def test_jack_rafter_cut_from_plane_start(tol):
    centerline = Line(Point(x=270.0, y=270.0, z=590.0), Point(x=1220.0, y=680.0, z=590.0))
    cross_section = (60, 120)
    beam = Beam.from_centerline(centerline, cross_section[0], cross_section[1])

    # cut the start of the beam
    normal = Vector(x=-0.996194698092, y=-0.0, z=-0.0871557427477)
    plane = Plane(Point(x=460.346635340, y=445.167151490, z=473.942755901), normal)
    instance = JackRafterCut.from_plane_and_beam(plane, beam)

    # assert tol.is_close(instance.start_x, 214.922)
    # assert tol.is_close(instance.start_y, 0.0)
    # assert tol.is_close(instance.angle, 113.344)
    # assert tol.is_close(instance.inclination, 95.443)
    # assert tol.is_close(instance.ref_side_index, 0)

    cut_plane = instance.plane_from_params_and_beam(beam)

    # should be the same plane, but point might be different
    assert cut_plane.is_parallel(plane, tol=tol.absolute)
    assert is_point_on_plane(cut_plane.point, plane, tol=tol.absolute)


def test_jack_rafter_cut_from_plane_end(tol):
    centerline = Line(Point(x=270.0, y=270.0, z=590.0), Point(x=1220.0, y=680.0, z=590.0))
    cross_section = (60, 120)
    beam = Beam.from_centerline(centerline, cross_section[0], cross_section[1])

    # cut the end of the beam
    normal = Vector(x=-0.996194698092, y=-0.0, z=-0.0871557427477) * -1.0
    plane = Plane(Point(x=460.346635340, y=445.167151490, z=473.942755901), normal)
    instance = JackRafterCut.from_plane_and_beam(plane, beam)

    assert tol.is_close(instance.start_x, 214.922)
    assert tol.is_close(instance.start_y, 0.0)
    assert tol.is_close(instance.angle, 113.344)
    assert tol.is_close(instance.inclination, 95.443)
    assert tol.is_close(instance.ref_side_index, 0)

    cut_plane = instance.plane_from_params_and_beam(beam)

    # should be the same plane, but point might be different
    assert cut_plane.is_parallel(plane, tol=tol.absolute)
    assert is_point_on_plane(cut_plane.point, plane, tol=tol.absolute)


def test_jack_rafter_cut_from_frame(tol):
    centerline = Line(Point(x=270.0, y=270.0, z=590.0), Point(x=1220.0, y=680.0, z=590.0))
    cross_section = (60, 120)
    beam = Beam.from_centerline(centerline, cross_section[0], cross_section[1])

    # cut the start of the beam
    normal = Vector(x=-0.996194698092, y=-0.0, z=-0.0871557427477)
    plane = Plane(Point(x=460.346635340, y=445.167151490, z=473.942755901), normal)
    instance = JackRafterCut.from_plane_and_beam(Frame.from_plane(plane), beam)

    # assert tol.is_close(instance.start_x, 214.922)
    # assert tol.is_close(instance.start_y, 0.0)
    # assert tol.is_close(instance.angle, 113.344)
    # assert tol.is_close(instance.inclination, 95.443)
    # assert tol.is_close(instance.ref_side_index, 0)

    cut_plane = instance.plane_from_params_and_beam(beam)

    # should be the same plane, but point might be different
    assert cut_plane.is_parallel(plane, tol=tol.absolute)
    assert is_point_on_plane(cut_plane.point, plane, tol=tol.absolute)


def test_jack_rafter_cut_data(tol):
    instance = JackRafterCut(OrientationType.START, 14.23, 0.22, 42, 123.555, 95.2, ref_side_index=3)

    copied_instance = json_loads(json_dumps(instance))

    assert copied_instance.orientation == instance.orientation
    assert copied_instance.start_x == instance.start_x
    assert copied_instance.start_y == instance.start_y
    assert copied_instance.angle == instance.angle
    assert copied_instance.inclination == instance.inclination
    assert copied_instance.ref_side_index == instance.ref_side_index


def test_jack_rafter_params_obj():
    instance = JackRafterCut(OrientationType.START, 14.23, 0.22, 42, 123.555, 95.2, ref_side_index=3)

    params = instance.params_dict

    assert params["Name"] == "JackRafterCut"
    assert params["Process"] == "yes"
    assert params["Priority"] == "0"
    assert params["ProcessID"] == "0"
    assert params["ReferencePlaneID"] == "4"

    assert params["Orientation"] == "start"
    assert params["StartX"] == "14.230"
    assert params["StartY"] == "0.220"
    assert params["StartDepth"] == "42.000"
    assert params["Angle"] == "123.555"
    assert params["Inclination"] == "95.200"
