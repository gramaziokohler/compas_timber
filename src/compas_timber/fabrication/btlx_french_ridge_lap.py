import math
from collections import OrderedDict
from compas.geometry import angle_vectors
from compas.geometry import angle_vectors_signed

from compas_timber.parts.beam import Beam
from compas_timber.connections.joint import Joint
from compas_timber.connections import FrenchRidgeLapJoint
from compas_timber.fabrication import BTLx
from compas_timber.fabrication import BTLxJoint
from compas_timber.fabrication import BTLxProcess
#from compas_timber.fabrication import BTLx

class BTLxFrenchRidgeLap(object):
    PROCESS_TYPE = "FrenchRidgeLap"

    def __init__(self, joint, top_beam_key):
        self.beams = joint.beams
        self.joint = joint.joint
        self.btlx_joint = joint
        self.apply_process = True
        self.which_beam = ""
        self.orientations = ["start", "start"]
        self.ref_edges = ["refedge", "refedge"]
        self._drill_hole = True
        self.drill_hole_diameter = 10.0

        """
        the following attributes are required for all processes, but the keys and values of header_attributes are process specific.
        """
        self.main_process_type = "FrenchRidgeLap"
        self.main_header_attributes = {
            "Name": "French ridge lap",
            "Process": "yes",
            "Priority": "0",
            "ProcessID": "0",
            "ReferencePlaneID": str(self.joint.reference_face_indices[0]),
        }

        self.cross_process_type = "FrenchRidgeLap"
        self.cross_header_attributes = {
            "Name": "French ridge lap",
            "Process": "yes",
            "Priority": "0",
            "ProcessID": "0",
            "ReferencePlaneID": str(self.joint.reference_face_indices[1]),
        }

        self.process_joints()

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


    def process_joints(self):
        """
        This property is required for all process types. It returns a dict with the geometric parameters to fabricate the joint. Use OrderedDict to maintain original order
        """
        self.get_ends()
        self.get_params()

        self.main_beam_parameters = OrderedDict([
            ("Orientation", str(self.orientations[0])),
            ("StartX", "{:.{prec}f}".format(self.startX, prec = BTLx.POINT_PRECISION)),
            ("Angle", "{:.{prec}f}".format(self.angle, prec = BTLx.POINT_PRECISION)),
            ("RefPosition", self.ref_edges[0]),
            ("Drillhole", self.drill_hole),
            ("DrillholeDiam", "{:.{prec}f}".format(self.drill_hole_diameter, prec = BTLx.POINT_PRECISION)),
        ])

        self.cross_beam_parameters = OrderedDict([
            ("Orientation", str(self.orientations[1])),
            ("StartX", "{:.{prec}f}".format(self.startX, prec = BTLx.POINT_PRECISION)),
            ("Angle", "{:.{prec}f}".format(self.angle, prec = BTLx.POINT_PRECISION)),
            ("RefPosition", self.ref_edges[1]),
            ("Drillhole", self.drill_hole),
            ("DrillholeDiam", "{:.{prec}f}".format(self.drill_hole_diameter, prec = BTLx.POINT_PRECISION)),
        ])


    def get_ends(self):
        start_distance = min([
            self.beams[0].centerline.start.distance_to_point(self.beams[1].centerline.start),
            self.beams[0].centerline.start.distance_to_point(self.beams[1].centerline.end)
        ])
        end_distance = min([
            self.beams[0].centerline.end.distance_to_point(self.beams[1].centerline.start),
            self.beams[0].centerline.end.distance_to_point(self.beams[1].centerline.end)
        ])
        print("start dist = {} ____________ end dist = {}".format(start_distance, end_distance))
        if start_distance > end_distance:
            self.orientations[0] = "end"

        start_distance = min([
            self.beams[1].centerline.start.distance_to_point(self.beams[0].centerline.start),
            self.beams[1].centerline.start.distance_to_point(self.beams[0].centerline.end)
        ])
        end_distance = min([
            self.beams[1].centerline.end.distance_to_point(self.beams[0].centerline.start),
            self.beams[1].centerline.end.distance_to_point(self.beams[0].centerline.end)
        ])
        print("start dist = {} ____________ end dist = {}".format(start_distance, end_distance))
        if start_distance > end_distance:
            self.orientations[1] = "end"

        print("orientations = {}".format(self.orientations))

    def get_params(self):
        """
        This is an internal method to generate process parameters
        """

        self.angle_rad = angle_vectors(self.joint.beams[0].frame.xaxis, self.joint.beams[1].frame.xaxis)
        if self.angle_rad < math.pi / 2:

            self.angle_rad = math.pi - self.angle_rad
        self.startX = self.btlx_joint.parts.values()[0].width / math.tan(math.pi - self.angle_rad)

    @classmethod
    def apply_processes(cls, joint, top_beam_key):
        frl_process = BTLxFrenchRidgeLap(joint, top_beam_key)
        keys = []
        for key in joint.parts.keys():
            keys.append(key)
        key_index = keys.index(top_beam_key)
        keys.pop(key_index)
        joint.parts[top_beam_key].processes.append(BTLxProcess(BTLxFrenchRidgeLap.PROCESS_TYPE, frl_process.main_header_attributes, frl_process.main_beam_parameters))
        joint.parts[keys[0]].processes.append(BTLxProcess(BTLxFrenchRidgeLap.PROCESS_TYPE, frl_process.cross_header_attributes, frl_process.cross_beam_parameters))



