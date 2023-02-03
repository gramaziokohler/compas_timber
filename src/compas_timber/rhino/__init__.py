import Rhino
from compas.plugins import plugin



@plugin(category="solvers", requires=["Rhino"])
def find_neighboring_beams(beams):
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
        pair = set((beams[searched_id], beams[found_id]))
        if searched_id != found_id and pair not in neighbors:
            neighbors.append(pair)

    rtree = Rhino.Geometry.RTree()
    bboxes = []
    for index, beam in enumerate(beams):
        bb = Rhino.Geometry.BoundingBox(*beam.aabb)
        bboxes.append(bb)
        rtree.Insert(bb, index)

    for index, bb in enumerate(bboxes):
        rtree.Search(bb, found_handler, index)

    return neighbors


__all__ = [
    "find_neighboring_beams",
]
