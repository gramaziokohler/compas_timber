"""Kinematic constraint types.

A constraint describes the freedom a single joint leaves to a single moving element,
assuming every other member of that joint is frozen. Constraints are consumed by
:mod:`assembly_sequencing.solver`, which intersects them.

Two types cover the whole vocabulary:

* :class:`HalfSpace` -- the moving element may travel anywhere in the half-space
  ``n . d >= 0``. Butt joints, laps and pockets produce these.
* :class:`SignedAxis` -- the moving element may travel along exactly one direction.
  Mortise-tenons, dovetails and seat cuts produce these.

Unknown constraint objects are rejected rather than ignored: a dropped constraint makes
an element look *more* free than it is, which is the dangerous direction to fail in.

"""

from compas.geometry import Vector

TOL = 1e-9
"""float: Numeric zero. Dot products within this of zero are treated as exactly zero."""

_DEGENERATE_LENGTH = 1e-12


class Constraint(object):
    """Base class for kinematic constraints.

    Attributes
    ----------
    inferred : bool
        True when the constraint did not come from a joint-specific implementation but
        from a permissive generic fallback. Inferred constraints are counted and
        surfaced in results so a caller can tell "computed" from "nobody implemented
        this joint yet".

    """

    inferred = False

    def allows(self, direction):
        """Whether `direction` satisfies this constraint.

        Parameters
        ----------
        direction : :class:`compas.geometry.Vector`
            A unit direction.

        Returns
        -------
        bool

        """
        raise NotImplementedError


class HalfSpace(Constraint):
    """A 3-DOF constraint: the moving element may travel anywhere in ``normal . d >= 0``.

    Parameters
    ----------
    normal : :class:`compas.geometry.Vector` or tuple of float
        The inward normal of the permitted half-space. Unitized on construction.
    inferred : bool, optional
        See :class:`Constraint`.

    """

    def __init__(self, normal, inferred=False):
        vector = Vector(*normal)
        if vector.length < _DEGENERATE_LENGTH:
            raise ValueError("HalfSpace normal is degenerate (zero length).")
        vector.unitize()
        self.normal = vector
        self.inferred = bool(inferred)

    def allows(self, direction):
        return self.normal.dot(direction) >= -TOL

    def margin(self, direction):
        """Signed clearance of `direction` against this half-space.

        Parameters
        ----------
        direction : :class:`compas.geometry.Vector`
            A unit direction.

        Returns
        -------
        float
            The sine of the angle by which `direction` clears the half-space boundary.
            Negative means the direction pushes through material.

        """
        return self.normal.dot(direction)

    def __repr__(self):
        return "HalfSpace({:.4f}, {:.4f}, {:.4f}{})".format(self.normal.x, self.normal.y, self.normal.z, ", inferred" if self.inferred else "")


class SignedAxis(Constraint):
    """A 1-DOF constraint: the moving element may travel along exactly one direction.

    **Signed, not bidirectional.** ``direction`` is the one permitted extraction
    direction; ``-direction`` pushes deeper into the joint. If the permitted direction
    pushes through other material the element is locked -- testing the reverse would be
    a bug, and two anti-parallel axes are a genuine deadlock rather than a sign mistake.

    Parameters
    ----------
    direction : :class:`compas.geometry.Vector` or tuple of float
        The single permitted extraction direction. Unitized on construction.
    origin : :class:`compas.geometry.Point`, optional
        The point the axis passes through. Carried for callers that want to draw the
        axis; **the solver never reads it**, because the constraint is on direction
        alone.
    inferred : bool, optional
        See :class:`Constraint`.

    """

    def __init__(self, direction, origin=None, inferred=False):
        vector = Vector(*direction)
        if vector.length < _DEGENERATE_LENGTH:
            raise ValueError("SignedAxis direction is degenerate (zero length).")
        vector.unitize()
        self.direction = vector
        self.origin = origin
        self.inferred = bool(inferred)

    @classmethod
    def from_line(cls, line, inferred=False):
        """Build a signed axis from a line, oriented ``start`` -> ``end``.

        Parameters
        ----------
        line : :class:`compas.geometry.Line`
            The line. Its direction is the permitted extraction direction; its start
            point is kept as :attr:`origin` and otherwise unused.
        inferred : bool, optional
            See :class:`Constraint`.

        Returns
        -------
        :class:`SignedAxis`

        """
        return cls(line.direction, origin=line.start, inferred=inferred)

    def allows(self, direction):
        return self.direction.dot(direction) >= 1.0 - TOL

    def __repr__(self):
        return "SignedAxis({:.4f}, {:.4f}, {:.4f}{})".format(self.direction.x, self.direction.y, self.direction.z, ", inferred" if self.inferred else "")


def validate_constraints(constraints):
    """Check that every item is a known :class:`Constraint`.

    Parameters
    ----------
    constraints : list
        The constraints to validate.

    Returns
    -------
    list of :class:`Constraint`
        The same list, unchanged.

    Raises
    ------
    TypeError
        If any item is not a :class:`Constraint`. Unknown types are never dropped
        silently -- see the module docstring.

    """
    for constraint in constraints:
        if not isinstance(constraint, Constraint):
            raise TypeError(
                "Unknown kinematic constraint type {!r}. Expected HalfSpace or SignedAxis. "
                "Unknown constraints are rejected rather than ignored, because dropping one "
                "makes an element look more free than it is.".format(type(constraint).__name__)
            )
    return list(constraints)


def count_inferred(constraints):
    """Number of constraints that came from a permissive generic fallback.

    Parameters
    ----------
    constraints : list of :class:`Constraint`

    Returns
    -------
    int

    """
    return sum(1 for constraint in constraints if constraint.inferred)
