import pytest
from compas.geometry import Line
from compas.geometry import Point

from compas_timber.connections import TStepJoint
from compas_timber.elements import Beam
from compas_timber.model import TimberModel


@pytest.fixture
def beams():
    """Create test fixtures with beams in T-topology."""
    # Create main beam (horizontal)
    main_centerline = Line(Point(0, 0, 0), Point(1000, 0, 0))
    main_beam = Beam.from_centerline(main_centerline, width=100, height=200)

    # Create cross beam (vertical, intersecting main beam)
    cross_centerline = Line(Point(500, -300, 0), Point(500, 300, 0))
    cross_beam = Beam.from_centerline(cross_centerline, width=120, height=150)

    return main_beam, cross_beam


def test_t_step_joint_creation_with_beams(beams):
    """Test that TStepJoint can be created with valid beam arguments."""
    main_beam, cross_beam = beams
    joint = TStepJoint(main_beam=main_beam, cross_beam=cross_beam, step_shape=0, step_depth=25.0, heel_depth=0.0)

    assert joint.main_beam == main_beam
    assert joint.cross_beam == cross_beam
    assert joint.step_shape == 0
    assert joint.step_depth == 25.0
    assert joint.heel_depth == 0.0


def test_t_step_joint_creation_with_beams_and_model(beams):
    """Test that TStepJoint can be created without beam arguments (deserialization case)."""
    main_beam, cross_beam = beams
    model = TimberModel()
    model.add_elements(beams)

    # This tests the fix for the deserialization issue
    joint = TStepJoint.create(model, main_beam=main_beam, cross_beam=cross_beam, step_shape=1, step_depth=0.0, heel_depth=25.0)

    assert joint.main_beam == main_beam
    assert joint.cross_beam == cross_beam
    assert joint.step_shape == 1
    assert joint.step_depth == 0.0
    assert joint.heel_depth == 25.0


def test_t_step_joint_serialization_deserialization(beams):
    """Test that TStepJoint can be serialized and deserialized without errors."""
    main_beam, cross_beam = beams

    # Create joint with beams
    original_joint = TStepJoint(main_beam=main_beam, cross_beam=cross_beam, step_shape=2, step_depth=30.0, heel_depth=20.0, tapered_heel=True, tenon_mortise_height=40.0)

    # Serialize to data
    data = original_joint.__data__

    # Deserialize from data (this should not raise errors)
    deserialized_joint = TStepJoint.__from_data__(data)

    # Check that deserialized joint has correct properties
    assert deserialized_joint.step_shape == 2
    assert deserialized_joint.step_depth == 30.0
    assert deserialized_joint.heel_depth == 20.0
    assert deserialized_joint.tapered_heel is True
    assert deserialized_joint.tenon_mortise_height == 40.0
    assert deserialized_joint.element_guids[0] == str(main_beam.guid)
    assert deserialized_joint.element_guids[1] == str(cross_beam.guid)

    # Beams should be None after deserialization (before restoration)
    assert deserialized_joint.main_beam is None
    assert deserialized_joint.cross_beam is None


def test_t_step_joint_beam_restoration_from_keys(beams):
    """Test that beams can be restored from GUIDs after deserialization."""
    main_beam, cross_beam = beams
    model = TimberModel()
    model.add_elements(beams)

    # Create joint and serialize
    original_joint = TStepJoint(main_beam=main_beam, cross_beam=cross_beam, step_shape=0)
    data = original_joint.__data__

    # Deserialize
    deserialized_joint = TStepJoint.__from_data__(data)

    # Restore beams from model
    deserialized_joint.restore_elements_from_keys(model)

    # Check that beams are properly restored
    assert deserialized_joint.main_beam == main_beam
    assert deserialized_joint.cross_beam == cross_beam


def test_step_depths_calculation(beams):
    """Test that step depths are calculated correctly based on step_shape."""
    main_beam, cross_beam = beams

    # Test step shape 0 (step only)
    joint_step = TStepJoint(main_beam=main_beam, cross_beam=cross_beam, step_shape=0)
    joint_step.set_step_depths()
    assert joint_step.step_depth > 0
    assert joint_step.heel_depth == 0.0

    # Test step shape 1 (heel only)
    joint_heel = TStepJoint(main_beam=main_beam, cross_beam=cross_beam, step_shape=1)
    joint_heel.set_step_depths()
    assert joint_heel.step_depth == 0.0
    assert joint_heel.heel_depth > 0

    # Test step shape 2 (double)
    joint_double = TStepJoint(main_beam=main_beam, cross_beam=cross_beam, step_shape=2)
    joint_double.set_step_depths()
    assert joint_double.step_depth > 0
    assert joint_double.heel_depth > 0
