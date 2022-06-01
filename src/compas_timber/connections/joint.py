from compas.geometry import intersection_line_line, intersection_line_plane, distance_point_point, angle_vectors
from compas.geometry import Vector, Point, Plane
from compas.data import Data
from compas_timber.parts.beam import Beam
from compas.datastructures import Part


# NOTE: some methods assume that for a given set of beams there is only one joint that can connect them.


class Joint(Data):
    """
    parts: beams and other parts of a joint, e.g. a dowel, a steel plate
    assembly: TimberAssembly object to which the parts belong
    """

    def __init__(self, parts, assembly):
        super(Joint, self).__init__()
        self.assembly = None
        self.key = None
        self.frame = None  # will be needed as coordinate system for structural calculations for the forces at the joint

        assembly.add_joint(self, parts)

    @property
    def _part_keys(self):
        n = self.assembly.graph.neighbors(self.key)
        return [k for k in n if self.assembly.node_attribute('type') == 'part']  # just double-check in case the joint-node would be somehow connecting to smth else in the graph

    @property
    def parts(self):
        return [self.assembly.find_by_key(key) for key in self._part_keys]

    @property
    def beams(self):
        return [part for part in self.parts if isinstance(part, Beam)]
