class FeatureApplicationError(Exception):
    """Raised when a feature cannot be applied to an element geometry.

    Attributes
    ----------
    feature_geometry : :class:`~compas.geometry.Geometry`
        The geometry of the feature that could not be applied.
    element_geometry : :class:`~compas.geometry.Geometry`
        The geometry of the element that could not be modified.
    message : str
        The error message.

    """

    def __init__(self, feature_geometry, element_geometry, message):
        super(FeatureApplicationError, self).__init__(message)
        self.feature_geometry = feature_geometry
        self.element_geometry = element_geometry
        self.message = message


__all__ = ["FeatureApplicationError"]
