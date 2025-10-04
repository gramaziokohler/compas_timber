from compas.data import Data
from compas.geometry import Box
from compas.geometry import Brep
from compas.geometry import Frame
from compas.geometry import Line
from compas.geometry import Point
from compas.geometry import Polyline
from compas.geometry import bounding_box
from compas_model.elements import Element

from compas_timber.utils import classify_polyline_segments
from compas_timber.elements import PlateGeometry

class OpeningType(object):
    DOOR = "door"
    WINDOW = "window"


class Opening(Data):
    @property
    def __data__(self):
        return {
            "polyline": self.polyline,
            "opening_type": self.opening_type,
        }

    def __init__(self, polyline, opening_type, **kwargs):
        super(Opening, self).__init__(**kwargs)
        self.polyline = polyline
        self.opening_type = opening_type

    def __repr__(self):
        return "Opening(type={})".format(self.opening_type)

    def orient_polyline(self, normal):
        self.polyline = _oriented_polyline(self.polyline, normal)


class Slab(Element, PlateGeometry):
    """Represents a single timber wall element.
    Serves as container for beams joints and other related elements and groups them together to form a wall.

    Wall is often a single unit of prefabricated timber wall element.
    It is often refered to as an enveloping body.

    TODO: complete this docstring

    """

    @property
    def __data__(self):
        data = Element.__data__(self)
        data["outline_a"] = self.outline_a
        data["outline_b"] = self.outline_b
        data["openings"] = [o.__data__ for o in self.openings]

    def __init__(self, frame, length, width, thickness, outline_a=None, outline_b=None, openings=None, **kwargs):
        Element.__init__(self, frame=frame, **kwargs)
        outline_a = outline_a or Polyline([Point(0, 0, 0), Point(length, 0, 0), Point(length, width, 0), Point(0, width, 0), Point(0, 0, 0)])
        outline_b = outline_b or Polyline([Point(p[0], p[1], thickness) for p in outline_a.points])
        PlateGeometry.__init__(self, outline_a, outline_b, openings=openings)
        self.frame = frame
        self.length = length
        self.width = width
        self.thickness = thickness
        self.attributes = {}
        self.attributes.update(kwargs)
        self.debug_info = []
        self.interfaces = []

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

    