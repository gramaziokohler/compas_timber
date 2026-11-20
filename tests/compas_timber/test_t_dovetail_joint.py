import pytest
from unittest.mock import patch

from compas.data import json_dumps
from compas.data import json_loads
from compas.geometry import Line
from compas.geometry import Point
from compas.geometry import Vector
from compas.tolerance import TOL
from compas_brep import Brep

from compas_timber.connections import TDovetailJoint
from compas_timber.elements import Beam
from compas_timber.fabrication import LimitationTopType
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


def test_t_dovetail_joint_creation_with_beams(beams):
    """Test that TDovetailJoint can be created with valid beam arguments."""
    main_beam, cross_beam = beams
    joint = TDovetailJoint(
        main_beam=main_beam,
        cross_beam=cross_beam,
        start_y=200.0,
        start_depth=30.0,
        rotation=15.0,
        length=150.0,
        width=50.0,
        cone_angle=10.0,
        dovetail_shape=TenonShapeType.ROUNDED,
        tool_angle=20.0,
        tool_diameter=10.0,
        tool_height=40.0,
    )

    assert joint.main_beam == main_beam
    assert joint.cross_beam == cross_beam
    assert joint.start_y == 200.0
    assert joint.start_depth == 30.0
    assert joint.rotation == 15.0
    assert joint.length == 150.0
    assert joint.width == 50.0
    assert joint.cone_angle == 10.0
    assert joint.dovetail_shape == TenonShapeType.ROUNDED
    assert joint.tool_angle == 20.0
    assert joint.tool_diameter == 10.0
    assert joint.tool_height == 40.0


def test_t_dovetail_joint_defaults_resolved_at_init(beams):
    """Test that all default attributes are resolved at construction time, without requiring add_features()."""
    main_beam, cross_beam = beams
    joint = TDovetailJoint(main_beam=main_beam, cross_beam=cross_beam)  # no explicit values

    # Geometry-derived defaults must be set immediately
    assert joint.start_y is not None
    assert joint.start_depth is not None
    assert joint.rotation is not None
    assert joint.length is not None
    assert joint.width is not None
    assert joint.cone_angle is not None
    assert joint.dovetail_shape is not None
    assert joint.tool_angle is not None
    assert joint.tool_diameter is not None
    assert joint.tool_height is not None


def test_t_dovetail_joint_model_roundtrip_preserves_state(beams):
    """Test that calculated attributes are identical before and after a model serialize/deserialize round-trip.

    This proves the fix: restore_beams_from_keys() must call _set_unset_attributes() so that
    joint state is fully consistent without requiring a subsequent call to add_features().
    """
    main_beam, cross_beam = beams
    model = TimberModel()
    model.add_elements(beams)
    joint = TDovetailJoint.create(model, main_beam=main_beam, cross_beam=cross_beam)

    start_y_before = joint.start_y
    start_depth_before = joint.start_depth
    rotation_before = joint.rotation
    length_before = joint.length
    width_before = joint.width
    cone_angle_before = joint.cone_angle
    dovetail_shape_before = joint.dovetail_shape
    tool_angle_before = joint.tool_angle
    tool_diameter_before = joint.tool_diameter
    tool_height_before = joint.tool_height

    restored_model = json_loads(json_dumps(model))
    restored_joint = list(restored_model.joints)[0]

    # All attributes must be resolved immediately after deserialization
    assert restored_joint.start_y == start_y_before
    assert restored_joint.start_depth == start_depth_before
    assert restored_joint.rotation == rotation_before
    assert restored_joint.length == length_before
    assert restored_joint.width == width_before
    assert restored_joint.cone_angle == cone_angle_before
    assert restored_joint.dovetail_shape == dovetail_shape_before
    assert restored_joint.tool_angle == tool_angle_before
    assert restored_joint.tool_diameter == tool_diameter_before
    assert restored_joint.tool_height == tool_height_before


def test_t_dovetail_joint_restore_beams_resolves_attributes(beams):
    """Test that restore_beams_from_keys() calls _set_unset_attributes(), but __from_data__ alone does not."""
    main_beam, cross_beam = beams
    model = TimberModel()
    model.add_elements(beams)

    original_joint = TDovetailJoint(main_beam=main_beam, cross_beam=cross_beam)
    data = original_joint.__data__
    deserialized_joint = TDovetailJoint.__from_data__(data)

    with patch.object(deserialized_joint, "_set_unset_attributes", wraps=deserialized_joint._set_unset_attributes) as spy:
        assert spy.call_count == 0  # not called yet — beams are absent

        deserialized_joint.restore_elements_from_keys(model)

        assert spy.call_count == 1  # called exactly once by restore_beams_from_keys()


def _dovetail_through_main_beam(dovetail_shape):
    # a dovetail longer than the main beam is high runs out of its bottom, so only its top end is length limited
    main_beam = Beam.from_centerline(Line(Point(0, 800, 0), Point(0, 0, 0)), width=80, height=160, z_vector=Vector(0, 0, 1))
    cross_beam = Beam.from_centerline(Line(Point(-600, 0, 0), Point(600, 0, 0)), width=80, height=160, z_vector=Vector(0, 0, 1))
    model = TimberModel()
    model.add_element(main_beam)
    model.add_element(cross_beam)
    TDovetailJoint.create(model, main_beam, cross_beam, length=200.0, dovetail_shape=dovetail_shape)
    model.process_joinery()
    return main_beam


@pytest.mark.requires_occ
def test_t_dovetail_joint_rounds_the_limited_end_of_a_dovetail_through_the_main_beam():
    main_beam = _dovetail_through_main_beam(TenonShapeType.ROUND)
    square_main_beam = _dovetail_through_main_beam(TenonShapeType.SQUARE)

    tenon = main_beam.features[0]
    assert tenon.length_limited_top
    assert not tenon.length_limited_bottom
    assert not main_beam.debug_info
    # the rounded edges are the two rising from the cutting plane at the top end, which lies at the cutting frame's origin
    volume = tenon.dovetail_volume_from_params_and_beam(main_beam)
    cutting_frame = tenon.frame_from_params_and_beam(main_beam)
    edge_indices = tenon._rounded_edge_indices(volume, cutting_frame)
    assert len(edge_indices) == 2
    for index in edge_indices:
        edge = volume.edges[index]
        for vertex in (edge.start_vertex, edge.end_vertex):
            assert TOL.is_zero(Vector.from_start_end(cutting_frame.point, vertex.point).dot(cutting_frame.yaxis))
    # rounding removes material from the dovetail
    assert main_beam.geometry.volume < square_main_beam.geometry.volume


@pytest.mark.requires_occ
def test_t_dovetail_mortise_rounds_its_limited_top_end_when_its_bottom_is_open():
    def mortise_and_cross_beam(dovetail_shape):
        main_beam = Beam.from_centerline(Line(Point(0, 800, 0), Point(0, 0, 0)), width=80, height=160, z_vector=Vector(0, 0, 1))
        cross_beam = Beam.from_centerline(Line(Point(-600, 0, 0), Point(600, 0, 0)), width=80, height=160, z_vector=Vector(0, 0, 1))
        model = TimberModel()
        model.add_element(main_beam)
        model.add_element(cross_beam)
        TDovetailJoint.create(model, main_beam, cross_beam, dovetail_shape=dovetail_shape)
        model.process_joinery()
        mortise = cross_beam.features[0]
        mortise.limitation_top = LimitationTopType.LIMITED
        mortise.length_limited_bottom = False
        return mortise, cross_beam

    mortise, cross_beam = mortise_and_cross_beam(TenonShapeType.ROUND)
    square_mortise, _ = mortise_and_cross_beam(TenonShapeType.SQUARE)

    # the rounded edges are the two rising from the cutting plane at the top end, which lies at the cutting frame's origin
    volume = mortise.dovetail_volume_from_params_and_beam(cross_beam)
    cutting_frame = mortise.frame_from_params_and_beam(cross_beam)
    edge_indices = mortise._rounded_edge_indices(volume, cutting_frame)
    assert len(edge_indices) == 2
    for index in edge_indices:
        edge = volume.edges[index]
        for vertex in (edge.start_vertex, edge.end_vertex):
            assert TOL.is_zero(Vector.from_start_end(cutting_frame.point, vertex.point).dot(cutting_frame.yaxis))
    # rounding the corners of the mortise removes less material
    blank = Brep.from_box(cross_beam.blank)
    assert mortise.apply(blank, cross_beam).volume > square_mortise.apply(blank, cross_beam).volume
