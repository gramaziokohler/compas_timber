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

    def __init__(self, outline, thickness, openings=None, justification="inside", frame=None, name=None, **kwargs):
        super(Wall, self).__init__(outline, thickness, openings, frame, name, **kwargs)
        if justification not in ["inside", "outside", "center"]:
            raise ValueError("Justification must be one of 'inside', 'outside', or 'center'.")
        if justification == "inside":
            self.outline = outline
        elif justification == "outside":
            self.outline = outline.translated(-thickness*self.frame.normal)
        elif justification == "center":
            self.outline = outline.offset(-(thickness / 2)*self.frame.normal)
        self.thickness = thickness
        self.openings = openings or []
        self.attributes = {}
        self.attributes.update(kwargs)

        self.justification = justification
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

    class WallJustificationType(object):
        """Enum for the alignment of the cut.
        Attributes
        ----------
        INSIDE : literal("inside")
            Inside alignment. Wall volume offsets to the z-direction when using right-handed outline curve.
        OUTSIDE : literal("outside")
            Outside alignment. Wall volume offsets to the z-direction when using left-handed outline curve.
        CENTER : literal("center")
            Center alignment.
        """

        INSIDE = "inside"
        OUTSIDE = "outside"
        CENTER = "center"
