from compas.geometry import Point
from compas.geometry import Vector

from compas_timber.connections import BallNodeJoint
from compas_timber.elements import Beam
from compas_timber.model import TimberModel


def test_create():
    B1 = Beam.from_endpoints(Point(0, 100, 0), Point(0, 0, 0), z_vector=Vector(0, 0, 1), width=10, height=20)
    B2 = Beam.from_endpoints(Point(-100, 100, 0), Point(0, 0, 0), z_vector=Vector(0, 0, 1), width=10, height=20)
    B3 = Beam.from_endpoints(Point(-100, -100, 0), Point(0, 0, 0), z_vector=Vector(0, 0, 1), width=10, height=20)
    A = TimberModel()
    A.add_element(B1)
    A.add_element(B2)
    A.add_element(B3)
    instance = BallNodeJoint.create(A, *[B1, B2, B3])

    assert len(list(instance.elements)) + len(instance.generated_elements) == 4
    assert isinstance(instance, BallNodeJoint)
    assert len(list(A.copy().elements())) == 4


def test_add_features_tracks_all_beam_features():
    """joint.features must contain every feature applied to the beams, so clear_features() can remove them all."""
    B1 = Beam.from_endpoints(Point(0, 100, 0), Point(0, 0, 0), z_vector=Vector(0, 0, 1), width=10, height=20)
    B2 = Beam.from_endpoints(Point(-100, 100, 0), Point(0, 0, 0), z_vector=Vector(0, 0, 1), width=10, height=20)
    B3 = Beam.from_endpoints(Point(-100, -100, 0), Point(0, 0, 0), z_vector=Vector(0, 0, 1), width=10, height=20)
    A = TimberModel()
    A.add_element(B1)
    A.add_element(B2)
    A.add_element(B3)
    instance = BallNodeJoint.create(A, B1, B2, B3)

    instance.add_features()

    total_applied = len(B1.features) + len(B2.features) + len(B3.features)
    assert total_applied > 0
    assert len(instance.features) == total_applied


def test_clear_features_removes_all_beam_features():
    B1 = Beam.from_endpoints(Point(0, 100, 0), Point(0, 0, 0), z_vector=Vector(0, 0, 1), width=10, height=20)
    B2 = Beam.from_endpoints(Point(-100, 100, 0), Point(0, 0, 0), z_vector=Vector(0, 0, 1), width=10, height=20)
    B3 = Beam.from_endpoints(Point(-100, -100, 0), Point(0, 0, 0), z_vector=Vector(0, 0, 1), width=10, height=20)
    A = TimberModel()
    A.add_element(B1)
    A.add_element(B2)
    A.add_element(B3)
    instance = BallNodeJoint.create(A, B1, B2, B3)
    instance.add_features()

    instance.clear_features()

    assert instance.features == []
    assert B1.features == []
    assert B2.features == []
    assert B3.features == []
