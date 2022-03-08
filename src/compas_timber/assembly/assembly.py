from compas.datastructures import Assembly


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
        return key

    def add_joint(self, joint, key=None):
        """Add a joint object to the assembly. 
        
        Parameters
        ----------
        joint : :class:`~compas_timber.parts.joint`
            An instance of a Joint class. 
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

        key = self.add_part(joint, key, type='joint')
        self._joints[key] = joint
        joint.key = key
        return key

    def add_connection(self, connection, key=None): 
        #TODO: do I need this?
        key = self.add_connection(connection, key, type='connection')
        self._connections[key] = connection
        connection.key = key
        return key

    def connect(self, parts, joint, attr_dict=None):
        attr = attr_dict or {}
        for part in parts:
            self.graph.add_edge(part.key, joint.key, type='connection')  # attr_dict=attr)
        return

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
