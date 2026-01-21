from compas_timber.connections.analyzers import Cluster
from compas_timber.connections.analyzers import JointTopology
from compas_timber.elements.beam import Beam


def parse_cross_beam_and_main_beams_from_cluster(cluster: Cluster) -> tuple[set[Beam], set[Beam]]:
    """
    Parses cross beams and main beams from a cluster of joints.

    Parameters
    ----------
    cluster : :class:`~compas_timber.connections.analyzers.Cluster`
        The cluster of joints to parse.

    Returns
    -------
    set[:class:`~compas_timber.elements.beam.Beam`], set[:class:`~compas_timber.elements.beam.Beam`]
        Two sets containing the cross beams and main beams respectively.
    """
    cross_beams = []
    main_beams = []
    for candidate in cluster.joints:
        if candidate.topology == JointTopology.TOPO_L:
            main_beams.extend(candidate.elements)
        elif candidate.topology == JointTopology.TOPO_T:
            main_beams.append(candidate.elements[0])
            cross_beams.append(candidate.elements[1])
        elif candidate.topology == JointTopology.TOPO_X:
            cross_beams.extend(candidate.elements)
    return set(cross_beams), set(main_beams)
