from compas.geometry import Plane
from compas.geometry import Point
from compas.geometry import Vector
from compas.geometry import cross_vectors

from compas_timber.utils.compas_extra import intersection_line_line_3D

from ..connections.joint import Joint


class LMiterJoint(Joint):
    def __init__(self, assembly, beamA, beamB):

        super(LMiterJoint, self).__init__(assembly, [beamA, beamB])
        self.beamA = beamA
        self.beamB = beamB

    @property
    def joint_type(self):
        return "L-Miter"

    def add_feature(self):
        """
        Adds the feature definitions (geometry, operation) to the involved beams.
        In a T-Butt joint, adds the trimming plane to the main beam (no features for the cross beam).
        """
        # TODO: how to saveguard this being added multiple times?
        plnA, plnB = self.cutting_planes
        self.beamA.add_feature(plnA, "trim")
        self.beamB.add_feature(plnB, "trim")
        # pass

    @property
    def cutting_planes(self):

        vA = Vector(*self.beamA.frame.xaxis)  # frame.axis gives a reference, not a copy
        vB = Vector(*self.beamB.frame.xaxis)

        # intersection point (average) of both centrelines
        pxA, pxB = intersection_line_line_3D(
            self.beamA.centreline,
            self.beamB.centreline,
            max_distance=self.beamA.height + self.beamB.height,
            limit_to_segments=False,
            return_t=False,
            tol=self.assembly.tol,
        )

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

        plnA = Plane(p, v_normal * -1.0)
        plnB = Plane(p, v_normal)

        return [plnA, plnB]
