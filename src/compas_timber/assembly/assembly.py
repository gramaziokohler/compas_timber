from compas.datastructures import Assembly
from compas.datastructures import AssemblyError

from compas_timber.connections import Joint
from compas_timber.connections import BeamJoinningError
from compas_timber.parts import Beam


class TimberAssembly(Assembly):
    """Represents a timber assembly containing beams and joints etc.

    Attributes
    ----------
    beams : list(:class:`~compas_timber.parts.Beam`)
        A list of beams assigned to this assembly.
    joints : list(:class:`~compas_timber.connections.Joint`)
        A list of joints assigned to this assembly.
    part_keys : list(int)
        A list of the keys of the parts included in this assembly.
    beam_keys :  list(int)
        A list of the keys of the beams included in this assembly.
    joint_keys :  list(int)
        A list of the keys of the joints included in this assembly.
    topologies :  list(dict)
        A list of JointTopology for assembly. dict is: {"detected_topo": detected_topo, "beam_a_key": beam_a_key, "beam_b_key":beam_b_key} See :class:`~compas_timber.connections.JointTopology`.

    """

    def __init__(self, *args, **kwargs):
        super(TimberAssembly, self).__init__()
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

    @classmethod
    def from_data(cls, data):
        assembly = super(TimberAssembly, cls).from_data(data)
        for part in assembly.parts():
            if isinstance(part, Beam):
                assembly._beams.append(part)
            if isinstance(part, Joint):
                assembly._joints.append(part)
                part.restore_beams_from_keys(assembly)
        for joint in assembly._joints:
            joint.add_features()
        return assembly

    @property
    def beams(self):
        return self._beams

    @property
    def joints(self):
        return self._joints

    @property
    def part_keys(self):
        return [part.key for part in self.parts()]

    @property
    def beam_keys(self):
        return [beam.key for beam in self._beams]

    @property
    def joint_keys(self):
        return [joint.key for joint in self._joints]

    def contains(self, obj):
        """Returns True if this assembly contains the given object, False otherwise.

        Parameters
        ----------
        obj: :class:`~compas.data.Data`
            The object to look for.

        Returns
        -------
        bool

        """
        return obj.guid in self._parts

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
        if beam in self._beams:
            raise AssemblyError("This beam has already been added to this assembly!")
        key = self.add_part(part=beam, type="part_beam")
        self._beams.append(beam)
        beam.is_added_to_assembly = True
        return key

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
        self._validate_joining_operation(joint, parts)
        # create an unconnected node in the graph for the joint object
        key = self.add_part(part=joint, type="joint")
        # joint.assembly = self
        self._joints.append(joint)

        # adds links to the beams
        for part in parts:
            self.add_connection(part, joint)
        return key

    def _validate_joining_operation(self, joint, parts):
        if not parts:
            raise AssemblyError("Cannot add this joint to assembly: no parts given.")

        if self.contains(joint):
            raise AssemblyError("This joint has already been added to this assembly.")

        # TODO: rethink this assertion, maybe it should be possible to have more than 1 joint for the same set of parts
        if not [self.contains(part) for part in parts]:
            raise AssemblyError("Cannot add this joint to assembly: some of the parts are not in this assembly.")

        if self.are_parts_joined(parts):
            raise BeamJoinningError(beams=parts, joint=joint, debug_info="Beams are already joined.")

    def remove_joint(self, joint):
        """Removes this joint object from the assembly.

        Parameters
        ----------
        joint : :class:`~compas_timber.connections.Joint`
            The joint to remove.

        """
        del self._parts[joint.guid]
        self.graph.delete_node(joint.key)
        self._joints.remove(joint)  # TODO: make it automatic
        joint.assembly = None  # TODO: should not be needed
        # TODO: distroy joint?

    def are_parts_joined(self, parts):
        """Checks if there is already a joint defined for the same set of parts.

        Parameters
        ----------
        parts : list(:class:`~compas.datastructure.Part`)
            The parts to check.

        Returns
        -------
        bool

        """
        n = len(parts)
        neighbor_keys = [set(self.graph.neighborhood(self._parts[part.guid], ring=1)) for part in parts]
        for i in range(n - 1):
            nki = neighbor_keys[i]
            for j in range(i + 1, n):
                nkj = neighbor_keys[j]
                nkx = nki.intersection(nkj)
                for x in nkx:
                    if self.graph.node[x]["type"] == "joint":
                        return True
        return False

    def set_topologies(self, topologies):
        self._topologies = topologies

    @property
    def topologies(self):
        return self._topologies
