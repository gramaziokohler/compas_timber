import pytest
from unittest.mock import patch

from compas.data import json_dumps
from compas.data import json_loads
from compas.geometry import Line
from compas.geometry import Point

from compas_timber.connections import LTenonMortiseJoint
from compas_timber.elements import Beam
from compas_timber.fabrication import TenonShapeType
from compas_timber.model import TimberModel


@pytest.fixture
def beams():
    """Create test fixtures with beams in L-topology."""
    main_centerline = Line(Point(0, 0, 0), Point(1000, 0, 0))
    main_beam = Beam.from_centerline(main_centerline, width=80, height=100)

    cross_centerline = Line(Point(1000, 0, 0), Point(1000, 500, 0))
    cross_beam = Beam.from_centerline(cross_centerline, width=80, height=100)

    return main_beam, cross_beam


def test_l_tenon_mortise_joint_creation_with_beams(beams):
    """Test that LTenonMortiseJoint can be created with valid beam arguments."""
    main_beam, cross_beam = beams
    joint = LTenonMortiseJoint(
        main_beam=main_beam,
        cross_beam=cross_beam,
        start_y=200.0,
        start_depth=30.0,
        rotation=15.0,
        length=150.0,
        width=50.0,
        height=40.0,
        tenon_shape=TenonShapeType.ROUNDED,
        shape_radius=10.0,
        modify_cross=True,
    )

    assert joint.main_beam == main_beam
    assert joint.cross_beam == cross_beam
    assert joint.start_y == 200.0
    assert joint.start_depth == 30.0
    assert joint.rotation == 15.0
    assert joint.length == 150.0
    assert joint.width == 50.0
    assert joint.height == 40.0
    assert joint.tenon_shape == TenonShapeType.ROUNDED
    assert joint.shape_radius == 10.0
    assert joint.modify_cross is True


def test_l_tenon_mortise_joint_defaults_resolved_at_init(beams):
    """Test that all default attributes are resolved at construction time, without requiring add_features()."""
    main_beam, cross_beam = beams
    joint = LTenonMortiseJoint(main_beam=main_beam, cross_beam=cross_beam)  # no explicit values

    # _set_unset_attributes() must have been called in __init__
    assert joint.start_y is not None
    assert joint.start_depth is not None
    assert joint.rotation is not None
    assert joint.length is not None and joint.length > 0
    assert joint.width is not None and joint.width > 0
    assert joint.height is not None and joint.height > 0
    assert joint.tenon_shape == TenonShapeType.ROUND
    assert joint.shape_radius is not None and joint.shape_radius > 0


def test_l_tenon_mortise_joint_serialization(beams):
    """Test that LTenonMortiseJoint can be serialized and the data contains expected keys and values."""
    main_beam, cross_beam = beams
    joint = LTenonMortiseJoint(
        main_beam=main_beam,
        cross_beam=cross_beam,
        start_y=10.0,
        start_depth=5.0,
        rotation=0.0,
        length=80.0,
        width=30.0,
        height=40.0,
        tenon_shape=TenonShapeType.ROUND,
        shape_radius=15.0,
        modify_cross=True,
    )
    data = joint.__data__

    assert data["start_y"] == 10.0
    assert data["start_depth"] == 5.0
    assert data["rotation"] == 0.0
    assert data["length"] == 80.0
    assert data["width"] == 30.0
    assert data["height"] == 40.0
    assert data["tenon_shape"] == TenonShapeType.ROUND
    assert data["shape_radius"] == 15.0
    assert data["modify_cross"] is True


def test_l_tenon_mortise_joint_model_roundtrip_preserves_state(beams):
    """Test that calculated attributes are identical before and after a model serialize/deserialize round-trip."""
    main_beam, cross_beam = beams
    model = TimberModel()
    model.add_elements(beams)
    joint = LTenonMortiseJoint.create(model, main_beam=main_beam, cross_beam=cross_beam, modify_cross=True)

    length_before = joint.length
    width_before = joint.width
    height_before = joint.height
    tenon_shape_before = joint.tenon_shape
    shape_radius_before = joint.shape_radius
    modify_cross_before = joint.modify_cross

    restored_model = json_loads(json_dumps(model))
    restored_joint = list(restored_model.joints)[0]

    assert restored_joint.length == length_before
    assert restored_joint.width == width_before
    assert restored_joint.height == height_before
    assert restored_joint.tenon_shape == tenon_shape_before
    assert restored_joint.shape_radius == shape_radius_before
    assert restored_joint.modify_cross == modify_cross_before


def test_l_tenon_mortise_joint_restore_beams_resolves_attributes(beams):
    """Test that restore_beams_from_keys() calls _set_unset_attributes(), but __from_data__ alone does not."""
    main_beam, cross_beam = beams
    model = TimberModel()
    model.add_elements(beams)

    original_joint = LTenonMortiseJoint(main_beam=main_beam, cross_beam=cross_beam, modify_cross=True)
    data = original_joint.__data__
    deserialized_joint = LTenonMortiseJoint.__from_data__(data)

    with patch.object(deserialized_joint, "_set_unset_attributes", wraps=deserialized_joint._set_unset_attributes) as spy:
        assert spy.call_count == 0  # not called yet — beams are absent

        deserialized_joint.restore_elements_from_keys(model)

        assert spy.call_count == 1  # called exactly once by restore_beams_from_keys()


def test_l_tenon_mortise_joint_modify_cross_false(beams):
    """Test that joint with modify_cross=False creates 2 features (tenon and mortise)."""
    main_beam, cross_beam = beams
    model = TimberModel()
    model.add_elements(beams)

    joint = LTenonMortiseJoint.create(model, main_beam=main_beam, cross_beam=cross_beam, modify_cross=False)
    model.process_joinery()

    assert len(joint.features) == 2


def test_l_tenon_mortise_joint_modify_cross_true(beams):
    """Test that joint with modify_cross=True creates 3 features (tenon, mortise, and cross cut)."""
    main_beam, cross_beam = beams
    model = TimberModel()
    model.add_elements(beams)

    joint = LTenonMortiseJoint.create(model, main_beam=main_beam, cross_beam=cross_beam, modify_cross=True)
    model.process_joinery()

    assert len(joint.features) == 3
