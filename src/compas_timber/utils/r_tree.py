from rtree.index import Index
from rtree.index import Property
from compas.plugins import plugin


@plugin(category="solvers", requires=["rtree"])
def find_neighboring_beams(beams, inflate_by=None):
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
    for index, beam in enumerate(beams):
        bbox = beam.aabb
        if inflate_by is not None:
            bbox = _inflate_bbox(bbox, inflate_by)
        b_boxes.append(bbox)
        r_tree.insert(index, bbox)

    neighbors = []
    for index, bbox in enumerate(b_boxes):
        for found_index in r_tree.intersection(bbox):
            pair = {beams[index], beams[found_index]}
            if found_index != index and pair not in neighbors:
                neighbors.append(pair)

    return neighbors

def _inflate_bbox(bbox, d):
    x1, y1, z1, x2, y2, z2 = bbox
    return (x1 - d, y1 - d, z1 - d, x2 + d, y2 + d, z2 + d)
