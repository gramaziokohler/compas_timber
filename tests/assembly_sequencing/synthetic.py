"""Hand-written sequencing fixtures.

Every fixture here is literals: an adjacency map and a constraint table typed out by
hand. No Rhino, no joint classes, no geometry engine, no ``compas_timber`` import. When
one of these fails, the failure can be attributed to a cause -- which is why they come
before the real-model regression net.

Constraint tables are keyed by ``(element_id, frozenset_of_active_neighbors)`` so that a
constraint set can depend on which neighbours are still in place. That is the n-ary case;
a two-element joint is the degenerate one.

"""

from compas.geometry import Vector

from assembly_sequencing import HalfSpace
from assembly_sequencing import SequencingInput
from assembly_sequencing import SignedAxis

UP = Vector(0, 0, 1)
DOWN = Vector(0, 0, -1)
EAST = Vector(1, 0, 0)
WEST = Vector(-1, 0, 0)


def _table_input(element_ids, neighbors, table, base_z, centroid_z, length=None, **kwargs):
    """Build a SequencingInput whose constraints come from a literal lookup table."""

    def constraints(element_id, active_neighbor_ids):
        return list(table.get((element_id, frozenset(active_neighbor_ids)), []))

    return SequencingInput(
        element_ids=element_ids,
        neighbors=neighbors,
        base_z=base_z,
        centroid_z=centroid_z,
        length=length if length is not None else {i: 1.0 for i in element_ids},
        constraints=constraints,
        **kwargs,
    )


def stack():
    """Three beams stacked, each free straight up. The easy case.

    The middle beam has a face above and a face below, so it is a slot: still feasible,
    sliding sideways, with a margin of exactly zero.

    Assembly order must be bottom, middle, top.
    """
    ids = ["bottom", "middle", "top"]
    neighbors = {"bottom": {"middle"}, "middle": {"bottom", "top"}, "top": {"middle"}}
    table = {
        ("bottom", frozenset(["middle"])): [HalfSpace(DOWN)],
        ("middle", frozenset(["bottom"])): [HalfSpace(UP)],
        ("middle", frozenset(["top"])): [HalfSpace(DOWN)],
        ("middle", frozenset(["bottom", "top"])): [HalfSpace(UP), HalfSpace(DOWN)],
        ("top", frozenset(["middle"])): [HalfSpace(UP)],
    }
    return _table_input(
        ids,
        neighbors,
        table,
        base_z={"bottom": 0.0, "middle": 1.0, "top": 2.0},
        centroid_z={"bottom": 0.5, "middle": 1.5, "top": 2.5},
    )


def slot():
    """A beam dropped vertically into a slot between two others.

    The only feasible direction is exactly parallel to both contact faces, so the margin
    is exactly zero. That is a correct answer about a genuinely tight fit, not an
    artifact, and it must classify as tight rather than locked.
    """
    ids = ["left", "right", "dropped"]
    neighbors = {"left": {"dropped"}, "right": {"dropped"}, "dropped": {"left", "right"}}
    table = {
        ("dropped", frozenset(["left"])): [HalfSpace(EAST)],
        ("dropped", frozenset(["right"])): [HalfSpace(WEST)],
        # Faces on both sides: the beam may only travel in the plane they share.
        ("dropped", frozenset(["left", "right"])): [HalfSpace(EAST), HalfSpace(WEST)],
        ("left", frozenset(["dropped"])): [HalfSpace(WEST)],
        ("right", frozenset(["dropped"])): [HalfSpace(EAST)],
    }
    return _table_input(
        ids,
        neighbors,
        table,
        base_z={"left": 0.0, "right": 0.0, "dropped": 0.0},
        centroid_z={"left": 1.0, "right": 1.0, "dropped": 1.0},
    )


def double_birdsmouth():
    """A rafter housed on both faces over a plate, with two free struts alongside.

    The canonical intrinsic lock. Two seat cuts, one on each side of the plate, each
    housing the rafter in a slot of its own: one demands the rafter slide out eastwards,
    the other demands westwards, and the same pair of demands applies to the plate
    negated. The two elements lock each other through a single joint, so no ordering can
    undo it -- cut the model down to just these two and they are still stuck. This is hand
    placement, and it is the only kind of failure that legitimately says so.
    """
    ids = ["plate", "rafter", "strut_west", "strut_east"]
    neighbors = {
        "plate": {"rafter", "strut_west"},
        "rafter": {"plate", "strut_east"},
        "strut_west": {"plate"},
        "strut_east": {"rafter"},
    }
    table = {
        # Two seat cuts pulling opposite ways: no motion at all, in either member.
        ("rafter", frozenset(["plate"])): [SignedAxis(EAST), SignedAxis(WEST)],
        ("plate", frozenset(["rafter"])): [SignedAxis(WEST), SignedAxis(EAST)],
        ("rafter", frozenset(["plate", "strut_east"])): [SignedAxis(EAST), SignedAxis(WEST), HalfSpace(UP)],
        ("rafter", frozenset(["strut_east"])): [HalfSpace(UP)],
        ("plate", frozenset(["rafter", "strut_west"])): [SignedAxis(WEST), SignedAxis(EAST), HalfSpace(UP)],
        ("plate", frozenset(["strut_west"])): [HalfSpace(UP)],
        ("strut_west", frozenset(["plate"])): [HalfSpace(UP)],
        ("strut_east", frozenset(["rafter"])): [HalfSpace(UP)],
    }
    return _table_input(
        ids,
        neighbors,
        table,
        base_z={"plate": 1.0, "rafter": 1.0, "strut_west": 2.0, "strut_east": 2.0},
        centroid_z={"plate": 1.2, "rafter": 1.4, "strut_west": 2.5, "strut_east": 2.6},
        length={"plate": 4.0, "rafter": 3.0, "strut_west": 1.0, "strut_east": 1.0},
    )


def portal_frame():
    """Sill, two posts tenoned into it, one rafter seated over both posts.

    Locked in the complete assembly and free in the right order -- the other half of the
    intrinsic / order-dependent distinction. The rafter's two seat cuts demand opposite
    sliding directions, so it cannot come out while both posts stand; each post is capped
    from above by the rafter and tenoned from below into the sill, so it cannot come out
    while both are there. Yet lower the sill away first and the whole thing comes apart.

    Nothing here should ever be reported as hand placement. Three of the four elements are
    locked at step zero, and every one of those locks is a fact about the order, not about
    the design.
    """
    ids = ["sill", "post_west", "post_east", "rafter"]
    neighbors = {
        "sill": {"post_west", "post_east"},
        "post_west": {"sill", "rafter"},
        "post_east": {"sill", "rafter"},
        "rafter": {"post_west", "post_east"},
    }
    table = {
        # The rafter slides out of the west seat towards the east, and vice versa.
        ("rafter", frozenset(["post_west"])): [SignedAxis(EAST)],
        ("rafter", frozenset(["post_east"])): [SignedAxis(WEST)],
        ("rafter", frozenset(["post_west", "post_east"])): [SignedAxis(EAST), SignedAxis(WEST)],
        # A post lifts up out of the sill mortise, but drops down out of the seat cut.
        ("post_west", frozenset(["sill"])): [SignedAxis(UP)],
        ("post_west", frozenset(["rafter"])): [SignedAxis(DOWN)],
        ("post_west", frozenset(["sill", "rafter"])): [SignedAxis(UP), SignedAxis(DOWN)],
        ("post_east", frozenset(["sill"])): [SignedAxis(UP)],
        ("post_east", frozenset(["rafter"])): [SignedAxis(DOWN)],
        ("post_east", frozenset(["sill", "rafter"])): [SignedAxis(UP), SignedAxis(DOWN)],
        # The sill lowers away from either or both posts.
        ("sill", frozenset(["post_west"])): [SignedAxis(DOWN)],
        ("sill", frozenset(["post_east"])): [SignedAxis(DOWN)],
        ("sill", frozenset(["post_west", "post_east"])): [SignedAxis(DOWN), SignedAxis(DOWN)],
    }
    return _table_input(
        ids,
        neighbors,
        table,
        base_z={"sill": 0.0, "post_west": 0.2, "post_east": 0.2, "rafter": 3.0},
        centroid_z={"sill": 0.1, "post_west": 1.6, "post_east": 1.6, "rafter": 3.1},
        length={"sill": 4.0, "post_west": 3.0, "post_east": 3.0, "rafter": 4.0},
    )


def ball_node():
    """One three-member joint where the middle strut is trapped by the other two.

    Nothing here is a two-element joint, so an implementation that skips joints without
    exactly two members contributes zero precedence and sees three free elements. The
    precedence is real: ``trapped`` is pinned between ``upper`` and ``lower`` and only
    comes free once one of them is gone.
    """
    ids = ["upper", "trapped", "lower"]
    neighbors = {
        "upper": {"trapped", "lower"},
        "trapped": {"upper", "lower"},
        "lower": {"upper", "trapped"},
    }
    table = {
        ("trapped", frozenset(["upper"])): [SignedAxis(DOWN)],
        ("trapped", frozenset(["lower"])): [SignedAxis(UP)],
        ("trapped", frozenset(["upper", "lower"])): [SignedAxis(UP), SignedAxis(DOWN)],
        ("upper", frozenset(["trapped"])): [HalfSpace(UP)],
        ("upper", frozenset(["lower"])): [HalfSpace(UP)],
        ("upper", frozenset(["trapped", "lower"])): [HalfSpace(UP)],
        ("lower", frozenset(["trapped"])): [HalfSpace(DOWN)],
        ("lower", frozenset(["upper"])): [HalfSpace(DOWN)],
        ("lower", frozenset(["trapped", "upper"])): [HalfSpace(DOWN)],
    }
    return _table_input(
        ids,
        neighbors,
        table,
        base_z={"upper": 2.0, "trapped": 1.0, "lower": 0.0},
        centroid_z={"upper": 2.5, "trapped": 1.5, "lower": 0.5},
    )


def three_way_interlock():
    """Three members that only lock once all three are present.

    Every pair is separable, so there is no pairwise precedence edge and no strongly
    connected component to find -- the up-front intrinsic-lock pass cannot see this. The
    search hits it and says so, which is the honest outcome: no order was found, rather
    than a claim that none exists.
    """
    ids = ["alpha", "beta", "gamma"]
    neighbors = {
        "alpha": {"beta", "gamma"},
        "beta": {"alpha", "gamma"},
        "gamma": {"alpha", "beta"},
    }
    table = {
        ("alpha", frozenset(["beta"])): [SignedAxis(UP)],
        ("alpha", frozenset(["gamma"])): [SignedAxis(DOWN)],
        ("alpha", frozenset(["beta", "gamma"])): [SignedAxis(UP), SignedAxis(DOWN)],
        ("beta", frozenset(["alpha"])): [SignedAxis(EAST)],
        ("beta", frozenset(["gamma"])): [SignedAxis(WEST)],
        ("beta", frozenset(["alpha", "gamma"])): [SignedAxis(EAST), SignedAxis(WEST)],
        ("gamma", frozenset(["alpha"])): [SignedAxis(UP)],
        ("gamma", frozenset(["beta"])): [SignedAxis(DOWN)],
        ("gamma", frozenset(["alpha", "beta"])): [SignedAxis(UP), SignedAxis(DOWN)],
    }
    return _table_input(
        ids,
        neighbors,
        table,
        base_z={"alpha": 0.0, "beta": 1.0, "gamma": 2.0},
        centroid_z={"alpha": 0.5, "beta": 1.5, "gamma": 2.5},
    )


def dense_lattice(seal_off_flyer=False):
    """Two beams free by their joints, with a third in the way that they are not jointed to.

    Constraints derived from joints only see jointed neighbours. Here ``flyer`` is
    kinematically free per its single joint -- its cone's most interior direction is the
    east-up bisector -- but that path runs straight through ``obstacle``, which it has no
    joint with. Only the swept broad-phase check can catch that, and the solver must then
    fall back to the next candidate by descending margin rather than declare a lock.

    Parameters
    ----------
    seal_off_flyer : bool, optional
        Obstruct every direction, so the swept check locks the element outright.
    """
    ids = ["anchor", "flyer", "obstacle"]
    neighbors = {"anchor": {"flyer"}, "flyer": {"anchor"}, "obstacle": set()}
    table = {
        ("flyer", frozenset(["anchor"])): [HalfSpace(UP), HalfSpace(EAST)],
        ("anchor", frozenset(["flyer"])): [HalfSpace(DOWN)],
    }

    def path_is_clear(element_id, direction, distance, active_ids):
        if element_id == "flyer" and "obstacle" in active_ids:
            if seal_off_flyer:
                return False
            return direction.dot(EAST) < 0.5
        return True

    return _table_input(
        ids,
        neighbors,
        table,
        base_z={"anchor": 0.0, "flyer": 1.0, "obstacle": 2.0},
        centroid_z={"anchor": 0.5, "flyer": 1.5, "obstacle": 2.5},
        path_is_clear=path_is_clear,
    )


def bridge_with_ground():
    """A line of four elements grounded only at one end, all kinematically free.

    Removing ``link`` strands ``far`` and ``tip`` from the ground. Removing either end
    element strands nothing.
    """
    ids = ["ground", "link", "far", "tip"]
    neighbors = {
        "ground": {"link"},
        "link": {"ground", "far"},
        "far": {"link", "tip"},
        "tip": {"far"},
    }
    return _table_input(
        ids,
        neighbors,
        {},
        base_z={"ground": 0.0, "link": 1.0, "far": 1.0, "tip": 1.0},
        centroid_z={"ground": 0.5, "link": 1.5, "far": 1.5, "tip": 1.5},
    )


def with_excluded():
    """Two beams plus a plate and a fastener that are excluded from sequencing.

    Excluded elements are reported out loud rather than silently sequenced at height zero,
    where they sink to the bottom of the ranking while looking like real measurements.
    """
    ids = ["beam_low", "beam_high"]
    neighbors = {"beam_low": {"beam_high"}, "beam_high": {"beam_low"}}
    table = {
        ("beam_low", frozenset(["beam_high"])): [HalfSpace(DOWN)],
        ("beam_high", frozenset(["beam_low"])): [HalfSpace(UP)],
    }
    return _table_input(
        ids,
        neighbors,
        table,
        base_z={"beam_low": 0.0, "beam_high": 1.0},
        centroid_z={"beam_low": 0.5, "beam_high": 1.5},
        excluded={"sheathing": "plate elements are not sequenced", "screw_1": "fasteners are not sequenced"},
    )


def _stacking_input(element_ids, rests_on, base_z, centroid_z, length, **kwargs):
    """A fixture whose constraints come from a "what rests on what" relation.

    The lookup tables above enumerate one entry per subset of active neighbours, which is
    fine for three elements and impossible for eleven. This builds the same constraints
    from a rule instead: an element with something still underneath it may only move up,
    one with something still on top of it may only move down, and one with both is a slot.

    """
    supports = {i: set() for i in element_ids}
    for element_id, supporters in rests_on.items():
        supports[element_id] |= set(supporters)

    carries = {i: set() for i in element_ids}
    for element_id, supporters in rests_on.items():
        for supporter in supporters:
            carries[supporter].add(element_id)

    neighbors = {i: set() for i in element_ids}
    for element_id, supporters in rests_on.items():
        for supporter in supporters:
            neighbors[element_id].add(supporter)
            neighbors[supporter].add(element_id)

    def constraints(element_id, active_neighbor_ids):
        found = []
        if active_neighbor_ids & supports[element_id]:
            found.append(HalfSpace(UP))
        if active_neighbor_ids & carries[element_id]:
            found.append(HalfSpace(DOWN))
        return found

    return SequencingInput(
        element_ids=element_ids,
        neighbors=neighbors,
        base_z=base_z,
        centroid_z=centroid_z,
        length=length,
        constraints=constraints,
        **kwargs,
    )


def wall_panels():
    """Two stud bays on a shared sill, each with a header, under one top plate.

    Ten elements with real slack in the ranking: at any step several elements are
    kinematically free, so which one comes off is decided entirely by the preference
    strategy rather than by feasibility. The small fixtures above cannot show a difference
    between strategies because their constraints leave almost no choice.

    The shapes each strategy has to argue about:

    * The **sill** is free downwards from the first step, and taking it strands everything
      -- so it separates strategies that respect the stability term from those that chase
      clearance.
    * The **studs** are slots while both the sill and their header are present, and become
      roomy once the header is gone. Tight-versus-roomy therefore changes over time.
    * The **bays** are declared groups, so cluster continuity has something to be
      continuous about.
    * Studs are short and peripheral; the sill and the plate are long and well connected.
      Length and degree point in opposite directions from height.

    """
    studs_a = ["stud_a1", "stud_a2", "stud_a3"]
    studs_b = ["stud_b1", "stud_b2", "stud_b3"]
    element_ids = ["sill"] + studs_a + ["header_a"] + studs_b + ["header_b"] + ["plate"]

    rests_on = {"sill": set()}
    for stud in studs_a + studs_b:
        rests_on[stud] = {"sill"}
    rests_on["header_a"] = set(studs_a)
    rests_on["header_b"] = set(studs_b)
    rests_on["plate"] = {"header_a", "header_b"}

    base_z = {"sill": 0.0, "plate": 2.8}
    centroid_z = {"sill": 0.05, "plate": 2.85}
    length = {"sill": 4.0, "plate": 4.0}
    for stud in studs_a + studs_b:
        base_z[stud] = 0.1
        centroid_z[stud] = 1.3
        length[stud] = 2.4
    for header in ("header_a", "header_b"):
        base_z[header] = 2.5
        centroid_z[header] = 2.55
        length[header] = 1.8

    groups = {"sill": "base", "plate": "roof"}
    for stud in studs_a:
        groups[stud] = "bay_a"
    groups["header_a"] = "bay_a"
    for stud in studs_b:
        groups[stud] = "bay_b"
    groups["header_b"] = "bay_b"

    return _stacking_input(element_ids, rests_on, base_z, centroid_z, length, groups=groups)


def blocked_ridge():
    """A ridge that is briefly unreachable, with a pier under it and a cleat to spare.

    The shape that separates a comparator which merely *sorts* by height from one that
    compares heights *between candidates*. The ridge is the highest element and stays
    obstructed while the cleat is in place, so at step zero it is not a candidate at all.
    Of what is left, the pier stands highest -- and the pier is carrying the ridge.

    Sorting by ``base_z`` therefore takes the pier out from under a ridge that is still up
    there, which read forwards puts the ridge into the model before the pier that holds it.
    The cleat is the way out: it is lower than the pier, it has nothing on it, and taking
    it first frees the ridge for the very next step.

    Everything here stays connected to the ground whichever element goes first, so the
    stability term cannot rescue the ordering -- this is a question about heights and it
    has to be answered by a term about heights.
    """
    element_ids = ["pad", "post", "pier", "ridge", "cleat"]
    rests_on = {
        "pad": set(),
        "post": {"pad"},
        "pier": {"pad"},
        "cleat": {"pad"},
        "ridge": {"pier", "post"},
    }

    def path_is_clear(element_id, direction, distance, active_ids):
        return not (element_id == "ridge" and "cleat" in active_ids)

    return _stacking_input(
        element_ids,
        rests_on,
        base_z={"pad": 0.0, "post": 0.0, "cleat": 0.0, "pier": 1.0, "ridge": 2.0},
        centroid_z={"pad": 0.0, "post": 1.0, "cleat": 0.1, "pier": 1.5, "ridge": 2.0},
        length={"pad": 4.0, "post": 2.0, "cleat": 0.5, "pier": 1.0, "ridge": 4.0},
        path_is_clear=path_is_clear,
    )
