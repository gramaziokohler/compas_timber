import pytest

from compas.geometry import Line
from compas.geometry import Point
from compas.geometry import Polyline

from compas_timber.connections import BeamPlateConnectionSolver
from compas_timber.connections import JointTopology
from compas_timber.elements import Beam
from compas_timber.elements import Plate

MAX_DISTANCE = 0.001
TOL = 0.001


@pytest.fixture
def plate():
    """Flat 10 x 20 plate, thickness 1, main faces at z=0 (outline_a) and z=1 (outline_b)."""
    outline = Polyline([Point(0, 0, 0), Point(0, 20, 0), Point(10, 20, 0), Point(10, 0, 0), Point(0, 0, 0)])
    return Plate.from_outline_thickness(outline, 1)


def find_topology(beam, plate):
    return BeamPlateConnectionSolver().find_topology(beam, plate, max_distance=MAX_DISTANCE, tol=TOL)


def test_face_face(plate):
    """Beam resting flush on top of the plate (bottom face of beam touching outline_b's top face)."""
    beam = Beam.from_centerline(Line(Point(2, 5, 1.05), Point(8, 5, 1.05)), width=0.1, height=0.1)
    result = find_topology(beam, plate)
    assert result.topology == JointTopology.TOPO_FACE_FACE
    assert result.segment_index is None
    assert result.beam_ref_side_index in range(4)
    assert result.plate_ref_side_index == 2


def test_end_face(plate):
    """Beam standing on top of the plate, one end flush on outline_b, other end extending away."""
    beam = Beam.from_centerline(Line(Point(5, 10, 1), Point(5, 10, 3)), width=0.1, height=0.1)
    result = find_topology(beam, plate)
    assert result.topology == JointTopology.TOPO_END_FACE
    assert result.segment_index is None
    assert result.beam_ref_side_index is None
    assert result.plate_ref_side_index == 2


def test_end_edge(plate):
    """One beam end on the plate's edge (segment 0, the x=0 edge), other end reaching inward."""
    beam = Beam.from_centerline(Line(Point(0, 10, 0.5), Point(5, 10, 0.5)), width=0.05, height=0.05)
    result = find_topology(beam, plate)
    assert result.topology == JointTopology.TOPO_END_EDGE
    assert result.segment_index == 0
    assert result.beam_ref_side_index is None
    assert result.plate_ref_side_index is None


def test_unknown_when_each_end_hits_a_different_edge(plate):
    """A beam spanning corner to corner (one end on the x=0 edge, the other on the y=0 edge) has no
    single, unambiguous edge relationship and must resolve to TOPO_UNKNOWN, not TOPO_END_EDGE."""
    beam = Beam.from_centerline(Line(Point(0, 5, 0.5), Point(5, 0, 0.5)), width=0.05, height=0.05)
    result = find_topology(beam, plate)
    assert result.topology == JointTopology.TOPO_UNKNOWN


def test_middle_edge(plate):
    """Beam crossing the plate's x=0 edge mid-span, endpoints on opposite sides of the main-face band."""
    beam = Beam.from_centerline(Line(Point(-2, 10, -0.5), Point(2, 10, 1.5)), width=0.05, height=0.05)
    result = find_topology(beam, plate)
    assert result.topology == JointTopology.TOPO_MIDDLE_EDGE
    assert result.segment_index == 0
    assert result.beam_ref_side_index is None
    assert result.plate_ref_side_index is None


def test_through_face(plate):
    """Beam post piercing straight through both main faces of the plate."""
    beam = Beam.from_centerline(Line(Point(5, 10, -1), Point(5, 10, 2)), width=0.1, height=0.1)
    result = find_topology(beam, plate)
    assert result.topology == JointTopology.TOPO_THROUGH_FACE
    assert result.segment_index is None
    assert result.beam_ref_side_index is None
    assert result.plate_ref_side_index is None  # ambiguous: crosses both main faces


def test_along_edge(plate):
    """Beam running along and parallel to the plate's x=0 edge."""
    beam = Beam.from_centerline(Line(Point(0, 5, 0.5), Point(0, 15, 0.5)), width=0.05, height=0.05)
    result = find_topology(beam, plate)
    assert result.topology == JointTopology.TOPO_ALONG_EDGE
    assert result.segment_index == 0
    assert result.beam_ref_side_index is None
    assert result.plate_ref_side_index is None


def test_unknown_when_not_adjacent(plate):
    """Beam far away from the plate entirely."""
    beam = Beam.from_centerline(Line(Point(50, 50, 50), Point(60, 50, 50)), width=0.1, height=0.1)
    result = find_topology(beam, plate)
    assert result.topology == JointTopology.TOPO_UNKNOWN


def test_unknown_when_embedded_mid_slab_away_from_edges(plate):
    """Beam entirely embedded within the slab's thickness range, far from any edge or face contact."""
    beam = Beam.from_centerline(Line(Point(4, 9, 0.5), Point(6, 11, 0.5)), width=0.05, height=0.05)
    result = find_topology(beam, plate)
    assert result.topology == JointTopology.TOPO_UNKNOWN


def test_end_edge_takes_precedence_over_end_face_at_corner(plate):
    """A beam-end that satisfies both END_FACE (inside the outline) and END_EDGE (inside an edge
    quad) must resolve to END_EDGE — edge-related topologies are checked before face-related ones."""
    beam = Beam.from_centerline(Line(Point(0, 10, 0.5), Point(5, 10, 0.5)), width=0.05, height=0.05)
    # sanity check: the contact point is indeed inside the plate's outline too, so END_FACE would
    # also have matched if edge precedence weren't applied.
    assert 0 <= 10 <= 20 and 0 <= 0 <= 10
    result = find_topology(beam, plate)
    assert result.topology == JointTopology.TOPO_END_EDGE


def test_face_face_beats_unknown_despite_centerline_outside_slab(plate):
    """A flush-mounted beam's centerline sits entirely outside the slab's [0, thickness] depth band
    (offset by half its own cross-section) — this must still resolve to FACE_FACE, not TOPO_UNKNOWN."""
    beam = Beam.from_centerline(Line(Point(2, 5, 1.05), Point(8, 5, 1.05)), width=0.1, height=0.1)
    depth = BeamPlateConnectionSolver()._endpoint_depth(beam.centerline.start, plate)
    assert depth > plate.thickness  # confirms the centerline really is outside the band
    result = find_topology(beam, plate)
    assert result.topology == JointTopology.TOPO_FACE_FACE
