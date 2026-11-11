"""Tests for LFrenchRidgeLapJoint."""

import pytest

from compas.data import json_dumps
from compas.data import json_loads
from compas.geometry import Line
from compas.geometry import Point
from compas.tolerance import TOL

from compas_timber.connections import LFrenchRidgeLapJoint
from compas_timber.connections.solver import JointTopology
from compas_timber.elements import Beam
from compas_timber.errors import BeamJoiningError
from compas_timber.fabrication import FrenchRidgeLap
from compas_timber.model import TimberModel


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def beam_a():
    """Beam going along +X from (0,0,0), 60x100 cross-section."""
    return Beam.from_centerline(Line(Point(0, 0, 0), Point(2000, 0, 0)), width=60, height=100)


@pytest.fixture
def beam_b():
    """Beam going along +Y from (0,0,0), matching 60x100 cross-section — valid L partner."""
    return Beam.from_centerline(Line(Point(0, 0, 0), Point(0, 2000, 0)), width=60, height=100)


@pytest.fixture
def model(beam_a, beam_b):
    m = TimberModel()
    m.add_element(beam_a)
    m.add_element(beam_b)
    return m


@pytest.fixture
def joint(model, beam_a, beam_b):
    return LFrenchRidgeLapJoint.create(model, beam_a, beam_b, drillhole_diam=12.0)


# ---------------------------------------------------------------------------
# 1. Creation
# ---------------------------------------------------------------------------


def test_create_joint(model, beam_a, beam_b):
    joint = LFrenchRidgeLapJoint.create(model, beam_a, beam_b)
    assert joint is not None
    assert isinstance(joint, LFrenchRidgeLapJoint)
    assert len(list(model.joints)) == 1


def test_supported_topology():
    assert LFrenchRidgeLapJoint.SUPPORTED_TOPOLOGY == JointTopology.TOPO_L


def test_joint_references_correct_beams(joint, beam_a, beam_b):
    assert joint.beam_a is beam_a
    assert joint.beam_b is beam_b


# ---------------------------------------------------------------------------
# 2. Parameters
# ---------------------------------------------------------------------------


def test_drillhole_diam_stored(model, beam_a, beam_b):
    joint = LFrenchRidgeLapJoint.create(model, beam_a, beam_b, drillhole_diam=14.0)
    assert TOL.is_close(joint.drillhole_diam, 14.0)


def test_drillhole_diam_default_is_none(model, beam_a, beam_b):
    joint = LFrenchRidgeLapJoint.create(model, beam_a, beam_b)
    assert joint.drillhole_diam is None


def test_flip_lap_side_default_false(model, beam_a, beam_b):
    joint = LFrenchRidgeLapJoint.create(model, beam_a, beam_b)
    assert joint.flip_lap_side is False


def test_flip_lap_side_stored(model, beam_a, beam_b):
    joint = LFrenchRidgeLapJoint.create(model, beam_a, beam_b, flip_lap_side=True)
    assert joint.flip_lap_side is True


# ---------------------------------------------------------------------------
# 3. Serialization
# ---------------------------------------------------------------------------


def test_data_contains_drillhole_diam(joint):
    assert "drillhole_diam" in joint.__data__
    assert TOL.is_close(joint.__data__["drillhole_diam"], 12.0)


def test_data_does_not_contain_cut_plane_bias(joint):
    """LFrenchRidgeLapJoint replaces cut_plane_bias with drillhole_diam."""
    assert "cut_plane_bias" not in joint.__data__


def test_data_contains_flip_lap_side(joint):
    assert "flip_lap_side" in joint.__data__


def test_json_roundtrip(model, joint):
    restored = json_loads(json_dumps(model))
    joints = list(restored.joints)
    assert len(joints) == 1
    rj = joints[0]
    assert isinstance(rj, LFrenchRidgeLapJoint)
    assert TOL.is_close(rj.drillhole_diam, joint.drillhole_diam)
    assert rj.flip_lap_side == joint.flip_lap_side
    assert rj.beam_a is not None
    assert rj.beam_b is not None


def test_json_roundtrip_no_drillhole(model, beam_a, beam_b):
    LFrenchRidgeLapJoint.create(model, beam_a, beam_b, drillhole_diam=None)
    restored = json_loads(json_dumps(model))
    rj = list(restored.joints)[0]
    assert isinstance(rj, LFrenchRidgeLapJoint)
    assert rj.drillhole_diam is None


# ---------------------------------------------------------------------------
# 4. process_joinery — feature generation
# ---------------------------------------------------------------------------


def test_process_joinery_adds_frl_features(model, beam_a, beam_b):
    LFrenchRidgeLapJoint.create(model, beam_a, beam_b, drillhole_diam=10.0)
    model.process_joinery()
    frl_a = [f for f in beam_a.features if isinstance(f, FrenchRidgeLap)]
    frl_b = [f for f in beam_b.features if isinstance(f, FrenchRidgeLap)]
    assert len(frl_a) == 1
    assert len(frl_b) == 1


def test_drillhole_diam_propagated_to_feature(model, beam_a, beam_b):
    LFrenchRidgeLapJoint.create(model, beam_a, beam_b, drillhole_diam=18.0)
    model.process_joinery()
    frl = next(f for f in beam_a.features if isinstance(f, FrenchRidgeLap))
    assert frl.drillhole
    assert TOL.is_close(frl.drillhole_diam, 18.0)


def test_no_drillhole_when_diam_is_none(model, beam_a, beam_b):
    LFrenchRidgeLapJoint.create(model, beam_a, beam_b, drillhole_diam=None)
    model.process_joinery()
    frl_a = next(f for f in beam_a.features if isinstance(f, FrenchRidgeLap))
    frl_b = next(f for f in beam_b.features if isinstance(f, FrenchRidgeLap))
    assert not frl_a.drillhole
    assert not frl_b.drillhole


def test_process_joinery_registers_features_on_joint(model, beam_a, beam_b):
    joint = LFrenchRidgeLapJoint.create(model, beam_a, beam_b, drillhole_diam=10.0)
    model.process_joinery()
    assert len(joint.features) == 2
    assert all(isinstance(f, FrenchRidgeLap) for f in joint.features)


def test_flip_lap_side_changes_ref_side(model, beam_a, beam_b):
    joint_normal = LFrenchRidgeLapJoint.create(model, beam_a, beam_b)
    idx_a_normal = joint_normal.ref_side_index_a

    model2 = TimberModel()
    ba2 = Beam.from_centerline(Line(Point(0, 0, 0), Point(2000, 0, 0)), width=60, height=100)
    bb2 = Beam.from_centerline(Line(Point(0, 0, 0), Point(0, 2000, 0)), width=60, height=100)
    model2.add_element(ba2)
    model2.add_element(bb2)
    joint_flipped = LFrenchRidgeLapJoint.create(model2, ba2, bb2, flip_lap_side=True)
    idx_a_flipped = joint_flipped.ref_side_index_a

    assert idx_a_normal != idx_a_flipped


# ---------------------------------------------------------------------------
# 5. check_elements_compatibility
# ---------------------------------------------------------------------------


def test_compatible_beams_returns_true(beam_a, beam_b):
    assert LFrenchRidgeLapJoint.check_elements_compatibility([beam_a, beam_b]) is True


def test_incompatible_beams_different_dimensions_returns_false():
    ba = Beam.from_centerline(Line(Point(0, 0, 0), Point(2000, 0, 0)), width=60, height=100)
    bb = Beam.from_centerline(Line(Point(0, 0, 0), Point(0, 2000, 0)), width=80, height=100)
    assert LFrenchRidgeLapJoint.check_elements_compatibility([ba, bb]) is False


def test_incompatible_beams_not_coplanar_returns_false():
    # Beam in XZ plane (diagonal) is out-of-plane relative to beam along X with Z-up frame
    ba = Beam.from_centerline(Line(Point(0, 0, 0), Point(2000, 0, 0)), width=60, height=100)
    bb = Beam.from_centerline(Line(Point(0, 0, 0), Point(0, 1000, 1000)), width=60, height=100)
    assert LFrenchRidgeLapJoint.check_elements_compatibility([ba, bb]) is False


def test_incompatible_raises_joining_error(beam_a):
    """raise_error=True should raise BeamJoiningError for incompatible beams."""
    incompatible = Beam.from_centerline(Line(Point(0, 0, 0), Point(0, 2000, 0)), width=80, height=100)
    with pytest.raises(BeamJoiningError):
        LFrenchRidgeLapJoint.check_elements_compatibility([beam_a, incompatible], raise_error=True)


def test_not_coplanar_raises_joining_error(beam_a):
    out_of_plane = Beam.from_centerline(Line(Point(0, 0, 0), Point(0, 1000, 1000)), width=60, height=100)
    with pytest.raises(BeamJoiningError):
        LFrenchRidgeLapJoint.check_elements_compatibility([beam_a, out_of_plane], raise_error=True)


# ---------------------------------------------------------------------------
# 6. Cutting planes
# ---------------------------------------------------------------------------


def test_cutting_planes_are_set(joint):
    assert joint.cutting_plane_a is not None
    assert joint.cutting_plane_b is not None


def test_cutting_plane_a_normal_is_parallel_to_beam_a_centerline(joint, beam_a):
    """Cutting plane A's normal is (anti-)parallel to beam_a's centerline — it is one of beam_a's long-side faces."""
    dot = abs(joint.cutting_plane_a.normal.dot(beam_a.centerline.direction.unitized()))
    assert TOL.is_close(dot, 1.0, rtol=1e-3)


def test_cutting_plane_b_normal_is_parallel_to_beam_b_centerline(joint, beam_b):
    """Cutting plane B's normal is (anti-)parallel to beam_b's centerline — it is one of beam_b's long-side faces."""
    dot = abs(joint.cutting_plane_b.normal.dot(beam_b.centerline.direction.unitized()))
    assert TOL.is_close(dot, 1.0, rtol=1e-3)
