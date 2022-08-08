from compas.geometry import Plane
from compas.geometry import Point
from compas.geometry import Vector
from compas.geometry import cross_vectors

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

    def calc_extension(self,beam,pln):
        edges = beam.long_edges
        x = {}
        for e in edges:
            p,t = intersection_line_plane(e,pln)
            x[t]=p
        
        tmin=min(x.keys())
        tmax=max(x.keys())
        ds=0.0
        de=0.0
        if tmin<0.0:
            ds = x[tmin].distance_to_point(beam.frame.point)
        if tmax>1.0:
            de = x[tmax].distance_to_point(beam.frame.point+beam.frame.xaxis*beam.length)
        return (ds,de)


    def add_feature(self):
        """
        Adds the feature definitions (geometry, operation) to the involved beams.
        In a T-Butt joint, adds the trimming plane to the main beam (no features for the cross beam).
        """
        # TODO: how to saveguard this being added multiple times?
        plnA, plnB = self.cutting_planes

        self.beamA.add_feature(self.calc_extension(self.beamA,plnA), "extend")
        self.beamB.add_feature(self.calc_extension(self.beamB,plnB), "extend")

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

    

