from compas_timber.connections import TButtJoint
from compas_timber.fabrication import BTLx
from compas_timber.fabrication import BTLxJackCut
from compas_timber.fabrication.btlx_processes.btlx_lap import BTLxLap
from compas_timber.fabrication.btlx_processes.btlx_doublecut import BTLxDoubleCut
from compas.geometry import intersection_plane_plane, intersection_plane_plane_plane, Vector, Plane, Frame, Transformation, Point
import math

class TButtFactory(object):
    """Factory class for creating T-Butt joints."""

    def __init__(self):
        pass


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





        frame1, frame2 = cross_part.beam.faces[sorted_keys[0]], cross_part.beam.faces[sorted_keys[1]]

        # frame1 = Frame(frame1.point, frame1.xaxis, -frame1.yaxis)

        print(frame1, cross_part.beam.faces[sorted_keys[0]])
        plane1, plane2 = Plane.from_frame(frame1), Plane.from_frame(frame2)
        intersect_vec = Vector.from_start_end(*intersection_plane_plane(plane2, plane1))

        angles_dict = {}
        for i, face in enumerate(main_part.beam.faces[0:4]):
            angles_dict[i] = (face.normal.angle(intersect_vec))
        ref_frame_id = min(angles_dict, key=angles_dict.get)
        print("ref_frame_id", ref_frame_id)
        ref_frame = main_part.reference_surface_planes(ref_frame_id+1)

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
        cut_plane = joint.get_main_cutting_plane()[0]
        if joint.birdsmouth == True:
            #calculate the process params
            joint_params = TButtFactory.calc_params_birdsmouth(joint, main_part, cross_part)
            main_part.processings.append(BTLxDoubleCut.create_process(joint_params, "T-Butt Joint"))
            #put processing here
        else:
            main_part.processings.append(BTLxJackCut.create_process(main_part, cut_plane, "T-Butt Joint"))

        if joint.mill_depth > 0:
            cross_part = parts[str(joint.cross_beam.key)]
            cross_part.processings.append(BTLxLap.create_process(joint.btlx_params_cross, "T-Butt Joint"))



BTLx.register_joint(TButtJoint, TButtFactory)
