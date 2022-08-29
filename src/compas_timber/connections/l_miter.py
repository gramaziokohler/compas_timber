from compas.geometry import Plane
from compas.geometry import Point
from compas.geometry import Vector
from compas.geometry import cross_vectors
from compas.geometry import Frame

from compas_timber.utils.compas_extra import intersection_line_line_3D
from compas_timber.utils.compas_extra import intersection_line_plane

from ..connections.joint import Joint


class LMiterJoint(Joint):
    def __init__(self, assembly, beamA, beamB, cutoff = None):

        super(LMiterJoint, self).__init__(assembly, [beamA, beamB])
        self.beamA = beamA
        self.beamB = beamB
        self.cutoff = cutoff #for very acute angles, limit the extension of the tip/beak of the joint 

    @property
    def joint_type(self):
        return "L-Miter"

    def add_features(self):
        """
        Adds the feature definitions (geometry, operation) to the involved beams.
        """
        plnA, plnB = self.cutting_planes

        self.beamA.add_feature(self.beamA.extension_to_plane(plnA), "extend")
        self.beamB.add_feature(self.beamB.extension_to_plane(plnB), "extend")

        self.beamA.add_feature(plnA, "trim")
        self.beamB.add_feature(plnB, "trim")


    @property
    def cutting_planes(self):

        vA = Vector(*self.beamA.frame.xaxis)  # frame.axis gives a reference, not a copy
        vB = Vector(*self.beamB.frame.xaxis)

        # intersection point (average) of both centrelines
        [pxA,tA], [pxB,tB] = intersection_line_line_3D(
            self.beamA.centreline,
            self.beamB.centreline,
            max_distance=self.beamA.height + self.beamB.height,
            limit_to_segments=False,
            tol=self.assembly.tol,
        )
        #TODO: add error-trap + solution for I-miter joints

        p = Point((pxA.x + pxB.x) * 0.5, (pxA.y + pxB.y) * 0.5, (pxA.z + pxB.z) * 0.5)

        # makes sure they point outward of a joint point
        tA, _ = self.beamA.endpoint_closest_to_point(pxA)
        if tA == "end":
            vA *= -1.0
        tB, _ = self.beamB.endpoint_closest_to_point(pxB)
        if tB == "end":
            vB *= -1.0

        # bisector
        v_bisector = vA + vB
        v_bisector.unitize()

        # get frame
        v_perp = Vector(*cross_vectors(v_bisector, vA))
        v_normal = Vector(*cross_vectors(v_bisector, v_perp))

        plnA = Plane(p, v_normal )
        plnB = Plane(p, v_normal * -1.0)

        plnA = Frame.from_plane(plnA)
        plnB = Frame.from_plane(plnB)
        return [plnA, plnB]

    

