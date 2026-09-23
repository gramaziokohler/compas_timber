from compas.tolerance import TOL

from compas_timber.elements import Beam
from compas_timber.elements import Panel
from compas_timber.elements import Plate

from .joint_candidate import JointCandidate
from .joint_candidate import PlateJointCandidate
from .solver import ConnectionSolver
from .solver import JointTopology
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

_CONNECTION_HANDLERS = {}


def _register(type_a, type_b):
    """Registers the decorated function as the connection-candidate handler for the given pair of element types."""

    def decorator(handler):
        _CONNECTION_HANDLERS[frozenset((type_a, type_b))] = handler
        return handler

    return decorator


@_register(Beam, Beam)
def _beam_connection_candidate(beam_a, beam_b, max_distance):
    """Builds a :class:`~compas_timber.connections.JointCandidate` for a pair of adjacent beams, or ``None`` if their topology is unknown."""
    result = ConnectionSolver().find_topology(beam_a, beam_b, max_distance=max_distance)
    if result.topology == JointTopology.TOPO_UNKNOWN:
        return None
    # use the beam order determined by find_topology to keep main, cross relationship
    return JointCandidate(result.beam_a, result.beam_b, topology=result.topology, distance=result.distance, location=result.location)


@_register(Plate, Plate)
@_register(Panel, Panel)
def _plate_connection_candidate(element_a, element_b, max_distance):
    """Builds a :class:`~compas_timber.connections.PlateJointCandidate` for a pair of adjacent plates/panels, or ``None`` if their topology is unknown."""
    result = PlateConnectionSolver().find_topology(element_a, element_b, tol=TOL.relative, max_distance=max_distance)
    if result.topology is JointTopology.TOPO_UNKNOWN:
        return None
    kwargs = {"topology": result.topology, "a_segment_index": result.a_segment_index, "distance": result.distance, "location": result.location}
    if result.topology == JointTopology.TOPO_EDGE_EDGE:
        kwargs["b_segment_index"] = result.b_segment_index
    return PlateJointCandidate(result.plate_a, result.plate_b, **kwargs)


def find_connection_handler(element_a, element_b):
    """Returns the registered handler for the given pair's element types, or ``None`` if unsupported."""
    key = frozenset((type(element_a), type(element_b)))
    return _CONNECTION_HANDLERS.get(key, None)


def get_connection_candidate(element_a, element_b, max_distance):
    """Builds the joint candidate for a pair of adjacent elements, or ``None`` if their type combination is unsupported or their topology is unknown."""
    handler = find_connection_handler(element_a, element_b)
    if handler is None:
        return None
    return handler(element_a, element_b, max_distance)
