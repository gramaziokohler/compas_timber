from pprint import pprint

from compas.datastructures import Assembly

from compas_timber.connections.joint import Joint


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

    @property
    def units(self):
        return self._units

    @units.setter
    def units(self, units_name):
        if not units_name in self._units_precision.keys():
            raise ValueError(
                "The units parameters must be one of the following strings: %s."
                % self._units_precision.keys()
            )
        else:
            self._units = units_name

    @property
    def tol(self):
        # TODO: change to compas PRECISION
        return self._units_precision[self.units]

    @property
    def beams(self):
        return [self.find_by_key(key) for key in self.beam_keys]

    @property
    def joints(self):
        return [self.find_by_key(key) for key in self.joint_keys]

    @property
    def part_keys(self):
        return list(
            self.graph.nodes_where_predicate(lambda _, attr: "part" in attr["type"])
        )

    @property
    def beam_keys(self):
        return list(self.graph.nodes_where({"type": "part_beam"}))

    @property
    def joint_keys(self):
        return list(self.graph.nodes_where({"type": "joint"}))

    def contains(self, obj):
        """
        Checks if this assembly already contains a given part or joint.
        """
        # omitting (object.assembly is self) check for now
        return obj.guid in self._parts

    def add_beam(self, beam):
        key = self.add_part(part=beam, type="part_beam")
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

        assert parts != [], "Cannot add this joint to assembly: no parts given."
        assert (
            self.contains(joint) == False
        ), "This joint has already been added to this assembly."
        assert all(
            [self.contains(part) == True for part in parts]
        ), "Cannot add this joint to assembly: some of the parts are not in this assembly."
        # TODO: rethink this assertion, maybe it should be possible to have more than 1 joint for the same set of parts
        assert (
            self.are_parts_joined(parts) == False
        ), "Cannot add this joint to assembly: some of the parts are already joined."

        # create an unconnected node in the graph for the joint object
        key = self.add_part(part=joint, type="joint")
        joint.assembly = self

        # adds links to the beams
        for part in parts:
            self.add_connection(part, joint)
        return key

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

    def print_structure(self):
        pprint("Beams:\n", self.beam_keys)
        pprint("Joints:\n", self.joint_keys)

        for joint in self.joints:
            print("[%s] %s: %s" % (joint.key, joint.type_name, joint.beam_keys))
