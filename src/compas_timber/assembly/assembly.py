from compas.datastructures import Assembly
import copy
from pprint import pprint
from compas_timber.connections.joint import Joint


class TimberAssembly(Assembly):
    """
    A data structure for managing the assembly. Assembly consist of parts and joints. 
    Parts are entities with a substantial physical presence, for example: beams, dowels, screws.
    Joints are abstract entities to describe how parts are joined together, for example: two beams joining through a lap joint with a screw or dowel through it. 
    Connections are low-level abstractions to link the joined parts, for example: beam1-beam2, beam1-dowel, beam2-dowel.
    TODO: Features - are they only attached to parts? what if a feature is shared by multiple parts?
    TODO: are nails parts? Glue?
    TODO: other model-level features/metadata, e.g. structural (loads, supports),..
    """

    def __init__(self,
                 _beams=None,
                 _connections=None):

        super(TimberAssembly, self).__init__()

        self.verbose = True
        self._beams = {}
        self._joints = {}
        self._connections = {}
        self.allowance = 0.000  # [m] global tolerance for joints = the gap size

        self.default_node_attributes = {
            'type': None  # string id
        }

        self.default_edge_attributes = {
            'type': None,  # string id
            'features': None,
            'location': None,
            'side': None,
            'motion': None,
            'dof': None,
            'locked': False
        }
        if _beams:
            for beam in _beams:
                self.add_beam(beam)

        if _connections:
            for connection in _connections:
                self.add_connection(connection)

    # def __copy__(self, *args, **kwargs):
    #     return self.copy()

    # def __deepcopy__(self, *args, **kwargs):
    #     result = object.__new__(self.__class__)
    #     result.__init__()
    #     result._beams = copy.deepcopy(self._beams)
    #     result._joints = copy.deepcopy(self._joints)
    #     result._connections = copy.deepcopy(self._connections)
    #     result.default_node_attributes = copy.deepcopy(self.default_node_attributes)
    #     result.default_edge_attributes = copy.deepcopy(self.default_edge_attributes)
    #     result.allowance = self.allowance
    #     result.verbose = self.verbose
    #     return result

    @property
    def beams(self):
        return [self._beams.get(key) for key in self.graph.nodes_where({'type': 'beam'})]

    @property
    def connections(self):
        return [self._connections.get(key) for key in self.graph.edges_where({'type': 'connection'})]

    @property
    def joints(self):
        return [self._joints.get(key) for key in self.graph.nodes_where({'type': 'joint'})]

    @property
    def beam_keys(self):
        return list(self.graph.nodes_where({'type': 'beam'}))

    @property
    def joint_keys(self):
        return list(self.graph.nodes_where({'type': 'joint'}))

    @property
    def connection_keys(self):
        return list(self.graph.edges_where({'type': 'connection'}))

    @property
    def beam_ids(self):
        return [beam.id for beam in self.beams]

    @property
    def joint_ids(self):
        return [joint.id for joint in self.joints]

    @property
    def connection_ids(self):
        return [connection.id for connection in self.connections]

    def add_beam(self, beam, key=None):
        key = self.add_part(beam, key, type='beam')
        self._beams[key] = beam
        beam.key = key
        beam.assembly = self
        return key

    def add_joint_with_parts(self, joint, key=None):
        """Add a joint object to the assembly. 

        Parameters
        ----------
        joint : :class:`~compas_timber.parts.joint`
            An instance of a Joint class. 
            The Beams and other Parts involved in the joint must be already defined in the Joint instance.
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
        

        # do not add a joint without parts, this doesn't make sense and will create a loose node
        assert joint.part_keys != [], "Cannot add this joint to assembly, it has no parts"
        assert joint.is_in_assembly(self) == False, "This joint has already been added to this assembly."

        # create an unconnected node in the graph for the joint object
        key = self.add_part(joint, key, type='joint')
        self._joints[key] = joint
        joint.key = key
        joint.assembly = self 

        # adds links to the beams
        for part in joint.parts:
            self.graph.add_edge(part.key, joint.key, type='connection') 
        return key     

    def remove_joint(self, joint):
        """
        Removes a joint from the assembly, i.e. disconnects it from assembly and from its parts. Does not delete the object.
        """
        assert joint.key in self.joint_keys
        self.graph.delete_node(joint.key)
        joint.part_keys = []
        joint.assembly = None

    def are_parts_joined_already(self,part_keys):
        """
        Checks if there is already a(nother) joint defined for the same set of parts
        """
        # TODO: could also restrict the search to beam objects only

        for j in self.joints:
            if set(j.part_keys) == set(part_keys):
                return True
        return False


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
        pprint("Beams:\n",self.beam_keys)
        pprint("Joints:\n",self.joint_keys)

        for joint in self.joints:
            print("[%s] %s: %s"%(joint.key, joint.type_name, joint.beam_keys))
