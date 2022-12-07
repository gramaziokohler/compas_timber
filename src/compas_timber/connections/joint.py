from compas_future.datastructures import Part
from compas.data import Data
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


class BeamJoinningError(BaseException):
    """Indicates that an error has occurred while trying to join two or more beams."""
    

class Joint(Data):
    """
    parts: beams and other parts of a joint, e.g. a dowel, a steel plate
    assembly: TimberAssembly object to which the parts belong
    """

    def __init__(self, assembly=None, *args, **kwargs):
        super(Joint, self).__init__()
        self._assembly = assembly  # TODO: CK: not sure we need this here
        # will be needed as coordinate system for structural calculations for the forces at the joint
        # TODO: CK: who's supposed to sets these?
        self.frame = None  
        self.key = None

    def __deepcopy__(self, memodict):
        # Having a refernce to assembly here causes very weird behavior
        # when copying using data.copy()
        # get rid of it for the sake of copying then restore so that the original is still valid
        assembly = self._assembly
        self._assembly = None
        c = self.copy()
        self._assembly = assembly
        return c

    @classmethod
    def create(cls, assembly, beams):
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

    def __ne__(self, other):
        return not self.__eq__(other)

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

    def add_features(self, apply=True):
        raise NotImplementedError

    @property
    def beams(self):
        return [part for part in self.parts if part.__class__.__name__ == Beam.__name__]
        # return [part for part in self.parts if isinstance(part, Beam)]
        # return [part for part in self.parts if self.assembly.graph.node[part.key]['type']=='part_beam']



def beam_side_incidence(beam1, beam2):
    """

    Parameters
    ----------
    beam1 : Beam
        The beam that attaches with one of its ends to the side of Beam2.
    beamm2 : Beam
        The other beamm

    Returns
    -------
    List of tuples (angle, frame)
        For each side of Beam2, the angle (in radians) between the x-axis of Beam1 and normal vector of the side frame.
    """

    # find the orientation of beam1's centerline so that it's pointing outward of the joint
    #   find the closest end
    p1x, p2x = intersection_line_line(beam1.centerline, beam2.centerline)
    which,_ = beam1.endpoint_closest_to_point(Point(*p1x))

    if which == 'start':
        centerline_vec = beam1.centerline.vector
    else:
        centerline_vec = beam1.centerline.vector*-1

    # compare with side normals
    angles = [
        angle_vectors(beam2.faces[i].normal, centerline_vec)
        for i in range(4)
        ]

    # map faces to their angle with centerline, choose smallest
    angle_face = [(angle_vectors(side.normal, centerline_vec), side) for side in beam2.faces[:4]]
    return angle_face
