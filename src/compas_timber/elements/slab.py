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

        data["name"] = self.name
        data["attributes"] = self.attributes
        return data

    def __init__(self, outline_a, outline_b, openings=None, frame=None, name=None, **kwargs):
        Sheet.__init__(self,outline_a, outline_b, openings=openings, frame=frame)
        ContainerElement.__init__(self, **kwargs)
        self.name = name or "Slab"
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
