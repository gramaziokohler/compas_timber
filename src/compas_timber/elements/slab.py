from compas.data import Data

from .plate import Plate


class OpeningType(object):
    DOOR = "door"
    WINDOW = "window"
    GENERIC = "generic"


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


class Slab(Plate):
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

    def __init__(self, outline_a, outline_b, openings=None, name=None, **kwargs):
        # type: (compas.geometry.Polyline, float, list[compas.geometry.Polyline], Frame, dict) -> None
        super(Slab, self).__init__(outline_a, outline_b, openings=openings, name=name, **kwargs)
        self.attributes = {}
        self.attributes.update(kwargs)
        self._edge_planes = []
        self.interfaces = []  # type: list[SlabToSlabInterface]

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

    def compute_geometry(self, include_features=True):
        # type: (bool) -> compas.datastructures.Mesh | compas.geometry.Brep
        """Compute the geometry of the element.

        Parameters
        ----------
        include_features : bool, optional
            If ``True``, include the features in the computed geometry.
            If ``False``, return only the plate shape.

        Returns
        -------
        :class:`compas.datastructures.Mesh` | :class:`compas.geometry.Brep`

        """

        # TODO: consider if Brep.from_curves(curves) is faster/better
        return self.shape
