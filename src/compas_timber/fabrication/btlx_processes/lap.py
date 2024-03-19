import math
from collections import OrderedDict

from compas.geometry import Line
from compas.geometry import Plane
from compas.geometry import angle_vectors_signed
from compas.geometry import cross_vectors

from compas_timber.fabrication import BTLx
from compas_timber.fabrication import BTLxProcess
from compas_timber.utils.compas_extra import intersection_line_plane


class BTLxLap(object):
    """
    Represents a lap process for timber fabrication.

    Parameters
    ----------
    part : :class:`~compas_timber.fabrication.btlx_part.BTLxPart`
        The BTLxPart object representing the beam.
    frame : :class:`~compas.geometry.Frame`
        The frame object representing the cutting plane.
    joint_name : str, optional
        The name of the joint. Defaults to None.

    """

    PROCESS_TYPE = "Lap"

    def __init__(self, param_dict, joint_name=None, **kwargs):
        self.apply_process = True
        self.reference_plane_id = ""
        self.orientation = "start"
        self.start_x = 0.0
        self.start_y = 0.0
        self.angle = 90.0
        self.inclination = 90.0
        self.slope_inclination = 0.0
        self.length = 200.0
        self.width = 50.0
        self.depth = 40.0
        self.lead_angle_parallel = "yes"
        self.lead_angle = 90.0
        self.lead_inclination_parallel = "yes"
        self.lead_inclination = 90.0
        self.machining_limits = []

        for key, value in param_dict.items():
            setattr(self, key, value)

        for key, value in kwargs.items():
            setattr(self, key, value)

        if joint_name:
            self.name = joint_name
        else:
            self.name = "lap"

    @property
    def header_attributes(self):
        """the following attributes are required for all processes, but the keys and values of header_attributes are process specific."""
        return {
            "Name": self.name,
            "Process": "yes",
            "Priority": "0",
            "ProcessID": "0",
            "ReferencePlaneID": str(self.reference_plane_id + 1)
        }

    @property
    def process_params(self):
        """This property is required for all process types. It returns a dict with the geometric parameters to fabricate the joint. """

        if self.apply_process:
            """the following attributes are specific to Lap"""
            od = OrderedDict(
                [
                    ("Orientation", str(self.orientation)),
                    ("StartX", "{:.{prec}f}".format(self.start_x, prec=BTLx.POINT_PRECISION)),
                    ("StartY", "{:.{prec}f}".format(self.start_y, prec=BTLx.POINT_PRECISION)),
                    ("Angle", "{:.{prec}f}".format(self.angle, prec=BTLx.ANGLE_PRECISION)),
                    ("Inclination", "{:.{prec}f}".format(self.inclination, prec=BTLx.ANGLE_PRECISION)),
                    ("Slope", "{:.{prec}f}".format(self.slope_inclination, prec=BTLx.ANGLE_PRECISION)),
                    ("Length", "{:.{prec}f}".format(self.length, prec=BTLx.POINT_PRECISION)),
                    ("Width", "{:.{prec}f}".format(self.width, prec=BTLx.POINT_PRECISION)),
                    ("Depth", "{:.{prec}f}".format(self.depth, prec=BTLx.POINT_PRECISION)),
                    ("LeadAngleParallel", "yes"),
                    ("LeadAngle", "{:.{prec}f}".format(self.lead_angle, prec=BTLx.ANGLE_PRECISION)),
                    ("LeadInclinationParallel", "yes"),
                    ("LeadInclination", "{:.{prec}f}".format(self.lead_inclination, prec=BTLx.ANGLE_PRECISION)),
                    ("MachiningLimits", self.machining_limits)
                ]
            )
            print("param dict", od)
            return od
        else:
            return None

    @classmethod
    def create_process(cls, param_dict, joint_name=None, **kwargs):
        lap = BTLxLap(param_dict, joint_name, **kwargs)
        return BTLxProcess(BTLxLap.PROCESS_TYPE, lap.header_attributes, lap.process_params)
