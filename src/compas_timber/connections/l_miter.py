from ..connections.joint import Joint
from compas.geometry import cross_vectors
from compas.geometry import Plane, Vector, Point
from compas_timber.utils.compas_extra import intersection_line_line_3D


class LMiterJoint(Joint):
    def __init__(self, beamA, beamB, assembly):

        super(LMiterJoint, self).__init__([beamA, beamB], assembly)
        self.beamA = beamA
        self.beamB = beamB

    @property
    def joint_type(self):
        return 'L-Miter'

    def add_feature(self):
        """
        Adds the feature definitions (geometry, operation) to the involved beams.
        In a T-Butt joint, adds the trimming plane to the main beam (no features for the cross beam).
        """
        # TODO: how to saveguard this being added multiple times?
        #plnA, plnB = self.cutting_planes
        #self.beamA.add_feature(plnA, 'trim')
        #self.beamB.add_feature(plnB, 'trim')
        pass

    @property
    def cutting_planes(self):
        vA = self.beamA.frame.xaxis
        vB = self.beamB.frame.xaxis

        # intersection point (average) of both centrelines
        pxA, pxB = intersection_line_line_3D(self.beamA.centreline,
                                             self.beamB.centreline,
                                             max_distance=self.beamA.height+self.beamB.height,
                                             limit_to_segments=False,
                                             return_t=False,
                                             tol=self.assembly.tol)

        p = Point((pxA.x+pxB.x)*0.5, (pxA.y+pxB.y)*0.5, (pxA.z+pxB.z)*0.5)

        # makes sure they point outward of a joint point
        tA, _ = self.beamA.endpoint_closest_to_point(pxA)
        if tA == 'end':
            vA *=-1.0
        tB, _ = self.beamA.endpoint_closest_to_point(pxB)
        if tB == 'end':
            vB*=-1.0

        # bisector
        v_bisector = vA+vB
        v_bisector.unitize()

        # get frame
        v_perp = Vector(*cross_vectors(vA, vB))
        v_normal = Vector(*cross_vectors(v_bisector, v_perp))

        plnA = Plane(p, v_normal)
        plnB = Plane(p, v_normal*-1.0)

        return [plnA, plnB]
