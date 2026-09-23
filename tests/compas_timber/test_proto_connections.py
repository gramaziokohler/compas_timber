"""End-to-end protobuf round-trip tests for joints and joint candidates."""

import json

import pytest
from compas.data import json_dumps
from compas.geometry import Line
from compas.geometry import Point
from compas_pb import pb_dump_bts
from compas_pb import pb_load_bts

from compas_timber.connections import JointCandidate
from compas_timber.connections import JointTopology
from compas_timber.connections import LButtJoint
from compas_timber.connections import LMiterJoint
from compas_timber.connections import TButtJoint
from compas_timber.connections import XLapJoint
from compas_timber.elements import Beam
from compas_timber.model import TimberModel


@pytest.fixture(autouse=True)
def load_serializers():
    import compas_timber.proto.conversions  # noqa: F401


def assert_lossless(obj):
    other = pb_load_bts(pb_dump_bts(obj))
    assert type(other) is type(obj)
    assert json.loads(json_dumps(other, minimal=True)) == json.loads(json_dumps(obj, minimal=True))
    assert str(other.guid) == str(obj.guid)
    return other


def _model_with_two_beams():
    model = TimberModel()
    a = Beam.from_centerline(Line(Point(0, 0, 0), Point(3000, 0, 0)), width=100.0, height=200.0)
    b = Beam.from_centerline(Line(Point(3000, 0, 0), Point(3000, 3000, 0)), width=100.0, height=200.0)
    model.add_element(a)
    model.add_element(b)
    return model, a, b


def test_l_miter_joint_roundtrip():
    model, a, b = _model_with_two_beams()
    joint = LMiterJoint.create(model, a, b)
    other = assert_lossless(joint)
    assert list(other.element_guids) == list(joint.element_guids)


def test_t_butt_joint_roundtrip():
    """TButtJoint has no __data__ of its own; it inherits ButtJoint's fields."""
    model, a, b = _model_with_two_beams()
    joint = TButtJoint.create(model, a, b)
    other = assert_lossless(joint)
    assert other.mill_depth == joint.mill_depth


def test_l_butt_joint_roundtrip():
    model, a, b = _model_with_two_beams()
    other = assert_lossless(LButtJoint.create(model, a, b))
    assert other.modify_cross is not None


def test_x_lap_joint_roundtrip():
    """XLapJoint inherits LapJoint's fields without overriding __data__."""
    model, a, b = _model_with_two_beams()
    joint = XLapJoint.create(model, a, b)
    other = assert_lossless(joint)
    assert other.flip_lap_side == joint.flip_lap_side


def test_joint_topology_and_location_roundtrip():
    model, a, b = _model_with_two_beams()
    joint = LMiterJoint.create(model, a, b)
    other = assert_lossless(joint)
    assert other.topology == joint.topology
    # compare the stored location; `.location` computes lazily from the
    # elements, which a detached round-tripped joint cannot reach
    assert other._location == joint._location


def test_joint_candidate_roundtrip():
    candidate = JointCandidate(
        element_guids=["aaa", "bbb"],
        topology=JointTopology.TOPO_L,
        location=Point(1.0, 2.0, 3.0),
        distance=0.5,
    )
    other = assert_lossless(candidate)
    assert list(other.element_guids) == ["aaa", "bbb"]
    assert other.distance == 0.5
    assert other.topology == JointTopology.TOPO_L


def test_joint_candidate_extra_kwargs_roundtrip():
    """JointCandidate merges an open-ended _extra_kwargs dict into __data__."""
    candidate = JointCandidate(
        element_guids=["aaa", "bbb"],
        topology=JointTopology.TOPO_T,
        location=Point(0.0, 0.0, 0.0),
        distance=1.0,
        a_segment_index=2,
    )
    other = assert_lossless(candidate)
    assert other.__data__["a_segment_index"] == 2
