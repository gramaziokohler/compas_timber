import copy

import pytest
from compas.datastructures import Mesh
from compas.geometry import Frame
from compas.geometry import Point
from compas.geometry import Vector
from compas.geometry import close

from compas_timber.parts.beam import Beam


@pytest.fixture
def mesh_geometry():
    return "mesh"


@pytest.fixture
def frame():
    return Frame([0.23, -0.19, 5.00], [1.0, 0.0, 0.0], [0.0, 0.1, 0.0])


def create_empty():
    _ = Beam()


def test_create_mesh(mocker, frame, mesh_geometry):
    beam = Beam(frame, length=1.0, width=2.0, height=3.0, geometry_type=mesh_geometry)

    assert close(beam.length, 1.0)
    assert close(beam.width, 2.0)
    assert close(beam.height, 3.0)
    assert beam.frame == frame
    assert isinstance(beam.geometry, Mesh)


def test_create_from_endpoints(mesh_geometry):
    P1 = Point(0, 0, 0)
    P2 = Point(1, 0, 0)
    B = Beam.from_endpoints(P1, P2, width=0.1, height=0.2, geometry_type=mesh_geometry)
    assert close(B.length, 1.0)  # the resulting beam length should be 1.0


def test__eq__(mesh_geometry):
    F1 = Frame(Point(0, 0, 0), Vector(1, 0, 0), Vector(0, 1, 0))
    F2 = Frame(Point(0, 0, 0), Vector(1, 0, 0), Vector(0, 1, 0))

    # checking if beams from identical input values are identical
    B1 = Beam(F1, length=1.0, width=0.1, height=0.17, geometry_type=mesh_geometry)
    B2 = Beam(F2, length=1.0, width=0.1, height=0.17, geometry_type=mesh_geometry)
    assert B1 is not B2
    assert B1.is_identical(B2)

    # checking for numerical imprecision artefacts
    # algebraically it equals 0.17, but numerically 0.16999999999999993,  https://docs.oracle.com/cd/E19957-01/806-3568/ncg_goldberg.html
    h = 10.1 - 9.93
    B2 = Beam(F2, length=1.0, width=0.1, height=h, geometry_type=mesh_geometry)
    assert B1.is_identical(B2)  # will the current tolerance setting of 1e-6 should return equal

    # checking if beams from equivalent imput values are identical
    B1 = Beam(F1, length=1.0, width=0.1, height=0.2, geometry_type=mesh_geometry)
    B2 = Beam.from_endpoints(
        Point(0, 0, 0), Point(1, 0, 0), z_vector=Vector(0, 0, 1), width=0.1, height=0.2, geometry_type=mesh_geometry
    )
    assert B1.is_identical(B2)


def test_deepcopy():
    B1 = Beam(Frame.worldXY(), length=1.0, width=0.1, height=0.2, geometry_type="mesh")
    B2 = copy.deepcopy(B1)

    assert B1.is_identical(B2)
    assert B2 is not B1
    assert B2.frame is not B1.frame
    assert B2.width is B1.width


def test_extension_to_plane():
    frame = Frame(Point(3.000, 0.000, 0.000), Vector(-1.000, 0.000, 0.000), Vector(0.000, -1.000, 0.000))
    _ = Beam(frame, length=3.00, width=0.12, height=0.06, geometry_type="mesh")
