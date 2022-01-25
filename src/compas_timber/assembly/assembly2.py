from compas.datastructures import Assembly 


class TimberAssembly(Assembly):
    def __init__(self,
                 _beams=None,
                 _connections=None):

        super(TimberAssembly, self).__init__()

        self.verbose = True
        self._beams = {}
        self._connections = {}
        self.allowance = 0.000 #[m] global tolerance for joints = the gap size

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
        return [self._beams.get(key) for key in self.nodes_where({"type": "beam"})]

    @property
    def connections(self):
        return [self._connections.get(key) for key in self.nodes_where({"type": "connection"})]

    @property
    def beam_keys(self):
        return list(self.nodes_where({"type": "beam"}))

    @property
    def connection_keys(self):
        return list(self.nodes_where({"type": "connection"}))

    @property
    def beam_ids(self):
        return [beam.id for beam in self.beams]

    @property
    def connection_ids(self):
        return [connection.id for connection in self.connections]


    def add_beam(self, beam, key=None):
        key = self.add_part(beam, key, type="beam")
        self._beams[key] = beam
        beam.key = key
        return key

    def add_connection(self, connection, key=None):
        key = self.add_part(connection, key, type="connection")
        self._connections[key] = connection
        connection.key = key
        return key

    def connect(self, key_u, key_v, key_c, attr_dict=None):
        attr = attr_dict or {}

        u = self.graph.add_edge(key_u, key_c, attr_dict=attr)
        v = self.graph.add_edge(key_v, key_c, attr_dict=attr)
        return u, v

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