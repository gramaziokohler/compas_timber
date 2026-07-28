from compas.tolerance import TOL

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
# `TopologyData` (via its guid-keyed `element_topo_data` of `BeamTopologyData`/`PlateTopologyData`)
# already represents any pair of element types uniformly (including mixed pairs, e.g. beam-to-plate),
# so registering a new type combination here only requires a solver that can actually detect that
# pair's topology; add it to `_CONNECTION_HANDLERS` below, keyed by a frozenset of the two element
# types (order-independent: both (a, b) and (b, a) pairs match).
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
