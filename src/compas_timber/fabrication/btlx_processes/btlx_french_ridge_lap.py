import xml.etree.ElementTree as ET
import math

from compas.geometry import angle_vectors
from compas.geometry import angle_vectors_signed

from compas_timber.parts.beam import Beam
from compas_timber.connections.joint import Joint
from compas_timber.connections import FrenchRidgeLapJoint
from compas_timber.fabrication.btlx import BTLxProcess
from compas_timber.fabrication.btlx import BTLx

class BTLxFrenchRidgeLap(BTLxProcess):
    def __init__(self, joint, part):
        super().__init__()
        self.part = part
        self.joint = joint
        self.apply_process = True


        if self.part is self.joint.parts[0]:
            self.other_part = self.joint.parts[1]
        else:
            self.other_part = self.joint.parts[0]


        #self.check_geometry()

        """
        the following attributes hold values used to create process_params
        """
        self.orientation = "start"
        self.startX = 0.0
        self.angle_rad = 0.0
        self.ref_edge = True
        self._drill_hole = True
        self.drill_hole_diameter = 10.0

        """
        the following attributes are required for all processes, but the keys and values of header_attributes are process specific.
        """
        self.process_type = "FrenchRidgeLap"
        self.header_attributes = {
            "Name": "Jack cut",
            "Process": "yes",
            "Priority": "0",
            "ProcessID": "0",
            "ReferencePlaneID": "1",
        }

    @property
    def angle(self):
        return self.angle_rad * 180 / math.pi

    @property
    def ref_position(self):
        if self.ref_edge:
            return "refedge"
        else:
            return "oppedge"

    @property
    def drill_hole(self):
        if self._drill_hole:
            return "yes"
        else:
            return "no"


    @property
    def process_params(self):
        """
        This property is required for all process types. It returns a dict with the geometric parameters to fabricate the joint.
        """
        self.generate_process()
        return {
            "Orientation": str(self.orientation),
            "StartX": f'{self.startX:.{BTLx.POINT_PRECISION}f}',
            "Angle": f'{self.angle:.{BTLx.ANGLE_PRECISION}f}',
            "RefPosition": self.ref_position,
            "Drillhole": self.drill_hole,
            "DrillholeDiam": f'{self.drill_hole_diameter:.{BTLx.ANGLE_PRECISION}f}',
        }


    # def check_geometry(self):
    #     """
    #     This method checks whether the parts are aligned as necessary to create French Ridge Lap.
    #     """
    #     if not len(self.joint.parts) == 2:
    #         raise ("French Ridge Lap requires 2 beams")

    #     if self.part is self.joint.parts[0]:
    #         self.other_part = self.joint.parts[1]
    #     else:
    #         self.other_part = self.joint.parts[0]

    #     if not (self.part.width == self.other_part.width and self.part.height == self.other_part.height):
    #         raise ("widths and heights for both beams must match for the French Ridge Lap")

    #     normal = cross_vectors(self.part.blank_frame.xaxis, self.other_part.blank_frame.xaxis)

    #     indices = []
    #     for part in self.parts:
    #         found = False
    #         for face_number in range(4):
    #             if angle_vectors(normal, part.reference_faces[face_number].normal) < 0.001:
    #                 indices.append(face_number)
    #                 found = True
    #                 break
    #         if not found:
    #             raise ("part not aligned with corner normal, no French Ridge Lap possible")
    #     if indices[1] <2:
    #         indices[1] +=2
    #     else:
    #         indices[1] -=2

    #     self.joint.reference_face_indices = (indices[0], indices[1])


    def generate_process(self):
        """
        This is an internal method to generate process parameters
        """
        self.angle_rad = angle_vectors(self.part.frame.xaxis, self.other_part.frame.xaxis)
        #self.angle_rad = angle_vectors_signed(self.part.frame.xaxis, self.other_part.frame.xaxis, self.part.frame.normal)
        if self.angle_rad < math.pi/2:
            self.angle_rad = math.pi - self.angle_rad
        self.startX = self.part.width/math.tan(math.pi-self.angle_rad)


BTLxProcess.register_process(FrenchRidgeLapJoint, BTLxFrenchRidgeLap)

