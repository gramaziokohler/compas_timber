import math
import xml.etree.ElementTree as ET

import pytest
from compas.data import json_dumps
from compas.data import json_loads
from compas.geometry import Frame
from compas.geometry import Plane
from compas.geometry import Point
from compas.tolerance import TOL
from compas.tolerance import Tolerance

from compas_timber.btlx import BTLxReader
from compas_timber.elements import Beam
from compas_timber.errors import BTLxParsingError
from compas_timber.fabrication import BTLxWriter
from compas_timber.fabrication import Connector
from compas_timber.fabrication import ConnectorInfo
from compas_timber.fabrication import ConnectorParameter
from compas_timber.fabrication import Drilling
from compas_timber.fabrication import InsertionPattern
from compas_timber.fabrication import InsertionPatterns
from compas_timber.fabrication import JackRafterCut
from compas_timber.fabrication import NodeContour
from compas_timber.fabrication import NodeContourSegment
from compas_timber.fabrication import PatternContour
from compas_timber.fabrication import ProcessingGroup
from compas_timber.fabrication import Variant
from compas_timber.fabrication import VariantParameter
from compas_timber.model import TimberModel

BEAM_VOLUME = 1000.0 * 100.0 * 200.0


@pytest.fixture
def beam():
    return Beam(Frame.worldXY(), 1000.0, 100.0, 200.0)


def _through_hole(start_x=0.0, start_y=0.0, diameter=10.0):
    return Drilling(start_x=start_x, start_y=start_y, angle=0.0, inclination=90.0, depth_limited=False, depth=0.0, diameter=diameter)


def _hole_volume(beam, diameter=10.0):
    return math.pi * (diameter / 2.0) ** 2 * beam.get_dimensions_relative_to_side(0)[1]


def _volume(beam):
    geometry = beam.compute_elementgeometry(include_features=True)
    assert not beam.debug_info
    return geometry.volume


def _round_trip(tmp_path, processing, unit="MM"):
    beam = Beam(Frame.worldXY(), 1000.0, 100.0, 200.0)
    beam.add_feature(processing)
    model = TimberModel(tolerance=Tolerance(unit=unit, absolute=1e-3, relative=1e-3))
    model.add_element(beam)
    path = str(tmp_path / "out.btlx")
    BTLxWriter().write(model, path)
    reader = BTLxReader()
    read_model = reader.read(path)
    assert not reader.errors
    return path, list(read_model.elements())[0].features[0]


def _pattern_contour():
    contour = NodeContour([100.0, 20.0, 0.0], [NodeContourSegment([400.0, 20.0, 0.0], 100.0), NodeContourSegment([400.0, 70.0, 0.0])])
    return PatternContour(insertion_patterns=InsertionPatterns([InsertionPattern(_through_hole())]), contour=contour)


def test_group_applies_its_processings(beam):
    beam.add_feature(ProcessingGroup(subprocessings=[_through_hole(100.0, 50.0), _through_hole(500.0, 50.0)]))

    assert TOL.is_close(_volume(beam), BEAM_VOLUME - 2 * _hole_volume(beam))


def test_group_round_trip_with_nested_wrapper(tmp_path):
    group = ProcessingGroup(subprocessings=[_through_hole(100.0, 50.0), _through_hole(500.0, 50.0)])

    path, read = _round_trip(tmp_path, group)

    assert isinstance(read, ProcessingGroup)
    assert [processing.start_x for processing in read.subprocessings] == [100.0, 500.0]
    assert ET.parse(path).getroot().find(".//{*}ProcessingGroup/{*}Processings/{*}Drilling") is not None


def test_nested_processings_scale_exactly_once_with_meters(tmp_path):
    group = ProcessingGroup(subprocessings=[_through_hole(0.1, 0.05, 0.01)])

    _, read = _round_trip(tmp_path, group, unit="M")

    assert TOL.is_close(read.subprocessings[0].start_x, 100.0)
    assert TOL.is_close(read.subprocessings[0].diameter, 10.0)


def test_group_json_round_trip():
    group = json_loads(json_dumps(ProcessingGroup(subprocessings=[_through_hole(100.0)])))

    assert isinstance(group.subprocessings[0], Drilling)
    assert group.subprocessings[0].start_x == 100.0


def test_connector_is_produced_by_its_processings(beam):
    info = ConnectorInfo("plate", Frame.worldXY())
    beam.add_feature(Connector(connector_info=info, subprocessings=[_through_hole(100.0, 50.0)]))

    assert TOL.is_close(_volume(beam), BEAM_VOLUME - _hole_volume(beam))


def test_connector_without_processings_leaves_geometry(beam):
    beam.add_feature(Connector(connector_info=ConnectorInfo("plate", Frame.worldXY())))

    assert TOL.is_close(_volume(beam), BEAM_VOLUME)


def test_connector_round_trip_keeps_schema_order(tmp_path):
    info = ConnectorInfo("plate", Frame([10.0, 20.0, 30.0], [0, 1, 0], [0, 0, 1]), [ConnectorParameter("Depth", 15.0), ConnectorParameter("Maker", "ACME")])
    connector = Connector(connector_info=info, subprocessings=[_through_hole(100.0)])

    path, read = _round_trip(tmp_path, connector)

    assert read.connector_info.connector_type == "plate"
    assert TOL.is_allclose(read.connector_info.position.point, [10.0, 20.0, 30.0])
    assert TOL.is_allclose(read.connector_info.position.xaxis, [0.0, 1.0, 0.0])
    assert [(parameter.name, parameter.value) for parameter in read.connector_info.parameters] == [("Depth", 15.0), ("Maker", "ACME")]
    assert [child.tag.split("}")[-1] for child in ET.parse(path).getroot().find(".//{*}Connector")] == ["Processings", "ConnectorInfo"]


def test_connector_scale():
    info = ConnectorInfo("plate", Frame([1.0, 2.0, 3.0], [1, 0, 0], [0, 1, 0]), [ConnectorParameter("Depth", 0.5), ConnectorParameter("Maker", "ACME")])
    connector = Connector(connector_info=info).scaled(1000.0)

    assert TOL.is_allclose(connector.connector_info.position.point, [1000.0, 2000.0, 3000.0])
    assert connector.connector_info.parameters[0].value == 500.0
    assert connector.connector_info.parameters[1].value == "ACME"


def test_variant_params_omit_unset_elements():
    params = Variant(start_x=10.0, cut_off=True).params.as_dict()

    assert list(params) == ["CutOff", "StartX"]
    assert params["CutOff"] == "yes"
    assert params["StartX"] == "10.000"


def test_variant_rejects_out_of_range():
    with pytest.raises(ValueError):
        Variant(start_x=100001.0)
    with pytest.raises(ValueError):
        Variant(orientation="middle")


def test_variant_leaves_geometry(beam):
    beam.add_feature(Variant(start_x=100.0, cut_off=True))

    assert TOL.is_close(_volume(beam), BEAM_VOLUME)


def test_variant_round_trip_keeps_repeated_parameters(tmp_path):
    variant = Variant(orientation="start", start_x=10.0, parameters=[VariantParameter("A", 1.5), VariantParameter("B", "text"), VariantParameter("C")])

    _, read = _round_trip(tmp_path, variant)

    assert read.start_x == 10.0
    assert [(parameter.name, parameter.value) for parameter in read.parameters] == [("A", 1.5), ("B", "text"), ("C", None)]


def test_node_frames_vertices_and_spaced_nodes_are_not_duplicated():
    frames = _pattern_contour().contour.node_frames()

    # 100..400 at a spacing of 100, then the end of the second segment. The corner at 400 is shared.
    assert [(frame.point.x, frame.point.y) for frame in frames] == [(100.0, 20.0), (200.0, 20.0), (300.0, 20.0), (400.0, 20.0), (400.0, 70.0)]


def test_node_frame_x_points_to_the_previous_point_and_y_stays_in_the_contour_plane():
    frame = _pattern_contour().contour.node_frames()[1]

    assert TOL.is_allclose(frame.xaxis, [-1.0, 0.0, 0.0])
    assert TOL.is_allclose(frame.yaxis, [0.0, -1.0, 0.0])
    assert TOL.is_allclose(frame.zaxis, [0.0, 0.0, 1.0])


def test_node_frames_respect_node_at_start_and_end():
    contour = NodeContour([0.0, 0.0, 0.0], [NodeContourSegment([300.0, 0.0, 0.0], 100.0, node_at_start=False, node_at_end=False)])

    assert [frame.point.x for frame in contour.node_frames()] == [100.0, 200.0]


def test_node_frames_shorter_last_space():
    contour = NodeContour([0.0, 0.0, 0.0], [NodeContourSegment([250.0, 0.0, 0.0], 100.0)])

    assert [frame.point.x for frame in contour.node_frames()] == [0.0, 100.0, 200.0, 250.0]


def test_pattern_contour_drills_at_each_node(beam):
    beam.add_feature(_pattern_contour())

    assert TOL.is_close(_volume(beam), BEAM_VOLUME - 5 * _hole_volume(beam))


def test_pattern_contour_holes_are_at_the_nodes(beam):
    """A cut which removes the part of the beam holding the first three nodes must take their holes with it."""
    beam.add_feature(_pattern_contour())
    beam.add_feature(JackRafterCut.from_plane_and_beam(Plane([350.0, 0.0, 0.0], [-1.0, 0.0, 0.0]), beam))

    assert TOL.is_close(_volume(beam), 650.0 * 100.0 * 200.0 - 2 * _hole_volume(beam))


def test_pattern_contour_position_offsets_from_the_node(beam):
    # an offset along the node's X axis, which points to the start of the segment
    pattern = InsertionPattern(_through_hole(), Frame([30.0, 0.0, 0.0], [1, 0, 0], [0, 1, 0]))
    contour = NodeContour([100.0, 50.0, 0.0], [NodeContourSegment([200.0, 50.0, 0.0], node_at_start=False)])
    beam.add_feature(PatternContour(insertion_patterns=InsertionPatterns([pattern]), contour=contour))
    # keep only the part of the beam up to x=180: holds the hole at x=170, but not the node at x=200
    beam.add_feature(JackRafterCut.from_plane_and_beam(Plane([180.0, 0.0, 0.0], [1.0, 0.0, 0.0]), beam))

    assert TOL.is_close(_volume(beam), 180.0 * 100.0 * 200.0 - _hole_volume(beam))


def test_pattern_contour_round_trip(tmp_path):
    processing = _pattern_contour()

    path, read = _round_trip(tmp_path, processing)

    assert isinstance(read.insertion_patterns.patterns[0].processing, Drilling)
    assert [frame.point.x for frame in read.contour.node_frames()] == [100.0, 200.0, 300.0, 400.0, 400.0]
    tags = [child.tag.split("}")[-1] for child in ET.parse(path).getroot().find(".//{*}PatternContour")]
    assert tags == ["InsertionPatterns", "Contour"]


def test_pattern_contour_scale():
    scaled = _pattern_contour().scaled(0.5)

    assert [frame.point.x for frame in scaled.contour.node_frames()] == [50.0, 100.0, 150.0, 200.0, 200.0]
    assert scaled.insertion_patterns.patterns[0].processing.diameter == 5.0


def test_pattern_contour_json_round_trip():
    processing = json_loads(json_dumps(_pattern_contour()))

    assert len(processing.contour.node_frames()) == 5
    assert isinstance(processing.insertion_patterns.patterns[0].processing, Drilling)


def test_pattern_contour_arc_is_reported():
    element = ET.fromstring('<Contour><StartPoint X="0" Y="0" Z="0"/><Arc><EndPoint X="1" Y="0" Z="0"/><PointOnArc X="0" Y="1" Z="0"/></Arc></Contour>')

    with pytest.raises(BTLxParsingError):
        NodeContour.from_xml(element)


def test_point_type_kept():
    assert isinstance(_pattern_contour().contour.start_point, Point)
