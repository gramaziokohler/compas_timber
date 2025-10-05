from compas.geometry import Point
from compas.geometry import Polyline
from compas_model.elements import Element

from .plate_geometry import PlateGeometry


class SlabType(object):
    WALL = "wall"
    FLOOR = "floor"
    ROOF = "roof"
    GENERIC = "generic"


class Slab(PlateGeometry, Element):
    """Represents a single timber wall element.
    Serves as container for beams joints and other related elements and groups them together to form a wall.

    Wall is often a single unit of prefabricated timber wall element.
    It is often refered to as an enveloping body.

    TODO: complete this docstring

    """

    @property
    def __data__(self):
        data = Element.__data__(self)
        data.update(PlateGeometry.__data__(self))
        data["name"] = self.name
        data["interfaces"] = self.interfaces
        data["attributes"] = self.attributes
        return data

    def __init__(self, frame, length, width, thickness, outline_a=None, outline_b=None, openings=None, name=None, **kwargs):
        Element.__init__(self, frame=frame, **kwargs)
        outline_a = outline_a or Polyline([Point(0, 0, 0), Point(length, 0, 0), Point(length, width, 0), Point(0, width, 0), Point(0, 0, 0)])
        outline_b = outline_b or Polyline([Point(p[0], p[1], thickness) for p in outline_a.points])
        PlateGeometry.__init__(self, outline_a, outline_b, openings=openings)
        self.length = length
        self.width = width
        self.height = thickness
        self.name = name or "Slab"
        self.interfaces = []
        self.attributes = {}
        self.attributes.update(kwargs)

    def __repr__(self):
        return "Slab(name={}, {}, {}, {:.3f})".format(self.name, self.frame, self.outline_a, self.thickness)

    def __str__(self):
        return "Slab(name={}, {}, {}, {:.3f})".format(self.name, self.frame, self.outline_a, self.thickness)

    @property
    def is_slab(self):
        return True

    @property
    def is_wall(self):
        return False

    @property
    def is_floor(self):
        return False

    @property
    def is_roof(self):
        return False

    @property
    def is_group_element(self):
        return True
