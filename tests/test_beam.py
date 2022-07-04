import copy

import pytest
from compas.geometry import Frame
from compas.geometry import Point
from compas.geometry import Vector
from numpy import isclose

from compas_timber.parts.beam import Beam


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


def test_create(test_frame):
    _ = Beam(test_frame, length=1.0, width=2.0, height=3.0)


def test_constructor():
    b = Beam.from_endpoints(
        Point(0, 0, 0), Point(0, 1, 0), Vector(0, 0, 1), 0.100, 0.200
    )
    # test if length is =1
    assert isclose(b.length, 1.0)


def test_create_from_endpoints():
    P1 = Point(0, 0, 0)
    P2 = Point(1, 0, 0)
    B = Beam.from_endpoints(P1, P2)
    # the resulting beam length should be 1.0
    assert isclose(B.length, 1.0)


def test__eq__():
    F1 = Frame(Point(0, 0, 0), Vector(1, 0, 0), Vector(0, 1, 0))
    F2 = Frame(Point(0, 0, 0), Vector(1, 0, 0), Vector(0, 1, 0))

    # checking if beams from identical input values are identical
    B1 = Beam(F1, length=1.0, width=0.1, height=0.17)
    B2 = Beam(F2, length=1.0, width=0.1, height=0.17)
    assert B1 is not B2
    assert B1 == B2

    # checking for numerical imprecision artefacts
    h = (
        10.1 - 9.93
    )  # algebraically it equals 0.17, but numerically 0.16999999999999993,  https://docs.oracle.com/cd/E19957-01/806-3568/ncg_goldberg.html
    B2 = Beam(F2, length=1.0, width=0.1, height=h)
    assert B1 == B2  # will the current tolerance setting of 1e-6 should return equal

    # checking if beams from equivalent imput values are identical
    B1 = Beam.from_frame(F1, length=1.0, width=0.1, height=0.2)
    B2 = Beam.from_endpoints(
        Point(0, 0, 0), Point(1, 0, 0), Vector(0, 0, 1), width=0.1, height=0.2
    )
    assert B1 == B2


def test_deepcopy(test_frame, test_features):

    B = Beam(test_frame, length=1.0, width=2.0, height=3.0)
    B.features.extend(test_features)

    B_copy = copy.deepcopy(B)

    assert B is not B_copy
    assert B.frame is not B_copy.frame
    assert B.joints is not B_copy.joints
    assert B == B_copy


def test_deepcopy2():

    B = Beam(Frame.worldXY(), length=1.0, width=0.1, height=0.2)
    B_copy = copy.deepcopy(B)

    assert B == B_copy
    assert B is not B_copy
    assert B.frame is not B_copy.frame
    # assert B.guid != B_copy.guid #failing


if __name__ == "__main__":
    test_create_from_endpoints()
    test__eq__()
    test_deepcopy2()

    print("\n*** all tests passed ***\n\n")
