from compas_timber.connections import XHalfLapJoint
from compas_timber.fabrication import BTLxJoint
from compas_timber.fabrication import BTLxLap
from compas.geometry import angle_vectors
from compas.geometry import Vector, Plane, Line, Frame
from compas.geometry import project_point_plane
from compas.geometry import intersection_line_line, intersection_plane_plane, intersection_line_plane, distance_point_point
from math import degrees


class XHalfLapFactory(object):
    def __init__(self):
        pass

    @classmethod
    def apply_processes(self, btlx_joint): #TODO clean up & no hard coding & repetitions
        part_a = btlx_joint.parts["0"]
        part_b = btlx_joint.parts["1"]
        frames_a = btlx_joint.joint.sorted_frames_a
        frames_b = btlx_joint.joint.sorted_frames_b
        planes_a = btlx_joint.joint.sorted_planes_a
        planes_b = btlx_joint.joint.sorted_planes_b
        crossplane_to_a = self._crossplane(planes_a, planes_b)
        crossplane_to_b = self._crossplane(planes_b, planes_a)
        cutplane_a = btlx_joint.joint.cutplane
        cutplane_b = btlx_joint.joint.cutplane
        cutplane_b[1] = cutplane_b[1] * -1 #Flip Cutplane a to get Cutplane b

        part1 = btlx_joint.parts[str(btlx_joint.joint.beam_a.key)]
        start_x = self._calculate_start_x(planes_a, crossplane_to_a)
        width = (btlx_joint.parts["1"].width)
        height = (btlx_joint.parts["0"].height)
        depth = self._calculate_depth(planes_a, crossplane_to_a, cutplane_a)
        reference_plane_id = self._operation_plane(btlx_joint.joint.operation_plane_a)
        angle = self._calculate_angle(frames_a, planes_a, crossplane_to_a)
        slope = self._calculate_slope(part_a, part_b)
        inclination = self._calculate_inclination(part_a, part_b)
        parameters1 = [width, height, angle, slope, inclination, reference_plane_id, start_x, depth]
        BTLxLap.apply_process(part1, btlx_joint, parameters1)

        part2 = btlx_joint.parts[str(btlx_joint.joint.beam_b.key)]
        start_x = self._calculate_start_x(planes_b, crossplane_to_b)
        width = (btlx_joint.parts["0"].width)
        height = (btlx_joint.parts["1"].height)
        depth = self._calculate_depth(planes_b, crossplane_to_b, cutplane_b)
        reference_plane_id = self._operation_plane(btlx_joint.joint.operation_plane_b)
        angle = self._calculate_angle(frames_b, planes_b, crossplane_to_b)
        slope = self._calculate_slope(part_b, part_a)
        inclination = self._calculate_inclination(part_b, part_a)
        parameters2 = [width, height, angle, slope, inclination, reference_plane_id, start_x, depth]
        BTLxLap.apply_process(part2, btlx_joint, parameters2)
    
    @staticmethod
    def _operation_plane(operation_plane_ct):
        # The Reference Planes from Compas Timber and BTLx don't match, this is a conversion to solve it.
        ct_to_bltx = {
            0:"3",
            1:"2",
            2:"1",
            3:"4",
            4:"5",
            5:"6"
        }
        operation_plane_btlx = ct_to_bltx[operation_plane_ct]
        return operation_plane_btlx

    @staticmethod
    def _crossplane(planes_main, planes_cross):
        # calculates the plane of beam_b that marks the angle center
        vector_a4 = planes_main[5][1]
        planes_b = planes_cross[1], planes_cross[3]
        vectors_b = planes_cross[1][1], planes_cross[3][1]
        angles = []
        for i in vectors_b:
            angles.append(angle_vectors(vector_a4, i))
        angles, planes_b = zip(*sorted(zip(angles, planes_b)))
        return planes_b[0]

    @staticmethod
    def _calculate_start_x(planes_main, crossplane):
        line = intersection_plane_plane(planes_main[0], planes_main[3])
        start = intersection_line_plane(line, planes_main[4])
        end = intersection_line_plane(line, crossplane)
        length = distance_point_point(start, end)
        return length

    @staticmethod
    def _calculate_angle(frames_main, planes_main, crossplane):
        vector_a3 = planes_main[3][1]
        vector_b = XHalfLapFactory._project_vector_to_frame(crossplane[1], frames_main[0])
        angle = angle_vectors(vector_a3, vector_b)
        return degrees(angle)

    @staticmethod
    def _calculate_depth(planes_main, crossplane, cutplane):
        line = intersection_plane_plane(planes_main[3], crossplane)
        start = intersection_line_plane(line, planes_main[0])
        end = intersection_line_plane(line, cutplane)
        depth = distance_point_point(start, end)
        return depth

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
    def _project_vector_to_frame(vector, frame):
        frame_x = frame.xaxis
        frame_y = frame.yaxis
        return Vector.cross(frame_x, Vector.cross(frame_x, vector)) + Vector.cross(frame_y, Vector.cross(frame_y, vector))

BTLxJoint.register_joint(XHalfLapJoint, XHalfLapFactory)
