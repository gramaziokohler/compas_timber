from compas.tolerance import TOL

from compas_timber.elements import Beam
from compas_timber.elements import Panel
from compas_timber.elements import Plate

from .joint_candidate import JointCandidate
from .solver import ConnectionSolver
from .solver import JointTopology
from .solver import PlateConnectionSolver

# ------------------------------------------------------------------
# element-type dispatch: picks the connection solver for an adjacent pair,
# based on the pair's element types, and builds a JointCandidate from its result.
#
# This module sits above `solver.py` and `joint_candidate.py`: it composes
# solvers, candidate classes, and element types, so it depends on all three
# rather than living inside any one of them.
#
# Solvers are registered per type pair via `_register`, order-independent
# (both (a, b) and (b, a) pairs match). To support a new type combination (e.g. beam-to-plate),
# register the solver that implements `find_topology` and `update_location` for that pair.
# Since the result is always a `TopologyInfo`, `JointCandidate` itself needs no changes.
# ------------------------------------------------------------------

_CONNECTION_SOLVERS = {}


def _register(type_a, type_b, solver_cls, **find_topology_kwargs):
    """Registers `solver_cls` as the connection solver for the given pair of element types.

    `find_topology_kwargs` are passed to every `solver_cls().find_topology()` call made for this pair.

    """
    _CONNECTION_SOLVERS[frozenset((type_a, type_b))] = (solver_cls, find_topology_kwargs)


_register(Beam, Beam, ConnectionSolver)
_register(Plate, Plate, PlateConnectionSolver, tol=TOL.relative)
_register(Panel, Panel, PlateConnectionSolver, tol=TOL.relative)


def _find_solver_entry(element_a, element_b):
    return _CONNECTION_SOLVERS.get(frozenset((type(element_a), type(element_b))), None)


def find_connection_solver(element_a, element_b):
    """Returns an instance of the connection solver registered for the given pair's element types, or ``None`` if unsupported."""
    entry = _find_solver_entry(element_a, element_b)
    if entry is None:
        return None
    solver_cls, _ = entry
    return solver_cls()


def solve_topology(element_a, element_b, max_distance=None):
    """Solves the connection topology of a pair of elements with the solver registered for their types.

    Parameters
    ----------
    element_a : :class:`~compas_model.elements.Element`
        First element of the pair.
    element_b : :class:`~compas_model.elements.Element`
        Second element of the pair.
    max_distance : float, optional
        Maximum distance at which the elements are considered connected. Passed to the solver as is, ``None``
        lets the solver choose (e.g. `PlateConnectionSolver` then uses the plates' thickness).

    Returns
    -------
    :class:`~compas_timber.connections.TopologyInfo` | None
        The solver's result, or ``None`` if the pair's type combination is unsupported.

    """
    entry = _find_solver_entry(element_a, element_b)
    if entry is None:
        return None
    solver_cls, find_topology_kwargs = entry
    return solver_cls().find_topology(element_a, element_b, max_distance=max_distance, **find_topology_kwargs)


def get_connection_candidate(element_a, element_b, max_distance):
    """Builds the joint candidate for a pair of adjacent elements, or ``None`` if their type combination is unsupported or their topology is unknown.

    The elements of the candidate are ordered by their role in the connection (main/edge first, cross/face second).

    """
    topology_info = solve_topology(element_a, element_b, max_distance=max_distance)
    if topology_info is None or topology_info.topology == JointTopology.TOPO_UNKNOWN:
        return None
    first, second = topology_info.get_element_by_role(element_a, element_b)
    return JointCandidate(first, second, topology_info=topology_info)
