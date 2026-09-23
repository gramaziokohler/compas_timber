"""Protobuf round-trip tests for fasteners and their timber interfaces.

These cover the parts of the schema that stopped being `AnyData`: the interface
outline as a flat coordinate array, the hole dicts as a typed message, the
deferred BTLx feature list, and a PlateFastener's polyline cutouts.
"""

import json
import math

import pytest
from compas.data import json_dumps
from compas.geometry import Frame
from compas.geometry import Line
from compas.geometry import Point
from compas.geometry import Polyline
from compas.geometry import Vector
from compas_pb import pb_dump_bts
from compas_pb import pb_load_bts

from compas_timber.elements import BallNodeFastener
from compas_timber.elements import FastenerTimberInterface
from compas_timber.elements import PlateFastener
from compas_timber.fabrication import BTLxFromGeometryDefinition
from compas_timber.fabrication import Drilling


@pytest.fixture(autouse=True)
def load_serializers():
    import compas_timber.proto.conversions  # noqa: F401


def roundtrip(obj):
    return pb_load_bts(pb_dump_bts(obj))


def assert_lossless(obj):
    other = roundtrip(obj)
    assert type(other) is type(obj)
    assert json.loads(json_dumps(other, minimal=True)) == json.loads(json_dumps(obj, minimal=True))
    assert str(other.guid) == str(obj.guid)
    return other


@pytest.fixture
def interface():
    return FastenerTimberInterface(
        outline_points=[Point(0, 0, 0), Point(100, 0, 0), Point(100, 50, 0)],
        thickness=8.0,
        holes=[
            {"point": Point(10, 10, 0), "diameter": 6.0, "through": True},
            {"point": Point(50, 10, 0), "diameter": 8.0, "vector": Vector(0, 0, 1)},
        ],
        frame=Frame.worldXY(),
    )


def test_interface_roundtrip(interface):
    assert_lossless(interface)


def test_empty_interface_roundtrip():
    assert_lossless(FastenerTimberInterface())


def test_interface_outline_points_preserved(interface):
    other = roundtrip(interface)
    assert [list(p) for p in other.outline_points] == [list(p) for p in interface.outline_points]


def test_interface_without_outline_keeps_none_distinct_from_empty():
    assert roundtrip(FastenerTimberInterface()).outline_points is None
    assert roundtrip(FastenerTimberInterface(outline_points=[])).outline_points == []


def test_interface_holes_preserved(interface):
    other = roundtrip(interface)
    assert len(other.holes) == 2
    assert list(other.holes[0]["point"]) == [10.0, 10.0, 0.0]
    assert other.holes[0]["diameter"] == 6.0
    assert other.holes[0]["through"] is True
    assert "vector" not in other.holes[0]
    assert list(other.holes[1]["vector"]) == [0.0, 0.0, 1.0]


def test_interface_hole_keeps_unexpected_keys():
    hole = {"point": Point(1, 2, 3), "diameter": 5.0, "note": "custom", "count": 3}
    other = roundtrip(FastenerTimberInterface(holes=[hole]))
    assert other.holes[0]["note"] == "custom"
    assert other.holes[0]["count"] == 3


def test_interface_features_are_btlx_definitions():
    definition = BTLxFromGeometryDefinition(Drilling, [Line(Point(0, 0, 0), Point(0, 0, 10))])
    other = roundtrip(FastenerTimberInterface(features=[definition]))
    assert len(other.features) == 1
    assert other.features[0].processing is Drilling
    assert list(other.features[0].geometries[0].start) == [0.0, 0.0, 0.0]


@pytest.mark.xfail(
    reason="BallNodeFastener.__data__ omits the required `node_point`, so it does not round-trip through compas JSON either. Class-level gap, not a proto one.",
    raises=TypeError,
    strict=True,
)
def test_ball_node_fastener_roundtrip(interface):
    fastener = BallNodeFastener(Point(0, 0, 0))
    fastener.interfaces = [interface]
    other = roundtrip(fastener)
    assert len(other.interfaces) == 1
    assert str(other.guid) == str(fastener.guid)


@pytest.fixture
def plate_fastener(interface):
    return PlateFastener(
        outline=Polyline([Point(0, 0, 0), Point(100, 0, 0), Point(100, 50, 0), Point(0, 0, 0)]),
        thickness=8.0,
        interfaces=[interface],
        frame=Frame.worldXY(),
        angle=math.pi / 3,
        topology="L",
        cutouts=[Polyline([Point(5, 5, 0), Point(10, 5, 0), Point(10, 10, 0), Point(5, 5, 0)])],
    )


def test_plate_fastener_roundtrip(plate_fastener):
    assert_lossless(plate_fastener)


def test_plate_fastener_cutouts_are_polylines(plate_fastener):
    other = roundtrip(plate_fastener)
    assert len(other.cutouts) == 1
    assert isinstance(other.cutouts[0], Polyline)
    assert [list(p) for p in other.cutouts[0]] == [list(p) for p in plate_fastener.cutouts[0]]


def test_plate_fastener_interfaces_rebuilt(plate_fastener):
    other = roundtrip(plate_fastener)
    assert len(other.interfaces) == 1
    assert isinstance(other.interfaces[0], FastenerTimberInterface)
    assert other.interfaces[0].thickness == 8.0
