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
    is_group_element : bool
        True if the element can be used as container for other elements.

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
    def is_group_element(self):
        return False

    @property
    def is_fastener(self):
        return False

    def reset(self):
        """Resets the element to its initial state by removing all features, extensions, and debug_info."""
        self.remove_features()
        if hasattr(self, "remove_blank_extension"):  # only beams should have this attribute
            self.remove_blank_extension()
        self.debug_info = []
