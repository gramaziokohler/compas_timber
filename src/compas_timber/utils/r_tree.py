from rtree.index import Index
from rtree.index import Property
from compas.plugins import plugin


@plugin(category="solvers", requires=["rtree"])
def find_neighboring_beams(beams):
    """Uses RTree implementation from the CPython `rtree` library: https://pypi.org/project/Rtree/.

    Parameters
    ----------
    beams : list(:class:`~compas_timber.parts.Beam`)


    Returns
    -------
    list(set(:class:`compas_timber.parts.Beam`))
        List containing sets or neightboring pairs beams.

    """
    p = Property()
    p.dimension = 3
    r_tree = Index(properties=p, interleaved=True)

    for index, beam in enumerate(beams):
        r_tree.insert(index, beam.aabb)

    neighbors = []
    for index, beam in enumerate(beams):
        for found_index in r_tree.intersection(beam.aabb):
            pair = {beams[index], beams[found_index]}
            if found_index != index and pair not in neighbors:
                neighbors.append(pair)

    return neighbors
