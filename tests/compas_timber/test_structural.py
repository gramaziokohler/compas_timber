import pytest
import pytest_mock

from compas.geometry import Frame
from compas.geometry import Line
from compas.geometry import Point
from compas.geometry import Vector
from compas_timber.elements import Beam
from compas_timber.structural import BeamStructuralElementSolver
from compas_timber.structural import InteractionType
from compas_timber.structural import StructuralGraph
from compas_timber.structural import StructuralSegment
from compas_timber.connections import Joint
from compas_timber.connections import JointCandidate
from compas_timber.model import TimberModel


def test_create_segments_from_beam_and_its_joints(mocker: pytest_mock.MockerFixture):
    beam = Beam(Frame.worldXY(), length=6000, width=200, height=400)

    j1_location = beam.centerline.point_at(0)
    j2_location = beam.centerline.point_at(0.5)
    j3_location = beam.centerline.point_at(0.75)
    j4_location = beam.centerline.point_at(1)

    joints = [
        mocker.MagicMock(spec=Joint, location=j1_location),
        mocker.MagicMock(spec=Joint, location=j2_location),
        mocker.MagicMock(spec=Joint, location=j3_location),
        mocker.MagicMock(spec=Joint, location=j4_location),
    ]

    model: TimberModel = mocker.MagicMock(spec=TimberModel)
    model.get_joints_for_element.return_value = joints
    model.get_candidates_for_element.return_value = []
    model.beams = [beam]

    solver = BeamStructuralElementSolver()
    segments, _ = solver.add_structural_segments(model)

    model.add_beam_structural_segments.assert_called_once()

    assert len(segments) == 3
    expected_lengths = [3000.0, 1500.0, 1500.0]

    for segment, expected_length in zip(segments, expected_lengths):
        actual_length = segment.line.length
        assert actual_length == pytest.approx(expected_length)


def test_create_segments_no_joints(mocker: pytest_mock.MockerFixture):
    beam = Beam(Frame.worldXY(), length=6000, width=200, height=400)
    model = mocker.MagicMock()
    model.get_joints_for_element.return_value = []
    model.get_candidates_for_element.return_value = []
    model.beams = [beam]

    solver = BeamStructuralElementSolver()
    segments, _ = solver.add_structural_segments(model)

    model.add_beam_structural_segments.assert_called_once()

    assert len(segments) == 1
    assert segments[0].line.length == pytest.approx(6000.0)


def test_create_segments_joints_at_ends_only(mocker: pytest_mock.MockerFixture):
    beam = Beam(Frame.worldXY(), length=6000, width=200, height=400)

    j_start_loc = beam.centerline.start
    j_end_loc = beam.centerline.end

    joints = [
        mocker.MagicMock(spec=Joint, location=j_start_loc),
        mocker.MagicMock(spec=Joint, location=j_end_loc),
    ]
    model = mocker.MagicMock()
    model.get_joints_for_element.return_value = joints
    model.get_candidates_for_element.return_value = []
    model.beams = [beam]

    solver = BeamStructuralElementSolver()
    segments, _ = solver.add_structural_segments(model)

    model.add_beam_structural_segments.assert_called_once()

    assert len(segments) == 1
    assert segments[0].line.length == pytest.approx(6000.0)


def test_create_segments_unsorted_joints(mocker: pytest_mock.MockerFixture):
    beam = Beam(Frame.worldXY(), length=1000, width=100, height=100)
    # joints at 0.8, 0.2, 0.5
    j1 = mocker.MagicMock(spec=Joint, location=beam.centerline.point_at(0.8))
    j2 = mocker.MagicMock(spec=Joint, location=beam.centerline.point_at(0.2))
    j3 = mocker.MagicMock(spec=Joint, location=beam.centerline.point_at(0.5))

    model = mocker.MagicMock()
    model.get_joints_for_element.return_value = [j1, j2, j3]
    model.get_candidates_for_element.return_value = []
    model.beams = [beam]

    solver = BeamStructuralElementSolver()
    segments, _ = solver.add_structural_segments(model)

    model.add_beam_structural_segments.assert_called_once()

    assert len(segments) == 4
    # Expected: 0.0 -> 0.2 (200), 0.2 -> 0.5 (300), 0.5 -> 0.8 (300), 0.8 -> 1.0 (200)
    expected_lengths = [200.0, 300.0, 300.0, 200.0]
    for seg, exp in zip(segments, expected_lengths):
        assert seg.line.length == pytest.approx(exp)


def test_create_segments_project_joints(mocker: pytest_mock.MockerFixture):
    beam = Beam(Frame.worldXY(), length=1000, width=100, height=100)
    # joint near centerline, e.g. at z=50 (on surface)
    # centerline is on X axis (by default Beam frame)

    loc_on_center = beam.centerline.point_at(0.5)
    loc_off_center = loc_on_center + [0, 50, 0]  # Shifted

    joint = mocker.MagicMock(spec=Joint, location=loc_off_center)
    model = mocker.MagicMock()
    model.get_joints_for_element.return_value = [joint]
    model.get_candidates_for_element.return_value = []
    model.beams = [beam]

    solver = BeamStructuralElementSolver()
    segments, _ = solver.add_structural_segments(model)

    model.add_beam_structural_segments.assert_called_once()

    assert len(segments) == 2
    assert segments[0].line.length == pytest.approx(500.0)
    assert segments[1].line.length == pytest.approx(500.0)


def test_get_beam_structural_segments(mocker: pytest_mock.MockerFixture):
    model = TimberModel()
    beam1 = Beam(Frame.worldXY(), length=1000, width=100, height=100)
    beam2 = Beam(Frame.worldXY().translated([0, 100, 0]), length=2000, width=100, height=100)
    model.add_element(beam1)
    model.add_element(beam2)

    # Mock interactions to return empty list so we get 1 segment per beam
    mocker.patch.object(model, "get_joints_for_element", return_value=[])
    mocker.patch.object(model, "get_candidates_for_element", return_value=[])

    solver = BeamStructuralElementSolver()
    solver.add_structural_segments(model)

    segments1 = model.get_beam_structural_segments(beam1)
    segments2 = model.get_beam_structural_segments(beam2)

    assert len(segments1) == 1
    assert segments1[0].line.length == pytest.approx(1000)

    assert len(segments2) == 1
    assert segments2[0].line.length == pytest.approx(2000)

    # Verify no cross contamination
    assert segments1[0] not in segments2
    assert segments2[0] not in segments1


def test_create_structural_segments_on_model(mocker: pytest_mock.MockerFixture):
    model = TimberModel()
    beam = Beam(Frame.worldXY(), length=1000, width=100, height=100)
    model.add_element(beam)

    # Mock interactions
    joint = mocker.MagicMock(spec=Joint, location=beam.centerline.point_at(0.5))
    mocker.patch.object(model, "get_joints_for_element", return_value=[joint])
    mocker.patch.object(model, "get_candidates_for_element", return_value=[])
    mocker.patch.object(TimberModel, "joints", new_callable=mocker.PropertyMock).return_value = {joint}

    model.create_beam_structural_segments()

    segments = model.get_beam_structural_segments(beam)
    assert len(segments) == 2


def test_create_structural_segments_raises_no_beams(mocker: pytest_mock.MockerFixture):
    model = TimberModel()
    joint = mocker.MagicMock(spec=Joint)
    mocker.patch.object(TimberModel, "joints", new_callable=mocker.PropertyMock).return_value = {joint}

    with pytest.raises(ValueError, match="No beams in the model"):
        model.create_beam_structural_segments()


def test_remove_beam_structural_segments(mocker: pytest_mock.MockerFixture):
    model = TimberModel()
    beam = Beam(Frame.worldXY(), length=1000, width=100, height=100)
    model.add_element(beam)

    # Mock interactions to return empty list so we get 1 segment per beam
    mocker.patch.object(model, "get_joints_for_element", return_value=[])
    mocker.patch.object(model, "get_candidates_for_element", return_value=[])

    solver = BeamStructuralElementSolver()
    solver.add_structural_segments(model)

    assert len(model.get_beam_structural_segments(beam)) == 1

    model.remove_beam_structural_segments(beam)

    assert len(model.get_beam_structural_segments(beam)) == 0


def test_segment_frame_origin_at_segment_start(mocker: pytest_mock.MockerFixture):
    beam = Beam(Frame.worldXY(), length=1000, width=100, height=100)

    j1 = mocker.MagicMock(spec=Joint, location=beam.centerline.point_at(0.5))

    model = mocker.MagicMock()
    model.get_joints_for_element.return_value = [j1]
    model.get_candidates_for_element.return_value = []
    model.beams = [beam]

    solver = BeamStructuralElementSolver()
    segments, _ = solver.add_structural_segments(model)

    assert len(segments) == 2

    # first segment: origin should be at beam.centerline.start
    assert segments[0].frame.point.x == pytest.approx(beam.centerline.start.x)
    assert segments[0].frame.point.y == pytest.approx(beam.centerline.start.y)
    assert segments[0].frame.point.z == pytest.approx(beam.centerline.start.z)

    # second segment: origin should be at joint location projected on centerline (midpoint)
    midpoint = beam.centerline.point_at(0.5)
    assert segments[1].frame.point.x == pytest.approx(midpoint.x)
    assert segments[1].frame.point.y == pytest.approx(midpoint.y)
    assert segments[1].frame.point.z == pytest.approx(midpoint.z)


def test_segment_frame_orientation_matches_beam(mocker: pytest_mock.MockerFixture):
    beam_frame = Frame(Point(10, 20, 30), Vector(0, 1, 0), Vector(0, 0, 1))
    beam = Beam(beam_frame, length=1000, width=100, height=100)

    j1 = mocker.MagicMock(spec=Joint, location=beam.centerline.point_at(0.25))
    j2 = mocker.MagicMock(spec=Joint, location=beam.centerline.point_at(0.75))

    model = mocker.MagicMock()
    model.get_joints_for_element.return_value = [j1, j2]
    model.get_candidates_for_element.return_value = []
    model.beams = [beam]

    solver = BeamStructuralElementSolver()
    segments, _ = solver.add_structural_segments(model)

    assert len(segments) == 3

    for seg in segments:
        # orientation (xaxis and yaxis) should match the beam's frame
        assert seg.frame.xaxis.x == pytest.approx(beam.frame.xaxis.x)
        assert seg.frame.xaxis.y == pytest.approx(beam.frame.xaxis.y)
        assert seg.frame.xaxis.z == pytest.approx(beam.frame.xaxis.z)

        assert seg.frame.yaxis.x == pytest.approx(beam.frame.yaxis.x)
        assert seg.frame.yaxis.y == pytest.approx(beam.frame.yaxis.y)
        assert seg.frame.yaxis.z == pytest.approx(beam.frame.yaxis.z)

        # origin should match the segment's start point
        assert seg.frame.point.x == pytest.approx(seg.line.start.x)
        assert seg.frame.point.y == pytest.approx(seg.line.start.y)
        assert seg.frame.point.z == pytest.approx(seg.line.start.z)


def test_segment_frame_no_joints(mocker: pytest_mock.MockerFixture):
    beam = Beam(Frame.worldXY(), length=5000, width=200, height=400)

    model = mocker.MagicMock()
    model.get_joints_for_element.return_value = []
    model.get_candidates_for_element.return_value = []
    model.beams = [beam]

    solver = BeamStructuralElementSolver()
    segments, _ = solver.add_structural_segments(model)

    assert len(segments) == 1

    # single segment frame should have beam's frame origin and orientation
    seg = segments[0]
    assert seg.frame.point.x == pytest.approx(beam.frame.point.x)
    assert seg.frame.point.y == pytest.approx(beam.frame.point.y)
    assert seg.frame.point.z == pytest.approx(beam.frame.point.z)
    assert seg.frame.xaxis.x == pytest.approx(beam.frame.xaxis.x)
    assert seg.frame.xaxis.y == pytest.approx(beam.frame.xaxis.y)
    assert seg.frame.xaxis.z == pytest.approx(beam.frame.xaxis.z)


def test_create_segments_with_only_joint_candidates(mocker: pytest_mock.MockerFixture):
    beam = Beam(Frame.worldXY(), length=1000, width=100, height=100)

    c1 = mocker.MagicMock(spec=JointCandidate, location=beam.centerline.point_at(0.25))
    c2 = mocker.MagicMock(spec=JointCandidate, location=beam.centerline.point_at(0.75))

    model = mocker.MagicMock(spec=TimberModel)
    model.get_joints_for_element.return_value = []
    model.get_candidates_for_element.return_value = [c1, c2]
    model.beams = [beam]

    solver = BeamStructuralElementSolver()
    segments, _ = solver.add_structural_segments(model)

    model.add_beam_structural_segments.assert_called_once()

    assert len(segments) == 3
    expected_lengths = [250.0, 500.0, 250.0]
    for seg, exp in zip(segments, expected_lengths):
        assert seg.line.length == pytest.approx(exp)


def test_create_segments_with_only_joints(mocker: pytest_mock.MockerFixture):
    beam = Beam(Frame.worldXY(), length=1000, width=100, height=100)

    j1 = mocker.MagicMock(spec=Joint, location=beam.centerline.point_at(0.4))
    j2 = mocker.MagicMock(spec=Joint, location=beam.centerline.point_at(0.6))

    model = mocker.MagicMock(spec=TimberModel)
    model.get_joints_for_element.return_value = [j1, j2]
    model.get_candidates_for_element.return_value = []
    model.beams = [beam]

    solver = BeamStructuralElementSolver()
    segments, _ = solver.add_structural_segments(model)

    model.add_beam_structural_segments.assert_called_once()

    assert len(segments) == 3
    expected_lengths = [400.0, 200.0, 400.0]
    for seg, exp in zip(segments, expected_lengths):
        assert seg.line.length == pytest.approx(exp)


def test_create_segments_auto_prefers_joints_over_candidates(mocker: pytest_mock.MockerFixture):
    """AUTO mode uses joints when available, ignoring candidates."""
    beam = Beam(Frame.worldXY(), length=1000, width=100, height=100)

    j1 = mocker.MagicMock(spec=Joint, location=beam.centerline.point_at(0.2))
    c1 = mocker.MagicMock(spec=JointCandidate, location=beam.centerline.point_at(0.5))
    j2 = mocker.MagicMock(spec=Joint, location=beam.centerline.point_at(0.8))

    model = mocker.MagicMock(spec=TimberModel)
    model.get_joints_for_element.return_value = [j1, j2]
    model.get_candidates_for_element.return_value = [c1]
    model.beams = [beam]

    solver = BeamStructuralElementSolver()
    segments, _ = solver.add_structural_segments(model)

    model.add_beam_structural_segments.assert_called_once()

    # AUTO prefers joints → splits at 0.2 and 0.8 only → 3 segments: 200, 600, 200
    assert len(segments) == 3
    expected_lengths = [200.0, 600.0, 200.0]
    for seg, exp in zip(segments, expected_lengths):
        assert seg.line.length == pytest.approx(exp)


def test_create_segments_candidates_at_ends_only(mocker: pytest_mock.MockerFixture):
    beam = Beam(Frame.worldXY(), length=1000, width=100, height=100)

    c_start = mocker.MagicMock(spec=JointCandidate, location=beam.centerline.start)
    c_end = mocker.MagicMock(spec=JointCandidate, location=beam.centerline.end)

    model = mocker.MagicMock(spec=TimberModel)
    model.get_joints_for_element.return_value = []
    model.get_candidates_for_element.return_value = [c_start, c_end]
    model.beams = [beam]

    solver = BeamStructuralElementSolver()
    segments, _ = solver.add_structural_segments(model)

    # candidates at ends should not split the beam
    assert len(segments) == 1
    assert segments[0].line.length == pytest.approx(1000.0)


def test_get_interactions_for_element_returns_candidates():
    """Test that get_interactions_for_element returns joint candidates stored on graph edges.

    This exercises the real _safely_get_interactions path (no mocking) to ensure
    it actually returns a value.
    """
    model = TimberModel()
    beam_a = Beam(Frame.worldXY(), length=1000, width=100, height=100)
    beam_b = Beam(Frame(Point(500, 0, 0), Vector(0, 1, 0), Vector(0, 0, 1)), length=1000, width=100, height=100)
    model.add_element(beam_a)
    model.add_element(beam_b)

    candidate = JointCandidate(element_a=beam_a, element_b=beam_b, distance=0.0)
    candidate.location = Point(500, 0, 0)
    model.add_joint_candidate(candidate)

    interactions = model.get_candidates_for_element(beam_a)

    assert len(interactions) > 0
    assert candidate in interactions


def test_solver_auto_prefers_joints_over_candidates(mocker: pytest_mock.MockerFixture):
    """AUTO mode should return joints when both joints and candidates exist."""
    model = TimberModel()
    beam_a = Beam(Frame.worldXY(), length=1000, width=100, height=100)
    beam_b = Beam(Frame(Point(500, 0, 0), Vector(0, 1, 0), Vector(0, 0, 1)), length=1000, width=100, height=100)
    model.add_element(beam_a)
    model.add_element(beam_b)

    candidate = JointCandidate(element_a=beam_a, element_b=beam_b, distance=0.0)
    candidate.location = Point(500, 0, 0)
    model.add_joint_candidate(candidate)

    joint = mocker.MagicMock(spec=Joint)
    joint.interactions = [(beam_a, beam_b)]
    joint.generated_elements = []
    model.add_joint(joint)

    solver = BeamStructuralElementSolver(interaction_type=InteractionType.AUTO)
    interactions = solver._get_interactions(beam_a, model)

    assert joint in interactions
    assert candidate not in interactions


def test_solver_auto_falls_back_to_candidates():
    """AUTO mode should return candidates when no joints exist."""
    model = TimberModel()
    beam_a = Beam(Frame.worldXY(), length=1000, width=100, height=100)
    beam_b = Beam(Frame(Point(500, 0, 0), Vector(0, 1, 0), Vector(0, 0, 1)), length=1000, width=100, height=100)
    model.add_element(beam_a)
    model.add_element(beam_b)

    candidate = JointCandidate(element_a=beam_a, element_b=beam_b, distance=0.0)
    candidate.location = Point(500, 0, 0)
    model.add_joint_candidate(candidate)

    solver = BeamStructuralElementSolver(interaction_type=InteractionType.AUTO)
    interactions = solver._get_interactions(beam_a, model)

    assert candidate in interactions


def test_solver_joints_only(mocker: pytest_mock.MockerFixture):
    """JOINTS interaction_type should return only joints, ignoring candidates."""
    model = TimberModel()
    beam_a = Beam(Frame.worldXY(), length=1000, width=100, height=100)
    beam_b = Beam(Frame(Point(500, 0, 0), Vector(0, 1, 0), Vector(0, 0, 1)), length=1000, width=100, height=100)
    model.add_element(beam_a)
    model.add_element(beam_b)

    candidate = JointCandidate(element_a=beam_a, element_b=beam_b, distance=0.0)
    candidate.location = Point(500, 0, 0)
    model.add_joint_candidate(candidate)

    solver = BeamStructuralElementSolver(interaction_type=InteractionType.JOINTS)
    interactions = solver._get_interactions(beam_a, model)

    assert len(interactions) == 0


def test_solver_candidates_only(mocker: pytest_mock.MockerFixture):
    """CANDIDATES interaction_type should return only candidates, ignoring joints."""
    model = TimberModel()
    beam_a = Beam(Frame.worldXY(), length=1000, width=100, height=100)
    beam_b = Beam(Frame(Point(500, 0, 0), Vector(0, 1, 0), Vector(0, 0, 1)), length=1000, width=100, height=100)
    model.add_element(beam_a)
    model.add_element(beam_b)

    candidate = JointCandidate(element_a=beam_a, element_b=beam_b, distance=0.0)
    candidate.location = Point(500, 0, 0)
    model.add_joint_candidate(candidate)

    joint = mocker.MagicMock(spec=Joint)
    joint.interactions = [(beam_a, beam_b)]
    joint.generated_elements = []
    model.add_joint(joint)

    solver = BeamStructuralElementSolver(interaction_type=InteractionType.CANDIDATES)
    interactions = solver._get_interactions(beam_a, model)

    assert candidate in interactions
    assert joint not in interactions


# =============================================================================
# build_structural_graph tests
# =============================================================================


def test_build_structural_graph_single_beam():
    """Single beam with no joints → one beam edge, two nodes."""
    model = TimberModel()
    beam = Beam(Frame.worldXY(), length=1000, width=100, height=100)
    model.add_element(beam)

    model.create_beam_structural_segments()
    sg = StructuralGraph.from_model(model)

    assert isinstance(sg, StructuralGraph)
    assert sg.number_of_nodes() == 2
    assert sg.number_of_edges() == 1

    (u, v) = list(sg.beam_edges)[0]
    assert sg.beam(u, v) is beam
    assert sg.segment(u, v) is not None
    assert isinstance(sg.node_point(u), Point)


def test_build_structural_graph_shared_endpoint(mocker: pytest_mock.MockerFixture):
    """Beam split at midpoint → 3 nodes (start, split, end), 2 beam edges sharing the middle node."""
    model = TimberModel()
    beam = Beam(Frame.worldXY(), length=1000, width=100, height=100)
    model.add_element(beam)

    joint = mocker.MagicMock(spec=Joint, location=beam.centerline.point_at(0.5))
    mocker.patch.object(model, "get_joints_for_element", return_value=[joint])
    mocker.patch.object(model, "get_candidates_for_element", return_value=[])

    model.create_beam_structural_segments()
    sg = StructuralGraph.from_model(model)

    assert sg.number_of_nodes() == 3  # start, midpoint, end → no duplicates
    assert sg.number_of_edges() == 2
    assert len(list(sg.beam_edges)) == 2
    assert len(list(sg.connector_edges)) == 0
    # the split point is shared → checking reverse lookup
    assert len(sg.segments_for_beam(beam)) == 2


def test_build_structural_graph_two_beams_no_connection():
    """Two isolated beams produce 4 nodes and 2 beam edges with no shared nodes."""
    model = TimberModel()
    beam_a = Beam(Frame.worldXY(), length=1000, width=100, height=100)
    beam_b = Beam(Frame(Point(0, 500, 0), Vector(1, 0, 0), Vector(0, 1, 0)), length=1000, width=100, height=100)
    model.add_element(beam_a)
    model.add_element(beam_b)

    model.create_beam_structural_segments()
    sg = StructuralGraph.from_model(model)

    assert sg.number_of_nodes() == 4
    assert sg.number_of_edges() == 2
    assert len(list(sg.beam_edges)) == 2
    assert len(sg.segments_for_beam(beam_a)) == 1
    assert len(sg.segments_for_beam(beam_b)) == 1


def test_build_structural_graph_raises_when_no_segments():
    """ValueError is raised when no structural segments have been computed yet."""
    model = TimberModel()
    beam = Beam(Frame.worldXY(), length=1000, width=100, height=100)
    model.add_element(beam)
    # deliberately skip create_beam_structural_segments()

    with pytest.raises(ValueError, match="No structural segments"):
        StructuralGraph.from_model(model)


def test_build_structural_graph_with_connector_segment():
    """A connector segment stored on a model edge appears as a 'connector' type edge."""
    model = TimberModel()
    beam_a = Beam(Frame.worldXY(), length=1000, width=100, height=100)
    # beam_b placed away so neither endpoint overlaps with beam_a
    beam_b = Beam(Frame(Point(0, 500, 0), Vector(1, 0, 0), Vector(0, 1, 0)), length=1000, width=100, height=100)
    model.add_element(beam_a)
    model.add_element(beam_b)

    # Create an interaction edge between the two beams (required for connector segments)
    candidate = JointCandidate(element_a=beam_a, element_b=beam_b, distance=0.0)
    candidate.location = Point(500, 0, 0)
    model.add_joint_candidate(candidate)

    # Add one segment per beam manually (equivalent to calling the solver)
    seg_a = StructuralSegment(
        line=beam_a.centerline,
        frame=Frame(beam_a.centerline.start, beam_a.frame.xaxis, beam_a.frame.yaxis),
        cross_section=(beam_a.width, beam_a.height),
    )
    seg_b = StructuralSegment(
        line=beam_b.centerline,
        frame=Frame(beam_b.centerline.start, beam_b.frame.xaxis, beam_b.frame.yaxis),
        cross_section=(beam_b.width, beam_b.height),
    )
    model.add_beam_structural_segments(beam_a, [seg_a])
    model.add_beam_structural_segments(beam_b, [seg_b])

    # Add a connector segment bridging the closest points on each beam's centerline
    p1 = beam_a.centerline.start  # (0, 0, 0)
    p2 = beam_b.centerline.start  # (0, 500, 0)
    connector = StructuralSegment(
        line=Line(p1, p2),
        frame=Frame(p1, Vector.Xaxis(), Vector.Yaxis()),
    )
    model.add_structural_connector_segments(beam_a, beam_b, [connector])

    sg = StructuralGraph.from_model(model)

    assert len(list(sg.beam_edges)) == 2
    assert len(list(sg.connector_edges)) == 1
    # The connector endpoints p1 and p2 coincide with beam segment start points,
    # so those nodes are shared → total unique nodes = 4 (beam_a: 2, beam_b: 2, connector reuses both starts)
    assert sg.number_of_nodes() == 4

    # connector has no joint (derived from candidate, not resolved joint)
    (cu, cv) = list(sg.connector_edges)[0]
    assert sg.joint(cu, cv) is None
    assert sg.segment(cu, cv) is connector

    # reverse lookups
    assert len(sg.segments_for_beam(beam_a)) == 1
    assert len(sg.segments_for_beam(beam_b)) == 1
    # segments_for_joint(None) returns connectors that have no joint (candidate-only)
    assert len(sg.segments_for_joint(None)) == 1

    # node_index gives a stable integer index
    indices = {sg.node_index(n) for n in sg.nodes()}
    assert indices == {0, 1, 2, 3}
