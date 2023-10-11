import xml.etree.ElementTree as ET
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
from compas_timber.connections import XHalfLapJoint
from compas_timber.fabrication.btlx import BTLxProcess
from compas_timber.fabrication.btlx import BTLx

class BTLxFrenchRidgeLap(BTLxProcess):
    def __init__(self, joint, part):
        """
        Constructor for BTLxJackCut can take Joint and Frame as argument because some other joints will use the jack cut as part of the milling process.
        """
        super().__init__()
        self.part = part
        self.apply_process = False

        """
        the following attributes are specific to Jack Cut
        """

        self.cut_plane = None
        if isinstance(joint, Frame):
            self.cut_plane = joint
        else:
            self.joint = joint
            self.parse_geometry()
        self.orientation = "start"
        self.startX = 0.0
        self.angle = 90.0
        self.ref_edge = True
        self.drill_hole = False
        self.drill_hole_diameter = 0.0


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


    """
    This property is required for all process types. It returns a dict with the geometric parameters to fabricate the joint.
    """
    @property
    def process_params(self):
        self.generate_process()
        return {
            "Orientation": str(self.orientation),
            "StartX": f'{self.startX:.{BTLx.POINT_PRECISION}f}',
            "StartY": f'{self.startY:.{BTLx.POINT_PRECISION}f}',
            "StartDepth": f'{self.start_depth:.{BTLx.POINT_PRECISION}f}',
            "Angle": f'{self.angle:.{BTLx.ANGLE_PRECISION}f}',
            "Inclination": f'{self.inclination:.{BTLx.ANGLE_PRECISION}f}',
        }


    def check_geometry(self):
        """
        This method is specific to jack cut, which has multiple possible joints that create it.
        """
        normal = self.joint.blank_frame.normal
        for joint.beams





    def generate_process(self):
        """
        This is an internal method to generate process parameters
        """
        self.x_edge = Line.from_point_and_vector(self.part.reference_surfaces[0].point, self.part.reference_surfaces[0].xaxis)
        self.startX = (
            intersection_line_plane(self.x_edge, Plane.from_frame(self.cut_plane))[1] * self.x_edge.length
        )
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
