import copy

import pytest
from compas.geometry import Point, Frame, Vector
from numpy import isclose

from compas_timber.parts.beam import Beam


def test_create_from_endpoints():
    P1 = Point(0, 0, 0)
    P2 = Point(1, 0, 0)
    B = Beam.from_endpoints(P1, P2, width=10, height=2)
    # the resulting beam length should be 1.0
    assert isclose(B.length, 1.0)


def test_deepcopy(test_frame, test_joints, test_features):
    b1 = Beam(test_frame, length=1., width=2., height=3.)
    b1.joints.extend(test_joints)
    b1.features.extend(test_features)

    b2 = copy.deepcopy(b1)

    assert b1 is not b2
    assert b1.frame is not b2.frame
    assert b1.joints is not b2.joints
    assert b1 == b2  # after deepcopy the objects should be the same


def test__eq__():
    F1 = Frame(Point(0, 0, 0), Vector(1, 0, 0), Vector(0, 1, 0))
    F2 = Frame(Point(0, 0, 0), Vector(1, 0, 0), Vector(0, 1, 0))

    # checking if beams from identical input values are identical
    B1 = Beam(F1, length=1.0, width=0.1, height=0.17)
    B2 = Beam(F2, length=1.0, width=0.1, height=0.17)
    assert B1 is not B2
    assert B1 == B2

    # checking for numerical imprecision artefacts
    h = 10.1 - 9.93  # algebraically it equals 0.17, but numerically 0.16999999999999993,  https://docs.oracle.com/cd/E19957-01/806-3568/ncg_goldberg.html
    B2 = Beam(F2, length=1.0, width=0.1, height=h)
    assert B1 == B2  # will the current tolerance setting of 1e-6 should return equal

    # checking if beams from equivalent imput values are identical
    B1 = Beam.from_frame(F1, length=1.0, width=0.1, height=0.2)
    B2 = Beam.from_endpoints(Point(0, 0, 0), Point(1, 0, 0), Vector(0, 0, 1), width=0.1, height=0.2)
    assert B1 == B2


@pytest.fixture()
def test_frame():
    return Frame(Point(-.43, .69, -.11), [1., 0., 0.], [0., 1., 0.])


@pytest.fixture()
def test_joints():
    class FakeJoint(object):
        pass
    return [FakeJoint(), FakeJoint(), FakeJoint(), FakeJoint()]


@pytest.fixture()
def test_features():
    return [(Frame.worldXY(), "trim")]


def test_create(test_frame):
    _ = Beam(test_frame, length=1., width=2., height=3.)


def test_beam_deepcopy(test_frame, test_joints, test_features):
    b1 = Beam(test_frame, length=1., width=2., height=3.)
    b1.joints.extend(test_joints)
    b1.features.extend(test_features)

    b2 = copy.deepcopy(b1)

    assert b1 is not b2
    assert b1.frame is not b2.frame
    assert b1.joints is not b2.joints


def test_beam_constructor():
    b = Beam.from_endpoints(Point(0, 0, 0), Point(0, 1, 0), Vector(0, 0, 1), 0.100, 0.200)
    # test if length is =1
    assert isclose(b.length, 1.0)


if __name__ == '__main__':
    test_create_from_endpoints()
    test__eq__()
    print("\n*** all tests passed ***\n\n")
