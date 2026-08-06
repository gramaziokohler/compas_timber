from .joint_candidate import JointCandidate
from .solver import JointTopology
from .solver import ConnectionSolver
from .solver import PlateConnectionSolver
from compas_timber.elements import Beam
from compas_timber.elements import Plate
from compas_timber.elements import Panel

# Element-type dispatch: which solver knows how to analyze a given pair of element types.
# Keyed by a frozenset of the two types, so lookup is order-independent: both (a, b) and (b, a) match.
#
# `TopologyData` (via its guid-keyed `element_topo_data`) already represents any pair of element types
# uniformly, including mixed pairs (e.g. beam-to-plate), so supporting a new combination only requires
# a solver that can actually detect that pair's topology. Add it below once one exists.
_SOLVERS = {
    frozenset((Beam, Beam)): ConnectionSolver,
    frozenset((Plate, Plate)): PlateConnectionSolver,
    frozenset((Panel, Panel)): PlateConnectionSolver,
}


def find_solver_for(element_a, element_b):
    """Returns the solver type registered for the given pair's element types, or ``None`` if unsupported.

    Parameters
    ----------
    element_a : :class:`~compas_model.elements.Element`
        The first element.
    element_b : :class:`~compas_model.elements.Element`
        The second element.

    Returns
    -------
    type[:class:`~compas_timber.connections.ConnectionSolver`] or None
        The solver class for this type combination, or ``None`` if the combination is unsupported.

    """
    return _SOLVERS.get(frozenset((type(element_a), type(element_b))))


def get_distance(element_a, element_b):
    """Builds the joint candidate for a pair of adjacent elements, or ``None`` if their type combination is unsupported or their topology is unknown.

    Parameters
    ----------
    element_a : :class:`~compas_model.elements.Element`
        The first element.
    element_b : :class:`~compas_model.elements.Element`
        The second element.
    max_distance : float
        The maximum distance between the elements to consider them connected.

    Returns
    -------
    :class:`~compas_timber.connections.JointCandidate` or None
        The candidate connecting the two elements, or ``None`` if none could be determined.

    """
    solver_type = find_solver_for(element_a, element_b)
    if solver_type is None:
        return None
    return solver_type().get_distance(element_a, element_b)

def get_location(element_a, element_b, max_distance, angle_tol):
    """Builds the joint candidate for a pair of adjacent elements, or ``None`` if their type combination is unsupported or their topology is unknown.

    Parameters
    ----------
    element_a : :class:`~compas_model.elements.Element`
        The first element.
    element_b : :class:`~compas_model.elements.Element`
        The second element.
    max_distance : float
        The maximum distance between the elements to consider them connected.

    Returns
    -------
    :class:`~compas_timber.connections.JointCandidate` or None
        The candidate connecting the two elements, or ``None`` if none could be determined.

    """
    solver_type = find_solver_for(element_a, element_b)
    if solver_type is None:
        return None
    return solver_type().get_location(element_a, element_b, max_distance, angle_tol)

def get_topology_data(element_a, element_b, max_distance, angle_tol):
    """Builds the topology data for a pair of adjacent elements, or ``None`` if their type combination is unsupported or their topology is unknown.

    Parameters
    ----------
    element_a : :class:`~compas_model.elements.Element`
        The first element.
    element_b : :class:`~compas_model.elements.Element`
        The second element.
    max_distance : float
        The maximum distance between the elements to consider them connected.

    Returns
    -------
    :class:`~compas_timber.connections.TopologyData` or None
        The topology data for the two elements, or ``None`` if none could be determined.

    """
    solver_type = find_solver_for(element_a, element_b)
    if solver_type is None:
        return None
    return solver_type().find_topology(element_a, element_b, max_distance)

def get_connection_candidate(element_a, element_b, max_distance):
    """Builds the joint candidate for a pair of adjacent elements, or ``None`` if their type combination is unsupported or their topology is unknown.

    Parameters
    ----------
    element_a : :class:`~compas_model.elements.Element`
        The first element.
    element_b : :class:`~compas_model.elements.Element`
        The second element.
    max_distance : float
        The maximum distance between the elements to consider them connected.

    Returns
    -------
    :class:`~compas_timber.connections.JointCandidate` or None
        The candidate connecting the two elements, or ``None`` if none could be determined.

    """
    solver_type = find_solver_for(element_a, element_b)
    if solver_type is None:
        return None

    topology_data = solver_type().solve(element_a, element_b, max_distance)
    if topology_data.topology == JointTopology.TOPO_UNKNOWN:
        return None

    # order the elements by their solver-assigned roles, so that e.g. main precedes cross
    elements_by_guid = {str(element_a.guid): element_a, str(element_b.guid): element_b}
    ordered_elements = [elements_by_guid[guid] for guid in topology_data.ordered_guids()]
    return JointCandidate(*ordered_elements, topology_data=topology_data)
