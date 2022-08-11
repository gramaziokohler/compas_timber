from compas.geometry import Plane
from compas.geometry import Point
from compas.geometry import Vector
from compas.geometry import cross_vectors
from compas.geometry import Frame

from compas_timber.utils.compas_extra import intersection_line_line_3D

from ..connections.joint import Joint


class LMiterJoint(Joint):
    def __init__(self, assembly=None, beamA=None, beamB=None):

        super(LMiterJoint, self).__init__(assembly, [beamA, beamB])
        self.beamA = beamA
        self.beamB = beamB
        self.beamA_key = None
        self.beamB_key = None
        self.features = []

    @property
    def joint_type(self):
        return "L-Miter"

    @property
    def data(self):
        data_dict = {
            "beamA_key": self.beamA.key,
            "beamB_key": self.beamB.key,
        }
        data_dict.update(Joint.data.fget(self))
        return data_dict

    @data.setter
    def data(self, value):
        Joint.data.fset(self, value)
        self.beamA_key = value["beamA_key"]
        self.beamB_key = value["beamB_key"]

    @Joint.assembly.setter
    def assembly(self, assembly):
        Joint.assembly.fset(self, assembly)
        self.beamA = self.assembly.find_by_key(self.beamA_key)
        self.beamB = self.assembly.find_by_key(self.beamB_key)

    @Joint.assembly.setter
    def assembly(self, assembly):
        Joint.assembly.fset(self, assembly)
        self.beamA = assembly.find_by_key(self.beamA_key)
        self.beamB = assembly.find_by_key(self.beamB_key)



    def add_features(self, apply = False):
        plnA, plnB = self.cutting_planes

        plnA = Frame.from_plane(plnA)
        plnB = Frame.from_plane(plnB)

        feature = self.beamA.add_feature(plnA, "trim")
        self.features.append(feature)

        feature = self.beamB.add_feature(plnB, "trim")
        self.features.append(feature)

        if apply:
            [feature.apply() for feature in self.features]

    @property
    def cutting_planes(self):

        vA = Vector(*self.beamA.frame.xaxis)  # frame.axis gives a reference, not a copy
        vB = Vector(*self.beamB.frame.xaxis)

        # intersection point (average) of both centrelines
        [pxA, tA], [pxB, tB] = intersection_line_line_3D(
            self.beamA.centerline,
            self.beamB.centerline,
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
