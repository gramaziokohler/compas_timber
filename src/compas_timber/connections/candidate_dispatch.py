
from compas_timber.elements import Beam
from compas_timber.elements import Panel
from compas_timber.elements import Plate

from .solver import ConnectionSolver
from .solver import PlateConnectionSolver

# ------------------------------------------------------------------
# element-type dispatch: builds a JointCandidate for an adjacent pair,
# based on the pair's element types.
#
# This module sits above `solver.py` and `joint_candidate.py`: it composes
# solvers, candidate classes, and element types, so it depends on all three
# rather than living inside any one of them.
#
# Handlers register the type pair(s) they support via `@_register`, order-independent
# (both (a, b) and (b, a) pairs match). To support a new type combination (e.g. beam-to-plate),
# add a handler decorated with `@_register(TypeA, TypeB)` once the corresponding
# topology-detection geometry exists.
# ------------------------------------------------------------------

_CONNECTION_HANDLERS = {
    frozenset((Beam, Beam)): ConnectionSolver,
    frozenset((Plate, Plate)): PlateConnectionSolver,
    frozenset((Panel, Panel)): PlateConnectionSolver,
}


def find_connection_handler(element_a, element_b):
    """Returns the registered handler for the given pair's element types, or ``None`` if unsupported."""
    key = frozenset((type(element_a), type(element_b)))
    return _CONNECTION_HANDLERS.get(key, None)


def get_connection_candidate(element_a, element_b, max_distance):
    """Builds the joint candidate for a pair of adjacent elements, or ``None`` if their type combination is unsupported or their topology is unknown."""
    handler_type = find_connection_handler(element_a, element_b)
    if handler_type is None:
        return None
    handler = handler_type()
    return handler.create_joint_candidate(element_a, element_b, max_distance)
