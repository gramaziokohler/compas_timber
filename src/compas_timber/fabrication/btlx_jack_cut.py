import math
from collections import OrderedDict
from compas.geometry import Frame
from compas.geometry import Line
from compas.geometry import Plane
from compas.geometry import cross_vectors
from compas.geometry import angle_vectors_signed
from compas_timber.parts.beam import Beam
from compas_timber.connections.joint import Joint
from compas_timber.utils.compas_extra import intersection_line_plane
from compas_timber.fabrication import BTLx
from compas_timber.fabrication import BTLxProcess
# from compas_timber.fabrication import BTLx


class BTLxJackCut(object):
    def __init__(self, frame, part, joint=None):
        """
        Constructor for BTLxJackCut can take Joint and Frame as argument because some other joints will use the jack cut as part of the milling process.
        """

        self.cut_plane = frame
        self.part = part
        self.apply_process = True
        self.generate_process()
        if joint:
            self.name = str(joint.joint.__class__.__name__)
        else:
            self.name = "jack cut"


    @property
    def process_type(self):
        return "JackRafterCut"

    @property
    def header_attributes(self):
        """ the following attributes are required for all processes, but the keys and values of header_attributes are process specific. """
        return {
            "Name": self.name,
            "Process": "yes",
            "Priority": "0",
            "ProcessID": "0",
            "ReferencePlaneID": "1",
            }

    @property
    def process_params(self):
        """ This property is required for all process types. It returns a dict with the geometric parameters to fabricate the joint. """

        if self.apply_process:

            """ the following attributes are specific to Jack Cut """
            od = OrderedDict([
                ("Orientation", str(self.orientation)),
                ("StartX", "{:.{prec}f}".format(self.startX, prec = BTLx.POINT_PRECISION)),
                ("StartY", "{:.{prec}f}".format(self.startY, prec = BTLx.POINT_PRECISION)),
                ("StartDepth", "{:.{prec}f}".format(self.start_depth, prec = BTLx.POINT_PRECISION)),
                ("Angle", "{:.{prec}f}".format(self.angle, prec = BTLx.ANGLE_PRECISION)),
                ("Inclination", "{:.{prec}f}".format(self.inclination, prec = BTLx.ANGLE_PRECISION))
                ])
            return od
        else:
            return None

    def generate_process(self):
        """ This is an internal method to generate process parameters """
        self.startY = 0.0
        self.start_depth = 0.0

        self.x_edge = Line.from_point_and_vector(
            self.part.reference_surfaces[0].point, self.part.reference_surfaces[0].xaxis
        )

        self.startX = intersection_line_plane(self.x_edge, Plane.from_frame(self.cut_plane))[1] * self.x_edge.length
        if self.startX < self.part.blank_length / 2:
            self.orientation = "start"
        else:
            self.orientation = "end"
        angle_direction = cross_vectors(self.part.reference_surfaces[0].normal, self.cut_plane.normal)
        self.angle = (
            angle_vectors_signed(
                self.part.reference_surfaces[0].xaxis, angle_direction, self.part.reference_surfaces[0].zaxis
            )
            * 180
            / math.pi
        )

        self.angle = abs(self.angle)
        self.angle = 90 - (self.angle - 90)

        self.inclination = (
            angle_vectors_signed(self.part.reference_surfaces[0].zaxis, self.cut_plane.normal, angle_direction)
            * 180
            / math.pi
        )
        self.inclination = abs(self.inclination)
        self.inclination = 90 - (self.inclination - 90)

    @classmethod
    def apply_processes(cls, frame, part, joint = None):
        jack_cut = BTLxJackCut(frame, part, joint)
        part.processes.append(BTLxProcess(jack_cut.process_type, jack_cut.header_attributes, jack_cut.process_params))
