import math
from collections import OrderedDict

from compas.geometry import Line
from compas.geometry import Plane
from compas.geometry import angle_vectors_signed
from compas.geometry import cross_vectors

from compas_timber.fabrication import BTLx
from compas_timber.fabrication import BTLxProcess
from compas_timber.utils.compas_extra import intersection_line_plane


class BTLxJackCut(object):
    """
    Represents a jack cut process for timber fabrication.

    Parameters
    ----------
    part : :class:`~compas_timber.fabrication.btlx_part.BTLxPart`
        The BTLxPart object representing the beam.
    frame : :class:`~compas.geometry.Frame`
        The frame object representing the cutting plane.
    joint_name : str, optional
        The name of the joint. Defaults to None.

    """

    PROCESS_TYPE = "JackRafterCut"

    def __init__(self, part, frame, joint_name=None):
        self.cut_plane = frame
        self.part = part
        self.apply_process = True
        self.reference_side = self.part.faces[0]
        self.generate_process()
        if joint_name:
            self.name = joint_name
        else:
            self.name = "jack cut"

    @property
    def header_attributes(self):
        """the following attributes are required for all processes, but the keys and values of header_attributes are process specific."""
        return {
            "Name": self.name,
            "Process": "yes",
            "Priority": "0",
            "ProcessID": "0",
            "ReferencePlaneID": "1",
        }

    @property
    def process_params(self):
        """This property is required for all process types. It returns a dict with the geometric parameters to fabricate the joint."""

        if self.apply_process:
            """the following attributes are specific to Jack Cut"""
            od = OrderedDict(
                [
                    ("Orientation", str(self.orientation)),
                    ("StartX", "{:.{prec}f}".format(self.startX, prec=BTLx.POINT_PRECISION)),
                    ("StartY", "{:.{prec}f}".format(self.startY, prec=BTLx.POINT_PRECISION)),
                    ("StartDepth", "{:.{prec}f}".format(self.start_depth, prec=BTLx.POINT_PRECISION)),
                    ("Angle", "{:.{prec}f}".format(self.angle, prec=BTLx.ANGLE_PRECISION)),
                    ("Inclination", "{:.{prec}f}".format(self.inclination, prec=BTLx.ANGLE_PRECISION)),
                ]
            )
            return od
        else:
            return None

    def generate_process(self):
        """This is an internal method to generate process parameters"""
        self.startY = 0.0
        self.start_depth = 0.0

        self.x_edge = Line.from_point_and_vector(self.reference_side.point, self.reference_side.xaxis)

        self.startX = intersection_line_plane(self.x_edge, Plane.from_frame(self.cut_plane))[1] * self.x_edge.length
        if self.startX < self.part.blank_length / 2:
            self.orientation = "start"
        else:
            self.orientation = "end"
        angle_direction = cross_vectors(self.reference_side.normal, self.cut_plane.normal)
        self.angle = (
            angle_vectors_signed(self.reference_side.xaxis, angle_direction, self.reference_side.zaxis) * 180 / math.pi
        )

        self.angle = abs(self.angle)
        self.angle = 90 - (self.angle - 90)

        self.inclination = (
            angle_vectors_signed(self.reference_side.zaxis, self.cut_plane.normal, angle_direction) * 180 / math.pi
        )
        self.inclination = abs(self.inclination)
        self.inclination = 90 - (self.inclination - 90)

    @classmethod
    def create_process(cls, part, frame, joint_name=None):
        jack_cut = BTLxJackCut(part, frame, joint_name)
        return BTLxProcess(BTLxJackCut.PROCESS_TYPE, jack_cut.header_attributes, jack_cut.process_params)
