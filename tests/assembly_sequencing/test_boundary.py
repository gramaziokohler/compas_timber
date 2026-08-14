import pytest
from synthetic import stack

from assembly_sequencing import SequencingInput
from assembly_sequencing import sort_key


def minimal(**overrides):
    kwargs = dict(
        element_ids=["a", "b"],
        neighbors={"a": {"b"}, "b": {"a"}},
        base_z={"a": 0.0, "b": 1.0},
        centroid_z={"a": 0.5, "b": 1.5},
        length={"a": 1.0, "b": 1.0},
        constraints=lambda element_id, active: [],
    )
    kwargs.update(overrides)
    return SequencingInput(**kwargs)


def test_a_minimal_input_builds():
    data = minimal()
    assert len(data) == 2
    assert "a" in data


def test_duplicate_ids_raise():
    with pytest.raises(ValueError):
        minimal(element_ids=["a", "b", "a"])


def test_an_asymmetric_neighbour_map_raises():
    with pytest.raises(ValueError) as error:
        minimal(neighbors={"a": {"b"}, "b": set()})
    assert "symmetric" in str(error.value)


def test_a_self_neighbour_raises():
    with pytest.raises(ValueError):
        minimal(neighbors={"a": {"a", "b"}, "b": {"a"}})


def test_an_unknown_neighbour_raises():
    with pytest.raises(ValueError):
        minimal(neighbors={"a": {"b", "ghost"}, "b": {"a"}})


@pytest.mark.parametrize("field", ["base_z", "centroid_z", "length"])
def test_a_missing_quantity_raises_rather_than_defaulting(field):
    # A silent 0.0 height sinks an element to the bottom of the ranking while looking like
    # a real measurement. Non-beam elements belong in `excluded`, not at height zero.
    with pytest.raises(ValueError) as error:
        minimal(**{field: {"a": 0.0}})
    assert field in str(error.value)


def test_an_element_cannot_be_both_sequenceable_and_excluded():
    with pytest.raises(ValueError):
        minimal(excluded={"a": "plate"})


def test_constraints_must_be_callable():
    # A per-joint lookup table cannot express an n-ary joint, so the boundary insists on a
    # function of the element and its still-present neighbours.
    with pytest.raises(ValueError):
        minimal(constraints={("a", frozenset(["b"])): []})


def test_path_is_clear_defaults_to_permissive_and_says_so():
    data = minimal()
    assert data.has_geometry is False
    assert data.path_is_clear("a", None, 1.0, {"b"}) is True


def test_path_is_clear_is_reported_when_supplied():
    data = minimal(path_is_clear=lambda element_id, direction, distance, active: False)
    assert data.has_geometry is True
    assert data.path_is_clear("a", None, 1.0, {"b"}) is False


def test_active_neighbors_intersects_with_the_active_set():
    data = stack()
    assert data.active_neighbors("middle", {"middle", "top"}) == {"top"}
    assert data.active_neighbors("middle", {"middle"}) == set()


def test_active_neighbors_never_includes_the_element_itself():
    data = stack()
    assert "middle" not in data.active_neighbors("middle", {"bottom", "middle", "top"})


def test_degree_counts_jointed_neighbours():
    data = stack()
    assert data.degree("middle") == 2
    assert data.degree("top") == 1


def test_sorted_ids_is_deterministic_for_unorderable_ids():
    import uuid

    ids = [uuid.uuid4() for _ in range(6)]
    data = SequencingInput(
        element_ids=ids,
        neighbors={i: set() for i in ids},
        base_z={i: 0.0 for i in ids},
        centroid_z={i: 0.0 for i in ids},
        length={i: 1.0 for i in ids},
        constraints=lambda element_id, active: [],
    )
    assert data.sorted_ids() == sorted(ids, key=sort_key)
    assert data.sorted_ids() == data.sorted_ids()


def test_joint_members_keeps_n_ary_joints_intact():
    data = minimal(joint_members={"j1": ("a", "b")})
    assert data.joint_members["j1"] == ("a", "b")
