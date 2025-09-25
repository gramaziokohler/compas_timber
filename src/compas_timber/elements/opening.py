from tkinter import E
from compas.data import Data
from compas_model.elements import Element


class OpeningType(object):
    DOOR = "door"
    WINDOW = "window"
    GENERIC = "generic"


class Opening(Element):
    """An opening in a sheet geometry, defined by one or two polylines.
    Parameters
    ----------
    polyline_a : :class:`compas.geometry.Polyline`
        The first polyline defining the opening.
    polyline_b : :class:`compas.geometry.Polyline`, optional
        The second polyline defining the opening. If not provided, the opening is defined by a single polyline.
    opening_type : OpeningType, optional
        The type of the opening (e.g., door, window, generic).


    Attributes
    ----------
    polyline_a : :class:`compas.geometry.Polyline`
        The first polyline defining the opening.
    polyline_b : :class:`compas.geometry.Polyline`, optional
        The second polyline defining the opening. If not provided, the opening is defined by a single polyline.
    opening_type : OpeningType
        The type of the opening (e.g., door, window, generic).
    """
    @property
    def __data__(self):
        return {
            "polyline_a": self.polyline_a,
            "polyline_b": self.polyline_b,
            "opening_type": self.opening_type,
        }

    def __init__(self, polyline_a, polyline_b=None, opening_type=None, **kwargs):
        super(Opening, self).__init__(**kwargs)
        self.polyline_a = polyline_a
        self.polyline_b = polyline_b
        self.opening_type = opening_type

    def __repr__(self):
        return "Opening(type={})".format(self.opening_type)



