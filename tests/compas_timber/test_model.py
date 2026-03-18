from pytest import raises

from copy import deepcopy
from compas.data import json_dumps
from compas.data import json_loads
from compas.geometry import Frame
from compas.geometry import Point
from compas.geometry import Vector
from compas.geometry import Polyline
from compas.geometry import Translation
from compas.tolerance import Tolerance
from compas.tolerance import TOL

from compas_timber.connections import LButtJoint
from compas_timber.connections import TButtJoint
from compas_timber.connections import JointCandidate
from compas_timber.connections import JointTopology
from compas.geometry import Line
from compas_timber.elements import Beam
from compas_timber.elements import Plate
from compas_timber.model import TimberModel


def test_create():
    model = TimberModel()
    assert model


def test_add_element():
    A = TimberModel()
    B = Beam(Frame.worldXY(), width=0.1, height=0.1, length=1.0)
    A.add_element(B)

    assert B in A.beams
    assert B in A.elements()
    assert len(list(A.graph.nodes())) == 1
    assert len(list(A.graph.edges())) == 0
    assert A.beams[0] is B
    assert len(A.beams) == 1


def test_add_elements():
    model = TimberModel()
    b1 = Beam(Frame.worldXY(), length=1.0, width=0.1, height=0.1)
    b2 = Beam(Frame.worldYZ(), length=1.0, width=0.1, height=0.1)

    model.add_elements([b1, b2])

    assert len(model.beams) == 2
    assert model.beams[0] is b1
    assert model.beams[1] is b2
    assert len(list(model.graph.nodes())) == 2
    assert len(list(model.graph.edges())) == 0


def test_add_joint():
    model = TimberModel()
    b1 = Beam(Frame.worldXY(), length=1.0, width=0.1, height=0.1)
    b2 = Beam(Frame.worldYZ(), length=1.0, width=0.1, height=0.1)

    model.add_element(b1)
    model.add_element(b2)
    _ = LButtJoint.create(model, b1, b2)

    assert len(model.beams) == 2
    assert len(list(model.joints)) == 1


def test_get_joint_from_interaction():
    model = TimberModel()
    b1 = Beam(Frame.worldXY(), length=1.0, width=0.1, height=0.1)
    b2 = Beam(Frame.worldYZ(), length=1.0, width=0.1, height=0.1)

    model.add_element(b1)
    model.add_element(b2)
    joint = LButtJoint.create(model, b1, b2)

    assert joint is list(model.joints)[0]


def test_copy(mocker):
    mocker.patch("compas_timber.connections.LButtJoint.add_features")
    F1 = Frame(Point(0, 0, 0), Vector(1, 0, 0), Vector(0, 1, 0))
    F2 = Frame(Point(0, 0, 0), Vector(1, 0, 0), Vector(0, 1, 0))
    B1 = Beam(F1, length=1.0, width=0.1, height=0.12)
    B2 = Beam(F2, length=1.0, width=0.1, height=0.12)
    A = TimberModel()
    A.add_element(B1)
    A.add_element(B2)
    _ = LButtJoint.create(A, B1, B2)

    A_copy = A.copy()
    assert A_copy is not A
    assert A_copy.beams[0] is not A.beams[0]


def test_deepcopy(mocker):
    mocker.patch("compas_timber.connections.LButtJoint.add_features")
    F1 = Frame(Point(0, 0, 0), Vector(1, 0, 0), Vector(0, 1, 0))
    F2 = Frame(Point(0, 0, 0), Vector(1, 0, 0), Vector(0, 1, 0))
    B1 = Beam(F1, length=1.0, width=0.1, height=0.12)
    B2 = Beam(F2, length=1.0, width=0.1, height=0.12)
    A = TimberModel()
    A.add_element(B1)
    A.add_element(B2)
    _ = LButtJoint.create(A, B1, B2)

    A_copy = A.copy()
    assert A_copy is not A
    assert A_copy.beams[0] is not A.beams[0]


def test_beams_have_keys_after_serialization():
    A = TimberModel()
    B1 = Beam(Frame.worldXY(), length=1.0, width=0.1, height=0.1)
    B2 = Beam(Frame.worldYZ(), length=1.0, width=0.1, height=0.1)
    B3 = Beam(Frame.worldZX(), length=1.0, width=0.1, height=0.1)
    A.add_element(B1)
    A.add_element(B2)
    A.add_element(B3)
    keys = [beam.guid for beam in A.beams]

    A = json_loads(json_dumps(A))

    assert keys == [beam.guid for beam in A.beams]


def test_serialization_with_l_butt_joints(mocker):
    mocker.patch("compas_timber.connections.LButtJoint.add_features")
    F1 = Frame(Point(0, 0, 0), Vector(1, 0, 0), Vector(0, 1, 0))
    F2 = Frame(Point(0, 0, 0), Vector(1, 0, 0), Vector(0, 1, 0))
    B1 = Beam(F1, length=1.0, width=0.1, height=0.12)
    B2 = Beam(F2, length=1.0, width=0.1, height=0.12)
    A = TimberModel()
    A.add_element(B1)
    A.add_element(B2)
    _ = LButtJoint.create(A, B1, B2)

    A = json_loads(json_dumps(A))


def test_serialization_with_t_butt_joints(mocker):
    mocker.patch("compas_timber.connections.LButtJoint.add_features")
    a = TimberModel()
    b1 = Beam(Frame.worldXY(), length=1.0, width=0.1, height=0.1)
    b2 = Beam(Frame.worldYZ(), length=1.0, width=0.1, height=0.1)
    a.add_element(b1)
    a.add_element(b2)
    _ = TButtJoint.create(a, b1, b2)

    a = json_loads(json_dumps(a))

    assert len(list(a.joints)) == 1
    assert type(list(a.joints)[0]) is TButtJoint


def test_generator_properties():
    model = TimberModel()

    polyline = Polyline(
        [
            Point(x=0.0, y=184.318671947, z=4252.92700512),
            Point(x=0.0, y=2816.40294074, z=4252.92700512),
            Point(x=0.0, y=2816.40294074, z=2720.97170805),
            Point(x=0.0, y=184.318671947, z=2720.97170805),
            Point(x=0.0, y=184.318671947, z=4252.92700512),
        ]
    )

    plate = Plate.from_outline_thickness(polyline, 10.0, Vector(1, 0, 0))
    model.add_element(plate)

    beam = Beam(Frame.worldXY(), 10.0, 10.0, 10.0)
    model.add_element(beam)

    assert len(model.plates) == 1
    assert len(model.beams) == 1


def test_type_properties():
    polyline = Polyline(
        [
            Point(x=0.0, y=184.318671947, z=4252.92700512),
            Point(x=0.0, y=2816.40294074, z=4252.92700512),
            Point(x=0.0, y=2816.40294074, z=2720.97170805),
            Point(x=0.0, y=184.318671947, z=2720.97170805),
            Point(x=0.0, y=184.318671947, z=4252.92700512),
        ]
    )

    plate = Plate.from_outline_thickness(polyline, 10.0, Vector(1, 0, 0))
    beam = Beam(Frame.worldXY(), 10.0, 10.0, 10.0)

    assert plate.is_plate
    assert beam.is_beam

    assert not plate.is_beam
    assert not beam.is_plate


def test_model_tolerance_default():
    model = TimberModel()

    assert model.tolerance == TOL


def test_model_tolerance_provided():
    meters = Tolerance(unit="M", absolute=1e-6, relative=1e-3)

    model = TimberModel(tolerance=meters)

    assert model.tolerance == meters


def test_copy_model_with_processing_jackraftercut_proxy():
    from compas_timber.fabrication import JackRafterCutProxy
    from compas_timber.fabrication import JackRafterCut

    # Create a TimberModel instance
    model = TimberModel()

    # Add a beam to the model
    height, width, length = 200.11, 100.05, 2001.12
    frame = Frame(point=Point(x=390.000, y=780.000, z=0.000), xaxis=Vector(x=0.989, y=0.145, z=0.000), yaxis=Vector(x=-0.145, y=0.989, z=-0.000))
    beam = Beam(frame, length=length, width=width, height=height)
    model.add_element(beam)

    cutting_plane = Frame(point=Point(x=627.517, y=490.000, z=-187.681), xaxis=Vector(x=0.643, y=0.000, z=0.766), yaxis=Vector(x=0.000, y=1.000, z=-0.000))

    # Create a processing proxy for the model
    beam.add_feature(JackRafterCutProxy.from_plane_and_beam(cutting_plane, beam))

    copied_model = model.copy()

    copied_beams = copied_model.beams
    assert len(copied_beams) == 1
    assert len(copied_beams[0].features) == 1
    assert isinstance(copied_beams[0].features[0], JackRafterCut)


def test_error_deepcopy_feature():
    from copy import deepcopy
    from compas_timber.errors import FeatureApplicationError

    error = FeatureApplicationError("mama", "papa", "dog")

    error = deepcopy(error)

    assert error.feature_geometry == "mama"
    assert error.element_geometry == "papa"
    assert error.message == "dog"


def test_error_deepcopy_fastener():
    from copy import deepcopy
    from compas_timber.errors import FastenerApplicationError

    error = FastenerApplicationError("mama", "papa", "dog")

    error = deepcopy(error)

    assert error.elements == "mama"
    assert error.fastener == "papa"
    assert error.message == "dog"


def test_error_deepcopy_joint():
    from compas_timber.errors import BeamJoiningError

    error = BeamJoiningError("mama", "papa", "dog", "cucumber")

    error = deepcopy(error)

    assert error.beams == "mama"
    assert error.joint == "papa"
    assert error.debug_info == "dog"
    assert error.debug_geometries == "cucumber"


def test_beam_graph_node_available_after_serialization():
    model = TimberModel()
    frame = Frame(Point(0, 0, 0), Vector(1, 0, 0), Vector(0, 1, 0))
    beam = Beam(frame, length=1.0, width=0.1, height=0.1)
    model.add_element(beam)

    graph_node = beam.graphnode
    deserialized_model = json_loads(json_dumps(model))

    assert graph_node is not None
    assert deserialized_model.beams[0].graphnode == graph_node


def test_beam_graph_node_available_after_deepcopying():
    model = TimberModel()
    frame = Frame(Point(0, 0, 0), Vector(1, 0, 0), Vector(0, 1, 0))
    beam = Beam(frame, length=1.0, width=0.1, height=0.1)
    model.add_element(beam)

    grap_node = beam.graphnode
    deserialized_model = deepcopy(model)

    assert grap_node is not None
    assert deserialized_model.beams[0].graphnode == grap_node


def test_joint_candidates_simple():
    """Test joint candidates with a simple two-beam setup."""
    # Create a simple model with two intersecting beams
    model = TimberModel()

    # Create two beams that intersect
    line1 = Line(Point(0, 0, 0), Point(1, 0, 0))
    line2 = Line(Point(0.5, -0.5, 0), Point(0.5, 0.5, 0))

    beam1 = Beam.from_centerline(line1, 0.1, 0.1)
    beam2 = Beam.from_centerline(line2, 0.1, 0.1)

    model.add_element(beam1)
    model.add_element(beam2)

    # Connect adjacent beams to create candidates
    model.connect_adjacent_beams()

    # Verify that candidates were created
    candidates = list(model.joint_candidates)
    assert len(candidates) == 1

    candidate = candidates[0]
    assert isinstance(candidate, JointCandidate)
    assert candidate.topology == JointTopology.TOPO_X  # Should be X topology
    assert isinstance(candidate.location, Point)

    # Verify that no actual joints were created
    assert len(model.joints) == 0

    # Test removing the candidate
    model.remove_joint_candidate(candidate)
    assert len(model.joint_candidates) == 0


def test_joint_candidates_and_joints_separate():
    """Test that joint candidates and normal joints stay separate."""
    # Create a model with three beams
    model = TimberModel()

    # Create three beams: two that will have a candidate, one that will have a joint
    line1 = Line(Point(0, 0, 0), Point(1, 0, 0))
    line2 = Line(Point(0.5, -0.5, 0), Point(0.5, 0.5, 0))
    line3 = Line(Point(2, 0, 0), Point(2, 1, 0))

    beam1 = Beam.from_centerline(line1, 0.1, 0.1)
    beam2 = Beam.from_centerline(line2, 0.1, 0.1)
    beam3 = Beam.from_centerline(line3, 0.1, 0.1)

    model.add_element(beam1)
    model.add_element(beam2)
    model.add_element(beam3)

    # Create candidates between beam1 and beam2
    model.connect_adjacent_beams()

    # Create a joint between beam1 and beam3 (after connect_adjacent_beams)
    joint = LButtJoint.create(model, beam1, beam3)

    # Verify separation
    assert len(model.joints) == 1
    assert len(model.joint_candidates) == 1

    # Verify the joint is the one we created
    assert list(model.joints)[0] is joint

    # Verify the candidate is between beam1 and beam2
    candidate = list(model.joint_candidates)[0]
    assert beam1 in candidate.elements
    assert beam2 in candidate.elements

    # Verify the joint is between beam1 and beam3
    assert beam1 in joint.elements
    assert beam3 in joint.elements


def test_remove_joint_candidates():
    """Test removal of joint candidates."""
    # Create a model with multiple beams
    model = TimberModel()

    # Create four beams in a square pattern
    lines = [
        Line(Point(0, 0, 0), Point(1, 0, 0)),  # bottom
        Line(Point(1, 0, 0), Point(1, 1, 0)),  # right
        Line(Point(1, 1, 0), Point(0, 1, 0)),  # top
        Line(Point(0, 1, 0), Point(0, 0, 0)),  # left
    ]

    beams = [Beam.from_centerline(line, 0.1, 0.1) for line in lines]
    for beam in beams:
        model.add_element(beam)

    # Create candidates
    model.connect_adjacent_beams()

    # Should have 4 candidates (one for each edge of the square)
    initial_candidates = list(model.joint_candidates)
    assert len(initial_candidates) == 4

    # Remove one candidate
    candidate_to_remove = initial_candidates[0]
    model.remove_joint_candidate(candidate_to_remove)

    # Should have 3 candidates left
    remaining_candidates = list(model.joint_candidates)
    assert len(remaining_candidates) == 3
    assert candidate_to_remove not in remaining_candidates

    # Remove all remaining candidates
    for candidate in remaining_candidates:
        model.remove_joint_candidate(candidate)

    # Should have no candidates left
    assert len(model.joint_candidates) == 0


def test_remove_joint_candidate_preserves_edge():
    """Test that removing a joint candidate preserves the edge and other attributes."""
    # Create a model with two beams
    model = TimberModel()

    line1 = Line(Point(0, 0, 0), Point(1, 0, 0))
    line2 = Line(Point(0.5, -0.5, 0), Point(0.5, 0.5, 0))

    beam1 = Beam.from_centerline(line1, 0.1, 0.1)
    beam2 = Beam.from_centerline(line2, 0.1, 0.1)

    model.add_element(beam1)
    model.add_element(beam2)

    # Create a candidate
    model.connect_adjacent_beams()

    # Verify candidate was created
    candidates = list(model.joint_candidates)
    assert len(candidates) == 1

    # Remove the candidate
    candidate = candidates[0]
    model.remove_joint_candidate(candidate)

    # Verify candidate is gone
    assert len(model.joint_candidates) == 0

    # Test that we can add a new candidate to the same edge
    # This verifies the edge still exists and can accept new candidates
    new_candidate = JointCandidate(beam1, beam2, topology=JointTopology.TOPO_X, location=Point(0.5, 0, 0))
    model.add_joint_candidate(new_candidate)

    # Verify the new candidate was added successfully
    assert len(model.joint_candidates) == 1
    assert list(model.joint_candidates)[0] is new_candidate


def test_model_transform_and_cache_invalidation():
    """Test that TimberModel.transform() properly transforms elements and invalidates caches."""
    beam = Beam(Frame(Point(1, 2, 3), Vector(1, 0, 0), Vector(0, 1, 0)), length=1.0, width=0.1, height=0.1)
    original_transformation = beam.modeltransformation  # computed property

    model = TimberModel()
    model.add_element(beam)

    # Create a translation transformation
    translation = Translation.from_vector(Vector(5, 10, 15))
    # Apply transformation to the model
    model.transform(translation)

    assert original_transformation != beam.modeltransformation
    assert beam.modeltransformation == translation * original_transformation


def test_get_element_returns_none_for_invalid_guid():
    model = TimberModel()
    beam = Beam(Frame.worldXY(), width=0.1, height=0.1, length=1.0)
    model.add_element(beam)
    result = model.get_element("invalid-guid")
    assert result is None


def test_get_element_returns_correct_element():
    model = TimberModel()
    beam = Beam(Frame.worldXY(), width=0.1, height=0.1, length=1.0)
    model.add_element(beam)
    result = model.get_element(str(beam.guid))
    assert result is beam


def test_getitem_raises_keyerror_for_invalid_guid():
    model = TimberModel()
    beam = Beam(Frame.worldXY(), width=0.1, height=0.1, length=1.0)
    model.add_element(beam)

    with raises(KeyError):
        _ = model["invalid-guid"]


def test_getitem_returns_correct_element():
    model = TimberModel()
    beam = Beam(Frame.worldXY(), width=0.1, height=0.1, length=1.0)
    model.add_element(beam)
    result = model[str(beam.guid)]
    assert result is beam


def test_element_by_guid_deprecated_warning(mocker):
    model = TimberModel()
    beam = Beam(Frame.worldXY(), width=0.1, height=0.1, length=1.0)
    model.add_element(beam)

    warn_spy = mocker.spy(model, "element_by_guid")

    _ = model.element_by_guid(str(beam.guid))

    warn_spy.assert_called_once()
