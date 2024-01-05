from compas_timber.connections import XHalfLapJoint
from compas_timber.fabrication import BTLxJoint
from compas_timber.fabrication import BTLxLap
from compas.geometry import Vector, Plane
from compas.geometry import angle_vectors
from compas.geometry import intersection_plane_plane
from compas.geometry import intersection_line_plane
from compas.geometry import distance_point_point
from math import degrees


class XHalfLapFactory(object):
    def __init__(self):
        pass

    @classmethod
    def apply_processes(self, btlx_joint):
        part_a = btlx_joint.parts["0"]
        part_b = btlx_joint.parts["1"]
        frames_a = btlx_joint.joint.sorted_frames_a
        frames_b = btlx_joint.joint.sorted_frames_b
        planes_a = btlx_joint.joint.sorted_planes_a
        planes_b = btlx_joint.joint.sorted_planes_b
        crossplane_to_a = self._crossplane(planes_a, planes_b)
        crossplane_to_b = self._crossplane(planes_b, planes_a)
        cutplane_a = btlx_joint.joint.cutplane
        cutplane_b = Plane(cutplane_a[0], cutplane_a[1] * -1)  # Flip Cutplane a to get Cutplane b

        # Apply Lap for Beam A
        reference_plane_id = self._operation_plane(btlx_joint.joint.operation_plane_a)
        self._apply_lap(
            btlx_joint, reference_plane_id, part_a, part_b, planes_a, planes_b, frames_a, cutplane_a, crossplane_to_a
        )

        # Apply Lap for Beam B
        reference_plane_id = self._operation_plane(btlx_joint.joint.operation_plane_b)
        self._apply_lap(
            btlx_joint, reference_plane_id, part_b, part_a, planes_b, planes_a, frames_b, cutplane_b, crossplane_to_b
        )
        output = crossplane_to_a, crossplane_to_b, cutplane_a #TODO delete if everything works
        return output #TODO delete if everything works

    @staticmethod
    def _apply_lap(
        btlx_joint, reference_plane_id, part, crosspart, planes_main, planes_cross, frames_main, cutplane, crossplane
    ):
        orientation = "start"
        start_x = XHalfLapFactory._calculate_start_x(part, planes_main, crossplane)
        start_y = "0.000"
        angle = XHalfLapFactory._calculate_angle(frames_main, planes_main, crossplane)
        inclination = XHalfLapFactory._calculate_inclination(planes_main, frames_main, cutplane)
        slope = XHalfLapFactory._calculate_slope(part, crosspart)
        length = XHalfLapFactory._calculate_length(planes_cross)
        width = XHalfLapFactory._calculate_width(planes_main)
        depth = XHalfLapFactory._calculate_depth(planes_main, crossplane, cutplane)
        lead_angle_parallel = "yes"
        lead_angle = "90.000"
        lead_inclination_parallel = "yes"
        lead_inclination = "90.000"
        machining_limits = ""
        parameters = [
            reference_plane_id,
            orientation,
            start_x,
            start_y,
            angle,
            inclination,
            slope,
            length,
            width,
            depth,
            lead_angle_parallel,
            lead_angle,
            lead_inclination_parallel,
            lead_inclination,
            machining_limits,
        ]
        BTLxLap.apply_process(part, btlx_joint, parameters)

    @staticmethod
    def _operation_plane(operation_plane_ct):
        # The Reference Planes from Compas Timber and BTLx don't match, this is a conversion to solve it.
        ct_to_bltx = {0: "3", 1: "2", 2: "1", 3: "4", 4: "5", 5: "6"}
        operation_plane_btlx = ct_to_bltx[operation_plane_ct]
        return operation_plane_btlx

    @staticmethod
    def _crossplane(planes_main, planes_cross):
        # calculates the plane of beam_b that marks the angle center
        vector_a4 = planes_main[4][1]  # TODO herausfinden ob [4] oder [5]
        planes_b = planes_cross[1], planes_cross[3]
        vectors_b = planes_cross[1][1], planes_cross[3][1]
        angles = []
        for i in vectors_b:
            angles.append(angle_vectors(vector_a4, i))
        angles, planes_b = zip(*sorted(zip(angles, planes_b)))
        return planes_b[0]

    @staticmethod
    def _calculate_start_x(part, planes_main, crossplane):
        line = intersection_plane_plane(planes_main[0], planes_main[3])
        start = intersection_line_plane(line, planes_main[4])
        end = intersection_line_plane(line, crossplane)
        length = distance_point_point(start, end)
        # Addition Trim Length
        if part.start_trim is None:
            trim = 0
        else:
            trim = part.start_trim
        length = length + trim
        return length

    @staticmethod
    def _calculate_angle(frames_main, planes_main, crossplane):
        vector_a3 = planes_main[1][1]
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
        frame = part_a.frame
        vector = part_b.frame.xaxis
        vector_projected = XHalfLapFactory._project_vector_to_frame(vector, frame)
        return 180 - degrees(angle_vectors(vector, vector_projected))

    @staticmethod
    def _calculate_length(planes_cross):
        start = planes_cross[1][0]
        end = planes_cross[3][0]
        return distance_point_point(start, end)

    @staticmethod
    def _calculate_width(planes_main):
        start = planes_main[1][0]
        end = planes_main[3][0]
        return distance_point_point(start, end)

    @staticmethod
    def _calculate_inclination(planes_main, frames_main, cutplane):
        v1 = planes_main[0][1]
        v2 = cutplane[1]
        frame = frames_main[1]
        v1_proj = XHalfLapFactory._project_vector_to_frame(v1, frame)
        v2_proj = XHalfLapFactory._project_vector_to_frame(v2, frame)
        return degrees(angle_vectors(v1_proj, v2_proj)) - 90

    @staticmethod
    def _project_vector_to_frame(vector, frame):
        frame_x = frame.xaxis
        frame_y = frame.yaxis
        return Vector.cross(frame_x, Vector.cross(frame_x, vector)) + Vector.cross(
            frame_y, Vector.cross(frame_y, vector)
        )


BTLxJoint.register_joint(XHalfLapJoint, XHalfLapFactory)
