from compas.plugins import plugin
from rtree.index import Index
from rtree.index import Property


@plugin(category="solvers", requires=["rtree"])
def find_neighboring_beams(beams, max_distance=None):
    """Uses RTree implementation from the CPython `rtree` library: https://pypi.org/project/Rtree/.

    Returns a list of sets. Each set contains a pair of neighboring beams.
    The beams are returned as sets as the order within each pair of beams doesn't matter.
    That way there are no duplicates i.e. (beam_a, beam_b) == (beam_b, beam_a).

    Parameters
    ----------
    beams : list(:class:`~compas_timber.parts.Beam`)

    Returns
    -------
    list(set(:class:`~compas_timber.parts.Beam`, :class:`~compas_timber.parts.Beam`))
        List containing sets of two neightboring beams each.

    """
    # insert and search three dimensional data (bounding boxes).
    p = Property(dimension=3)
    r_tree = Index(properties=p, interleaved=True)  # interleaved => x_min, y_min, z_min, x_max, y_max, z_max

    d = max_distance or 0.0
    d *= 0.5
    for index, beam in enumerate(beams):
        x1, y1, z1, x2, y2, z2 = beam.aabb
        aabb_with_padding = [x1 - d, y1 - d, z1 - d, x2 + d, y2 + d, z2 + d]
        r_tree.insert(index, aabb_with_padding)

    neighbors = []
    for index, beam in enumerate(beams):
        for found_index in r_tree.intersection(beam.aabb):
            pair = {beams[index], beams[found_index]}
            if found_index != index and pair not in neighbors:
                neighbors.append(pair)

    return neighbors
