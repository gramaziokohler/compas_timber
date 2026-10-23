"""End-to-end protobuf round-trip tests for structural types."""

import json

import pytest
from compas.data import json_dumps
from compas.geometry import Frame
from compas.geometry import Line
from compas.geometry import Point
from compas.geometry import Polyline
from compas_pb import pb_dump_bts
from compas_pb import pb_load_bts

from compas_timber.elements import Plate
from compas_timber.model import TimberModel
from compas_timber.structural import PlateStructuralElementSolver
from compas_timber.structural import StructuralSegment
from compas_timber.structural import StructuralSurface
from compas_timber.structural import StructuralSurfaceLine


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


@pytest.fixture
def outline():
    return Polyline([Point(0, 0, 0), Point(1000, 0, 0), Point(1000, 500, 0), Point(0, 500, 0), Point(0, 0, 0)])


def test_structural_surface_roundtrip(outline):
    surface = StructuralSurface(outline, Frame.worldXY(), 20.0, parent_plate_guid="9b0a1f43-3c4e-4c1a-9d43-6b1a1f2e3d4c", material="C24")
    other = assert_lossless(surface)
    assert other.thickness == 20.0
    assert other.role == "surface"
    assert other.parent_plate_guid == surface.parent_plate_guid
    assert other.attributes == {"material": "C24"}


def test_structural_surface_line_roundtrip(line):
    surface_line = StructuralSurfaceLine(
        line,
        line_type="connection",
        parent_surface_guid="0f1e2d3c-4b5a-4968-8776-655443322110",
        parent_plate_guid="9b0a1f43-3c4e-4c1a-9d43-6b1a1f2e3d4c",
    )
    other = assert_lossless(surface_line)
    assert other.line_type == "connection"
    assert other.parent_surface_guid == surface_line.parent_surface_guid
    assert other.parent_plate_guid == surface_line.parent_plate_guid


def test_model_with_structural_surfaces_roundtrip():
    model = TimberModel()
    plate_a = Plate.from_outline_thickness(Polyline([Point(0, 0, 0), Point(1000, 0, 0), Point(1000, 500, 0), Point(0, 500, 0), Point(0, 0, 0)]), 20.0)
    plate_b = Plate.from_outline_thickness(Polyline([Point(1000, 0, 0), Point(1000, 0, 1000), Point(1000, 500, 1000), Point(1000, 500, 0), Point(1000, 0, 0)]), 20.0)
    model.add_element(plate_a)
    model.add_element(plate_b)
    model.connect_adjacent_plates()
    solver = PlateStructuralElementSolver()
    _, joints = solver.add_structural_surfaces(model)
    solver.add_joint_structural_lines(model, joints)

    other = pb_load_bts(pb_dump_bts(model))

    for plate in other.plates:
        surfaces = other.get_plate_structural_surfaces(plate)
        assert len(surfaces) == 1
        assert surfaces[0].parent_plate is plate
    lines = [line for edge in other._graph.edges() for line in other._graph.edge_attribute(edge, "structural_surface_lines") or []]
    assert len(lines) == 2
    assert all(line.parent_plate is not None and line.parent_surface is not None for line in lines)
