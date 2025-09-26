from compas_model.elements import Element
from compas_model.elements import reset_computed


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
    def __data__(self):
        data = super(TimberElement, self).__data__
        data["features"] = [f for f in self.features if not f.is_joinery]  # type: ignore
        return data

    def __init__(self, features=None, **kwargs):
        super(TimberElement, self).__init__(**kwargs)
        self._features = features or []
        self.debug_info = []

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

    @property
    def features(self):
        # type: () -> list[Feature]
        return self._features

    @features.setter
    def features(self, features):
        self._features = features

    def remove_blank_extension(self):
        pass

    def reset(self):
        """Resets the element to its initial state by removing all features, extensions, and debug_info."""
        self.remove_features()
        self.remove_blank_extension()
        self.debug_info = []

    @reset_computed
    def add_features(self, features):
        # type: (Feature | list[Feature]) -> None
        """Adds one or more features to the beam.

        Parameters
        ----------
        features : :class:`~compas_timber.parts.Feature` | list(:class:`~compas_timber.parts.Feature`)
            The feature to be added.

        """
        if not isinstance(features, list):
            features = [features]
        self._features.extend(features)  # type: ignore

    @reset_computed
    def remove_features(self, features=None):
        # type: (None | Feature | list[Feature]) -> None
        """Removes a feature from the beam.

        Parameters
        ----------
        feature : :class:`~compas_timber.parts.Feature` | list(:class:`~compas_timber.parts.Feature`)
            The feature to be removed. If None, all features will be removed.

        """
        if features is None:
            self._features = []
        else:
            if not isinstance(features, list):
                features = [features]
            self._features = [f for f in self._features if f not in features]
