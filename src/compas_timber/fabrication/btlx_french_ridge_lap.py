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

        # self.check_geometry()

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
            "StartX": "{:.{prec}f}".format(self.startX, prec = BTLx.POINT_PRECISION),
            "Angle": "{:.{prec}f}".format(self.angle, prec = BTLx.POINT_PRECISION),
            "RefPosition": self.ref_position,
            "Drillhole": self.drill_hole,
            "DrillholeDiam":"{:.{prec}f}".format(self.drill_hole_diameter, prec = BTLx.POINT_PRECISION),
        }

    def generate_process(self):
        """
        This is an internal method to generate process parameters
        """
        self.angle_rad = angle_vectors(self.part.frame.xaxis, self.other_part.frame.xaxis)
        # self.angle_rad = angle_vectors_signed(self.part.frame.xaxis, self.other_part.frame.xaxis, self.part.frame.normal)
        if self.angle_rad < math.pi / 2:
            self.angle_rad = math.pi - self.angle_rad
        self.startX = self.part.width / math.tan(math.pi - self.angle_rad)


BTLxProcess.register_process(FrenchRidgeLapJoint, BTLxFrenchRidgeLap)
