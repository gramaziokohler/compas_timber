from compas.data import json_loads
from compas.data import json_dumps
from compas.geometry import Line, Point, Vector

from compas_timber.connections import YButtJoint
from compas_timber.elements import Beam
from compas_timber.model import TimberModel


def _create_y_butt_model():
    """Helper to create a Y-butt model with 3 beams and 1 joint."""
    main_line = Line(Point(0, 0, 0), Point(1000, 0, 0))
    cross_line_a = Line(Point(1000, 0, 0), Point(1500, 500, 0))
    cross_line_b = Line(Point(1000, 0, 0), Point(1500, -500, 0))

    z = Vector(0, 0, 1)
    main_beam = Beam.from_centerline(main_line, width=60.0, height=120.0, z_vector=z)
    cross_beam_a = Beam.from_centerline(cross_line_a, width=60.0, height=120.0, z_vector=z)
    cross_beam_b = Beam.from_centerline(cross_line_b, width=60.0, height=120.0, z_vector=z)

    model = TimberModel()
    model.add_element(main_beam)
    model.add_element(cross_beam_a)
    model.add_element(cross_beam_b)

    joint = YButtJoint.create(model, main_beam, cross_beam_a, cross_beam_b, mill_depth=10.0)
    return model, joint, main_beam, cross_beam_a, cross_beam_b


def test_y_butt_joint():
    model, joint, _, _, _ = _create_y_butt_model()

    assert joint is not None
    assert len(model.joints) == 1
    assert len(model.beams) == 3

    loaded_model = json_loads(json_dumps(model))
    assert isinstance(loaded_model, TimberModel)

    assert len(loaded_model.joints) == 1
    assert len(loaded_model.beams) == 3


def test_y_butt_joint_no_duplication_after_deserialization():
    """The same joint instance should not be duplicated across multiple edges after roundtrip."""
    model, joint, _, _, _ = _create_y_butt_model()

    assert len(model.joints) == 1

    serialized = json_dumps(model)
    loaded_model = json_loads(serialized)

    # After deserialization, there should still be exactly 1 joint
    assert len(loaded_model.joints) == 1

    # The single joint should be the same object from all edges
    loaded_joint = list(loaded_model.joints)[0]
    assert isinstance(loaded_joint, YButtJoint)
    assert str(loaded_joint.guid) == str(joint.guid)

    # Verify interactions resolve to the same joint instance
    for beam in loaded_model.beams:
        interactions = loaded_model.get_interactions_for_element(beam)
        for interaction_joint in interactions:
            assert interaction_joint is loaded_joint
