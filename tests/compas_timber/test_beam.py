import copy

import pytest
from compas.geometry import Frame
from compas.geometry import Point
from compas.geometry import Vector
from numpy import isclose

from compas_timber.parts.beam import Beam

geometry_type = "mesh"

def create_empty():
    _ = Beam()

def test_create(test_frame):
    _ = Beam(test_frame, length=1.0, width=2.0, height=3.0, geometry_type=geometry_type)


def test_create_from_endpoints():
    P1 = Point(0, 0, 0)
    P2 = Point(1, 0, 0)
    B = Beam.from_endpoints(P1, P2, width=0.1, height=0.2, geometry_type=geometry_type)
    assert isclose(B.length, 1.0)     # the resulting beam length should be 1.0


def test__eq__():
    F1 = Frame(Point(0, 0, 0), Vector(1, 0, 0), Vector(0, 1, 0))
    F2 = Frame(Point(0, 0, 0), Vector(1, 0, 0), Vector(0, 1, 0))

    # checking if beams from identical input values are identical
    B1 = Beam(F1, length=1.0, width=0.1, height=0.17, geometry_type=geometry_type)
    B2 = Beam(F2, length=1.0, width=0.1, height=0.17, geometry_type=geometry_type)
    assert B1 is not B2
    assert B1.is_identical(B2)

    # checking for numerical imprecision artefacts
    # algebraically it equals 0.17, but numerically 0.16999999999999993,  https://docs.oracle.com/cd/E19957-01/806-3568/ncg_goldberg.html
    h = 10.1 - 9.93
    B2 = Beam(F2, length=1.0, width=0.1, height=h, geometry_type=geometry_type)
    assert B1.is_identical(B2) # will the current tolerance setting of 1e-6 should return equal

    # checking if beams from equivalent imput values are identical
    B1 = Beam(F1, length=1.0, width=0.1, height=0.2, geometry_type=geometry_type)
    B2 = Beam.from_endpoints(
        Point(0, 0, 0), Point(1, 0, 0), z_vector=Vector(0, 0, 1), width=0.1, height=0.2, geometry_type=geometry_type)
    assert B1.is_identical(B2)


def test_deepcopy():

    B1 = Beam(Frame.worldXY(), length=1.0, width=0.1, height=0.2, geometry_type=geometry_type)
    B2 = copy.deepcopy(B1)

    assert B1.is_identical(B2)
    assert B2 is not B1
    assert B2.frame is not B1.frame
    assert B2.width is B1.width

    # ---------------------------------------------

    @pytest.fixture()
    def test_frame():
        return Frame(Point(-0.43, 0.69, -0.11), [1.0, 0.0, 0.0], [0.0, 1.0, 0.0])

    @pytest.fixture()
    def test_joints():
        class FakeJoint(object):
            pass

        return [FakeJoint(), FakeJoint(), FakeJoint(), FakeJoint()]

    @pytest.fixture()
    def test_features():
        return [(Frame.worldXY(), "trim")]


if __name__ == "__main__":
    create_empty()
    #test_create()
    test_create_from_endpoints()
    test__eq__()
    test_deepcopy()

    print("\n*** all tests passed ***\n\n")
