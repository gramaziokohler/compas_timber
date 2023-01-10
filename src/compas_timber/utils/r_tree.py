def find_neighbours_using_rtree_cpython(object_boundingboxes):
    """
    cpython version using rtree
    https://pypi.org/project/Rtree/

    object_boundingboxes: list of a bounding boxes as a 6-tuples (minX, minY, minZ, maxX, maxY, maxZ) (interleaved=True)
    returns: for each input object, indices of bounding boxes that intersect with it

    """
    import rtree

    def create_rtree(object_boundingboxes):
        """
        objects: a list of bounding boxes as a 6-tuple (minX, minY, minZ, maxX, maxY, maxZ) (interleaved=True)

        """
        p = rtree.index.Property()
        # p.variant = "RT_Star"
        p.dimension = 3
        rt = rtree.index.Index(properties=p, interleaved=True)
        for i, bb in enumerate(object_boundingboxes):
            rt.insert(i, bb)
        return rt

    def find_intersections(myrtree, search_boundingbox):
        """
        search_boundingbox: a bounding box as a 6-tuple (minX, minY, minZ, maxX, maxY, maxZ) (interleaved=True)
        """
        return list(myrtree.intersection(search_boundingbox, objects=False))

    rt = create_rtree(object_boundingboxes)
    results = [[j for j in find_intersections(rt, bb) if j != i] for i, bb in enumerate(object_boundingboxes)]
    return results


def find_neighbours_using_rtree_rhino(object_boundingboxes):

    """
    Rhino version using Rhino.Geometry.RTree
    object_boundingboxes: list of Rhino.Geometry.BoundingBox objects
    returns: for each input object, indices of bounding boxes that intersect with it
    """
    import Rhino.Geometry as rg

    class SearchData:
        def __init__(self, searchboundingbox):
            self.Found = []
            self.SearchBB = searchboundingbox

    def SearchCallback(sender, e):
        data = e.Tag
        e.SearchBoundingBox = data.SearchBB  # why needed?
        data.Found.append(e.Id)

    def RunSearch(rtree, searchbb):
        data = SearchData(searchbb)
        if rtree.Search(data.SearchBB, SearchCallback, data):
            return data.Found

    RT = rg.RTree()
    for i, bb in enumerate(object_boundingboxes):
        RT.Insert(bb, i)
    results = [[j for j in RunSearch(RT, bb) if j != i] for i, bb in enumerate(object_boundingboxes)]
    return results


### helper methods


def getAABB_minmax_fromBeam(beam):
    """
    find an axis-aligned bounding box of a beam
    """
    from compas.geometry import Box, Frame, Point

    def bbox_from_points(points):
        x, y, z = zip(*points)
        min_x = min(x)
        max_x = max(x)
        min_y = min(y)
        max_y = max(y)
        min_z = min(z)
        max_z = max(z)
        # return [[min_x, min_y, min_z],[max_x,max_y, max_z]]
        return [min_x, min_y, min_z, max_x, max_y, max_z]

    if beam.width and beam.height and beam.length and beam.frame:
        box = beam.shape
        pts = box.points
    else:
        line = beam.centerline
        pts = [line[0], line[1]]
    return bbox_from_points(pts)


def getBB_fromBeam(beam):
    """
    find an axis-aligned bounding box of a beam
    """
    from compas.geometry import Box, Frame, Point

    def bbox_from_points(points):
        x, y, z = zip(*points)
        min_x = min(x)
        max_x = max(x)
        min_y = min(y)
        max_y = max(y)
        min_z = min(z)
        max_z = max(z)
        x = abs(max_x - min_x)
        y = abs(max_y - min_y)
        z = abs(max_z - min_z)
        origin = Point(min_x + x / 2, min_y + y / 2, min_z + z / 2)
        frame = Frame(origin, [1, 0, 0], [0, 1, 0])
        return Box(frame, x, y, z)

    if beam.width and beam.height and beam.length and beam.frame:
        box = beam.shape
        bb = bbox_from_points(box.points)
    else:
        line = beam.centerline
        bb = bbox_from_points(*line)
    return bb


if __name__ == "__main__":
    bb = [[0, 0, 0, 1, 1, 1], [2, 2, 2, 3, 3, 3], [-1, -1, -1, 1, 1, 1]]
    results = find_neighbours_using_rtree_cpython(bb)
    for i, r in enumerate(results):
        print("{} contains: {}".format(i, r))
