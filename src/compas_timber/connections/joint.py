from compas.data import Data
from compas.datastructures import Part
from compas.geometry import Frame
from compas.geometry import Plane
from compas.geometry import Point
from compas.geometry import Vector
from compas.geometry import angle_vectors
from compas.geometry import distance_point_point
from compas.geometry import intersection_line_line
from compas.geometry import intersection_line_plane

from compas_timber.parts.beam import Beam

# NOTE: some methods assume that for a given set of beams there is only one joint that can connect them.


class Joint(Data):
    """
    parts: beams and other parts of a joint, e.g. a dowel, a steel plate
    assembly: TimberAssembly object to which the parts belong
    """

    def __init__(self, assembly, *beams):
        super(Joint, self).__init__()
        self._assembly = assembly
        self.frame = None  # will be needed as coordinate system for structural calculations for the forces at the joint
        self.key = None

    def __deepcopy__(self, memodict):
        # Having a refernce to assembly here causes very weird behavior
        # when copying using data.copy()
        self._assembly = None
        return self.copy()

    @classmethod
    def create(cls, assembly, *beams):
        if len(beams) < 2:
            raise ValueError("Expected at least 2 beams. Got instead: {}".format(len(beams)))

        joint = cls(assembly, *beams)
        assembly.add_joint(joint, beams)
        return joint

    @property
    def data(self):
        # omitting self.assembly to avoid circular reference
        return {"frame": self.frame, "key": self.key}

    @data.setter
    def data(self, value):
        self.frame = value["frame"]
        self.key = value["key"]

    @property
    def assembly(self):
        return self._assembly

    @assembly.setter
    def assembly(self, assembly):
        self._assembly = assembly

    def __eq__(self, other):
        return (
            isinstance(other, Joint)
            and self.frame == other.frame
            # TODO: add generic comparison if two lists of beams are equal
            # self.assembly == other.assembly and #not implemented yet
            # set(self.beams)==set(other.beams) #doesn't work because Beam not hashable
        )

    @property
    def _get_part_keys(self):
        neighbor_keys = self.assembly.graph.neighbors(self.key)
        # just double-check in case the joint-node would be somehow connecting to smth else in the graph
        return [
            k
            for k in neighbor_keys
            if "part" in self.assembly.graph.node_attribute(key=k, name="type")
        ]

    @property
    def parts(self):
        return [self.assembly.find_by_key(key) for key in self._get_part_keys]

    def apply_features(self):
        raise NotImplementedError

    @property
    def beams(self):
        return [part for part in self.parts if part.__class__.__name__ == Beam.__name__]
