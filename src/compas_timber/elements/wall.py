from .slab import Slab


class Wall(Slab):
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

    def __init__(self, outline_a, outline_b, openings=None, **kwargs):
        super(Wall, self).__init__(outline_a, outline_b, **kwargs)
        self.outline_a = outline_a
        self.outline_b = outline_b
        self.openings = openings or []
        self.attributes = {}
        self.attributes.update(kwargs)
        self._faces = None
        self._corners = None

        if not outline_a.is_closed or not outline_b.is_closed:
            raise ValueError("Outline is not closed.")
        if len(self.outline_a) != 5 or len(self.outline_b) != 5:
            raise ValueError("Wall outline must have 4 segments.")

    def __repr__(self):
        return "Wall(name={}, {}, {}, {:.3f})".format(self.name, self.frame, self.outline_a, self.outline_b)

    @property
    def is_wall(self):
        return True
