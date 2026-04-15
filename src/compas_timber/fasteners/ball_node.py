from compas.geometry import Box
from compas.geometry import Cylinder
from compas.geometry import Frame
from compas.geometry import Plane
from compas.geometry import Sphere
from compas.geometry import dot_vectors

from compas_timber.fabrication import JackRafterCut

from .part import Part


class BallNode(Part):
    def __init__(self, diameter: float, frame: Frame = Frame.worldXY()):
        self.diameter = diameter
        self.frame = frame

    def copy(self):
        ball_node = BallNode(self.diameter, self.frame.copy())
        return ball_node

    @property
    def radius(self):
        return self.diameter / 2

    @property
    def frame(self):
        return self._frame

    @frame.setter
    def frame(self, value):
        if not isinstance(value, Frame):
            raise ValueError("Frame should be a Frame.")
        self._frame = value

    @property
    def geometry(self):
        sphere = Sphere(self.radius, self.frame)
        sphere_brep = sphere.to_brep()
        return sphere_brep

    def apply_features(self, elements):
        pass


class BallNodeRod(Part):
    def __init__(self, length: float, diameter: float, frame: Frame = Frame.worldXY()):
        self.length = length
        self.diameter = diameter
        self.frame = frame

    def copy(self):
        rod = BallNodeRod(self.length, self.diameter, self.frame.copy())
        return rod

    @property
    def frame(self):
        return self._frame

    @frame.setter
    def frame(self, value):
        if not isinstance(value, Frame):
            raise ValueError("Frame should be a Frame.")
        self._frame = value

    @property
    def geometry(self):
        cylinder = Cylinder(radius=self.diameter / 2, height=self.length, frame=self.frame)
        cylinder.frame.point += self.frame.zaxis * self.length / 2
        cylinder_brep = cylinder.to_brep()
        return cylinder_brep

    def apply_features(self, elements):
        pass


class BallNodePlate(Part):
    def __init__(self, thickness, frame):
        self.frame = frame
        self.thicknees = thickness

    @property
    def frame(self):
        return self._frame

    @frame.setter
    def frame(self, value):
        if not isinstance(value, Frame):
            raise ValueError("Frame should be a Frame.")
        self._frame = value

    @property
    def geometry(self):
        box = Box(100, 100, self.thicknees, frame=self.frame)
        box.frame.point += self.frame.zaxis * self.thicknees / 2
        box_brep = box.to_brep()
        return box_brep

    def copy(self):
        plate = BallNodePlate(self.thicknees / (2), self.frame.copy())
        return plate

    def apply_features(self, elements):
        cutting_plane = Plane(self.frame.point, self.frame.zaxis)
        cutting_plane.translate(self.frame.zaxis * self.thicknees)

        features = []
        for ele in elements:
            if dot_vectors(ele.frame.xaxis, cutting_plane.normal) >= 0.8:
                cutting_plane.normal *= -1
                jrc = JackRafterCut.from_plane_and_beam(cutting_plane, ele)
                ele.add_feature(jrc)
                features.append(jrc)
        return features
