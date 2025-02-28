from compas.geometry import Point
from compas.geometry import Vector
from compas_timber.elements.beam import Beam

from compas_timber.connections.utilities import are_beams_coplanar


def test_bemas_coplanar_parallel():
    B1 = Beam.from_endpoints(Point(0, 0, 0), Point(1, 0, 0), z_vector=Vector(0, 0, 1), width=0.1, height=0.2)
    B2 = Beam.from_endpoints(Point(0, 0, 0), Point(-1, 0, 0), z_vector=Vector(0, 0, 1), width=0.1, height=0.2)
    assert are_beams_coplanar(B1, B2)


def test_beams_coplanar_parallel_bad_z():
    B1 = Beam.from_endpoints(Point(0, 0, 0), Point(1, 0, 0), z_vector=Vector(0, 0, 1), width=0.1, height=0.2)
    B2 = Beam.from_endpoints(Point(0, 0, 0), Point(-1, 0, 0), z_vector=Vector(0, 1, 1), width=0.1, height=0.2)
    assert not are_beams_coplanar(B1, B2)


def test_parallel_coplanar_different_height():
    B1 = Beam.from_endpoints(Point(0, 0, 0), Point(1, 0, 0), z_vector=Vector(0, 0, 1), width=0.1, height=0.2)
    B2 = Beam.from_endpoints(Point(0, 0, 0), Point(-1, 0, 0), z_vector=Vector(0, 0, 1), width=0.1, height=0.1)
    assert not are_beams_coplanar(B1, B2)


def test_parallel_coplanar_different_width():
    B1 = Beam.from_endpoints(Point(0, 0, 0), Point(1, 0, 0), z_vector=Vector(0, 0, 1), width=0.1, height=0.2)
    B2 = Beam.from_endpoints(Point(0, 0, 0), Point(-1, 0, 0), z_vector=Vector(0, 0, 1), width=0.2, height=0.2)
    assert not are_beams_coplanar(B1, B2)


def test_beams_coplanar_parallel_zvectors_perpendicular():
    B1 = Beam.from_endpoints(Point(0, 0, 0), Point(1, 0, 0), z_vector=Vector(0, 0, 1), width=0.1, height=0.2)
    B2 = Beam.from_endpoints(Point(0, 0, 0), Point(-1, 0, 0), z_vector=Vector(0, 1, 0), width=0.1, height=0.2)
    assert not are_beams_coplanar(B1, B2)


def test_beams_coplanar_parallel_zvectors_perpendicular_flipped_dims():
    B1 = Beam.from_endpoints(Point(0, 0, 0), Point(1, 0, 0), z_vector=Vector(0, 0, 1), width=0.1, height=0.2)
    B2 = Beam.from_endpoints(Point(0, 0, 0), Point(-1, 0, 0), z_vector=Vector(0, 1, 0), width=0.2, height=0.1)
    assert are_beams_coplanar(B1, B2)


def test_beams_coplanar_angle():
    B1 = Beam.from_endpoints(Point(0, 0, 0), Point(1, 1, 0), z_vector=Vector(0, 0, 1), width=0.1, height=0.2)
    B2 = Beam.from_endpoints(Point(0, 0, 0), Point(-1, 0, 0), z_vector=Vector(0, 0, 1), width=0.1, height=0.2)
    assert are_beams_coplanar(B1, B2)


def test_beams_coplanar_angle_bad_z():
    B1 = Beam.from_endpoints(Point(0, 0, 0), Point(1, 1, 0), z_vector=Vector(0, 0, 1), width=0.1, height=0.2)
    B2 = Beam.from_endpoints(Point(0, 0, 0), Point(-1, 0, 0), z_vector=Vector(0, 1, 1), width=0.1, height=0.2)
    assert not are_beams_coplanar(B1, B2)


def test_beams_coplanar_angle_different_width():
    B1 = Beam.from_endpoints(Point(0, 0, 0), Point(1, 1, 0), z_vector=Vector(0, 0, 1), width=0.1, height=0.2)
    B2 = Beam.from_endpoints(Point(0, 0, 0), Point(-1, 0, 0), z_vector=Vector(0, 0, 1), width=0.2, height=0.2)
    assert are_beams_coplanar(B1, B2)


def test_beams_coplanar_angle_different_height():
    B1 = Beam.from_endpoints(Point(0, 0, 0), Point(1, 1, 0), z_vector=Vector(0, 0, 1), width=0.1, height=0.2)
    B2 = Beam.from_endpoints(Point(0, 0, 0), Point(-1, 0, 0), z_vector=Vector(0, 0, 1), width=0.1, height=0.1)
    assert not are_beams_coplanar(B1, B2)


def test_beams_coplanar_angle_z_flipped_different_width():
    B1 = Beam.from_endpoints(Point(0, 0, 0), Point(1, 1, 0), z_vector=Vector(-1, 1, 0), width=0.1, height=0.2)
    B2 = Beam.from_endpoints(Point(0, 0, 0), Point(-1, 0, 0), z_vector=Vector(0, 1, 0), width=0.2, height=0.2)
    assert not are_beams_coplanar(B1, B2)


def test_beams_coplanar_angle_z_flipped_different_height():
    B1 = Beam.from_endpoints(Point(0, 0, 0), Point(1, 1, 0), z_vector=Vector(-1, 1, 0), width=0.1, height=0.2)
    B2 = Beam.from_endpoints(Point(0, 0, 0), Point(-1, 0, 0), z_vector=Vector(0, 1, 0), width=0.1, height=0.1)
    assert are_beams_coplanar(B1, B2)


def test_beams_coplanar_angle_flipped():
    B1 = Beam.from_endpoints(Point(0, 0, 0), Point(1, 1, 0), z_vector=Vector(-1, 1, 0), width=0.1, height=0.2)
    B2 = Beam.from_endpoints(Point(0, 0, 0), Point(-1, 0, 0), z_vector=Vector(0, 1, 0), width=0.1, height=0.2)
    assert are_beams_coplanar(B1, B2)


def test_beams_coplanar_angle_zvectors_perpendicular():
    B1 = Beam.from_endpoints(Point(0, 0, 0), Point(1, 1, 0), z_vector=Vector(0, 0, 1), width=0.1, height=0.2)
    B2 = Beam.from_endpoints(Point(0, 0, 0), Point(-1, 0, 0), z_vector=Vector(0, 1, 0), width=0.1, height=0.2)
    assert not are_beams_coplanar(B1, B2)


def test_beams_coplanar_angle_zvectors_perpendicular_flipped_dims():
    B1 = Beam.from_endpoints(Point(0, 0, 0), Point(1, 1, 0), z_vector=Vector(0, 0, 1), width=0.1, height=0.2)
    B2 = Beam.from_endpoints(Point(0, 0, 0), Point(-1, 0, 0), z_vector=Vector(0, 1, 0), width=0.2, height=0.2)
    assert are_beams_coplanar(B1, B2)
