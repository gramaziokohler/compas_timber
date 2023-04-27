from pprint import pprint

from compas.datastructures import Assembly
from compas.datastructures import AssemblyError

from compas_timber.connections.joint import Joint
from compas_timber.parts import Beam


class TimberAssembly(Assembly):
    """Represents a timber assembly containing beams and joints etc.

    Attributes
    ----------
    units : literal("meters"|"millimiters")
        Returns the currently selected unit type used in this assembly.
    tol : float
        The used tolerance for floating point operations, this is a function of the selected unit type.
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

    """

    def __init__(self, *args, **kwargs):
        super(TimberAssembly, self).__init__()
        self._units = "meters"  # options: 'meters', 'millimeters' #TODO: change to global compas PRECISION
        self._units_precision = {"meters": 1e-9, "millimeters": 1e-6}
        self._beams = []
        self._joints = []

    def __str__(self):
        """Returns a formatted string representation of this assembly.

        Return
        ------
        str

        """
        return "Timber Assembly ({}) with {} beam(s) and {} joint(s).".format(
            self.guid, len(self.beams), len(self.joints)
        )

    @Assembly.data.setter
    def data(self, value):
        Assembly.data.fset(self, value)
        # restore what got removed to avoid circular reference
        for part in self.parts():
            if isinstance(part, Beam):
                self._beams.append(part)
            if isinstance(part, Joint):
                self._joints.append(part)
                part.restore_beams_from_keys(self)

    @property
    def units(self):
        return self._units

    @units.setter
    def units(self, units_name):
        if units_name not in self._units_precision.keys():
            raise ValueError(
                "The units parameters must be one of the following strings: {}.".format(self._units_precision.keys())
            )
        else:
            self._units = units_name

    @property
    def tol(self):
        # TODO: change to compas PRECISION
        return self._units_precision[self.units]


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
            The beam to add.

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
            raise AssemblyError("Cannot add this joint to assembly: some of the parts are already joined.")

    def remove_joint(self, joint):
        """Removes a joint from the assembly, i.e. disconnects it from assembly and from its parts.

        Does not delete the object.

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
