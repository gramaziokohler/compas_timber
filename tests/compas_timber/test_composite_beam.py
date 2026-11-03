"""Tests for CompositeBeam (elements/composite_beam.py) and the joint-agnostic routing it relies on
(Joint.resolve_composite_elements, called by TimberModel.process_joinery)."""

import pytest

from compas.data import json_dumps
from compas.data import json_loads
from compas.geometry import Frame
from compas.geometry import Point
from compas.geometry import Vector

from compas_timber.connections import ButtJoint
from compas_timber.connections import CompositeJoint
from compas_timber.connections import ISimpleScarf
from compas_timber.connections import Joint
from compas_timber.elements import Beam
from compas_timber.elements import CompositeBeam
from compas_timber.elements import Plate
from compas_timber.model import TimberModel


def _linear_composite():
    """A 200-long CompositeBeam along world X, split into two 100-long parts, end to end."""
    frame = Frame(Point(0, 0, 0), Vector(1, 0, 0), Vector(0, 1, 0))
    composite = CompositeBeam(frame, length=200, width=30, height=30)

    part_1 = Beam(Frame(Point(0, 0, 0), Vector(1, 0, 0), Vector(0, 1, 0)), length=100, width=30, height=30)
    part_2 = Beam(Frame(Point(100, 0, 0), Vector(1, 0, 0), Vector(0, 1, 0)), length=100, width=30, height=30)
    composite.add_part(part_1)
    composite.add_part(part_2)
    return composite, part_1, part_2


# ---------------------------------------------------------------------------
# parts / add_part / merge_contained_elements
# ---------------------------------------------------------------------------


def test_is_group_element():
    composite, _, _ = _linear_composite()
    assert composite.is_group_element is True


def test_parts_before_model_returns_added_parts_in_order():
    composite, part_1, part_2 = _linear_composite()
    assert composite.parts == [part_1, part_2]


def test_merge_contained_elements_adds_parts_to_model():
    composite, part_1, part_2 = _linear_composite()

    model = TimberModel()
    model.add_element(composite)
    composite.merge_contained_elements(model)

    assert part_1 in model.elements()
    assert part_2 in model.elements()
    assert set(composite.parts) == {part_1, part_2}


def test_merge_contained_elements_does_not_duplicate_already_added_parts():
    composite, part_1, part_2 = _linear_composite()

    model = TimberModel()
    model.add_element(composite)
    model.add_element(part_1, parent=composite)
    composite.merge_contained_elements(model)  # part_1 already there, should be skipped, not raise

    assert len([e for e in model.elements() if e is part_1]) == 1
    assert part_2 in model.elements()


# ---------------------------------------------------------------------------
# resolve_part_at
# ---------------------------------------------------------------------------


def test_resolve_part_at_returns_the_closest_part():
    composite, part_1, part_2 = _linear_composite()

    assert composite.resolve_part_at(Point(50, 0, 0)) is part_1
    assert composite.resolve_part_at(Point(150, 0, 0)) is part_2
    # a point outside either part's box still resolves to the nearest one
    assert composite.resolve_part_at(Point(5000, 0, 0)) is part_2


def test_resolve_part_at_works_after_model_attachment():
    composite, part_1, part_2 = _linear_composite()
    model = TimberModel()
    model.add_element(composite)
    composite.merge_contained_elements(model)

    assert composite.resolve_part_at(Point(150, 0, 0)) is part_2


def test_resolve_part_at_raises_with_no_parts():
    frame = Frame(Point(0, 0, 0), Vector(1, 0, 0), Vector(0, 1, 0))
    empty_composite = CompositeBeam(frame, length=200, width=30, height=30)
    with pytest.raises(ValueError):
        empty_composite.resolve_part_at(Point(0, 0, 0))


# ---------------------------------------------------------------------------
# Joint.resolve_composite_elements - joint-agnostic, lives on the base class only
# ---------------------------------------------------------------------------


def test_resolve_composite_elements_is_a_noop_for_plain_beams():
    beam_a = Beam(Frame(Point(0, 0, 0), Vector(1, 0, 0), Vector(0, 1, 0)), length=100, width=30, height=30)
    beam_b = Beam(Frame(Point(0, 100, 0), Vector(1, 0, 0), Vector(0, 1, 0)), length=100, width=30, height=30)
    joint = Joint(elements=(beam_a, beam_b))

    joint.resolve_composite_elements()

    assert joint.elements == (beam_a, beam_b)


def test_resolve_composite_elements_routes_to_the_correct_part():
    composite, part_1, part_2 = _linear_composite()
    # a beam crossing the composite's axis near its far end
    other_beam = Beam(Frame(Point(190, -50, 0), Vector(0, 1, 0), Vector(1, 0, 0)), length=100, width=30, height=30)
    joint = Joint(elements=(composite, other_beam))

    joint.resolve_composite_elements()

    assert joint.elements == (part_2, other_beam)


def test_resolve_composite_elements_is_idempotent():
    composite, part_1, part_2 = _linear_composite()
    other_beam = Beam(Frame(Point(190, -50, 0), Vector(0, 1, 0), Vector(1, 0, 0)), length=100, width=30, height=30)
    joint = Joint(elements=(composite, other_beam))

    joint.resolve_composite_elements()
    joint.resolve_composite_elements()  # calling again should not error or change anything

    assert joint.elements == (part_2, other_beam)


def test_resolve_composite_elements_updates_element_guids_to_match():
    """element_guids must stay consistent with elements, or restore_elements_from_keys() would
    restore the joint pointing at the composite again after a serialize/deserialize round-trip."""
    composite, part_1, part_2 = _linear_composite()
    other_beam = Beam(Frame(Point(190, -50, 0), Vector(0, 1, 0), Vector(1, 0, 0)), length=100, width=30, height=30)
    joint = Joint(elements=(composite, other_beam))

    joint.resolve_composite_elements()

    assert joint.element_guids == tuple(str(e.guid) for e in joint.elements)
    assert str(composite.guid) not in joint.element_guids
    assert str(part_2.guid) in joint.element_guids


# ---------------------------------------------------------------------------
# CompositeJoint delegates to its own sub-joints, not its own (inert) .elements
# ---------------------------------------------------------------------------


def test_composite_joint_resolve_composite_elements_routes_each_subjoint():
    composite, part_1, part_2 = _linear_composite()
    other_beam = Beam(Frame(Point(190, -50, 0), Vector(0, 1, 0), Vector(1, 0, 0)), length=100, width=30, height=30)
    third_beam = Beam(Frame(Point(0, 100, 0), Vector(1, 0, 0), Vector(0, 1, 0)), length=100, width=30, height=30)

    sub_joint_touching_composite = ISimpleScarf(composite, other_beam)
    sub_joint_unrelated = ISimpleScarf(part_1, third_beam)
    composite_joint = CompositeJoint([sub_joint_touching_composite, sub_joint_unrelated])

    composite_joint.resolve_composite_elements()

    # the sub-joint that actually touched the composite gets routed to the real part
    assert composite not in sub_joint_touching_composite.elements
    assert part_2 in sub_joint_touching_composite.elements

    # the CompositeJoint's own (flattened) elements/element_guids reflect the resolved sub-joints
    assert composite not in composite_joint.elements
    assert composite_joint.element_guids == tuple(str(e.guid) for e in composite_joint.elements)


def test_expand_composite_joints_passes_through_composite_joint_unchanged():
    """CompositeJoint can't be reconstructed as type(joint)(*part_pair, **kwargs) (its constructor
    takes a `joints` list, not element positionals), so it must never be handed to that path."""
    composite, part_1, part_2 = _linear_composite()
    composite.cut_all_parts = True
    other_beam = Beam(Frame(Point(190, -50, 0), Vector(0, 1, 0), Vector(1, 0, 0)), length=100, width=30, height=30)
    third_beam = Beam(Frame(Point(0, 100, 0), Vector(1, 0, 0), Vector(0, 1, 0)), length=100, width=30, height=30)

    sub_joint = ISimpleScarf(composite, other_beam)
    composite_joint = CompositeJoint([sub_joint, ISimpleScarf(part_1, third_beam)])

    model = TimberModel()
    model.add_element(composite)
    composite.merge_contained_elements(model)

    expanded = model._expand_composite_joints([composite_joint])

    assert expanded == [composite_joint]


# ---------------------------------------------------------------------------
# End-to-end: TimberModel.process_joinery() routes features/extensions to a
# real part, no joint subclass involved in the routing.
# ---------------------------------------------------------------------------


def test_process_joinery_routes_butt_joint_to_a_single_part_not_the_composite():
    composite, part_1, part_2 = _linear_composite()
    end_beam = Beam(Frame(Point(200, -60, 0), Vector(0, 1, 0), Vector(-1, 0, 0)), width=30, height=30, length=120)

    model = TimberModel()
    model.add_element(composite)
    composite.merge_contained_elements(model)
    model.add_element(end_beam)

    joint = ButtJoint.create(model, composite, end_beam, mill_depth=0)
    model.process_joinery()

    # the joint itself now points at the real part, not the composite
    assert composite not in joint.elements
    assert part_2 in joint.elements

    # the composite stays a pure nominal envelope - it never receives anything
    assert composite._blank_extensions == {}
    assert composite.features == []

    assert joint.guid in part_2._blank_extensions
    assert joint.guid not in part_1._blank_extensions
    assert len(part_2.features) == 1
    assert len(part_1.features) == 0


def test_process_joinery_internal_splice_joint_is_unaffected_by_composite_routing():
    composite, part_1, part_2 = _linear_composite()

    model = TimberModel()
    model.add_element(composite)
    composite.merge_contained_elements(model)

    joint = ISimpleScarf.create(model, part_1, part_2)
    model.process_joinery()

    # neither element of an ordinary joint between two real parts is a CompositeBeam,
    # so resolve_composite_elements() is a no-op here
    assert joint.elements == (part_1, part_2)
    assert part_1.features
    assert part_2.features


# ---------------------------------------------------------------------------
# cut_all_parts=True: TimberModel._expand_composite_joints
# ---------------------------------------------------------------------------


def _stacked_composite(x_origin, cut_all_parts=True):
    """A CompositeBeam at x_origin with 2 Beam parts stacked along Z."""
    frame = Frame(Point(x_origin, 0, 0), Vector(1, 0, 0), Vector(0, 1, 0))
    composite = CompositeBeam(frame, length=100, width=30, height=30, cut_all_parts=cut_all_parts)
    bottom = Beam(Frame(Point(x_origin, 0, 0), Vector(1, 0, 0), Vector(0, 1, 0)), length=100, width=30, height=30)
    top = Beam(Frame(Point(x_origin, 0, 100), Vector(1, 0, 0), Vector(0, 1, 0)), length=100, width=30, height=30)
    composite.add_part(bottom)
    composite.add_part(top)
    return composite, bottom, top


def test_expand_composite_joints_clones_per_matching_part_pair():
    composite_a, a_bottom, a_top = _stacked_composite(0)
    composite_b, b_bottom, b_top = _stacked_composite(500)

    model = TimberModel()
    model.add_element(composite_a)
    composite_a.merge_contained_elements(model)
    model.add_element(composite_b)
    composite_b.merge_contained_elements(model)

    joint = ISimpleScarf(composite_a, composite_b)
    expanded = model._expand_composite_joints([joint])

    assert {j.elements for j in expanded} == {(a_bottom, b_bottom), (a_top, b_top)}


def test_expand_composite_joints_repeats_plain_element_for_each_part():
    composite, bottom, top = _stacked_composite(0)
    plain_beam = Beam(Frame(Point(0, 100, 0), Vector(1, 0, 0), Vector(0, 1, 0)), length=100, width=30, height=30)

    model = TimberModel()
    model.add_element(composite)
    composite.merge_contained_elements(model)
    model.add_element(plain_beam)

    joint = ISimpleScarf(composite, plain_beam)
    expanded = model._expand_composite_joints([joint])

    assert {j.elements for j in expanded} == {(bottom, plain_beam), (top, plain_beam)}


def test_expand_composite_joints_skips_pairs_without_centerline():
    frame_a = Frame(Point(0, 0, 0), Vector(1, 0, 0), Vector(0, 1, 0))
    composite_a = CompositeBeam(frame_a, length=100, width=30, height=30, cut_all_parts=True)
    beam_a = Beam(Frame(Point(0, 0, 0), Vector(1, 0, 0), Vector(0, 1, 0)), length=100, width=30, height=30)
    plate_a = Plate(Frame(Point(0, 0, 100), Vector(1, 0, 0), Vector(0, 1, 0)), length=100, width=30, thickness=10)
    composite_a.add_part(beam_a)
    composite_a.add_part(plate_a)

    frame_b = Frame(Point(500, 0, 0), Vector(1, 0, 0), Vector(0, 1, 0))
    composite_b = CompositeBeam(frame_b, length=100, width=30, height=30, cut_all_parts=True)
    beam_b = Beam(Frame(Point(500, 0, 0), Vector(1, 0, 0), Vector(0, 1, 0)), length=100, width=30, height=30)
    plate_b = Plate(Frame(Point(500, 0, 100), Vector(1, 0, 0), Vector(0, 1, 0)), length=100, width=30, thickness=10)
    composite_b.add_part(beam_b)
    composite_b.add_part(plate_b)

    model = TimberModel()
    model.add_element(composite_a)
    composite_a.merge_contained_elements(model)
    model.add_element(composite_b)
    composite_b.merge_contained_elements(model)

    joint = ISimpleScarf(composite_a, composite_b)
    expanded = model._expand_composite_joints([joint])

    # only the Beam-Beam pair survives; the Plate-Plate pair (no centerline) is skipped
    assert len(expanded) == 1
    assert expanded[0].elements == (beam_a, beam_b)


def test_expand_composite_joints_passes_through_when_cut_all_parts_false():
    composite, part_1, part_2 = _linear_composite()  # cut_all_parts=False by default
    other_beam = Beam(Frame(Point(190, -50, 0), Vector(0, 1, 0), Vector(1, 0, 0)), length=100, width=30, height=30)

    model = TimberModel()
    model.add_element(composite)
    composite.merge_contained_elements(model)
    model.add_element(other_beam)

    joint = Joint(elements=(composite, other_beam))
    expanded = model._expand_composite_joints([joint])

    assert expanded == [joint]


def test_process_joinery_cut_all_parts_applies_joint_to_every_beam_part():
    composite_a, a_bottom, a_top = _stacked_composite(0)
    composite_b, b_bottom, b_top = _stacked_composite(500)

    model = TimberModel()
    model.add_element(composite_a)
    composite_a.merge_contained_elements(model)
    model.add_element(composite_b)
    composite_b.merge_contained_elements(model)

    ISimpleScarf.create(model, composite_a, composite_b)
    errors = model.process_joinery()

    assert errors == []
    assert composite_a.features == []
    assert composite_b.features == []
    for part in (a_bottom, a_top, b_bottom, b_top):
        assert part.features, "{!r} should have received a feature from the expanded joint".format(part)


def test_process_joinery_cut_all_parts_is_idempotent_across_repeated_calls():
    """Regression test: _expand_composite_joints() must reuse the same clone joint for a given part
    pair across calls, or clear_features()/clear_extensions() has nothing to undo each time (a fresh
    clone has no memory of what a previous, discarded clone applied) and features/extensions
    silently accumulate on every re-run instead of staying constant."""
    composite_a, a_bottom, a_top = _stacked_composite(0)
    composite_b, b_bottom, b_top = _stacked_composite(500)

    model = TimberModel()
    model.add_element(composite_a)
    composite_a.merge_contained_elements(model)
    model.add_element(composite_b)
    composite_b.merge_contained_elements(model)

    ISimpleScarf.create(model, composite_a, composite_b)

    model.process_joinery()
    counts_after_first_run = [len(part.features) for part in (a_bottom, a_top, b_bottom, b_top)]

    for _ in range(3):
        model.process_joinery()
        counts = [len(part.features) for part in (a_bottom, a_top, b_bottom, b_top)]
        assert counts == counts_after_first_run


def test_expand_composite_joints_reuses_the_same_clone_across_calls():
    composite_a, a_bottom, a_top = _stacked_composite(0)
    composite_b, b_bottom, b_top = _stacked_composite(500)

    model = TimberModel()
    model.add_element(composite_a)
    composite_a.merge_contained_elements(model)
    model.add_element(composite_b)
    composite_b.merge_contained_elements(model)

    joint = ISimpleScarf(composite_a, composite_b)

    first_pass = {j.elements: j for j in model._expand_composite_joints([joint])}
    second_pass = {j.elements: j for j in model._expand_composite_joints([joint])}

    assert first_pass.keys() == second_pass.keys()
    for elements in first_pass:
        assert first_pass[elements] is second_pass[elements]


# ---------------------------------------------------------------------------
# Serialization round-trip
# ---------------------------------------------------------------------------


def test_composite_beam_cut_all_parts_survives_json_round_trip():
    composite = CompositeBeam(Frame(Point(0, 0, 0), Vector(1, 0, 0), Vector(0, 1, 0)), length=200, width=30, height=30, cut_all_parts=True)
    restored = json_loads(json_dumps(composite))
    assert restored.cut_all_parts is True


def test_model_round_trip_joint_stays_pointed_at_the_resolved_part_not_the_composite():
    """Regression test for the element_guids consistency fix in Joint.resolve_composite_elements():
    without it, restore_elements_from_keys() would rebuild the joint's elements from the (stale)
    guids captured before routing, silently undoing the routing on every reload."""
    composite, part_1, part_2 = _linear_composite()
    end_beam = Beam(Frame(Point(200, -60, 0), Vector(0, 1, 0), Vector(-1, 0, 0)), width=30, height=30, length=120)

    model = TimberModel()
    model.add_element(composite)
    composite.merge_contained_elements(model)
    model.add_element(end_beam)
    ButtJoint.create(model, composite, end_beam, mill_depth=0)
    model.process_joinery()

    restored = json_loads(json_dumps(model))
    r_joint = list(restored.joints)[0]
    r_composite = next(e for e in restored.elements() if isinstance(e, CompositeBeam))
    r_part_1, r_part_2 = r_composite.parts

    # the joint restores pointing at the real part, not the composite - both in .elements and
    # in the .element_guids it was restored from
    assert r_composite not in r_joint.elements
    assert r_part_2 in r_joint.elements
    assert r_joint.element_guids == tuple(str(e.guid) for e in r_joint.elements)

    # and re-running joinery on the reloaded model reproduces the same, correctly-routed result
    restored.process_joinery()
    assert r_composite.features == []
    assert r_part_1.features == []
    assert r_part_2.features
