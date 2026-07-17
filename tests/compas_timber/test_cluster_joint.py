"""Tests for ClusterJoint — a multi-beam joint that delegates to pairwise sub-joints."""

import pytest

from compas.data import json_dumps
from compas.data import json_loads
from compas.geometry import Line
from compas.geometry import Point

from compas_timber.connections import Cluster
from compas_timber.connections import ClusterJoint
from compas_timber.connections import LButtJoint
from compas_timber.connections import TButtJoint
from compas_timber.connections.solver import JointTopology
from compas_timber.elements import Beam
from compas_timber.model import TimberModel


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_model(*beams):
    m = TimberModel()
    for b in beams:
        m.add_element(b)
    return m


# ---------------------------------------------------------------------------
# Fixtures
#
# Three-beam portal: beam_a is the horizontal header (along X), beam_b and
# beam_c are vertical legs in L-topology with beam_a at each end.
#
#   beam_b            beam_c
#      |  ← beam_a →  |
#
# ---------------------------------------------------------------------------


@pytest.fixture
def beam_a():
    """Horizontal header, 1000 mm along X, 60×100 cross-section."""
    return Beam.from_centerline(Line(Point(0, 0, 0), Point(1000, 0, 0)), width=60, height=100)


@pytest.fixture
def beam_b():
    """Left leg: from (-30, 0, 0) upward along Y — L-topology with beam_a's left end."""
    return Beam.from_centerline(Line(Point(-30, 0, 0), Point(-30, 1000, 0)), width=60, height=100)


@pytest.fixture
def beam_c():
    """Right leg: from (1030, 0, 0) upward along Y — L-topology with beam_a's right end."""
    return Beam.from_centerline(Line(Point(1030, 0, 0), Point(1030, 1000, 0)), width=60, height=100)


@pytest.fixture
def model(beam_a, beam_b, beam_c):
    return _make_model(beam_a, beam_b, beam_c)


@pytest.fixture
def sub_joints(beam_a, beam_b, beam_c):
    """Two pairwise LButtJoints — constructed directly (not registered in the model)."""
    j1 = LButtJoint(main_beam=beam_a, cross_beam=beam_b)
    j2 = LButtJoint(main_beam=beam_a, cross_beam=beam_c)
    return [j1, j2]


@pytest.fixture
def composite(model, sub_joints):
    return ClusterJoint.create(model, cluster=Cluster(sub_joints))


# ---------------------------------------------------------------------------
# 1. Basic creation
# ---------------------------------------------------------------------------


def test_create_returns_composite_joint(model, sub_joints):
    joint = ClusterJoint.create(model, cluster=Cluster(sub_joints))
    assert isinstance(joint, ClusterJoint)


def test_create_registers_in_model(model, sub_joints):
    ClusterJoint.create(model, cluster=Cluster(sub_joints))
    assert len(list(model.joints)) == 1


def test_composite_holds_sub_joints(composite, sub_joints):
    assert len(composite.joints) == len(sub_joints)
    assert composite.joints[0] is sub_joints[0]
    assert composite.joints[1] is sub_joints[1]


def test_composite_elements_are_union_of_sub_joint_elements(composite, beam_a, beam_b, beam_c):
    all_elements = set(composite.elements)
    assert beam_a in all_elements
    assert beam_b in all_elements
    assert beam_c in all_elements
    assert len(all_elements) == 3


def test_repr(composite):
    r = repr(composite)
    assert "ClusterJoint" in r
    assert "2" in r  # 2 sub-joints


# ---------------------------------------------------------------------------
# 2. Class-level attributes
# ---------------------------------------------------------------------------


def test_supported_topology():
    assert ClusterJoint.SUPPORTED_TOPOLOGY == JointTopology.TOPO_UNKNOWN


def test_min_element_count():
    assert ClusterJoint.MIN_ELEMENT_COUNT == 3


def test_max_element_count_is_none():
    assert ClusterJoint.MAX_ELEMENT_COUNT is None


# ---------------------------------------------------------------------------
# 3. process_joinery integration
# ---------------------------------------------------------------------------


def test_process_joinery_completes_without_error(model, sub_joints):
    ClusterJoint.create(model, cluster=Cluster(sub_joints))
    errors = model.process_joinery()
    assert errors == []


def test_process_joinery_adds_features_to_beams(model, beam_a, beam_b, beam_c, sub_joints):
    ClusterJoint.create(model, cluster=Cluster(sub_joints))
    model.process_joinery()
    # Each L-butt joint adds at least one feature on the main beam (beam_a)
    assert len(beam_a.features) > 0


def test_process_joinery_adds_features_to_cross_beams(model, beam_b, beam_c, sub_joints):
    ClusterJoint.create(model, cluster=Cluster(sub_joints))
    model.process_joinery()
    assert len(beam_b.features) > 0
    assert len(beam_c.features) > 0


def test_process_joinery_does_not_add_sub_joints_to_model(model, sub_joints):
    """Sub-joints must not be independently registered in the model."""
    ClusterJoint.create(model, cluster=Cluster(sub_joints))
    model.process_joinery()
    # Only the one ClusterJoint should be in the model
    assert len(list(model.joints)) == 1


# ---------------------------------------------------------------------------
# 4. Serialization / JSON round-trip
# ---------------------------------------------------------------------------


def test_data_contains_joints_key(composite):
    assert "cluster" in composite.__data__


def test_data_contains_element_guids(composite, beam_a, beam_b, beam_c):
    guids = set(composite.__data__["element_guids"])
    expected = {str(beam_a.guid), str(beam_b.guid), str(beam_c.guid)}
    assert guids == expected


def test_json_roundtrip_model(model, sub_joints):
    ClusterJoint.create(model, cluster=Cluster(sub_joints))
    restored = json_loads(json_dumps(model))

    joints = list(restored.joints)
    assert len(joints) == 1
    rj = joints[0]
    assert isinstance(rj, ClusterJoint)


def test_json_roundtrip_sub_joint_count(model, sub_joints):
    ClusterJoint.create(model, cluster=Cluster(sub_joints))
    restored = json_loads(json_dumps(model))
    rj = list(restored.joints)[0]
    assert len(rj.joints) == 2


def test_json_roundtrip_sub_joint_types(model, sub_joints):
    ClusterJoint.create(model, cluster=Cluster(sub_joints))
    restored = json_loads(json_dumps(model))
    rj = list(restored.joints)[0]
    for sub in rj.joints:
        assert isinstance(sub, LButtJoint)


def test_json_roundtrip_elements_restored(model, beam_a, beam_b, beam_c, sub_joints):
    ClusterJoint.create(model, cluster=Cluster(sub_joints))
    restored = json_loads(json_dumps(model))
    rj = list(restored.joints)[0]
    # All element references must be live objects (not None) after deserialization
    assert all(e is not None for e in rj.elements)
    assert len(set(rj.elements)) == 3


def test_json_roundtrip_sub_joint_elements_restored(model, sub_joints):
    ClusterJoint.create(model, cluster=Cluster(sub_joints))
    restored = json_loads(json_dumps(model))
    rj = list(restored.joints)[0]
    for sub in rj.joints:
        assert sub.main_beam is not None
        assert sub.cross_beam is not None


def test_json_roundtrip_process_joinery(model, sub_joints):
    """Deserialized model should still be able to run process_joinery."""
    ClusterJoint.create(model, cluster=Cluster(sub_joints))
    restored = json_loads(json_dumps(model))
    errors = restored.process_joinery()
    assert errors == []


def test_json_roundtrip_features_generated_after_reload(model, sub_joints):
    """After deserialization and process_joinery, features are added to beams."""
    ClusterJoint.create(model, cluster=Cluster(sub_joints))
    restored = json_loads(json_dumps(model))
    restored.process_joinery()
    beams = list(restored.beams)
    # At least some beams should have features after processing
    assert any(len(b.features) > 0 for b in beams)


# ---------------------------------------------------------------------------
# 5. Location
# ---------------------------------------------------------------------------


def test_location_delegated_to_first_sub_joint(composite, sub_joints):
    """ClusterJoint.location falls back to first sub-joint's location when not set."""
    assert composite.location is not None


# ---------------------------------------------------------------------------
# 6. Mixed sub-joint types
# ---------------------------------------------------------------------------


def test_mixed_sub_joint_types(beam_a, beam_b, beam_c):
    """ClusterJoint can hold sub-joints of different types."""
    # One L-type and one T-type sub-joint
    j_l = LButtJoint(main_beam=beam_a, cross_beam=beam_b)
    # beam_c crosses beam_a in T topology (approaching from the side)
    beam_t = Beam.from_centerline(Line(Point(500, -500, 0), Point(500, 500, 0)), width=60, height=100)
    j_t = TButtJoint(main_beam=beam_a, cross_beam=beam_t)

    m = _make_model(beam_a, beam_b, beam_c, beam_t)
    joint = ClusterJoint.create(m, cluster=Cluster([j_l, j_t]))

    assert len(joint.joints) == 2
    assert isinstance(joint.joints[0], LButtJoint)
    assert isinstance(joint.joints[1], TButtJoint)
    assert len(set(joint.elements)) == 3  # beam_a, beam_b, beam_t (3 unique)


# ---------------------------------------------------------------------------
# 7. clear_features / clear_extensions delegation
# ---------------------------------------------------------------------------


def test_clear_features_removes_features_from_elements(model, beam_a, beam_b, beam_c, composite):
    model.process_joinery()
    assert len(beam_a.features) > 0
    assert len(beam_b.features) > 0
    assert len(beam_c.features) > 0

    composite.clear_features()

    assert beam_a.features == []
    assert beam_b.features == []
    assert beam_c.features == []


def test_clear_features_delegates_to_sub_joints(model, composite):
    model.process_joinery()
    assert any(sub.features for sub in composite.joints)

    composite.clear_features()

    assert all(sub.features == [] for sub in composite.joints)
    assert composite.features == []


def test_clear_features_without_prior_processing_does_not_raise(composite):
    # No process_joinery has run yet, so there are no features to clear.
    composite.clear_features()
    assert composite.features == []


def test_clear_extensions_removes_blank_extensions_from_cross_beams(model, beam_b, beam_c, sub_joints, composite):
    model.process_joinery()
    j1, j2 = sub_joints
    assert j1.guid in beam_b._blank_extensions
    assert j2.guid in beam_c._blank_extensions

    composite.clear_extensions()

    assert j1.guid not in beam_b._blank_extensions
    assert j2.guid not in beam_c._blank_extensions


def test_clear_extensions_without_prior_processing_does_not_raise(composite):
    # No process_joinery has run yet, so there are no extensions to clear.
    composite.clear_extensions()


def test_mixed_sub_joints_json_roundtrip(beam_a, beam_b, beam_c):
    j_l = LButtJoint(main_beam=beam_a, cross_beam=beam_b)
    beam_t = Beam.from_centerline(Line(Point(500, -500, 0), Point(500, 500, 0)), width=60, height=100)
    j_t = TButtJoint(main_beam=beam_a, cross_beam=beam_t)

    m = _make_model(beam_a, beam_b, beam_c, beam_t)
    ClusterJoint.create(m, cluster=Cluster([j_l, j_t]))

    restored = json_loads(json_dumps(m))
    rj = list(restored.joints)[0]
    assert isinstance(rj, ClusterJoint)
    sub_types = {type(s) for s in rj.joints}
    assert LButtJoint in sub_types
    assert TButtJoint in sub_types
