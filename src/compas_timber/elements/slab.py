from .plate import Plate


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

    def __init__(self, outline_a, outline_b, openings=None, interfaces=None, detail_set=None, name=None, **kwargs):
        # type: (compas.geometry.Polyline, float, list[compas.geometry.Polyline], Frame, dict) -> None
        super(Slab, self).__init__(outline_a, outline_b, name=name, **kwargs)
        self.openings = openings
        self.opening_outlines = [opening.outline for opening in self.openings] if openings else []
        self.attributes = {}
        self.attributes.update(kwargs)
        self._edge_planes = []
        self.openings = openings if openings is not None else []
        self.interfaces = interfaces if interfaces is not None else []  # type: list[SlabToSlabInterface]
        self.elements = []
        self.joints = []
        self.populator = None
        self.detail_set = detail_set

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

    def add_opening(self, opening):
        """Add an opening to the slab."""
        self.openings.append(opening)
        self.opening_outlines.append(opening.outline)
