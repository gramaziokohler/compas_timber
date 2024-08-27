from compas.plugins import plugin
from compas.geometry import Plane
from compas.geometry import Frame
from compas.geometry import Box
from compas.geometry import bounding_box


@plugin(category="solvers", requires=["Rhino"])
def find_neighboring_beams(beams, inflate_by=0.0):
    """Uses the Rhino.Geometry.RTree implementation of RTree to find neighboring beams.

    Parameters
    ----------
    beams : list(:class:`~compas_timber.parts.Beam`)
        The collection of beams to check.
    inflate_by : float
        If set, inflate bounding boxes by this amount in all directions prior to adding to the RTree.

    Returns
    -------
    list(set(:class:`compas_timber.parts.Beam`))
        List containing sets or neightboring pairs beams.

    """
    import Rhino

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
    for index, beam in enumerate(beams):
        aabb = beam.compute_aabb(inflate_by)
        bb = Rhino.Geometry.BoundingBox(aabb.xmin, aabb.ymin, aabb.zmin, aabb.xmax, aabb.ymax, aabb.zmax)
        bboxes.append(bb)
        rtree.Insert(bb, index)

    for index, bb in enumerate(bboxes):
        rtree.Search(bb, found_handler, index)

    return neighbors


def filter_neightboring_elements(line, elements, inflate_line_factor):
    import Rhino

    neighbors = []

    def found_handler(sender, e_args):
        """Called for each found item"""
        searched_id = e_args.Tag
        found_id = e_args.Id

        # eliminate duplicates (1, 2) == (2, 1)
        if searched_id != found_id and elements[searched_id] not in neighbors:
            neighbors.append(elements[found_id])

    plane = Plane(line.start, line.vector)
    frame = Frame.from_plane(plane)
    frame.point += frame.zaxis * line.length * 0.5
    line_box = Box(inflate_line_factor, inflate_line_factor, line.length, frame)

    rtree = Rhino.Geometry.RTree()
    bboxes = []
    for index, beam in enumerate(elements):
        aabb = beam.compute_aabb()
        bb = Rhino.Geometry.BoundingBox(aabb.xmin, aabb.ymin, aabb.zmin, aabb.xmax, aabb.ymax, aabb.zmax)
        bboxes.append(bb)
        rtree.Insert(bb, index)
    bb_line = Rhino.Geometry.BoundingBox(
        line_box.xmin, line_box.ymin, line_box.zmin, line_box.xmax, line_box.ymax, line_box.zmax
    )
    rtree.Insert(bb_line, index)
    # here just search for the id of the line bbox
    for index, bb in enumerate(bboxes):
        rtree.Search(bb, found_handler, index)

    return neighbors


__all__ = [
    "find_neighboring_beams",
]
