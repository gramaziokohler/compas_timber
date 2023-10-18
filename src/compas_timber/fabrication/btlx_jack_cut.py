import math

from compas.geometry import Frame
from compas.geometry import Line
from compas.geometry import Plane
from compas.geometry import cross_vectors
from compas.geometry import angle_vectors_signed

from compas_timber.parts.beam import Beam
from compas_timber.connections.joint import Joint
from compas_timber.utils.compas_extra import intersection_line_plane
from compas_timber.connections import TButtJoint
from compas_timber.connections import LButtJoint
from compas_timber.connections import LMiterJoint
from compas_timber.fabrication.btlx import BTLxProcess
from compas_timber.fabrication.btlx import BTLx


class BTLxJackCut(BTLxProcess):
    def __init__(self, joint, part):
        """
        Constructor for BTLxJackCut can take Joint and Frame as argument because some other joints will use the jack cut as part of the milling process.
        """
        super().__init__()


        print("Instantiating Jack Cut")


        self.part = part
        self.apply_process = True

        """
        the following attributes are specific to Jack Cut
        """

        self.cut_plane = None
        if isinstance(joint, Frame):
            self.cut_plane = joint
        else:
            self.joint = joint.joint
            self.parse_geometry()
        self.orientation = "start"
        self.startX = 0
        self.startY = 0
        self.start_depth = 0
        self.angle = 90
        self.inclination = 90

        """
        the following attributes are required for all processes, but the keys and values of header_attributes are process specific.
        """
        self.process_type = "JackRafterCut"
        self.header_attributes = {
            "Name": "Jack cut",
            "Process": "yes",
            "Priority": "0",
            "ProcessID": "0",
            "ReferencePlaneID": "1",
        }

    """
    This property is required for all process types. It returns a dict with the geometric parameters to fabricate the joint.
    """

    @property
    def process_params(self):
        self.generate_process()
        return {
            "Orientation": str(self.orientation),
             "StartX": "{:.{prec}f}".format(self.startX, prec = BTLx.POINT_PRECISION),
            "StartY": "{:.{prec}f}".format(self.startY, prec = BTLx.POINT_PRECISION),
            "StartDepth": "{:.{prec}f}".format(self.start_depth, prec = BTLx.POINT_PRECISION),
            "Angle": "{:.{prec}f}".format(self.angle, prec = BTLx.ANGLE_PRECISION),
            "Inclination": "{:.{prec}f}".format(self.inclination, prec = BTLx.ANGLE_PRECISION),
        }

    def parse_geometry(self):
        """
        This method is specific to jack cut, which has multiple possible joints that create it.
        """
        if isinstance(self.joint, TButtJoint):
            if self.part.beam is self.joint.main_beam:
                self.cut_plane = self.joint.cutting_plane
            else:
                self.apply_process = False
        if isinstance(self.joint, LButtJoint):
            if self.part.beam is self.joint.main_beam:
                self.cut_plane = self.joint.cutting_plane_main
            elif self.part.beam is self.joint.cross_beam:
                self.cut_plane = self.joint.cutting_plane_cross
        if isinstance(self.joint, LMiterJoint):
            if self.part.beam is self.joint.beam_a:
                self.cut_plane = self.joint.cutting_planes[0]
            elif self.part.beam is self.joint.beam_b:
                self.cut_plane = self.joint.cutting_planes[1]

    def generate_process(self):
        """
        This is an internal method to generate process parameters
        """
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


BTLxProcess.register_process(TButtJoint, BTLxJackCut)
BTLxProcess.register_process(LButtJoint, BTLxJackCut)
BTLxProcess.register_process(LMiterJoint, BTLxJackCut)

