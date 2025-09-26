from .slab import Slab
from compas.geometry import Frame
from compas.geometry import Polyline

class Wall(object):
    """Represents a single timber wall element.
    Serves as container for beams joints and other related elements and groups them together to form a wall.

    Wall is often a single unit of prefabricated timber wall element.
    It is often refered to as an enveloping body.

    TODO: complete this docstring

    """

    @property
    def __data__(self):
        data = super(Wall, self).__data__
        data["outline"] = self.outline
        data["openings"] = self.openings
        data["thickness"] = self.thickness
        data["attributes"] = self.attributes
        return data

    def __init__(self, outline, thickness, openings=None, frame=None, name=None, **kwargs):
        self.outline = outline
        self.thickness = thickness
        self.openings = openings or []
        self.attributes = {}
        self.attributes.update(kwargs)

        self._faces = None
        self._corners = None

        if not outline.is_closed:
            raise ValueError("Outline is not closed.")
        if len(self.outline) != 5:
            raise ValueError("Wall outline must have 4 segments.")

    def __repr__(self):
        return "Wall(name={}, {}, {}, {:.3f})".format(self.name, self.frame, self.outline, self.thickness)

    @property
    def is_wall(self):
        return True

    @classmethod
    def from_boundary(cls, polyline, normal, thickness, openings=None, **kwargs):
        """Use this to make sure the polyline is oriented correctly."""
        oriented_polyline = _oriented_polyline(polyline, normal)
        openings = openings or []
        for opening in openings:
            opening.orient_polyline(normal)
        wall_frame = cls._frame_from_polyline(oriented_polyline, normal)
        return cls(oriented_polyline, thickness, openings, wall_frame, **kwargs)

    @staticmethod
    def _frame_from_polyline(polyline, normal):
        points = polyline.points
        xaxis = points[1] - points[0]
        xaxis.unitize()
        yaxis = normal.cross(xaxis)
        return Frame(points[0], xaxis, yaxis)

def _oriented_polyline(polyline, normal):
    # returns a polyline that is oriented consistently ccw around the normal
    # ^  3 ---- 2
    # |  |      |
    # z  0 ---- 1
    #    x -->
    sorted_points = sorted(polyline.points[:4], key=lambda pt: pt.z)
    bottom_points = sorted_points[:2]
    top_points = sorted_points[2:]

    # Ensure counterclockwise order
    if normal.cross(bottom_points[1] - bottom_points[0]).z < 0:
        bottom_points.reverse()

    if normal.cross(top_points[1] - top_points[0]).z > 0:
        top_points.reverse()

    return Polyline(bottom_points + top_points + [bottom_points[0]])
