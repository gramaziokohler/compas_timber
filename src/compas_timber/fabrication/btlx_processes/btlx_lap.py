import math
from collections import OrderedDict
from compas.geometry import angle_vectors_signed
from compas_timber.fabrication import BTLx
from compas_timber.fabrication import BTLxProcess
import math


class BTLxLap(object):
    PROCESS_TYPE = "Lap"

    def __init__(self, part, joint, parameters):
        self.part = part
        for beam in joint.beams:
            if beam is part.beam:
                self.beam = beam
            else:
                self.other_beam = beam

        self.joint = joint.joint
        self.parameters = parameters
        self.btlx_joint = joint
        self.apply_process = True
        self._ref_edge = True
        self._drill_hole = True
        self.drill_hole_diameter = 10.0


        """
        the following attributes are required for all processes, but the keys and values of header_attributes are process specific.
        """

        self.main_process_type = "Lap"

        self.header_attributes = {
            "Name": "Lap",
            "Process": "yes",
            "Priority": "0",
            "ProcessID": "0",
            "ReferencePlaneID": "2",
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

        self.process_parameters = OrderedDict(
            [
                ("Orientation", "start"), #TODO Define
                ("StartX", "500.000"), #TODO Define
                ("StartY", "0.000"), #TODO Define
                ("Angle", str(self.parameters[2])),
                ("Inclination", str(self.parameters[4])),
                ("Slope", str(self.parameters[3])),
                ("Length", str(self.parameters[1])),
                ("Width", str(self.parameters[0])),
                ("Depth", "40.000"), #TODO Define
                ("LeadAngleParallel", "yes"), #TODO Define
                ("LeadAngle", "90.000"), #TODO Define
                ("LeadInclinationParallel", "yes"), #TODO Define
                ("LeadInclination", "90.000"), #TODO Define
                ("MachiningLimits", ""), #TODO Define
            ]
        )

    def get_params(self):
        """
        This is an internal method to generate process parameters
        """
        # TODO Get Params


    @classmethod
    def apply_process(cls, part, joint, parameters):
        frl_process = BTLxLap(part, joint, parameters)

        part.processes.append(
            BTLxProcess(BTLxLap.PROCESS_TYPE, frl_process.header_attributes, frl_process.process_parameters)
        )
