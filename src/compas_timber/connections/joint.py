from itertools import combinations

from compas.geometry import Point
from compas.geometry import distance_point_line
from compas_model.interactions import Interaction

from .solver import JointTopology


class Joint(Interaction):
    """Base class for a joint connecting two beams.

    This is a base class and should not be instantiated directly.
    Use the `create()` class method of the respective implementation of `Joint` instead.

    Attributes
    ----------
    beams : tuple(:class:`~compas_timber.parts.Beam`)
        The beams joined by this joint.
    ends : dict(:class:`~compas_timber.parts.Beam`, str)
        A map of which end of each beam is joined by this joint.
    frame : :class:`~compas.geometry.Frame`
        The frame of the joint.
    key : str
        A unique identifier for this joint.
    features : list(:class:`~compas_timber.parts.Feature`)
        A list of features that were added to the beams by this joint.
    attributes : dict
        A dictionary of additional attributes for this joint.
    topology : literal, one of JointTopology.TOPO_UNKNOWN, JointTopology.TOPO_L, JointTopology.TOPO_T, JointTopology.TOPO_X, JointTopology.TOPO_I
        The topology by which the two elements connected with this joint interact.
    location : :class:`~compas.geometry.Point`
        The estimated location of the interaction point of the two elements connected with this joint.
    """

    SUPPORTED_TOPOLOGY = JointTopology.TOPO_UNKNOWN
    MIN_ELEMENT_COUNT = 2
    MAX_ELEMENT_COUNT = 2

    def __init__(self, topology=None, location=None, **kwargs):
        super(Joint, self).__init__(name=self.__class__.__name__)
        self._topology = topology if topology is not None else JointTopology.TOPO_UNKNOWN
        self._location = location or Point(0, 0, 0)

    @property
    def topology(self):
        return self._topology

    @property
    def location(self):
        return self._location

    @property
    def elements(self):
        raise NotImplementedError

    @property
    def generated_elements(self):
        return []

    @classmethod
    def element_count_complies(cls, elements):
        if cls.MAX_ELEMENT_COUNT:
            return len(elements) >= cls.MIN_ELEMENT_COUNT and len(elements) <= cls.MAX_ELEMENT_COUNT
        else:
            return len(elements) >= cls.MIN_ELEMENT_COUNT

    def add_features(self):
        """Adds the features defined by this joint to affected beam(s).

        Raises
        ------
        :class:`~compas_timber.connections.BeamJoiningError`
            Should be raised whenever the joint was not able to calculate the features to be applied to the beams.

        """
        raise NotImplementedError

    def add_extensions(self):
        """Adds the extensions defined by this joint to affected beam(s).
        This is optional and should only be implemented by joints that require it.

        Notes
        -----
        Extensions are added to all beams before the features are added.

        Raises
        ------
        :class:`~compas_timber.connections.BeamJoiningError`
            Should be raised whenever the joint was not able to calculate the extensions to be applied to the beams.

        """
        pass

    def check_elements_compatibility(self):
        """Checks if the beams are compatible for the creation of the joint.
        This is optional and should only be implemented by joints that require it.

        Raises
        ------
        :class:`~compas_timber.connections.BeamJoiningError`
            Should be raised whenever the elements did not comply with the requirements of the joint.

        """
        pass

    def restore_beams_from_keys(self, model):
        """Restores the reference to the beams associate with this joint.

        During serialization, :class:`compas_timber.parts.Beam` objects
        are serialized by :class:`compas_timber.model`. To avoid circular references, Joint only stores the keys
        of the respective beams.

        This method is called by :class:`compas_timber.model` during de-serialization to restore the references.
        Since the roles of the beams are joint specific (e.g. main/cross beam) this method should be implemented by
        the concrete implementation.

        Examples
        --------
        See :class:`compas_timber.connections.TButtJoint`.

        """
        raise NotImplementedError

    @classmethod
    def create(cls, model, *elements, **kwargs):
        """Creates an instance of this joint and creates the new connection in `model`.

        `beams` are expected to have been added to `model` before calling this method.

        This code does not verify that the given beams are adjacent and/or lie in a topology which allows connecting
        them. This is the responsibility of the calling code.

        A `ValueError` is raised if `beams` contains less than two `Beam` objects.

        Parameters
        ----------
        model : :class:`~compas_timber.model.TimberModel`
            The model to which the beams and this joing belong.
        beams : list(:class:`~compas_timber.parts.Beam`)
            A list containing two beams that whould be joined together

        Returns
        -------
        :class:`compas_timber.connections.Joint`
            The instance of the created joint.

        """

        joint = cls(*elements, **kwargs)
        model.add_joint(joint)
        return joint

    @property
    def ends(self):
        """Returns a map of which end of each beam is joined by this joint."""

        self._ends = {}
        for index, beam in enumerate(self.elements):
            if distance_point_line(beam.centerline.start, self.elements[index - 1].centerline) < distance_point_line(beam.centerline.end, self.elements[index - 1].centerline):
                self._ends[str(beam.guid)] = "start"
            else:
                self._ends[str(beam.guid)] = "end"
        return self._ends

    @property
    def interactions(self):
        """Returns all possible interactions between elements that are connected by this joint.
        interaction is defined as a tuple of (element_a, element_b, joint).
        """
        interactions = []
        for pair in combinations(self.elements, 2):
            interactions.append((pair[0], pair[1]))
        return interactions
