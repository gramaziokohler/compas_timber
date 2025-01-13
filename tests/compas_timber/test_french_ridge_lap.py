import pytest

from compas.data import json_dumps
from compas.data import json_loads
from compas.geometry import Line
from compas.geometry import Point
from compas.geometry import Plane
from compas.geometry import Vector
from compas.geometry import is_point_on_plane

from compas_timber.elements import Beam
from compas_timber.fabrication import FrenchRidgeLap
from compas_timber.fabrication import OrientationType
from compas_timber.fabrication import EdgePositionType

from compas.tolerance import Tolerance


@pytest.fixture
def tol():
    return Tolerance(unit="MM", absolute=1e-3, relative=1e-3)


def test_ortho_french_ridge_lap_ref(tol):
    centerline = Line(Point(x=2000.0, y=0.0, z=0.0), Point(x=-30.0, y=0.0, z=0.0))
    cross_section = (60, 100)
    beam = Beam.from_centerline(centerline, cross_section[0], cross_section[1])

    # cut the start of the beam
    other_beam = Beam.from_centerline(Line(Point(x=0.0, y=30.0, z=0.0), Point(x=0.0, y=-2461.14222434, z=0.0)), 60, 100)
    plane = Plane(point=Point(x=-30.000, y=0.000, z=-50.000), normal=Vector(x=-1.000, y=0.000, z=0.000))
    drillhole_diam = 10.0

    instance = FrenchRidgeLap.from_beam_beam_and_plane(beam, other_beam, plane, drillhole_diam, ref_side_index=2)

    assert instance.orientation == OrientationType.END
    assert tol.is_close(instance.start_x, 2030.0)
    assert tol.is_close(instance.angle, 90.0)
    assert instance.ref_position == EdgePositionType.REFEDGE
    assert instance.drillhole
    assert tol.is_close(instance.drillhole_diam, 10.0)
    assert tol.is_close(instance.ref_side_index, 2)

    cut_plane = Plane.from_frame(instance.frame_from_params_and_beam(beam))
    # should be the same plane, but point might be different
    assert cut_plane.is_parallel(plane, tol=tol.absolute)
    assert is_point_on_plane(cut_plane.point, plane, tol=tol.absolute)


def test_ortho_french_ridge_lap_opp(tol):
    centerline = Line(Point(x=0.0, y=30.0, z=0.0), Point(x=0.0, y=-2461.14222434, z=0.0))
    cross_section = (60, 100)
    beam = Beam.from_centerline(centerline, cross_section[0], cross_section[1])

    # cut the start of the beam
    other_beam = Beam.from_centerline(Line(Point(x=2000.0, y=0.0, z=0.0), Point(x=-30.0, y=0.0, z=0.0)), 60, 100)
    plane = Plane(point=Point(x=2000.000, y=30.000, z=-50.000), normal=Vector(x=0.000, y=1.000, z=-0.000))

    instance = FrenchRidgeLap.from_beam_beam_and_plane(beam, other_beam, plane, ref_side_index=0)

    assert instance.orientation == OrientationType.START
    assert tol.is_close(instance.start_x, 0.0)
    assert tol.is_close(instance.angle, 90.0)
    assert instance.ref_position == EdgePositionType.OPPEDGE
    assert not instance.drillhole
    assert tol.is_close(instance.drillhole_diam, 0.0)
    assert tol.is_close(instance.ref_side_index, 0)

    cut_plane = Plane.from_frame(instance.frame_from_params_and_beam(beam))
    # should be the same plane, but point might be different
    assert cut_plane.is_parallel(plane, tol=tol.absolute)
    assert is_point_on_plane(cut_plane.point, plane, tol=tol.absolute)


def test_french_ridge_lap_data(tol):
    instance = FrenchRidgeLap(OrientationType.START, 14.23, 31.24, EdgePositionType.REFEDGE, True, 11.0, ref_side_index=3)
    copied_instance = json_loads(json_dumps(instance))

    assert copied_instance.orientation == instance.orientation
    assert copied_instance.start_x == instance.start_x
    assert copied_instance.angle == instance.angle
    assert copied_instance.ref_position == instance.ref_position
    assert copied_instance.drillhole == instance.drillhole
    assert copied_instance.ref_side_index == instance.ref_side_index


def test_french_ridge_lap_params_obj():
    instance = FrenchRidgeLap(OrientationType.START, 14.23, 31.24, EdgePositionType.REFEDGE, True, 11.0, ref_side_index=3)
    params = instance.params_dict

    assert params["Name"] == "FrenchRidgeLap"
    assert params["Process"] == "yes"
    assert params["Priority"] == "0"
    assert params["ProcessID"] == "0"
    assert params["ReferencePlaneID"] == "4"

    assert params["Orientation"] == "start"
    assert params["StartX"] == "14.230"
    assert params["Angle"] == "31.240"
    assert params["RefPosition"] == "refedge"
    assert params["Drillhole"] == "yes"
    assert params["DrillholeDiam"] == "11.000"
