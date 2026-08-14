"""Model-level regression net for assembly sequencing.

The synthetic fixtures under ``tests/assembly_sequencing`` come first and are where a
failure can be attributed to a cause. These tests exercise the adapter: a real model, real
joint classes, real geometry. When one of these fails on its own it will not tell you why
-- a hundred interacting decisions produced that order -- which is exactly why the
synthetic fixtures exist.

"""

import pytest
from compas.geometry import Line
from compas.geometry import Plane
from compas.geometry import Point
from compas.geometry import Polyline
from compas.geometry import Vector

from assembly_sequencing import HalfSpace
from assembly_sequencing import SignedAxis
from compas_timber.connections import TButtJoint
from compas_timber.connections import TTenonMortiseJoint
from compas_timber.elements import Beam
from compas_timber.model import TimberModel
from compas_timber.planning import InsertionSolver
from compas_timber.planning import KinematicSequenceGenerator
from compas_timber.planning import TimberModelAdapter
from compas_timber.planning import generate_assembly_sequence
from compas_timber.planning.sequencing import MANUAL_ATTRIBUTE
from compas_timber.planning.sequencing import SEQUENCE_ATTRIBUTE
from compas_timber.planning.sequencing import VECTOR_ATTRIBUTE
from compas_timber.planning.sequencing import constraints_from_joint_output

WIDTH = 100.0
HEIGHT = 100.0


@pytest.fixture
def portal():
    """Two posts and a top beam, T-butted together."""
    model = TimberModel()
    post_west = Beam.from_centerline(Line(Point(0, 0, 0), Point(0, 0, 2000)), WIDTH, HEIGHT)
    post_east = Beam.from_centerline(Line(Point(3000, 0, 0), Point(3000, 0, 2000)), WIDTH, HEIGHT)
    top = Beam.from_centerline(Line(Point(0, 0, 2000), Point(3000, 0, 2000)), WIDTH, HEIGHT)
    for beam in (post_west, post_east, top):
        model.add_element(beam)
    TButtJoint.create(model, top, post_west)
    TButtJoint.create(model, top, post_east)
    model.process_joinery()
    return model, post_west, post_east, top


def ids_to_beams(result, adapter):
    return [adapter.elements_by_id[element_id] for element_id in result.order]


# ---------------------------------------------------------------------------
# constraint conversion
# ---------------------------------------------------------------------------


def test_a_line_becomes_a_signed_axis_oriented_start_to_end():
    constraints = constraints_from_joint_output(Line(Point(0, 0, 0), Point(0, 0, 5)))
    assert len(constraints) == 1
    assert isinstance(constraints[0], SignedAxis)
    assert constraints[0].direction.z == pytest.approx(1.0)


def test_a_vector_becomes_a_half_space():
    constraints = constraints_from_joint_output(Vector(1, 0, 0))
    assert isinstance(constraints[0], HalfSpace)


def test_a_list_of_vectors_becomes_several_half_spaces():
    constraints = constraints_from_joint_output([Vector(1, 0, 0), Vector(0, 1, 0)])
    assert len(constraints) == 2
    assert all(isinstance(constraint, HalfSpace) for constraint in constraints)


def test_a_plane_is_rejected_rather_than_dropped():
    # Four docstrings used to promise a Plane return that no implementation produces. If one
    # ever appears it must fail loudly, not vanish and leave the element looking free.
    with pytest.raises(TypeError):
        constraints_from_joint_output(Plane(Point(0, 0, 0), Vector(0, 0, 1)))


def test_the_inferred_flag_is_carried_through_conversion():
    constraints = constraints_from_joint_output([Vector(1, 0, 0)], inferred=True)
    assert constraints[0].inferred is True


# ---------------------------------------------------------------------------
# mortise-tenon sign regression
# ---------------------------------------------------------------------------


def test_mortise_tenon_signs_are_opposite_for_the_two_members():
    # The class once defined get_kinematic_constraint twice with opposite signs. That class
    # of defect only ever surfaces as a sign flip in output, so pin it: main_beam takes
    # + axis, cross_beam takes - axis.
    main_beam = Beam.from_centerline(Line(Point(0, 0, 0), Point(1000, 0, 0)), 80, 100)
    cross_beam = Beam.from_centerline(Line(Point(500, -300, 0), Point(500, 300, 0)), 80, 100)
    joint = TTenonMortiseJoint(main_beam=main_beam, cross_beam=cross_beam)

    axis = cross_beam.ref_sides[joint.cross_beam_ref_side_index].normal
    main_constraint = constraints_from_joint_output(joint.get_kinematic_constraint(main_beam))[0]
    cross_constraint = constraints_from_joint_output(joint.get_kinematic_constraint(cross_beam))[0]

    assert main_constraint.direction.dot(axis) == pytest.approx(1.0)
    assert cross_constraint.direction.dot(axis) == pytest.approx(-1.0)
    assert main_constraint.direction.dot(cross_constraint.direction) == pytest.approx(-1.0)


def test_mortise_tenon_is_a_strict_one_dof_constraint():
    main_beam = Beam.from_centerline(Line(Point(0, 0, 0), Point(1000, 0, 0)), 80, 100)
    cross_beam = Beam.from_centerline(Line(Point(500, -300, 0), Point(500, 300, 0)), 80, 100)
    joint = TTenonMortiseJoint(main_beam=main_beam, cross_beam=cross_beam)
    assert isinstance(constraints_from_joint_output(joint.get_kinematic_constraint(main_beam))[0], SignedAxis)


# ---------------------------------------------------------------------------
# adapter
# ---------------------------------------------------------------------------


def test_the_adapter_flattens_a_model(portal):
    model, post_west, post_east, top = portal
    data = TimberModelAdapter(model).build()

    assert len(data.element_ids) == 3
    assert data.neighbors[str(top.guid)] == {str(post_west.guid), str(post_east.guid)}
    assert data.neighbors[str(post_west.guid)] == {str(top.guid)}
    assert len(data.joint_members) == 2


def test_the_adapter_measures_height_and_length_from_the_centerline(portal):
    model, post_west, _, top = portal
    data = TimberModelAdapter(model).build()

    assert data.base_z[str(post_west.guid)] == pytest.approx(0.0)
    assert data.centroid_z[str(post_west.guid)] == pytest.approx(1000.0)
    assert data.base_z[str(top.guid)] == pytest.approx(2000.0)
    assert data.length[str(top.guid)] == pytest.approx(3000.0)


def test_the_adapter_supplies_a_swept_check_by_default(portal):
    model, _, _, _ = portal
    assert TimberModelAdapter(model).build().has_geometry is True
    assert TimberModelAdapter(model, use_geometry=False).build().has_geometry is False


def test_plates_are_excluded_and_reported():
    from compas_timber.elements import Plate

    model = TimberModel()
    beam = Beam.from_centerline(Line(Point(0, 0, 0), Point(1000, 0, 0)), WIDTH, HEIGHT)
    model.add_element(beam)
    outline = Polyline([Point(0, 0, 0), Point(500, 0, 0), Point(500, 500, 0), Point(0, 500, 0), Point(0, 0, 0)])
    plate = Plate.from_outline_thickness(outline, 20.0)
    model.add_element(plate)

    data = TimberModelAdapter(model).build()
    assert data.element_ids == [str(beam.guid)]
    assert str(plate.guid) in data.excluded
    assert "beams only" in data.excluded[str(plate.guid)]


# ---------------------------------------------------------------------------
# end to end
# ---------------------------------------------------------------------------


def test_a_real_model_sequences_end_to_end(portal):
    model, post_west, post_east, top = portal
    result, adapter = generate_assembly_sequence(model)

    assert result.is_complete
    assert result.stuck is None
    assert result.pin_conflict is None
    assert len(result.order) == 3

    ordered = ids_to_beams(result, adapter)
    assert ordered[-1] is top, "the posts must stand before the beam goes on top"
    assert set(ordered[:2]) == {post_west, post_east}


def test_every_sequenced_element_gets_a_unit_insertion_vector(portal):
    model, _, _, _ = portal
    result, _ = generate_assembly_sequence(model)
    for element_id in result.order:
        vector = result.insertion_vectors[element_id]
        assert vector is not None
        assert vector.length == pytest.approx(1.0)


def test_the_sequence_is_written_onto_the_model(portal):
    model, _, _, top = portal
    generate_assembly_sequence(model)

    assert top.attributes[SEQUENCE_ATTRIBUTE] == 2
    assert top.attributes[VECTOR_ATTRIBUTE] is not None
    assert top.attributes[MANUAL_ATTRIBUTE] is False
    assert model._graph.node_attribute(top.graphnode, SEQUENCE_ATTRIBUTE) == 2


def test_a_real_model_sequences_the_same_way_twice(portal):
    model, _, _, _ = portal
    first, _ = generate_assembly_sequence(model)
    second, _ = generate_assembly_sequence(model)
    assert first.order == second.order


def test_the_hand_placement_set_round_trips_through_element_attributes(portal):
    model, post_west, _, _ = portal
    # A fact about the design, so it is persisted on the element and picked up on re-run.
    post_west.attributes[MANUAL_ATTRIBUTE] = True

    result, _ = generate_assembly_sequence(model)
    assert str(post_west.guid) in result.manual_set
    assert post_west.attributes[MANUAL_ATTRIBUTE] is True


def test_an_explicit_manual_set_overrides_the_persisted_one(portal):
    model, post_west, _, _ = portal
    post_west.attributes[MANUAL_ATTRIBUTE] = True
    result, _ = generate_assembly_sequence(model, manual_set=set())
    assert str(post_west.guid) not in result.manual_set


def test_sequencing_without_geometry_still_works(portal):
    model, _, _, top = portal
    result, adapter = generate_assembly_sequence(model, use_geometry=False)
    assert result.is_complete
    assert ids_to_beams(result, adapter)[-1] is top


def test_a_pinned_order_is_honoured_on_a_real_model(portal):
    model, post_west, post_east, top = portal
    wanted = [str(post_east.guid), str(post_west.guid), str(top.guid)]
    result, _ = generate_assembly_sequence(model, pinned_order=wanted)
    assert result.is_complete
    assert result.order == wanted


def test_an_unjointed_beam_is_free_rather_than_locked():
    # Zero constraints means entirely free. It used to mean locked.
    model = TimberModel()
    beam = Beam.from_centerline(Line(Point(0, 0, 0), Point(1000, 0, 0)), WIDTH, HEIGHT)
    model.add_element(beam)
    result, _ = generate_assembly_sequence(model)
    assert result.is_complete
    assert result.insertion_vectors[str(beam.guid)] is not None


# ---------------------------------------------------------------------------
# the legacy path, kept as a fallback
# ---------------------------------------------------------------------------
#
# `InsertionSolver` and `KinematicSequenceGenerator` are the original implementations,
# deliberately left untouched while the new package is being verified against real
# designs. They share no code with `assembly_sequencing` -- nothing in the new path
# imports them -- so the two can be compared on the same model.
#
# These tests pin the legacy behaviour as it stands, including the parts the new solver
# was built to replace. They are not statements that the old answers are correct.


def test_legacy_solver_resolves_a_list_of_half_spaces():
    solver = InsertionSolver(None)
    vector = solver.resolve_constraints([[Vector(0, 0, 1), Vector(1, 0, 0)]])
    assert vector is not None
    assert vector.length == pytest.approx(1.0)


def test_legacy_solver_returns_none_when_locked():
    solver = InsertionSolver(None)
    locked = [Line(Point(0, 0, 0), Point(0, 0, 1)), Line(Point(0, 0, 0), Point(0, 0, -1))]
    assert solver.resolve_constraints(locked) is None


def test_legacy_solver_conflates_free_with_locked():
    # Both answers are None: no constraints at all, and constraints that admit no
    # direction. This is the ambiguity the new Solution / Locked split resolves.
    from assembly_sequencing import Solution
    from assembly_sequencing import solve

    solver = InsertionSolver(None)
    assert solver.resolve_constraints([]) is None
    assert isinstance(solve([]), Solution)


def test_legacy_solver_takes_the_first_passing_candidate():
    # Straight up is tried first and returned because it merely passes, even though it
    # sits exactly on both constraint boundaries and the bisector clears them by 45
    # degrees. The new solver takes the argmax instead.
    from assembly_sequencing import HalfSpace
    from assembly_sequencing import solve

    constraints = [Vector(0, 0, 1), Vector(1, 0, 0)]
    legacy = InsertionSolver(None).resolve_constraints([constraints])
    assert legacy.z == pytest.approx(1.0)

    current = solve([HalfSpace(v) for v in constraints])
    assert current.direction.z == pytest.approx(0.5**0.5)
    assert current.margin > 0.0


def test_legacy_generator_writes_the_model(portal):
    model, _, _, top = portal
    generator = KinematicSequenceGenerator(model)
    assert generator.generate() is None  # the legacy call returns nothing

    assert top.attributes[SEQUENCE_ATTRIBUTE] is not None
    assert VECTOR_ATTRIBUTE in top.attributes
    assert MANUAL_ATTRIBUTE in top.attributes
    assert model._graph.node_attribute(top.graphnode, SEQUENCE_ATTRIBUTE) is not None


def test_legacy_generator_keeps_its_intermediate_graphs(portal):
    # Grasshopper definitions may read these; they have no equivalent in the new package,
    # where hierarchy ordering was deliberately dropped and subassemblies come from SCCs.
    model, _, _, _ = portal
    generator = KinematicSequenceGenerator(model)
    generator.generate()
    assert generator.topological_levels
    assert generator.precedence_graph
    assert generator.hierarchy_graph
    assert generator.subassemblies


def test_legacy_generator_accepts_a_heuristic(portal):
    model, _, _, top = portal
    # The highest score is disassembled first, which puts it last in the assembly order.
    KinematicSequenceGenerator(model, heuristic=lambda beam: beam.centerline.midpoint.z).generate()
    assert top.attributes[SEQUENCE_ATTRIBUTE] == 2

    # Invert the heuristic and the top beam moves to the front.
    KinematicSequenceGenerator(model, heuristic=lambda beam: -beam.centerline.midpoint.z).generate()
    assert top.attributes[SEQUENCE_ATTRIBUTE] == 0


def test_both_paths_sequence_the_same_model(portal):
    # The two implementations are independent; this only asserts that each produces a
    # complete ordering of the same elements, not that they agree on the order.
    model, _, _, _ = portal
    KinematicSequenceGenerator(model).generate()
    legacy_order = [element.name for element in model.assembly_sequence]

    result, adapter = generate_assembly_sequence(model)
    current_order = [adapter.elements_by_id[i].name for i in result.order]

    assert sorted(legacy_order) == sorted(current_order)
    assert result.is_complete
