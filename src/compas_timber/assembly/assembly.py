from pprint import pprint

from compas.datastructures import Assembly
from compas.datastructures import AssemblyError

from compas_timber.connections.joint import Joint
from compas_timber.parts import Beam


class TimberAssembly(Assembly):
    """
    A data structure for managing the assembly. Assembly consist of parts and joints.
    Parts are entities with a substantial physical presence, for example: beams, dowels, screws.
    Joints are abstract entities to describe how parts are joined together, for example: two beams joining through a lap joint with a screw or dowel through it.
    Connections are low-level abstractions to link the joined parts, for example: beam1-beam2, beam1-dowel, beam2-dowel.

    Graph:
    Nodes store objects under 'object' attribute.
        default node attributes:
            'type': None,  # string 'beam', 'joint', 'other_part'

        default edge attributes:
            'type': None,  # not being used at the moment

    """

    def __init__(self, *args, **kwargs):
        super(TimberAssembly, self).__init__()
        self._units = "meters"  # options: 'meters', 'millimeters' #TODO: change to global compas PRECISION
        self._units_precision = {"meters": 1e-9, "millimeters": 1e-6}

        self._beams = []
        self._joints = []

    @Assembly.data.setter
    def data(self, value):
        Assembly.data.fset(self, value)
        # restore what got removed to avoid circular reference
        for part in self.parts():
            part.assembly = self
            if isinstance(part, Beam):
                self._beams.append(part)
                part.clear_features()
            if isinstance(part, Joint):
                self._joints.append(part)
                part.add_features(apply=False)

    @property
    def units(self):
        return self._units

    @units.setter
    def units(self, units_name):
        if not units_name in self._units_precision.keys():
            raise ValueError("The units parameters must be one of the following strings: {}.".format(self._units_precision.keys()))
        else:
            self._units = units_name

    @property
    def tol(self):
        # TODO: change to compas PRECISION
        return self._units_precision[self.units]

    @property
    def beams(self):
        """
        Returns all Beam objects which are part of this assembly.

        Returns
        -------
        List[:class:`~compas_timber.parts.Beam`]
        """
        return self._beams

    @property
    def joints(self):
        """
        Returns all Joint objects which are part of this assembly.

        Returns
        -------
        List[:class:`~compas_timber.connections.Joint`]
        """
        return self._joints

    @property
    def part_keys(self):
        """
        Returns a list of the grahp keys of all the parts associated with this assembly.

        Returns
        -------
        List[int]
        """
        return [part.key for part in self.parts()]

    @property
    def beam_keys(self):
        """
        Returns a list of the grahp keys of all the Beam objects associated with this assembly.

        Returns
        -------
        List[int]
        """
        return [beam.key for beam in self._beams]

    @property
    def joint_keys(self):
        """
        Returns a list of the grahp keys of all the Joint objects associated with this assembly.

        Returns
        -------
        List[int]
        """
        return [joint.key for joint in self._joints]

    def contains(self, obj):
        """
        Returns True if this assembly contains the given object, False otherwise.

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
        """
        Adds a Beam to this assembly.

        Parameters
        ----------
        beam: :class:`~compas_timber.parts.Beam`
            The beam to add

        Returns
        -------
        int
            The graph key identifier of the added beam.
        """
        if beam.assembly:
            raise AssemblyError("Beam is already associated with an Assembly! Cannot be added to an additional one.")
        key = self.add_part(part=beam, type="part_beam")
        self._beams.append(beam)
        beam.assembly = self
        return key

    def add_plate(self, plate):
        raise NotImplementedError

    def remove_part(self, part):
        raise NotImplementedError

    def add_joint(self, joint, parts):
        """Add a joint object to the assembly.

        Parameters
        ----------
        joint : :class:`~compas_timber.parts.joint`
            An instance of a Joint class.

        parts : A list of instances of e.g. a Beam class.
                The Beams and other Parts (dowels, steel plates) involved in the joint.

        key : int | str, optional
            The identifier of the joint in the assembly.
            Note that the key is unique only in the context of the current assembly.
            Nested assemblies may have the same `key` value for one of their parts.
            Default is None, in which case the key will be an automatically assigned integer value.

        Returns
        -------
        int | str
            The identifier of the joint in the current assembly graph.
        """
        self._validate_joining_operation(joint, parts)
        # create an unconnected node in the graph for the joint object
        key = self.add_part(part=joint, type="joint")
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
        """
        Removes a joint from the assembly, i.e. disconnects it from assembly and from its parts. Does not delete the object.
        """
        del self._parts[joint.guid]
        self.graph.delete_node(joint.key)
        joint.assembly = None  # TODO: should not be needed

    def are_parts_joined(self, parts):
        """
        Checks if there is already a joint defined for the same set of parts.
        """

        # method 1
        n = len(parts)
        neighbor_keys = [set(self.graph.neighborhood(self._parts[part.guid], ring=1)) for part in parts]
        for i in range(n-1):
            nki = neighbor_keys[i]
            for j in range(i + 1, n):
                nkj = neighbor_keys[j]
                nkx = nki.intersection(nkj)
                for x in nkx:
                    if self.graph.node[x]['type']=='joint':
                        return True
        return False

        # # method 2: assuming that every part is joined through a Joint object, i.e. assume that parts are 2nd-ring neighbours.
        # n = len(parts)
        # for i in range(n - 1):
        #     neighbor_keys = self.graph.neighborhood(self._parts[parts[i].guid], ring=2)
        #     for j in range(i + 1, n):
        #         if self._parts[parts[j].guid] in neighbor_keys: return True
        # return False

    def apply_joint_features(self):
        """
        Triggers the application of the joint features to their associated beams.

        Returns
        -------
        None
        """
        for joint in self.joints:
            joint.add_features()

    def print_structure(self):
        pprint("Beams:\n", self.beam_keys)
        pprint("Joints:\n", self.joint_keys)

        for joint in self.joints:
            print("[%s] %s: %s" % (joint.key, joint.type_name, joint.beam_keys))
