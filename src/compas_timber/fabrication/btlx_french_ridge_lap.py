import math
from collections import OrderedDict
from compas.geometry import Vector
from compas.geometry import Frame
from compas.geometry import angle_vectors
from compas.geometry import angle_vectors_signed
from compas.geometry import Rotation

from compas_timber.parts.beam import Beam
from compas_timber.connections.joint import Joint
from compas_timber.connections import FrenchRidgeLapJoint
from compas_timber.fabrication import BTLx
from compas_timber.fabrication import BTLxJoint
from compas_timber.fabrication import BTLxProcess
#from compas_timber.fabrication import BTLx

class BTLxFrenchRidgeLap(object):
    PROCESS_TYPE = "FrenchRidgeLap"
    def __init__(self, part, joint, is_top, end):

        self.part = part
        for beam in joint.beams:
            if beam is part.beam:
                self.beam = beam
            else:
                self.other_beam = beam

        self.joint = joint.joint
        self.btlx_joint = joint
        self.is_top = is_top
        self.orientation = end
        self.apply_process = True
        self._ref_edge = True
        self._drill_hole = True
        self.drill_hole_diameter = 10.0

        self.ref_face_index = self.joint.reference_face_indices[str(self.beam.key)]
        self.ref_face = self.part.reference_surfaces[str(self.ref_face_index)]

        """
        the following attributes are required for all processes, but the keys and values of header_attributes are process specific.
        """

        self.main_process_type = "FrenchRidgeLap"

        self.header_attributes = {
            "Name": "French ridge lap",
            "Process": "yes",
            "Priority": "0",
            "ProcessID": "0",
            "ReferencePlaneID": str(self.ref_face_index),
        }

        self.process_joints()

    @property
    def angle(self):
        return self.angle_rad * 180 / math.pi

    @property
    def ref_edge(self):
        if self._ref_edge:
            return "refedge"
        else:
            return "oppedge"

    @property
    def drill_hole(self):
        if self._drill_hole:
            return "yes"
        else:
            return "no"


    def process_joints(self):
        """
        This property is required for all process types. It returns a dict with the geometric parameters to fabricate the joint. Use OrderedDict to maintain original order
        """
        self.get_params()

        self.process_parameters = OrderedDict([
            ("Orientation", str(self.orientation)),
            ("StartX", "{:.{prec}f}".format(self.startX, prec = BTLx.POINT_PRECISION)),
            ("Angle", "{:.{prec}f}".format(self.angle, prec = BTLx.POINT_PRECISION)),
            ("RefPosition", self.ref_edge),
            ("Drillhole", self.drill_hole),
            ("DrillholeDiam", "{:.{prec}f}".format(self.drill_hole_diameter, prec = BTLx.POINT_PRECISION)),
        ])


    def get_params(self):
        """
        This is an internal method to generate process parameters
        """



        other_vector = self.other_beam.frame.xaxis
        if self.btlx_joint.ends[str(self.other_beam.key)] == "end":
            other_vector = - other_vector

        self.angle_rad = angle_vectors_signed(self.ref_face.xaxis, other_vector, self.ref_face.normal)

        if self.orientation == "start":
            if self.angle_rad < math.pi/2 and self.angle_rad > - math.pi/2:
                raise Exception("french ridge lap joint beams must join at 90-180 degrees")
            elif self.angle_rad < -math.pi/2:
                self._ref_edge = False
                self.angle_rad = abs(self.angle_rad)

        else:
            if self.angle_rad < -math.pi/2 or self.angle_rad > math.pi/2:
                raise Exception("french ridge lap joint beams must join at 90-180 degrees")
            elif self.angle_rad < 0:
                self.angle_rad = abs(self.angle_rad)
                self._ref_edge = False
            self.angle_rad = math.pi - self.angle_rad

        self.startX = self.btlx_joint.parts.values()[0].width / abs(math.tan(self.angle_rad))

        if self.orientation == "end":
            if self._ref_edge:

                self.startX = self.part.blank_length - self.startX
            else:
                self.startX = self.part.blank_length + self.startX

    @classmethod
    def apply_processes(cls, part, joint, is_top, end):

        frl_process = BTLxFrenchRidgeLap(part, joint, is_top, end)

        part.processes.append(BTLxProcess(BTLxFrenchRidgeLap.PROCESS_TYPE, frl_process.header_attributes, frl_process.process_parameters))



