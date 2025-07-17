class FeatureApplicationError(Exception):
    """Raised when a feature cannot be applied to an element geometry.

    # TODO: perhaps should be renamed to ProcessingVisualizationError or something similar.

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

    def __reduce__(self):
        # without this the error cannot be deepcopied
        return (FeatureApplicationError, (self.feature_geometry, self.element_geometry, self.message))


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
        super(BeamJoiningError, self).__init__(debug_info)
        self.beams = beams
        self.joint = joint
        self.debug_info = debug_info
        self.debug_geometries = debug_geometries or []

    def __reduce__(self):
        # without this the error cannot be deepcopied
        return (BeamJoiningError, (self.beams, self.joint, self.debug_info, self.debug_geometries))


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

    def __reduce__(self):
        # without this the error cannot be deepcopied
        return (FastenerApplicationError, (self.elements, self.fastener, self.message))


class BTLxProcessingError(Exception):
    """Exception raised when an error occurs while writing a Processing to BTLx file.

    TODO: some work here to figure out the different types of feature/processing related errors.
    TODO: this one is somewhat similar to FeatureApplicationError, but only relevant when processing is created from its proxy.
    TOOD: also BTLxProcessingError is never throws but rather collected to form some sort of a report for the user.

    Parameters
    ----------
    message : str
        The error message.
    part : :class:`BTLxPart`
        The part that caused the error.
    failed_processing : :class:`BTLxProcessing`
        The processing that caused the error.

    Attributes
    ----------
    message : str
        The error message.
    part : :class:`BTLxPart`
        The part that caused the error.
    failed_processing : :class:`BTLxProcessing`
        The processing that caused the error.

    """

    def __init__(self, message, part, failed_processing):
        super(BTLxProcessingError, self).__init__(message)
        self.message = message
        self.part = part
        self.failed_processing = failed_processing


__all__ = [
    "BeamJoiningError",
    "BTLxProcessingError",
    "FastenerApplicationError",
    "FeatureApplicationError",
]
