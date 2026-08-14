"""The cone feasibility solver.

Pure geometry. No model, no joint classes, no Rhino -- :func:`solve` takes a list of
constraints and returns a :class:`~assembly_sequencing.result.Solution` or a
:class:`~assembly_sequencing.result.Locked`. That property is the point of the whole
package split: every claim about extraction feasibility can be tested against hand-built
constraint sets.

The problem is

.. code-block:: none

    maximise   min_i (n_i . d)
    subject to |d| = 1

over the intersection of the half-spaces. The optimum of a 3D polyhedral cone lies on one
of its extreme rays, so the maximum is found by evaluating a finite candidate set and
taking the **argmax** -- not the first candidate that happens to pass.

"""

from math import radians
from math import sin

from compas.geometry import Vector

from .constraints import TOL
from .constraints import HalfSpace
from .constraints import SignedAxis
from .constraints import count_inferred
from .constraints import validate_constraints
from .result import LOCKED
from .result import ROOMY
from .result import TIGHT
from .result import Locked
from .result import Solution

ROOMY_MARGIN = sin(radians(5.0))
"""float: Boundary between a roomy fit and a tight one, as sin(5 degrees).

Below this the extraction direction clears its nearest constraint boundary by less than
five degrees. That is still feasible -- it is a slot, not a lock -- but it is not
somewhere to send a robot without a second look.
"""

PARALLEL_TOL = 1e-5
"""float: Tolerance for the 1-DOF parallelism test, as ``dot > 1 - PARALLEL_TOL``.

That is about 0.26 degrees, which is deliberately strict: two exact 1-DOF constraints
that are merely *near*-parallel really are over-constrained, because neither axis has any
freedom to give.
"""

APPROACH_DISTANCE = 100.0
"""float: Default swept-check distance, in model units.

Short and fixed by design. This package answers "can the element begin to move clear",
not "how far can it travel before it hits something" -- see the limitations in the
package docstring.
"""

FREE_DIRECTION = Vector(0.0, 0.0, 1.0)
"""Vector: The direction reported for an entirely unconstrained element."""

_ROUND = 9

_NORMAL_DIGITS = 6
"""int: Rounding used to recognise two half-space normals as the same constraint.

Coarser than :data:`_ROUND`, which is only ever used for deterministic ordering. Two
normals agreeing to a millionth are the same face for sequencing purposes, and treating
them as one keeps the candidate enumeration quadratic in *distinct* directions rather than
in joint count.
"""


def classify(margin):
    """Map a clearance margin onto an extraction state.

    Margin classifies; it never rejects. A margin of exactly zero is a real, feasible,
    zero-clearance fit.

    Parameters
    ----------
    margin : float

    Returns
    -------
    str
        One of :data:`~assembly_sequencing.result.ROOMY`,
        :data:`~assembly_sequencing.result.TIGHT`,
        :data:`~assembly_sequencing.result.LOCKED`.

    """
    if margin >= ROOMY_MARGIN:
        return ROOMY
    if margin >= -TOL:
        return TIGHT
    return LOCKED


def candidate_directions(normals):
    """The extreme rays of the cone defined by a set of half-space normals.

    Parameters
    ----------
    normals : list of :class:`compas.geometry.Vector`
        Unit inward normals.

    Returns
    -------
    list of :class:`compas.geometry.Vector`
        Unit candidates, deduplicated, in a deterministic order.

    Notes
    -----
    The candidate set is the normals themselves, both signs of every normalized pairwise
    cross product, and the normalized sum of all normals as an interior seed. Crosses
    against the world axes are not included; they are noise unrelated to the geometry of
    the constraint set.

    One degenerate case needs explicit handling. A pointed cone's optimum always lies on
    an extreme ray, and every extreme ray is the intersection of two boundary planes,
    which is what the pairwise crosses enumerate. But when two normals are
    *anti-parallel* their cross vanishes and the feasible set collapses into the plane
    they share -- a linear subspace with no extreme rays at all. A beam housed between two
    parallel faces is exactly this: it can still slide, in any direction in that plane,
    with a margin of exactly zero. For each such pair an orthonormal basis of the shared
    plane is added, so the collapse is reported as the tight fit it is rather than as a
    lock.

    Repeated normals are collapsed first. A duplicate half-space is mathematically
    redundant, and dense models produce a great many of them -- a plate jointed to a
    hundred identical studs sees the same normal a hundred times, which would otherwise
    cost ~5000 pairwise crosses for the two distinct directions actually present. Margins
    are still measured against every original constraint, so this changes the cost and not
    the answer.

    """
    normals = _distinct_normals(normals)
    candidates = []

    interior = Vector(0.0, 0.0, 0.0)
    for normal in normals:
        interior += normal
    if interior.length > TOL:
        candidates.append(interior.unitized())

    for normal in normals:
        candidates.append(normal.unitized())

    count = len(normals)
    for i in range(count):
        for j in range(i + 1, count):
            cross = normals[i].cross(normals[j])
            if cross.length > 1e-6:
                cross.unitize()
                candidates.append(cross)
                candidates.append(-cross)
            elif normals[i].dot(normals[j]) < 0.0:
                candidates.extend(_plane_basis(normals[i]))

    return _dedupe(candidates)


def _plane_basis(normal):
    """Four unit directions spanning the plane perpendicular to `normal`.

    The seed axis is the world axis least aligned with `normal`, chosen by index on ties,
    so the basis is a deterministic function of `normal` alone.

    """
    axes = (Vector(1.0, 0.0, 0.0), Vector(0.0, 1.0, 0.0), Vector(0.0, 0.0, 1.0))
    seed = min(axes, key=lambda axis: (round(abs(normal.dot(axis)), _ROUND), axes.index(axis)))
    first = normal.cross(seed)
    first.unitize()
    second = normal.cross(first)
    second.unitize()
    return [first, -first, second, -second]


def _dedupe(vectors, digits=_ROUND):
    seen = set()
    unique = []
    for vector in vectors:
        key = (round(vector.x, digits), round(vector.y, digits), round(vector.z, digits))
        if key in seen:
            continue
        seen.add(key)
        unique.append(vector)
    return unique


def _distinct_normals(normals):
    """The distinct half-spaces in a constraint set.

    Duplicates are redundant as constraints, and letting them through would also let
    multiplicity sway the interior-seed heuristic -- so an element jointed to twenty
    identical studs would be ranked differently from one jointed to two. Margins are
    always measured against the full set, so this is a canonical view, not an
    approximation of one.

    """
    return _dedupe(list(normals), digits=_NORMAL_DIGITS)


def _margin(direction, normals):
    if not normals:
        return 1.0
    return min(normal.dot(direction) for normal in normals)


def rank_candidates(normals):
    """Candidate directions with their margins, best first.

    Parameters
    ----------
    normals : list of :class:`compas.geometry.Vector`
        Unit inward normals.

    Returns
    -------
    list of tuple
        ``(margin, direction)`` pairs sorted by descending margin.

    Notes
    -----
    Margin decides. Where margins are *exactly* equal -- which happens whenever the cone
    degenerates to a plane or a ray, and the tied directions are then genuinely equally
    good -- three further keys settle it: alignment with the interior seed, then alignment
    with world up, then the rounded components. The world-up term is a gravity-friendly
    preference among directions the geometry cannot distinguish; it is emphatically not
    the earlier behaviour of trying straight up first and returning it if it merely
    passed, which let a marginal vertical answer beat a comfortable one.

    """
    interior = Vector(0.0, 0.0, 0.0)
    for normal in _distinct_normals(normals):
        interior += normal
    if interior.length > TOL:
        interior.unitize()

    scored = []
    for direction in candidate_directions(normals):
        scored.append((_margin(direction, normals), direction))
    scored.sort(
        key=lambda item: (
            -round(item[0], _ROUND),
            -round(interior.dot(item[1]), _ROUND),
            -round(FREE_DIRECTION.dot(item[1]), _ROUND),
            round(item[1].x, _ROUND),
            round(item[1].y, _ROUND),
            round(item[1].z, _ROUND),
        )
    )
    return scored


def solve(constraints, path_check=None):
    """Intersect a set of constraints and return the best extraction direction.

    Parameters
    ----------
    constraints : list of :class:`~assembly_sequencing.constraints.Constraint`
        The constraints from every joint that still has an active partner. An **empty**
        list means the element is entirely free, not that it is locked.
    path_check : callable, optional
        ``f(direction) -> bool``. The swept broad-phase test, already bound to the
        element and the active set by the caller so this function stays pure. Candidates
        are offered to it in descending order of margin, and the first one that clears
        wins.

    Returns
    -------
    :class:`~assembly_sequencing.result.Solution` or :class:`~assembly_sequencing.result.Locked`

    Raises
    ------
    TypeError
        If `constraints` contains an unrecognised type.

    """
    validate_constraints(constraints)
    inferred = count_inferred(constraints)

    axes = [c for c in constraints if isinstance(c, SignedAxis)]
    normals = [c.normal for c in constraints if isinstance(c, HalfSpace)]

    if axes:
        return _solve_one_dof(axes, normals, inferred, path_check)

    if not normals:
        return Solution(FREE_DIRECTION.copy(), 1.0, ROOMY, inferred)

    ranked = rank_candidates(normals)
    if not ranked or ranked[0][0] < -TOL:
        return Locked("no direction satisfies all {} half-space constraints".format(len(normals)), inferred)
    for margin, direction in ranked:
        if margin < -TOL:
            break
        if path_check is None or path_check(direction):
            return Solution(direction, margin, classify(margin), inferred)

    return Locked("every kinematically feasible direction is obstructed along the approach distance", inferred)


def _solve_one_dof(axes, normals, inferred, path_check):
    """Resolve a constraint set containing at least one strict 1-DOF axis.

    The axis is signed: only ``+direction`` is tested, never its reverse. If the one
    permitted direction pushes through material the element is locked, and two
    anti-parallel axes are a genuine deadlock.

    """
    base = axes[0].direction
    for axis in axes[1:]:
        dot = base.dot(axis.direction)
        if dot < 1.0 - PARALLEL_TOL:
            return Locked(
                "conflicting 1-DOF axes (dot = {:.6f}); the element is held to two incompatible sliding directions".format(dot),
                inferred,
            )

    # A strict 1-DOF fit is a slot by definition, so it is never roomy however generous the
    # surrounding half-spaces are. Half-spaces can only make it worse, i.e. locked.
    margin = min(0.0, _margin(base, normals)) if normals else 0.0
    if margin < -TOL:
        return Locked(
            "the single permitted 1-DOF direction pushes through material (margin = {:.6f})".format(margin),
            inferred,
        )

    if path_check is not None and not path_check(base):
        return Locked("the single permitted 1-DOF direction is obstructed along the approach distance", inferred)

    return Solution(base.copy(), margin, TIGHT, inferred)
