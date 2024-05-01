from compas_timber.connections import TButtJoint
from compas_timber.fabrication import BTLx
from compas_timber.fabrication import BTLxJackCut
from compas_timber.fabrication.btlx_processes.btlx_lap import BTLxLap
from compas_timber.fabrication.btlx_processes.btlx_double_cut import BTLxDoubleCut

from compas_timber.utils.compas_extra import intersection_line_plane

class TButtFactory(object):
    """Factory class for creating T-Butt joints."""

    def __init__(self):
        pass


    @staticmethod
    def line_intersects_face(line, face, x_max, y_max):
        """
        Check if a line intersects a face.

        Parameters:
        ----------
            line (object): The line object.
            face (object): The face object.

        Returns:
        ----------
            bool: True if the line intersects the face, False otherwise.

        """
        point = intersection_line_plane(line, Plane.from_frame(face))[0]
        point.transform(Transformation.from_frame_to_frame(face, Frame.worldXY()))
        print(point)
        if point.x >= 0 and point.x <= x_max:
            if point.y >= 0 and point.y <= y_max:
                print("found it!!!!")
                return True
        return False



    @staticmethod
    def get_intersecting_face(intersect_line, main_part, cross_part):
        print(main_part, cross_part)
        print(cross_part.beam.faces)
        for i, face in enumerate(main_part.beam.faces[0:4]):
            if i % 2 == 0:
                if TButtFactory.line_intersects_face(intersect_line, face, cross_part.blank_length, cross_part.width):
                    return i, face
            else:
                if TButtFactory.line_intersects_face(intersect_line, face, cross_part.blank_length, cross_part.height):
                    return i, face



    @staticmethod
    def calc_params_birdsmouth(joint, main_part, cross_part):
        """
        Calculate the parameters for a birdsmouth joint.

        Parameters:
        ----------
            joint (object): The joint object.
            main_part (object): The main part object.
            cross_part (object): The cross part object.

        Returns:
        ----------
            dict: A dictionary containing the calculated parameters for the birdsmouth joint

        """
        face_dict = joint._beam_side_incidence(main_part.beam, cross_part.beam, ignore_ends=True)
        sorted_keys = sorted(face_dict.keys(), key=face_dict.get)

        cross_vector = main_part.beam.centerline.direction.cross(cross_part.beam.centerline.direction)

        frame1, frame2 = joint.get_main_cutting_plane()[0], cross_part.beam.faces[sorted_keys[1]]
        angle = angle_vectors(cross_vector, frame2.normal, deg=True)
        if angle<1.0 or angle>179.0:
            return False

        frame1 = Frame(frame1.point, frame1.xaxis, -frame1.yaxis)
        print(frame1, cross_part.beam.faces[sorted_keys[0]])
        plane1, plane2 = Plane.from_frame(frame1), Plane.from_frame(frame2)
        intersect_vec = Vector.from_start_end(*intersection_plane_plane(plane2, plane1))
        intersect_line = Line(*intersection_plane_plane(plane2, plane1))

        ind, main_ref_frame = TButtFactory.get_intersecting_face(intersect_line, main_part, cross_part)

        print (ind, main_ref_frame)




        angles_dict = {}
        for i, face in enumerate(main_part.beam.faces[0:4]):
            angles_dict[i] = (face.normal.angle(cross_part.beam.centerline.direction))
        ref_frame_id = min(angles_dict.keys(), key=angles_dict.get)
        ref_frame = main_part.reference_surface_planes(ref_frame_id+1)

        print(angles_dict)

        print("ref_frame", ref_frame_id)
        joint.test.append(ref_frame)


        dot_frame1 = plane1.normal.dot(ref_frame.yaxis)
        if dot_frame1 > 0:
            plane1, plane2 = plane2, plane1

        start_point = Point(*intersection_plane_plane_plane(plane1, plane2, Plane.from_frame(ref_frame)))
        start_point.transform(Transformation.from_frame_to_frame(ref_frame, Frame.worldXY()))
        StartX, StartY = start_point[0], start_point[1]

        intersect_vec1 = Vector.from_start_end(*intersection_plane_plane(plane1, Plane.from_frame(ref_frame)))
        intersect_vec2 = Vector.from_start_end(*intersection_plane_plane(plane2, Plane.from_frame(ref_frame)))

        dot_2 = math.degrees(intersect_vec1.dot(ref_frame.yaxis))
        if dot_2 < 0:
            intersect_vec1 = -intersect_vec1

        dot_1 = math.degrees(intersect_vec2.dot(ref_frame.yaxis))
        if dot_1 < 0:
            intersect_vec2 = -intersect_vec2

        if joint.ends[str(main_part.key)] == "start":
            reference_frame = ref_frame.xaxis
        else:
            reference_frame = -ref_frame.xaxis

        Angle1 = math.degrees(intersect_vec1.angle(reference_frame))
        Angle2 = math.degrees(intersect_vec2.angle(reference_frame))

        Inclination1 = math.degrees(plane1.normal.angle(ref_frame.zaxis))
        Inclination2 = math.degrees(plane2.normal.angle(ref_frame.zaxis))

        return {
            "Orientation": joint.ends[str(main_part.key)],
            "StartX": StartX,
            "StartY": StartY,
            "Angle1": Angle1,
            "Inclination1": Inclination1,
            "Angle2": Angle2,
            "Inclination2": Inclination2,
            "ReferencePlaneID": ref_frame_id
        }



    @classmethod
    def apply_processings(cls, joint, parts):
        """
        Apply processings to the joint and its associated parts.

        Parameters
        ----------
        joint : :class:`~compas_timber.connections.joint.Joint`
            The joint object.
        parts : dict
            A dictionary of the BTLxParts connected by this joint, with part keys as the dictionary keys.

        Returns
        -------
        None

        """

        main_part = parts[str(joint.main_beam.key)]
        cross_part = parts[str(joint.cross_beam.key)]
        cut_plane, ref_plane = joint.get_main_cutting_plane()

        if joint.birdsmouth:
            joint.calc_params_birdsmouth()
            ref_face = main_part.beam.faces[joint.btlx_params_main["ReferencePlaneID"]]
            joint.btlx_params_main["ReferencePlaneID"] = str(main_part.reference_surface_from_beam_face(ref_face))
            main_part.processings.append(BTLxDoubleCut.create_process(joint.btlx_params_main, "T-Butt Joint"))
        else:
            main_part.processings.append(BTLxJackCut.create_process(main_part, cut_plane, "T-Butt Joint"))

        joint.btlx_params_cross["reference_plane_id"] = cross_part.reference_surface_from_beam_face(ref_plane)
        if joint.mill_depth > 0:
            joint.btlx_params_cross["machining_limits"] = {"FaceLimitedFront": "no", "FaceLimitedBack": "no"}
            cross_part.processings.append(BTLxLap.create_process(joint.btlx_params_cross, "T-Butt Joint"))



BTLx.register_joint(TButtJoint, TButtFactory)
