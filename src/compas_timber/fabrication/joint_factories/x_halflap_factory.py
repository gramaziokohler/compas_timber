from compas_timber.connections import XHalfLapJoint
from compas_timber.fabrication import BTLxJoint
from compas_timber.fabrication import BTLxLap
from compas.geometry import angle_vectors
from compas.geometry import Vector, Plane, Line
from compas.geometry import project_point_plane
from compas.geometry import intersection_line_line
from math import degrees


class XHalfLapFactory(object):
    def __init__(self):
        pass

    @classmethod
    def apply_processes(self, btlx_joint): #TODO clean up & no hard coding & repetitions
        part_a = btlx_joint.parts["0"]
        part_b = btlx_joint.parts["1"]
        #print(part_a.length)
        #print(part_a.blank_length)

        part1 = btlx_joint.parts[str(btlx_joint.joint.beam_a.key)]
        width = (btlx_joint.parts["1"].width)
        height = (btlx_joint.parts["0"].height)
        angle = self._calculate_angle(part_a, part_b)
        slope = self._calculate_slope(part_a, part_b)
        inclination = self._calculate_inclination(part_a, part_b)
        parameters1 = [width, height, angle, slope, inclination]
        BTLxLap.apply_process(part1, btlx_joint, parameters1)

        part2 = btlx_joint.parts[str(btlx_joint.joint.beam_b.key)]
        width = (btlx_joint.parts["0"].width)
        height = (btlx_joint.parts["1"].height)
        angle = self._calculate_angle(part_b, part_a)
        slope = self._calculate_slope(part_b, part_a)
        inclination = self._calculate_inclination(part_b, part_a)
        parameters2 = [width, height, angle, slope, inclination]
        BTLxLap.apply_process(part2, btlx_joint, parameters2)

        ## Hier weiter machen!
        #print(btlx_joint.beams)
        #print(part_a.reference_surfaces["2"]) ##TODO Winkel von all den References zur Cutplane messen
        #print(self._calculate_face(part_a, part_b))

    @staticmethod
    def _calculate_face(part_a, part_b):
        return "calculate face"
    
    @staticmethod
    def _calculate_angle(part_a, part_b):
        # Calculates the Angle
        frame = part_a.frame
        part_a_xaxis = part_a.frame.xaxis
        vector = part_b.frame.xaxis
        vector_projected = XHalfLapFactory._project_vector_to_frame(vector, frame)
        return degrees(angle_vectors(part_a_xaxis, vector_projected))

    @staticmethod
    def _calculate_slope(part_a, part_b):
        # Calculates the Slope
        frame = part_a.frame
        vector = part_b.frame.xaxis
        vector_projected = XHalfLapFactory._project_vector_to_frame(vector, frame)
        return 180 - degrees(angle_vectors(vector, vector_projected))
    
    @staticmethod
    def _calculate_inclination(part_a, part_b):
        # Calculates the Inclination
        frame = part_a.frame
        vector = part_b.frame.yaxis
        vector_projected = XHalfLapFactory._project_vector_to_frame(vector, frame)
        return 180 - degrees(angle_vectors(vector, vector_projected)) + 90
    
    @staticmethod
    def _calculate_startx(part_a, part_b):
        a_origin = part_a.frame.point
        a_xaxis = part_a.frame.xaxis
        b_origin = part_b.frame.point
        b_xaxis = part_b.frame.xaxis
        a_centerline = Line.from_point_and_vector(a_origin, a_xaxis)
        b_centerline = Line.from_point_and_vector(b_origin, b_xaxis)
        intersection_point = intersection_line_line(a_centerline, b_centerline)

        ## Hier weiter machen!
        return part_a._reference_surfaces
    
    @staticmethod
    def _project_vector_to_frame(vector, frame):
        frame_x = frame.xaxis
        frame_y = frame.yaxis
        return Vector.cross(frame_x, Vector.cross(frame_x, vector)) + Vector.cross(frame_y, Vector.cross(frame_y, vector))



BTLxJoint.register_joint(XHalfLapJoint, XHalfLapFactory)
