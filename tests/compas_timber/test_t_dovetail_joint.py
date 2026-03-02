import pytest
from compas.data import json_dumps
from compas.data import json_loads
from compas.geometry import Line
from compas.geometry import Point

from compas_timber.connections import TDovetailJoint
from compas_timber.elements import Beam
from compas_timber.fabrication import TenonShapeType
from compas_timber.model import TimberModel


@pytest.fixture
def beams():
    """Create test fixtures with beams in T-topology."""
    main_centerline = Line(Point(0, 0, 0), Point(1000, 0, 0))
    main_beam = Beam.from_centerline(main_centerline, width=80, height=100)

    cross_centerline = Line(Point(500, -300, 0), Point(500, 300, 0))
    cross_beam = Beam.from_centerline(cross_centerline, width=80, height=100)

    return main_beam, cross_beam


def test_t_dovetail_joint_defaults_resolved_at_init(beams):
    """Test that all default attributes are resolved at construction time, without requiring add_features()."""
    main_beam, cross_beam = beams
    joint = TDovetailJoint(main_beam=main_beam, cross_beam=cross_beam)  # no explicit values

    # Geometry-derived defaults must be set immediately
    assert joint.start_y is not None
    assert joint.start_depth is not None
    assert joint.rotation is not None
    assert joint.length is not None and joint.length > 0
    assert joint.width is not None and joint.width > 0
    assert joint.cone_angle == 10.0
    assert joint.dovetail_shape == TenonShapeType.RADIUS
    assert joint.tool_angle == 15.0
    assert joint.tool_diameter is not None and joint.tool_diameter > 0
    assert joint.tool_height is not None and joint.tool_height > 0

    # define_dovetail_tool() must also have been called, setting the derived private attributes
    assert joint._height is not None and joint._height > 0
    assert joint._flank_angle is not None
    assert joint._shape_radius is not None


def test_t_dovetail_joint_model_roundtrip_preserves_state(beams):
    """Test that calculated attributes are identical before and after a model serialize/deserialize round-trip.

    This proves the fix: restore_beams_from_keys() must call _set_unset_attributes() so that
    joint state is fully consistent without requiring a subsequent call to add_features().
    """
    main_beam, cross_beam = beams
    model = TimberModel()
    model.add_elements(beams)
    joint = TDovetailJoint.create(model, main_beam=main_beam, cross_beam=cross_beam)

    length_before = joint.length
    width_before = joint.width
    tool_diameter_before = joint.tool_diameter
    tool_height_before = joint.tool_height
    height_before = joint._height
    flank_angle_before = joint._flank_angle
    shape_radius_before = joint._shape_radius

    restored_model = json_loads(json_dumps(model))
    restored_joint = list(restored_model.joints)[0]

    # All attributes must be resolved immediately after deserialization — no add_features() call
    assert restored_joint.length == length_before
    assert restored_joint.width == width_before
    assert restored_joint.tool_diameter == tool_diameter_before
    assert restored_joint.tool_height == tool_height_before
    assert restored_joint._height == height_before
    assert restored_joint._flank_angle == flank_angle_before
    assert restored_joint._shape_radius == shape_radius_before


def test_t_dovetail_joint_restore_beams_resolves_attributes(beams):
    """Test that restore_beams_from_keys() calls _set_unset_attributes(), resolving defaults post-deserialization."""
    main_beam, cross_beam = beams
    model = TimberModel()
    model.add_elements(beams)

    original_joint = TDovetailJoint(main_beam=main_beam, cross_beam=cross_beam)
    height_before = original_joint._height
    flank_angle_before = original_joint._flank_angle
    shape_radius_before = original_joint._shape_radius

    data = original_joint.__data__
    deserialized_joint = TDovetailJoint.__from_data__(data)

    # Before beam restoration, beams are absent — derived attributes are unset
    assert deserialized_joint.main_beam is None
    assert deserialized_joint.cross_beam is None
    assert deserialized_joint._height is None
    assert deserialized_joint._flank_angle is None
    assert deserialized_joint._shape_radius is None

    deserialized_joint.restore_beams_from_keys(model)

    # After restoration, _set_unset_attributes() must have run and recomputed the derived attributes
    assert deserialized_joint._height == height_before
    assert deserialized_joint._flank_angle == flank_angle_before
    assert deserialized_joint._shape_radius == shape_radius_before
