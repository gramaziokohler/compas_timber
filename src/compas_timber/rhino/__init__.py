import Rhino
from compas.plugins import plugin


@plugin(category="solvers", requires=["Rhino"])
def find_neighboring_beams(beams, max_distance=None):
    """Uses the Rhino.Geometry.RTree implementation of RTree to find neighboring beams.

    Parameters
    ----------
    beams : list(:class:`~compas_timber.parts.Beam`)


    Returns
    -------
    list(set(:class:`compas_timber.parts.Beam`))
        List containing sets or neightboring pairs beams.

    """
    neighbors = []

    def found_handler(sender, e_args):
        """Called for each found item"""
        searched_id = e_args.Tag
        found_id = e_args.Id

        # eliminate duplicates (1, 2) == (2, 1)
        pair = {beams[searched_id], beams[found_id]}
        if searched_id != found_id and pair not in neighbors:
            neighbors.append(pair)

    rtree = Rhino.Geometry.RTree()
    bboxes = []

    d = max_distance or 0.0
    d *= 0.5
    for index, beam in enumerate(beams):
        # TODO: this is a simple way of adding padding to bounding box. Could instead create a beam box with padding and then aabb from it.
        x1, y1, z1, x2, y2, z2 = beam.aabb
        aabb_with_padding = [x1 - d, y1 - d, z1 - d, x2 + d, y2 + d, z2 + d]
        bb = Rhino.Geometry.BoundingBox(*aabb_with_padding)
        bboxes.append(bb)
        rtree.Insert(bb, index)

    for index, bb in enumerate(bboxes):
        rtree.Search(bb, found_handler, index)

    return neighbors


__all__ = [
    "find_neighboring_beams",
]
