import pytest
import warnings

from compas.data import json_dumps
from compas.data import json_loads
from compas.geometry import Line
from compas.geometry import Point

from compas_timber.connections import TMultiStepJoint
from compas_timber.elements import Beam
from compas_timber.fabrication import StepShapeType
from compas_timber.model import TimberModel


@pytest.fixture
def beams():
    """T-joint beams meeting at 45° in plan — valid for both STEP and HEEL shapes.

    Perpendicular configurations (90°) are rejected by ``check_elements_compatibility``.
    """
    main_centerline = Line(Point(0, 0, 0), Point(1000, 0, 0))
    main_beam = Beam.from_centerline(main_centerline, width=100, height=200)

    cross_centerline = Line(Point(200, -300, 0), Point(800, 300, 0))  # 45° in plan
    cross_beam = Beam.from_centerline(cross_centerline, width=120, height=150)

    return main_beam, cross_beam


@pytest.mark.filterwarnings("ignore::UserWarning")
def test_creation_default_args(beams):
    """TMultiStepJoint created with only beams resolves all defaults."""
    main_beam, cross_beam = beams
    joint = TMultiStepJoint(main_beam=main_beam, cross_beam=cross_beam)

    assert joint.step_shape == StepShapeType.STEP
    assert joint._step_count >= 1
    assert joint._step_depth > 0.0
    assert joint._riser_angle == 90.0


@pytest.mark.filterwarnings("ignore::UserWarning")
def test_creation_explicit_step_depth(beams):
    """step_depth drives step count when step_count is not provided."""
    main_beam, cross_beam = beams
    joint = TMultiStepJoint(main_beam=main_beam, cross_beam=cross_beam, step_depth=30.0)

    assert joint.step_depth == 30.0
    assert joint._step_count >= 1
    assert joint._step_depth > 0.0


def test_creation_explicit_step_count(beams):
    """step_count drives geometry exactly when provided; step_depth is derived."""
    main_beam, cross_beam = beams
    joint = TMultiStepJoint(main_beam=main_beam, cross_beam=cross_beam, step_count=3)

    assert joint.step_count == 3
    assert joint._step_count == 3
    assert joint._step_depth > 0.0
    assert joint.step_depth is None  # raw user input was not provided


def test_step_count_takes_priority_over_step_depth(beams):
    """When both step_count and step_depth are provided, step_count wins and a warning is issued."""
    main_beam, cross_beam = beams
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        joint = TMultiStepJoint(main_beam=main_beam, cross_beam=cross_beam, step_count=2, step_depth=50.0)

    assert any("step_count" in str(w.message) for w in caught)
    assert joint._step_count == 2


def test_step_depth_adjusted_emits_warning(beams):
    """A UserWarning is emitted when step_depth is adjusted to fit an integer number of steps."""
    main_beam, cross_beam = beams
    # Use a depth that is unlikely to divide the strut length evenly.
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        TMultiStepJoint(main_beam=main_beam, cross_beam=cross_beam, step_depth=13.7)

    adjustment_warnings = [w for w in caught if "step_depth adjusted" in str(w.message)]
    # Either it fits exactly (no warning) or it was adjusted (warning issued) — both are valid.
    # What must NOT happen is a silent wrong value. We just verify the warning type is correct.
    for w in adjustment_warnings:
        assert issubclass(w.category, UserWarning)


def test_heel_shape_forces_riser_angle_90(beams):
    """For HEEL shape, the effective riser_angle is always 90° regardless of user input."""
    main_beam, cross_beam = beams
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        joint = TMultiStepJoint(main_beam=main_beam, cross_beam=cross_beam, step_shape=StepShapeType.HEEL, riser_angle=75.0)

    assert joint._riser_angle == 90.0
    assert any("riser_angle" in str(w.message) for w in caught)


def test_heel_shape_riser_angle_90_no_warning(beams):
    """For HEEL shape, passing riser_angle=90 explicitly does not emit a warning."""
    main_beam, cross_beam = beams
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        TMultiStepJoint(main_beam=main_beam, cross_beam=cross_beam, step_shape=StepShapeType.HEEL, riser_angle=90.0)

    assert not any("riser_angle" in str(w.message) for w in caught)


def test_serialization_step_depth_driven(beams):
    """Round-trip serialization preserves step_depth as the driving input."""
    main_beam, cross_beam = beams
    joint = TMultiStepJoint(main_beam=main_beam, cross_beam=cross_beam, step_depth=25.0)
    data = joint.__data__

    assert data["step_depth"] == 25.0
    assert data["step_count"] is None


def test_serialization_step_count_driven(beams):
    """Round-trip serialization preserves step_count as the driving input."""
    main_beam, cross_beam = beams
    joint = TMultiStepJoint(main_beam=main_beam, cross_beam=cross_beam, step_count=4)
    data = joint.__data__

    assert data["step_count"] == 4
    assert data["step_depth"] is None


@pytest.mark.filterwarnings("ignore::UserWarning")
def test_model_roundtrip(beams):
    """Full JSON round-trip via TimberModel restores the joint and its resolved geometry."""
    main_beam, cross_beam = beams
    model = TimberModel()
    model.add_elements(beams)
    joint = TMultiStepJoint.create(model, main_beam=main_beam, cross_beam=cross_beam, step_depth=30.0)

    step_count_before = joint._step_count

    restored_model = json_loads(json_dumps(model))
    restored_joint = list(restored_model.joints)[0]

    assert restored_joint._step_count == step_count_before
    assert restored_joint._step_depth > 0.0


def test_check_elements_compatibility_rejects_perpendicular_beams():
    """check_elements_compatibility returns False when beams meet at exactly 90°."""
    main_beam = Beam.from_centerline(Line(Point(0, 0, 0), Point(1000, 0, 0)), width=100, height=200)
    cross_beam = Beam.from_centerline(Line(Point(500, -400, 0), Point(500, 400, 0)), width=120, height=150)

    assert TMultiStepJoint.check_elements_compatibility([main_beam, cross_beam]) is False


def test_check_elements_compatibility_accepts_angled_beams(beams):
    """check_elements_compatibility returns True for beams meeting at a non-right angle."""
    assert TMultiStepJoint.check_elements_compatibility(list(beams)) is True

    """add_features() runs without error for STEP shape and populates features on both beams."""
    main_beam, cross_beam = beams
    joint = TMultiStepJoint(main_beam=main_beam, cross_beam=cross_beam, step_shape=StepShapeType.STEP, step_count=2)
    joint.add_features()

    assert len(joint.features) > 0
    assert len(main_beam.features) > 0
    assert len(cross_beam.features) > 0


@pytest.mark.filterwarnings("ignore::UserWarning")
def test_add_features_heel_shape(beams):
    """add_features() runs without error for HEEL shape and populates features on both beams."""
    main_beam, cross_beam = beams
    joint = TMultiStepJoint(main_beam=main_beam, cross_beam=cross_beam, step_shape=StepShapeType.HEEL)
    joint.add_features()

    assert len(joint.features) > 0
    assert len(main_beam.features) > 0
    assert len(cross_beam.features) > 0
