import math

from compas.geometry import Box
from compas.geometry import Brep
from compas.geometry import Cylinder
from compas.geometry import Frame
from compas.geometry import Plane
from compas.geometry import Sphere
from compas.geometry import Vector
from compas.geometry import dot_vectors

from compas_timber.elements.beam import Beam
from compas_timber.fabrication import JackRafterCut
from compas_timber.fabrication import Slot

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
    def __init__(self, length: float, diameter: float, beam, frame: Frame = Frame.worldXY()):
        self.length = length
        self.diameter = diameter
        self.frame = frame
        self.referenced_beam = beam

    def copy(self):
        rod = BallNodeRod(self.length, self.diameter, self.referenced_beam, self.frame.copy())
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
    def __init__(self, x_size, y_size, thickness, frame, plate_depth, rod, ball):
        self.x_size = x_size
        self.y_size = y_size
        self.frame = frame
        self.thicknees = thickness
        self.plate_depth = plate_depth
        self.rod = rod
        self.ball = ball

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
        # cap plate
        box = Box(self.x_size, self.y_size, self.thicknees, frame=self.frame)
        box.frame.point += self.frame.zaxis * self.thicknees / 2
        box_brep = box.to_brep()

        # slot_plate
        slot_plate_frame = self.frame.copy()
        slot_plate_frame.translate(slot_plate_frame.zaxis * (self.thicknees + self.plate_depth / 2))
        box = Box(self.thicknees, self.y_size, self.plate_depth, frame=slot_plate_frame)
        slot_brep = box.to_brep()

        full_brep = Brep.from_boolean_union(box_brep, slot_brep)[0]
        return full_brep

    def copy(self):
        plate = BallNodePlate(self.x_size, self.y_size, self.thicknees / (2), self.frame.copy(), self.plate_depth, self.rod.copy(), self.ball.copy())
        return plate

    def apply_features(self, elements):
        features = []
        for ele in elements:
            if ele is self.rod.referenced_beam:
                cutting_plane = Plane(self.frame.point, self.frame.zaxis)
                cutting_plane.translate(self.frame.zaxis * self.thicknees)
                cutting_plane.normal *= -1

                # jack rafter cut
                jrc = JackRafterCut.from_plane_and_beam(cutting_plane, ele)
                ele.add_feature(jrc)
                features.append(jrc)

                # slot
                plane = Plane(self.frame.point, self.frame.xaxis)
                slot_depth = self.plate_depth + self.thicknees + self.rod.length + self.ball.radius
                slot = Slot.from_plane_and_beam(plane, ele, slot_depth, self.thicknees)
                ele.add_feature(slot)
                features.append(slot)

        return features
