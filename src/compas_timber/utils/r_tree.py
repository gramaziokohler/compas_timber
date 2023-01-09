
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
        #p.variant = "RT_Star"
        p.dimension = 3

        rt = rtree.index.Index(properties=p, interleaved=True)


        for i,bb in enumerate(object_boundingboxes):
            rt.insert(i,bb)

        return rt

    def find_intersections(myrtree, search_boundingbox):
        """
        search_boundingbox: a bounding box as a 6-tuple (minX, minY, minZ, maxX, maxY, maxZ) (interleaved=True)
        """
        return list(myrtree.intersection(search_boundingbox, objects=False))

    rt = create_rtree(object_boundingboxes)
    results = [[bi for bi in find_intersections(rt, bb) if bi!=bb] for bb in object_boundingboxes]
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
        e.SearchBoundingBox = data.SearchBB #why needed?
        data.Found.append(e.Id)


    def RunSearch(rtree, searchbb):
        data = SearchData(searchbb)
        if rtree.Search(data.SearchBB, SearchCallback, data):
            return data.Found

    RT = rg.RTree()
    for i,bb in enumerate(object_boundingboxes): RT.Insert(bb, i)
    results = [RunSearch(RT, bb) for bb in object_boundingboxes]
    return results

### helper methods

def getBB_fromBeam(beam):
    """
    find an axis-aligned bounding box of a beam
    """

    from compas.geometry import Point
    from compas.geometry import Frame
    from compas.geometry import Box 

    boundingbox = None
    if beam.width and beam.height and beam.length and beam.frame:
        box = beam.shape
        #TODO: find axis-aligned bounding box for beam's box shape
    else:
        shape = beam.centerline
        #TODO: find axis-aligned bounding box for beam's centerline
    return boundingbox