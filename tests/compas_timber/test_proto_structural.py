"""End-to-end protobuf round-trip tests for structural types."""

import json

import pytest
from compas.data import json_dumps
from compas.geometry import Frame
from compas.geometry import Line
from compas.geometry import Point
from compas_pb import pb_dump_bts
from compas_pb import pb_load_bts

from compas_timber.structural import StructuralSegment


@pytest.fixture(autouse=True)
def load_serializers():
    import compas_timber.proto.conversions  # noqa: F401


def assert_lossless(obj):
    other = pb_load_bts(pb_dump_bts(obj))
    assert type(other) is type(obj)
    assert json.loads(json_dumps(other, minimal=True)) == json.loads(json_dumps(obj, minimal=True))
    assert str(other.guid) == str(obj.guid)
    return other


@pytest.fixture
def line():
    return Line(Point(0, 0, 0), Point(3000, 0, 0))


def test_structural_segment_roundtrip(line):
    segment = StructuralSegment(line, Frame.worldXY(), cross_section=(100.0, 200.0))
    other = assert_lossless(segment)
    assert other.cross_section == (100.0, 200.0)
    assert other.line.start == line.start
    assert other.line.end == line.end
    assert other.frame == Frame.worldXY()


def test_structural_segment_without_cross_section_roundtrip(line):
    # cross_section is optional, and None must stay None rather than come back
    # as the empty tuple the repeated proto field would otherwise yield.
    segment = StructuralSegment(line, Frame.worldYZ())
    other = assert_lossless(segment)
    assert other.cross_section is None


def test_structural_segment_named_roundtrip(line):
    segment = StructuralSegment(line, Frame.worldXY(), name="post_01")
    other = assert_lossless(segment)
    assert other.name == "post_01"
    # `name` belongs to Data, not to the free-form attributes
    assert other.attributes == {}


def test_structural_segment_attributes_roundtrip(line):
    # Any keyword other than the declared ones is collected into `attributes`
    # and travels as the message's attributes map.
    segment = StructuralSegment(line, Frame.worldXY(), cross_section=(100.0, 200.0), role="post", load=5.5)
    other = assert_lossless(segment)
    assert other.attributes == {"role": "post", "load": 5.5}
    assert other.cross_section == (100.0, 200.0)
