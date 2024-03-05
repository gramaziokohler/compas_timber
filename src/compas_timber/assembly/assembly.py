from compas_model.model import Model

from compas_timber.parts import Beam
from compas_timber.connections import Joint


class TimberModel(Model):
    """Represents a timber assembly containing beams and joints etc.

    Attributes
    ----------
    beams : list(:class:`~compas_timber.parts.Beam`)
        A list of beams assigned to this assembly.
    joints : list(:class:`~compas_timber.connections.Joint`)
        A list of joints assigned to this assembly.
    topologies :  list(dict)
        A list of JointTopology for assembly. dict is: {"detected_topo": detected_topo, "beam_a_key": beam_a_key, "beam_b_key":beam_b_key} See :class:`~compas_timber.connections.JointTopology`.

    """

    @classmethod
    def __from_data__(cls, data):
        model = super(TimberModel, cls).__from_data__(data)
        for element in model.elementlist:
            if isinstance(element, Beam):
                model._beams.append(element)
            if isinstance(element, Joint):
                model._joints.append(element)
        for joint in model.joints:
            joint.add_features()
        return model

    def __init__(self, *args, **kwargs):
        super(TimberModel, self).__init__()
        self._beams = []
        self._joints = []
        self._topologies = []  # added to avoid calculating multiple times

    def __str__(self):
        """Returns a formatted string representation of this assembly.

        Return
        ------
        str

        """
        return "Timber Assembly ({}) with {} beam(s) and {} joint(s).".format(
            self.guid, len(self.beams), len(self.joints)
        )

    @property
    def beams(self):
        return self._beams

    @property
    def joints(self):
        return self._joints

    def add_beam(self, beam):
        """Adds a Beam to this assembly.

        Parameters
        ----------
        beam : :class:`~compas_timber.parts.Beam`
            The beam to add to the assembly.

        Returns
        -------
        int
            The graph key identifier of the added beam.

        """
        _ = self.add_element(beam)
        self._beams.append(beam)

    def add_joint(self, joint, parts):
        """Add a joint object to the assembly.

        Parameters
        ----------
        joint : :class:`~compas_timber.parts.joint`
            An instance of a Joint class.

        parts : list(:class:`~compas.datastructure.Part`)
            Beams or other Parts (dowels, steel plates) involved in the joint.

        Returns
        -------
        int
            The identifier of the joint in the current assembly graph.

        """
        # self._validate_joining_operation(joint, parts)
        # create an unconnected node in the graph for the joint object
        # TODO: for each two parts pairwise do.. in the meantime, allow only two parts
        if len(parts) != 2:
            raise ValueError("Expected 2 parts. Got instead: {}".format(len(parts)))
        a, b = parts
        _ = self.add_interaction(a, b, interaction=joint)
        self._joints.append(joint)

    def remove_joint(self, joint):
        """Removes this joint object from the assembly.

        Parameters
        ----------
        joint : :class:`~compas_timber.connections.Joint`
            The joint to remove.

        """
        a, b = joint.parts
        self.remove_interaction(a, b)
        self._joints.remove(joint)


    def set_topologies(self, topologies):
        self._topologies = topologies

    @property
    def topologies(self):
        return self._topologies
