import copy

import pytest
from compas.geometry import Point, Frame, Vector
from numpy import isclose

from compas_timber.parts.beam import Beam


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
    class FakeFeature(object):
        pass
    return [FakeFeature(), FakeFeature(), FakeFeature(), FakeFeature()]


def test_create_beam(test_frame):
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
