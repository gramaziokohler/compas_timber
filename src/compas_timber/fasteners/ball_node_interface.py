from __future__ import annotations

from compas.geometry import Box
from compas.geometry import Brep
from compas.geometry import Cylinder
from compas.geometry import Frame
from compas.geometry import Plane

from compas_timber.elements import Beam
from compas_timber.fabrication import JackRafterCutProxy
from compas_timber.fasteners.interface import Interface


class BallNodeInterface(Interface):
    def __init__(self, frame, length, **kwargs):
        super().__init__(frame=frame, **kwargs)
        self.length = length
        self.plate_thickness = 1
        self._beam = None

    @property
    def __data__(self):
        return {"type": "BallNodeInterface", "frame": self.frame.__data__, "length": self.length}

    @classmethod
    def __from_data__(cls, data):
        frame = Frame.__from_data__(data["frame"])
        length = data["length"]
        return cls(frame, length)

    def apply_to_fastener_geometry(self, fastener_geometry):
        """
        Applies the screw to the fastener geometry
        """
        # Small Rod
        cylinder_frame = self.frame.copy()
        cylinder_frame.point += cylinder_frame.zaxis * self.length / 2
        cylinder = Cylinder(1.5, self.length, frame=cylinder_frame)
        cylinder_geometry = Brep.from_cylinder(cylinder)
        fastener_geometry += cylinder_geometry

        # Plate
        # Find the ref side of the beam close to the ball_node
        if self._beam:
            ref_side: Frame = min(self._beam.ref_sides, key=lambda x: x.point.distance_to_point(self.frame.point)).copy()
            height = self._beam.height
            width = self._beam.width
            ref_side.point = self.frame.point + (self.length - self.plate_thickness / 2) * self.frame.zaxis
            plate_geometry = Brep.from_box(Box(self.plate_thickness, width, height, frame=ref_side))
            fastener_geometry += plate_geometry

        return fastener_geometry

    def feature(self, element, transformation_to_joint):
        rafter_cut_frame = self.frame.copy()
        rafter_cut_frame.point += rafter_cut_frame.zaxis * self.length
        cutting_plane = Plane.from_frame(rafter_cut_frame)
        cutting_plane.normal *= -1
        try:
            jkrc = JackRafterCutProxy.from_plane_and_beam(cutting_plane, element)
            print(jkrc)
            return [jkrc]
        except Exception as e:
            print(f"Error creating JackRafterCut: {e}")
            return []

    def apply_features_to_elements(self, joint, transformation_to_joint):
        for beam in joint.elements:
            if not isinstance(beam, Beam):
                continue

            if abs(self.frame.zaxis.dot(beam.centerline.direction)) > 0.999:
                self._beam = beam
                processings = self.feature(beam, transformation_to_joint)
                beam.features.extend(processings)
