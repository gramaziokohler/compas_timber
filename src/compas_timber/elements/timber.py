from compas_model.elements import Element


class TimberElement(Element):
    """Base class for all timber elements.

    This is an abstract class and should not be instantiated directly.

    Attributes
    ----------
    is_beam : bool
        True if the element is a beam.
    is_plate : bool
        True if the element is a plate.
    is_wall : bool
        True if the element is a wall.

    """

    @property
    def is_beam(self):
        return False

    @property
    def is_plate(self):
        return False

    @property
    def is_wall(self):
        return False

    @property
    def is_fastener(self):
        return False
