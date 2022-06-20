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
    Keys of the nodes are strings equal to the guids of the objects stored in them.

    """

    def __init__(self, **kwargs):
        super(TimberAssembly, self).__init__()

        self.default_node_attributes = {
            'type': None,  # string 'beam', 'joint', 'other_part'
            'object': None  # instance of the given object
        }

        self.default_edge_attributes = {
            'type': None,  # not being used at the moment
        }

        self._units = 'meters'  # options: 'meters', 'millimeters' #TODO: change to global compas PRECISION

        self._units_precision = {
            'meters': 1e-9,
            'millimeters': 1e-6
        }

    def __eq__(self, other):
        return self is other #TODO: by ref comparison for now
        #raise NotImplementedError

    @property
    def units(self):
        return self._units

    @units.setter
    def units(self, units_name):
        if not units_name in self._units_precision.keys():
            raise ValueError("The units parameters must be one of the following strings: %s." % self._units_precision.keys())
        else:
            self._units = units_name

    @property
    def tol(self):
        # TODO: change to compas PRECISION
        return self._units_precision[self.units]

    #NOTE:cannot be @property, because of implementation in compas.Assembly
    def parts(self):
        return [self.find_by_key(key) for key in self.part_keys]

    @property
    def beams(self):
        return [self.find_by_key(key) for key in self.beam_keys]

    @property
    def joints(self):
        return [self.find_by_key(key) for key in self.joint_keys]

    @property
    def part_keys(self):
        return list(self.graph.nodes_where_predicate(lambda _, attr: "part" in attr["type"]))

    @property
    def beam_keys(self):
        return list(self.graph.nodes_where({'type': 'part_beam'}))

    @property
    def joint_keys(self):
        return list(self.graph.nodes_where({'type': 'joint'}))

    def contains(self, obj):
        """
        Checks if this assembly already contains a given part or joint.
        """
        # omitting (object.assembly is self) check for now
        return str(obj.guid) in self.graph.node.keys()


    def add_part(self, part, type):
        if self.contains(part):
            raise UserWarning("This part will not be added: it is already in the assembly (%s)" % part)
        key = self.graph.add_node(key=str(part.guid), object=part, type=type)
        part.key = key
        part.assembly = self
        return key

    def add_beam(self, beam):
        key = self.add_part(beam, type='part_beam')
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
        assert self.contains(joint) == False, "This joint has already been added to this assembly."
        assert all([self.contains(part) == True for part in parts]), "Cannot add this joint to assembly: some of the parts are not in this assembly."
        # TODO: rethink this assertion, maybe it should be possible to have more than 1 joint for the same set of parts
        assert self.are_parts_joined(parts) == False, "Cannot add this joint to assembly: some of the parts are already joined."

        # create an unconnected node in the graph for the joint object
        key = self.graph.add_node(key=str(joint.guid), object=joint, type='joint')
        joint.key = key
        joint.assembly = self

        # adds links to the beams
        for part in parts:
            self.graph.add_edge(part.key, joint.key)
        return key

    def remove_joint(self, joint):
        """
        Removes a joint from the assembly, i.e. disconnects it from assembly and from its parts. Does not delete the object.
        """
        self.graph.delete_node(joint.key)
        joint.assembly = None

    def are_parts_joined(self, parts):
        """
        Checks if there is already a joint defined for the same set of parts.
        """
        part_keys = [p.key for p in parts]
        return any([set(j._get_part_keys) == set(part_keys) for j in self.joints])

    def get_beam_keys_connected_to(self, beam_key):
        nbrs = self.neighbors(beam_key, ring=2)
        return [n for n in nbrs if n in self.beam_keys and n != beam_key]

    def get_beam_ids_connected_to(self, beam_id):
        beam_key = self.get_beam_key_from_id(beam_id)
        nbrs = self.get_beam_keys_connected_to(beam_key)
        return [self.get_beam_id_from_key(n) for n in nbrs]

    def get_beam_key_from_id(self, beam_id):
        for beam_key, beam in self._beams.items():
            if beam.id == beam_id:
                return beam_key

    def get_beam_id_from_key(self, beam_key):
        beam = self._beams.get(beam_key)
        if beam:
            return beam.id

    def print_structure(self):
        pprint("Beams:\n", self.beam_keys)
        pprint("Joints:\n", self.joint_keys)

        for joint in self.joints:
            print("[%s] %s: %s" % (joint.key, joint.type_name, joint.beam_keys))

    def find_by_key(self, key):
        key = str(key)
        if key not in self.graph.node:
            return None
        return self.graph.node_attribute(key, 'object')
