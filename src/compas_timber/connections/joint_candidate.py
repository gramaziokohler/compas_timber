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

    @property
    def __data__(self):
        data_dict = super().__data__
        data_dict.update(
            {
                "element_a_guid": self.element_a_guid,
                "element_b_guid": self.element_b_guid,
                "distance": self.distance,
            }
        )
        return data_dict

    def __init__(self, element_a=None, element_b=None, distance=None, **kwargs):
        super(JointCandidate, self).__init__(**kwargs)
        self.element_a = element_a
        self.element_b = element_b
        self.distance = distance
        self.element_a_guid = kwargs.get("element_a_guid") or str(element_a.guid)
        self.element_b_guid = kwargs.get("element_b_guid") or str(element_b.guid)

    @classmethod
    def create(cls, model, *elements, **kwargs):
        raise NotImplementedError("JointCandidate cannot be created directly as a joint. Use `model.add_joint_candidate()` instead.")

    @property
    def elements(self):
        return [self.element_a, self.element_b]

    def restore_beams_from_keys(self, model):
        """After de-serialization, restores references to elements saved in the model."""
        self.element_a = model.element_by_guid(self.element_a_guid)
        self.element_b = model.element_by_guid(self.element_b_guid)

    def add_features(self):
        """This joint does not add any features."""
        pass


class PlateJointCandidate(PlateJoint, JointCandidate):
    """A PlateJointCandidate is an information-only joint for plate connections.

    It is used to create a first-pass joinery information which can be later used to perform analysis using :class:`~compas_timber.connections.analyzers.BeamGroupAnalyzer`.

    Parameters
    ----------
    plate_a : :class:`~compas_timber.parts.Plate`
        First plate to be joined.
    plate_b : :class:`~compas_timber.parts.Plate`
        Second plate to be joined.

    Attributes
    ----------
    plate_a : :class:`~compas_timber.parts.Plate`
        First plate to be joined.
    plate_b : :class:`~compas_timber.parts.Plate`
        Second plate to be joined.

    """

    def __init__(self, plate_a=None, plate_b=None, **kwargs):
        super(PlateJointCandidate, self).__init__(plate_a=plate_a, plate_b=plate_b, element_a=plate_a, element_b=plate_b, **kwargs)
