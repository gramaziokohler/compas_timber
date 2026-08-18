"""End-to-end protobuf round-trip tests for BTLx processings."""

import json

import pytest
from compas.data import json_dumps
from compas.geometry import Frame
from compas.geometry import Line
from compas.geometry import Point
from compas.geometry import Polyline
from compas_pb import pb_dump_bts
from compas_pb import pb_load_bts

from compas_timber.elements import Beam
from compas_timber.fabrication import Contour
from compas_timber.fabrication import DoubleCut
from compas_timber.fabrication import Drilling
from compas_timber.fabrication import FreeContour
from compas_timber.fabrication import JackRafterCut
from compas_timber.fabrication import Lap
from compas_timber.fabrication import Mortise
from compas_timber.fabrication import Slot
from compas_timber.fabrication import Text


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
def beam():
    return Beam.from_centerline(Line(Point(0, 0, 0), Point(3000, 0, 0)), width=100.0, height=200.0)


def test_jack_rafter_cut_roundtrip(beam):
    other = assert_lossless(JackRafterCut.from_plane_and_beam(Frame.worldYZ(), beam))
    assert other.PROCESSING_NAME == "JackRafterCut"


def test_drilling_roundtrip():
    other = assert_lossless(Drilling(start_x=100.0, start_y=50.0, diameter=8.0, depth=25.0, depth_limited=True))
    assert other.diameter == 8.0
    assert other.depth_limited is True


def test_double_cut_roundtrip():
    assert_lossless(DoubleCut(start_x=10.0, start_y=20.0, angle_1=45.0, inclination_1=90.0, angle_2=45.0, inclination_2=90.0))


def test_mortise_roundtrip():
    assert_lossless(Mortise(start_x=10.0, start_y=20.0, length=60.0, width=30.0, depth=40.0))


def test_text_roundtrip():
    """A processing carrying a string payload."""
    other = assert_lossless(Text(text="BEAM-01", start_x=10.0, start_y=5.0, text_height=12.0))
    assert other.text == "BEAM-01"


def test_lap_machining_limits_roundtrip():
    """machining_limits is a dict[str, bool] and maps onto a proto map field."""
    lap = Lap(start_x=10.0, start_y=0.0, length=100.0, width=50.0, depth=20.0)
    other = assert_lossless(lap)
    assert other.machining_limits.limits == lap.machining_limits.limits


def test_slot_roundtrip():
    assert_lossless(Slot(start_x=10.0, start_y=0.0, length=100.0, depth=20.0, thickness=5.0))


def test_ref_side_index_and_priority_roundtrip():
    """The inherited BTLxProcessing fields are copied into every message."""
    cut = JackRafterCut(orientation="start", start_x=10.0, ref_side_index=3, priority=2)
    other = assert_lossless(cut)
    assert other.ref_side_index == 3
    assert other.priority == 2


def test_free_contour_with_contour_roundtrip():
    """FreeContour's contour_param_object is a oneof over Contour / DualContour."""
    polyline = Polyline([Point(0, 0, 0), Point(100, 0, 0), Point(100, 100, 0), Point(0, 0, 0)])
    other = assert_lossless(FreeContour(Contour(polyline, depth=10.0)))
    assert isinstance(other.contour_param_object, Contour)
    assert other.contour_param_object.depth == 10.0


def test_contour_roundtrip():
    polyline = Polyline([Point(0, 0, 0), Point(100, 0, 0), Point(100, 100, 0), Point(0, 0, 0)])
    other = assert_lossless(Contour(polyline, depth=5.0))
    assert other.polyline == polyline


def test_beam_with_features_roundtrip(beam):
    """A non-joinery feature travels with its beam."""
    beam.add_features(Drilling(start_x=100.0, start_y=50.0, diameter=8.0, is_joinery=False))
    other = pb_load_bts(pb_dump_bts(beam))
    assert len(other.features) == 1
    assert isinstance(other.features[0], Drilling)
    assert other.features[0].diameter == 8.0
