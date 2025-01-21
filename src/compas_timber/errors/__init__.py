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


class BeamJoiningError(Exception):
    """Indicates that an error has occurred while trying to join two or more beams.

    This error should indicate that an error has occurred while calculating the features which
    should be applied by this joint.

    Attributes
    ----------
    beams : list(:class:`~compas_timber.parts.Beam`)
        The beams that were supposed to be joined.
    debug_geometries : list(:class:`~compas.geometry.Geometry`)
        A list of geometries that can be used to visualize the error.
    debug_info : str
        A string containing debug information about the error.
    joint : :class:`~compas_timber.connections.Joint`
        The joint that was supposed to join the beams.

    """

    def __init__(self, beams, joint, debug_info=None, debug_geometries=None):
        super(BeamJoiningError, self).__init__()
        self.beams = beams
        self.joint = joint
        self.debug_info = debug_info
        self.debug_geometries = debug_geometries or []


class FastenerApplicationError(Exception):
    """Raised when a fastener cannot be applied to a joint.

    Attributes
    ----------
    elements : list of : class:`~compas_timber.elements.TimberElement`
        The elements of the `Joint` to which the fastener could not be applied.
    fastener : :class:`~compas_timber.elements.Fastener`
        The fastener that could not be applied.
    message : str
        The error message.

    """

    def __init__(self, elements, fastener, message):
        super(FastenerApplicationError, self).__init__(message)
        self.elements = elements
        self.fastener = fastener
        self.message = message


__all__ = [
    "FeatureApplicationError",
    "BeamJoiningError",
    "FeatureApplicationError",
]
