from compas.geometry import intersection_line_line, intersection_line_plane, distance_point_point, angle_vectors
from compas.geometry import Vector, Point, Plane
from compas.data import Data

#TODO: replace direct references to beam objects

class TButtJoint(Data):
    def __init__(self, assembly=None, main_beam=None, cross_beam=None):
        super(TButtJoint, self).__init__()
        self.assembly = assembly
        self.main_beam_key = main_beam.key
        self.cross_beam_key = cross_beam.key
        # self.gap = gap #float, additional gap, e.g. for glue
        self.joint_type_name = 'T-Butt'
        self.frame = None # will be needed as coordinate system for structural calculations for the forces at the joint

        assembly.add_joint(self)
        assembly.connect(self,[main_beam, cross_beam])

    # TODO: add this property to some joint template class
    @property
    def beams(self):
        return [self.main_beam, self.cross_beam]

    @property
    def main_beam(self): 
        return self.assembly.find_by_key(self.main_beam_key)

    @property
    def cross_beam(self): 
        return self.assembly.find_by_key(self.cross_beam_key)

    @property
    def __find_side(self):
        """
        calculate which side of the cross beam is the cutting side for the main beam
        """

        # find the orientation of the mainbeam's centreline so that it's pointing outward of the joint
        #   find the closest end
        pm, pc = intersection_line_line(self.main_beam.centreline, self.cross_beam.centreline)
        p1 = self.main_beam.centreline.start
        p2 = self.main_beam.centreline.end
        d1 = distance_point_point(pm, p1)
        d2 = distance_point_point(pm, p2)

        if d1 < d2:
            centreline_vec = Vector.from_start_end(p1, p2)
        else:
            centreline_vec = Vector.from_start_end(p2, p1)

        # compare with side normals
        angles = [angle_vectors(self.cross_beam.side_frame(i).normal, centreline_vec) for i in range(4)]
        x = list(zip(angles, range(4)))
        x.sort()
        side = x[0][1]
        return side

    @property
    def cutting_plane(self):
        cfr = self.cross_beam.side_frame(self.__find_side)
        #TODO: move the frame's center to the intersection
        #cfr.point = Point(intersection_line_plane(self.main_beam.centreline, Plane.from_frame(cfr))[0], 1e-6)     
        #TODO: flip normal 
        return cfr

    def apply_feature(self):
        #TODO: how to saveguard this being added multiple times? 
        self.main_beam.add_feature(self.cutting_plane, 'trim')