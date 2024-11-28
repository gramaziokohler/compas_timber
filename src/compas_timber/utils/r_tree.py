from compas.plugins import plugin
from rtree.index import Index
from rtree.index import Property


@plugin(category="solvers", requires=["rtree"])
def find_neighboring_elements(elements, inflate_by=0.0):
    """Uses RTree implementation from the CPython `rtree` library: https://pypi.org/project/Rtree/.

    Returns a list of sets. Each set contains a pair of neighboring beams.
    The beams are returned as sets as the order within each pair of beams doesn't matter.
    That way there are no duplicates i.e. (beam_a, beam_b) == (beam_b, beam_a).

    Parameters
    ----------
    beams : list(:class:`~compas_timber.parts.Beam`)
        The collection of beams to check.
    inflate_by : float
        If set, inflate bounding boxes by this amount in all directions prior to adding to the RTree.

    Returns
    -------
    list(set(:class:`~compas_timber.parts.Beam`, :class:`~compas_timber.parts.Beam`))
        List containing sets of two neightboring beams each.

    """
    # insert and search three dimensional data (bounding boxes).
    p = Property(dimension=3)
    r_tree = Index(properties=p, interleaved=True)  # interleaved => x_min, y_min, z_min, x_max, y_max, z_max
    b_boxes = []
    for index, beam in enumerate(elements):
        aabb = beam.compute_aabb(inflate_by)
        bbox = (aabb.xmin, aabb.ymin, aabb.zmin, aabb.xmax, aabb.ymax, aabb.zmax)
        b_boxes.append(bbox)
        r_tree.insert(index, bbox)

    neighbors = []
    for index, bbox in enumerate(b_boxes):
        for found_index in r_tree.intersection(bbox):
            pair = {elements[index], elements[found_index]}
            if found_index != index and pair not in neighbors:
                neighbors.append(pair)

    return neighbors
