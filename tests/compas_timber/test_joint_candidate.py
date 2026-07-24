import pytest
from compas.data import json_dumps
from compas.data import json_loads
from compas.geometry import Frame
from compas.geometry import Line
from compas.geometry import Point
from compas.geometry import Polyline
from compas.tolerance import TOL

from compas_timber.connections import JointCandidate
from compas_timber.connections import JointTopology
from compas_timber.connections import LButtJoint
from compas_timber.connections import PlateJointCandidate
from compas_timber.elements import Beam
from compas_timber.elements import Plate
from compas_timber.model import TimberModel


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def two_beam_model():
    """A model with two intersecting beams in an L-topology."""
    model = TimberModel()
    b1 = Beam(Frame.worldXY(), length=1.0, width=0.1, height=0.1)
    b2 = Beam(Frame.worldYZ(), length=1.0, width=0.1, height=0.1)
    model.add_element(b1)
    model.add_element(b2)
    return model, b1, b2


@pytest.fixture
def crossing_beams_model():
    """Two beams that cross in space — suitable for connect_adjacent_beams."""
    model = TimberModel()
    line1 = Line(Point(0, 0, 0), Point(1, 0, 0))
    line2 = Line(Point(0.5, -0.5, 0), Point(0.5, 0.5, 0))
    b1 = Beam.from_centerline(line1, 0.1, 0.1)
    b2 = Beam.from_centerline(line2, 0.1, 0.1)
    model.add_element(b1)
    model.add_element(b2)
    return model, b1, b2


# =============================================================================
# connect_adjacent_beams() / connect_adjacent_plates() create candidates
# =============================================================================


def test_connect_adjacent_beams_creates_joint_candidates():
    w, h = 20, 20

    lines = [
        Line(Point(x=-10.0, y=-10.0, z=0.0), Point(x=300.0, y=200.0, z=0.0)),
        Line(Point(x=-10.0, y=-10.0, z=0.0), Point(x=-40.0, y=270.0, z=0.0)),
        Line(Point(x=-10.0, y=-10.0, z=0.0), Point(x=0.0, y=20.0, z=160.0)),
        Line(Point(x=45.89488087618746, y=234.15459672257862, z=0.0), Point(x=168.58797240614388, y=-95.31137353132192, z=0.0)),
    ]

    model = TimberModel()
    model.add_elements([Beam.from_centerline(line, w, h) for line in lines])

    model.connect_adjacent_beams()

    # Joint candidates should be stored separately from actual joints
    assert all((isinstance(j, JointCandidate) for j in model.joint_candidates))
    assert len(model.joint_candidates) == 4
    assert len(model.joints) == 0  # No actual joints should be created

    l_joints = [j for j in model.joint_candidates if j.topology == JointTopology.TOPO_L]
    x_joints = [j for j in model.joint_candidates if j.topology == JointTopology.TOPO_X]
    assert len(l_joints) == 3
    assert len(x_joints) == 1

    for j in l_joints:
        assert TOL.is_allclose(j.location, Point(x=-10.0, y=-10.0, z=0.0))
    for j in x_joints:
        assert TOL.is_allclose(j.location, Point(x=107.24142664116566, y=69.42161159562835, z=0.0))


def test_connect_adjacent_plates_creates_plate_joint_candidates():
    polyline_a = Polyline([Point(0, 0, 0), Point(0, 20, 0), Point(10, 20, 0), Point(10, 0, 0), Point(0, 0, 0)])
    plate_a = Plate.from_outline_thickness(polyline_a, 1)

    polyline_b = Polyline([Point(0, 10, 0), Point(10, 10, 0), Point(20, 20, 10), Point(0, 20, 10), Point(0, 10, 0)])
    plate_b = Plate.from_outline_thickness(polyline_b, 1)

    model = TimberModel()
    model.add_elements([plate_a, plate_b])

    model.connect_adjacent_plates()

    assert all((isinstance(j, PlateJointCandidate) for j in model.joint_candidates))

    assert len(model.joint_candidates) == 1
    edge_face_joints = [j for j in model.joint_candidates if j.topology == JointTopology.TOPO_EDGE_FACE]
    assert len(edge_face_joints) == 1
    assert isinstance(edge_face_joints[0], PlateJointCandidate)
    assert edge_face_joints[0].topology == JointTopology.TOPO_EDGE_FACE
    assert list(model.joint_candidates)[0].elements[0] == plate_b


# =============================================================================
# model.joint_candidates / model.add_joint_candidate()
# =============================================================================


def test_candidates_returns_added_candidates(crossing_beams_model):
    model, b1, b2 = crossing_beams_model
    model.connect_adjacent_beams()
    candidates = model.joint_candidates
    assert len(list(candidates)) == 1


def test_candidates_are_joint_candidate_instances(crossing_beams_model):
    model, b1, b2 = crossing_beams_model
    model.connect_adjacent_beams()
    for candidate in model.joint_candidates:
        assert isinstance(candidate, JointCandidate)


def test_candidates_empty_when_none_added():
    model = TimberModel()
    assert len(model.joint_candidates) == 0


def test_manual_candidate_is_joint_candidate(two_beam_model):
    model, b1, b2 = two_beam_model
    candidate = JointCandidate(b1, b2, topology=JointTopology.TOPO_L)
    model.add_joint_candidate(candidate)
    retrieved = list(model.joint_candidates)[0]
    assert isinstance(retrieved, JointCandidate)
    assert retrieved is candidate


def test_candidates_and_joints_are_separate(crossing_beams_model):
    """Joint candidates should not appear in model.joints."""
    model, b1, b2 = crossing_beams_model
    model.connect_adjacent_beams()
    assert len(model.joint_candidates) == 1
    assert len(model.joints) == 0


def test_adding_joint_does_not_affect_candidates(crossing_beams_model):
    """Adding a joint should not remove existing candidates."""
    model, b1, b2 = crossing_beams_model
    model.connect_adjacent_beams()
    candidates_before = len(model.joint_candidates)
    LButtJoint.create(model, b1, b2)
    assert len(model.joint_candidates) == candidates_before
    assert len(model.joints) == 1


# =============================================================================
# JointCandidate.create()
# =============================================================================


def test_joint_candidate_create_still_works():
    """JointCandidate.create() adds the candidate to model.joint_candidates, not model.joints."""
    w, h = 20, 20

    lines = [
        Line(Point(x=0.0, y=0.0, z=0.0), Point(x=1.0, y=0.0, z=0.0)),
        Line(Point(x=0.5, y=-0.5, z=0.0), Point(x=0.5, y=0.5, z=0.0)),
    ]

    model = TimberModel()
    beams = [Beam.from_centerline(line, w, h) for line in lines]
    model.add_elements(beams)

    # JointCandidate.create() should not create actual joints
    joint = JointCandidate.create(model, beams[0], beams[1], topology=JointTopology.TOPO_T, location=Point(0.5, 0, 0))

    assert isinstance(joint, JointCandidate)
    assert joint not in model.joints  # Should not be in actual joints
    assert joint in model.joint_candidates  # Should be in joint_candidates
    assert len(model.joints) == 0
    assert len(model.joint_candidates) == 1


# =============================================================================
# JointCandidate.location
# =============================================================================


def test_joint_candidate_location_explicitly_set():
    """Location returns the explicitly set value without computing from elements."""
    model = TimberModel()
    b1 = Beam.from_centerline(Line(Point(0, 0, 0), Point(1, 0, 0)), 0.1, 0.1)
    b2 = Beam.from_centerline(Line(Point(0.5, -0.5, 0), Point(0.5, 0.5, 0)), 0.1, 0.1)
    model.add_element(b1)
    model.add_element(b2)

    loc = Point(0.5, 0.0, 0.0)
    joint = JointCandidate.create(model, b1, b2, topology=JointTopology.TOPO_X, location=loc)

    assert TOL.is_allclose(joint.location, loc)


def test_joint_candidate_location_computed_from_intersecting_beams():
    """When centerlines intersect (distance ≈ 0), location is the intersection point."""
    model = TimberModel()
    b1 = Beam.from_centerline(Line(Point(0, 0, 0), Point(2, 0, 0)), 0.1, 0.1)
    b2 = Beam.from_centerline(Line(Point(1, -1, 0), Point(1, 1, 0)), 0.1, 0.1)
    model.add_element(b1)
    model.add_element(b2)

    joint = JointCandidate.create(model, b1, b2, topology=JointTopology.TOPO_X)
    assert TOL.is_allclose(joint.location, Point(1, 0, 0))


def test_joint_candidate_location_computed_from_skew_beams():
    """When centerlines don't intersect, location is the midpoint between closest points."""
    model = TimberModel()
    b1 = Beam.from_centerline(Line(Point(0, 0, 0), Point(2, 0, 0)), 0.1, 0.1)
    b2 = Beam.from_centerline(Line(Point(1, -1, 1), Point(1, 1, 1)), 0.1, 0.1)
    model.add_element(b1)
    model.add_element(b2)

    joint = JointCandidate.create(model, b1, b2, topology=JointTopology.TOPO_X)
    # closest points are (1,0,0) and (1,0,1), midpoint is (1,0,0.5)
    assert TOL.is_allclose(joint.location, Point(1, 0, 0.5))


def test_joint_candidate_location_setter_rejects_non_point():
    """Setting location to a non-Point value raises TypeError."""
    model = TimberModel()
    b1 = Beam.from_centerline(Line(Point(0, 0, 0), Point(1, 0, 0)), 0.1, 0.1)
    b2 = Beam.from_centerline(Line(Point(0.5, -0.5, 0), Point(0.5, 0.5, 0)), 0.1, 0.1)
    model.add_element(b1)
    model.add_element(b2)

    joint = JointCandidate.create(model, b1, b2, topology=JointTopology.TOPO_X)
    with pytest.raises(TypeError, match="Location must be a Point"):
        joint.location = [1, 2, 3]


def test_joint_candidate_location_raises_before_elements_available():
    """Accessing location before elements are restored (e.g. during deserialization) raises ValueError."""
    candidate = JointCandidate.__from_data__(
        {
            "element_guids": ["00000000-0000-0000-0000-000000000001", "00000000-0000-0000-0000-000000000002"],
            "name": "JointCandidate",
        }
    )
    # elements are None at this point (not yet restored from model)
    with pytest.raises(ValueError, match="Location of the joint could not be determined"):
        _ = candidate.location


def test_plate_joint_candidate_location_defaults_to_origin_when_unset():
    """`PlateJointCandidate.location` defaults to the origin (matching `PlateJoint.location`'s default), not a centerline computation."""
    polyline_a = Polyline([Point(0, 0, 0), Point(0, 20, 0), Point(10, 20, 0), Point(10, 0, 0), Point(0, 0, 0)])
    plate_a = Plate.from_outline_thickness(polyline_a, 1)
    polyline_b = Polyline([Point(0, 10, 0), Point(10, 10, 0), Point(20, 20, 10), Point(0, 20, 10), Point(0, 10, 0)])
    plate_b = Plate.from_outline_thickness(polyline_b, 1)

    candidate = PlateJointCandidate(plate_a, plate_b, topology=JointTopology.TOPO_EDGE_EDGE)

    assert TOL.is_allclose(candidate.location, Point(0, 0, 0))


# =============================================================================
# Serialization
# =============================================================================


def test_joint_candidate_location_and_topology_survive_serialization():
    """Location and topology are preserved through a JSON round-trip of the model."""
    model = TimberModel()
    b1 = Beam.from_centerline(Line(Point(0, 0, 0), Point(2, 0, 0)), 0.1, 0.1)
    b2 = Beam.from_centerline(Line(Point(1, -1, 0), Point(1, 1, 0)), 0.1, 0.1)
    model.add_element(b1)
    model.add_element(b2)

    joint = JointCandidate.create(model, b1, b2, topology=JointTopology.TOPO_X, location=Point(1, 0, 0))
    original_location = joint.location
    original_topology = joint.topology

    restored = json_loads(json_dumps(model))

    restored_joint = list(restored.joint_candidates)[0]
    assert isinstance(restored_joint, JointCandidate)
    assert TOL.is_allclose(restored_joint.location, original_location)
    assert restored_joint.topology == original_topology


def test_plate_joint_candidate_extra_kwargs_survive_serialization():
    """`a_segment_index`/`b_segment_index` (arbitrary extra kwargs) survive a JSON round-trip."""
    polyline_a = Polyline([Point(0, 0, 0), Point(0, 20, 0), Point(10, 20, 0), Point(10, 0, 0), Point(0, 0, 0)])
    plate_a = Plate.from_outline_thickness(polyline_a, 1)
    polyline_b = Polyline([Point(0, 10, 0), Point(10, 10, 0), Point(20, 20, 10), Point(0, 20, 10), Point(0, 10, 0)])
    plate_b = Plate.from_outline_thickness(polyline_b, 1)

    model = TimberModel()
    model.add_elements([plate_a, plate_b])

    candidate = PlateJointCandidate(plate_a, plate_b, topology=JointTopology.TOPO_EDGE_EDGE, a_segment_index=1, b_segment_index=0)
    model.add_joint_candidate(candidate)

    restored = json_loads(json_dumps(model))
    restored_candidate = list(restored.joint_candidates)[0]

    assert restored_candidate.a_segment_index == 1
    assert restored_candidate.b_segment_index == 0
