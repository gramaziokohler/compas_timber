from typing import Container
from compas.data import Data
from compas.geometry import Box
from compas.geometry import Brep
from compas.geometry import Frame
from compas.geometry import Line
from compas.geometry import Plane
from compas.geometry import Polyline
from compas.geometry import bounding_box

from compas_timber.utils import classify_polyline_segments

from .container import ContainerElement
from .sheet import Sheet

class SlabType(object):
    WALL = "wall"
    FLOOR = "floor"
    ROOF = "roof"
    GENERIC = "generic"

class Slab(Sheet, ContainerElement):
    """Represents a single timber wall element.
    Serves as container for beams joints and other related elements and groups them together to form a wall.

    Wall is often a single unit of prefabricated timber wall element.
    It is often refered to as an enveloping body.

    TODO: complete this docstring

    """

    @property
    def __data__(self):
        data = super(Slab, self).__data__
        data["outline_a"] = self.outline_a
        data["outline_b"] = self.outline_b
        data["openings"] = self.openings
        data["attributes"] = self.attributes
        return data

    def __init__(self, outline_a, outline_b, openings=None, interfaces=None, name=None, **kwargs):
        # type: (compas.geometry.Polyline, float, list[compas.geometry.Polyline], Frame, dict) -> None
        super(Slab, self).__init__(outline_a, outline_b, name=name, **kwargs)
        for opening in openings:
            self.add_opening(opening)
        for interface in interfaces:
            self.add_interface(interface)
        self.opening_outlines = [opening.outline for opening in self.openings] if openings else []
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
    def is_group_element(self):
        return True

    @property
    def opening_outlines(self):
        return [opening.outline for opening in self.openings]

    def add_opening(self, opening):
        """Add an opening to the slab."""
        self.add_element(opening)
        self.openings.append(opening)
        self.opening_outlines.append(opening.outline)

    def remove_opening(self, opening):
        """Remove an opening from the slab."""
        self.remove_element(opening)
        self.openings.remove(opening)
        self.opening_outlines.remove(opening.outline)

    def add_interface(self, interface):
        """Add an interface to the slab."""
        self.add_element(interface)
        self.interfaces.append(interface)

    def remove_interface(self, interface):
        """Remove an interface from the slab."""
        self.remove_element(interface)
        self.interfaces.remove(interface)
