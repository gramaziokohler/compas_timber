from .joint import Joint
from .plate_joint import PlateJoint


class JointCandidate(Joint):
    """A JointCandidate is an information-only joint, which does not add any features to the elements it connects.

    It is used to create a first-pass joinery information which can be later used to perform analysis using :class:`~compas_timber.connections.analyzers.BeamGroupAnalyzer`.

    Please use `JointCandidate.create()` to properly create an instance of this class and associate it with an model.

    Parameters
    ----------
    element_a : :class:`~compas_timber.elements.TimberElement`
        First element to be joined.
    element_b : :class:`~compas_timber.elements.TimberElement`
        Second element to be joined.
    distance : float | None
        Distance between the elements.

    Attributes
    ----------
    element_a : :class:`~compas_timber.elements.TimberElement`
        First element to be joined.
    element_b : :class:`~compas_timber.elements.TimberElement`
        Second element to be joined.
    distance : float | None
        Distance between the elements.

    """

    def __init__(self, element_a=None, element_b=None, distance=None, **kwargs):
        super(JointCandidate, self).__init__(elements=(element_a, element_b), **kwargs)
        # TODO: make distance a property of `Joint`?
        self.distance = distance if distance is not None else None

    def add_features(self):
        """This joint does not add any features."""
        pass


class PlateJointCandidate(PlateJoint):
    """A PlateJointCandidate is an information-only joint for plate connections.

    It is used to create a first-pass joinery information which can be later used to perform analysis using :class:`~compas_timber.connections.analyzers.BeamGroupAnalyzer`.

    Parameters
    ----------
    plate_a : :class:`~compas_timber.elements.Plate`
        First plate to be joined.
    plate_b : :class:`~compas_timber.elements.Plate`
        Second plate to be joined.

    Attributes
    ----------
    plate_a : :class:`~compas_timber.elements.Plate`
        First plate to be joined.
    plate_b : :class:`~compas_timber.elements.Plate`
        Second plate to be joined.

    """

    def __init__(self, plate_a=None, plate_b=None, **kwargs):
        super(PlateJointCandidate, self).__init__(plate_a=plate_a, plate_b=plate_b, **kwargs)

    def _set_edge_planes(self):
        pass
