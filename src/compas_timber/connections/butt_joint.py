from compas.geometry import Frame
from compas.geometry import Line
from compas.geometry import Plane
from compas.geometry import Point
from compas.geometry import Polyhedron
from compas.geometry import Transformation
from compas.geometry import Vector
from compas.geometry import angle_vectors
from compas.geometry import angle_vectors_signed
from compas.geometry import closest_point_on_line
from compas.geometry import distance_line_line
from compas.geometry import dot_vectors
from compas.geometry import intersection_plane_plane
from compas.geometry import intersection_plane_plane_plane
from compas.geometry import subtract_vectors

from .joint import Joint


class ButtJoint(Joint):
    """Abstract Lap type joint with functions common to L-Butt and T-Butt Joints.

    Do not instantiate directly. Please use `**LapJoint.create()` to properly create an instance of lap sub-class and associate it with an model.

    Parameters
    ----------
    main_beam : :class:`~compas_timber.parts.Beam`
        The main beam to be joined.
    cross_beam : :class:`~compas_timber.parts.Beam`
        The cross beam to be joined.
    small_beam_butts : bool, default False
        If True, the beam with the smaller cross-section will be trimmed. Otherwise, the main beam will be trimmed.
    modify_cross : bool, default True
        If True, the cross beam will be extended to the opposite face of the main beam and cut with the same plane.
    reject_i : bool, default False
        If True, the joint will be rejected if the beams are not in I topology (i.e. main butts at crosses end).

    Attributes
    ----------
    beams : list(:class:`~compas_timber.parts.Beam`)
        The beams joined by this joint.
    joint_type : str
        A string representation of this joint's type.

    """

    @property
    def __data__(self):
        data_dict = {
            "main_beam_guid": self.main_beam_guid,
            "cross_beam_guid": self.cross_beam_guid,
            "mill_depth": self.mill_depth,
            "birds_mouth": self.birdsmouth,
        }
        data_dict.update(super(ButtJoint, self).__data__)
        return data_dict

    @classmethod
    def __from_data__(cls, value):
        instance = cls(**value)
        instance.main_beam_guid = value["main_beam_guid"]
        instance.cross_beam_guid = value["cross_beam_guid"]
        return instance

    def __init__(self, main_beam=None, cross_beam=None, mill_depth=0, birdsmouth=False, **kwargs):
        super(ButtJoint, self).__init__(**kwargs)
        self.main_beam = main_beam
        self.cross_beam = cross_beam
        self.main_beam_guid = str(main_beam.guid) if main_beam else None
        self.cross_beam_guid = str(cross_beam.guid) if cross_beam else None
        self.mill_depth = mill_depth
        self.birdsmouth = birdsmouth
        self.btlx_params_main = {}
        self.btlx_params_cross = {}
        self.features = []
        self.test = []

    @property
    def beams(self):
        return [self.main_beam, self.cross_beam]

    def restore_beams_from_keys(self, model):
        """After de-serialization, restors references to the main and cross beams saved in the model."""
        self.main_beam = model.element_by_guid(self.main_beam_guid)
        self.cross_beam = model.element_by_guid(self.cross_beam_guid)

    def side_surfaces_cross(self):
        assert self.main_beam and self.cross_beam

        face_dict = Joint._beam_side_incidence(self.main_beam, self.cross_beam, ignore_ends=True)
        face_indices = face_dict.keys()
        angles = face_dict.values()
        angles, face_indices = zip(*sorted(zip(angles, face_indices)))

        return self.cross_beam.faces[(face_indices[0] + 1) % 4], self.cross_beam.faces[(face_indices[0] + 3) % 4]

    def front_back_surface_main(self):
        assert self.main_beam and self.cross_beam

        face_dict = Joint._beam_side_incidence(self.cross_beam, self.main_beam, ignore_ends=True)
        face_indices = face_dict.keys()
        angles = face_dict.values()
        angles, face_indices = zip(*sorted(zip(angles, face_indices)))
        return self.main_beam.faces[face_indices[0]], self.main_beam.faces[face_indices[3]]

    def back_surface_main(self):
        face_dict = Joint._beam_side_incidence(self.main_beam, self.cross_beam, ignore_ends=True)
        face_dict.sort(lambda x: x.values())
        return face_dict.values()[3]

    def get_main_cutting_plane(self):
        # TODO: this should be split into two functions. It's hard to read on the calling side.
        assert self.main_beam and self.cross_beam
        self.reference_side_index_cross, cfr = self.get_face_most_ortho_to_beam(
            self.main_beam, self.cross_beam, ignore_ends=True
        )

        cross_mating_frame = cfr.copy()
        cfr = Frame(cfr.point, cfr.xaxis, cfr.yaxis * -1.0)  # flip normal
        cfr.point = cfr.point + cfr.zaxis * self.mill_depth
        return cfr, cross_mating_frame

    def subtraction_volume(self):
        """Returns the volume to be subtracted from the cross beam.

        # TODO: break this function into smaller more readable parts
        # TODO: BTLx related code here should end up in a LapFeature..

        """
        vertices = []
        front_frame, back_frame = self.front_back_surface_main()
        top_frame, bottom_frame = self.get_main_cutting_plane()
        sides = self.side_surfaces_cross()
        for i, side in enumerate(sides):
            points = []
            for frame in [bottom_frame, top_frame]:
                for fr in [front_frame, back_frame]:
                    points.append(
                        intersection_plane_plane_plane(
                            Plane.from_frame(side), Plane.from_frame(frame), Plane.from_frame(fr)
                        )
                    )
            pv = [subtract_vectors(pt, self.cross_beam.blank_frame.point) for pt in points]
            dots = [dot_vectors(v, self.cross_beam.centerline.direction) for v in pv]
            dots, points = zip(*sorted(zip(dots, points)))
            min_pt, max_pt = points[0], points[-1]
            if i == 1:
                self.btlx_params_cross["start_x"] = abs(dots[0])

            top_line = Line(*intersection_plane_plane(Plane.from_frame(side), Plane.from_frame(top_frame)))
            top_min = Point(*closest_point_on_line(min_pt, top_line))
            top_max = Point(*closest_point_on_line(max_pt, top_line))

            bottom_line = Line(*intersection_plane_plane(Plane.from_frame(side), Plane.from_frame(bottom_frame)))

            bottom_min = Point(*closest_point_on_line(min_pt, bottom_line))
            bottom_max = Point(*closest_point_on_line(max_pt, bottom_line))

            vertices.extend([Point(*top_min), Point(*top_max), Point(*bottom_max), Point(*bottom_min)])

        top_front = Line(vertices[0], vertices[4])
        top_back = Line(vertices[1], vertices[5])
        _len = distance_line_line(top_front, top_back)

        front_line = Line(*intersection_plane_plane(Plane.from_frame(front_frame), Plane.from_frame(top_frame)))

        self.btlx_params_cross["depth"] = self.mill_depth

        self.btlx_params_cross["width"] = (
            self.cross_beam.height if self.reference_side_index_cross % 2 == 0 else self.cross_beam.width
        )

        self.btlx_params_cross["length"] = _len
        if dot_vectors(top_frame.yaxis, front_line.direction) < 0:
            front_line = Line(front_line.end, front_line.start)
        self.btlx_params_cross["angle"] = abs(
            angle_vectors_signed(top_frame.xaxis, front_line.direction, top_frame.zaxis, deg=True)
        )

        center = (vertices[0] + vertices[1] + vertices[2] + vertices[3]) * 0.25
        angle = angle_vectors_signed(
            subtract_vectors(vertices[0], center), subtract_vectors(vertices[1], center), sides[0].zaxis
        )
        if angle > 0:
            ph = Polyhedron(
                vertices, [[0, 1, 2, 3], [1, 0, 4, 5], [2, 1, 5, 6], [3, 2, 6, 7], [0, 3, 7, 4], [7, 6, 5, 4]]
            )
        else:
            ph = Polyhedron(
                vertices, [[3, 2, 1, 0], [5, 4, 0, 1], [6, 5, 1, 2], [7, 6, 2, 3], [4, 7, 3, 0], [4, 5, 6, 7]]
            )

        return ph

    def calc_params_birdsmouth(self):
        """
        Calculate the parameters for a birdsmouth joint.

        # TODO: break this function into smaller more readable parts
        # TODO: this is BTLx only code, it should move some where else
        # TODO: eventually, there should be a DoubleCut Feature that holds these parameters
        # TODO: there's no birds mouth in L-Butt, if there shouldn't be then at least move to T-Butt

        Parameters:
        ----------
            joint (object): The joint object.
            main_part (object): The main part object.
            cross_part (object): The cross part object.

        Returns:
        ----------
            dict: A dictionary containing the calculated parameters for the birdsmouth joint

        """
        face_dict = self._beam_side_incidence(self.main_beam, self.cross_beam, ignore_ends=True)
        face_keys = sorted([key for key in face_dict.keys()], key=face_dict.get)

        frame1 = self.get_main_cutting_plane()[0]  # offset pocket mill plane
        frame2 = self.cross_beam.faces[face_keys[1]]

        plane1, plane2 = Plane(frame1.point, -frame1.zaxis), Plane.from_frame(frame2)
        intersect_vec = Vector.from_start_end(*intersection_plane_plane(plane2, plane1))

        angles_dict = {}
        for i, face in enumerate(self.main_beam.faces[0:4]):
            angles_dict[i] = face.normal.angle(intersect_vec)
        ref_frame_id = min(angles_dict.keys(), key=angles_dict.get)
        ref_frame = self.main_beam.faces[ref_frame_id]

        ref_frame.point = self.main_beam.blank_frame.point
        if ref_frame_id % 2 == 0:
            ref_frame.point = ref_frame.point - ref_frame.yaxis * self.main_beam.height * 0.5
            ref_frame.point = ref_frame.point + ref_frame.zaxis * self.main_beam.width * 0.5
        else:
            ref_frame.point = ref_frame.point - ref_frame.yaxis * self.main_beam.width * 0.5
            ref_frame.point = ref_frame.point + ref_frame.zaxis * self.main_beam.height * 0.5
        self.test.append(ref_frame)

        start_point = Point(*intersection_plane_plane_plane(plane1, plane2, Plane.from_frame(ref_frame)))
        start_point.transform(Transformation.from_frame_to_frame(ref_frame, Frame.worldXY()))
        StartX, StartY = start_point[0], start_point[1]

        dot_frame1 = plane1.normal.dot(ref_frame.yaxis)
        if dot_frame1 > 0:
            plane1, plane2 = plane2, plane1

        intersect_vec1 = Vector.from_start_end(*intersection_plane_plane(plane1, Plane.from_frame(ref_frame)))
        intersect_vec2 = Vector.from_start_end(*intersection_plane_plane(plane2, Plane.from_frame(ref_frame)))

        if self.ends[str(self.main_beam.guid)] == "start":
            reference_vector = ref_frame.xaxis
        else:
            reference_vector = -ref_frame.xaxis

        if intersect_vec1.dot(ref_frame.yaxis) < 0:
            intersect_vec1 = -intersect_vec1
        if intersect_vec2.dot(ref_frame.yaxis) < 0:
            intersect_vec2 = -intersect_vec2

        Angle1 = angle_vectors(intersect_vec1, reference_vector, deg=True)
        Angle2 = angle_vectors(intersect_vec2, reference_vector, deg=True)

        Inclination1 = angle_vectors(ref_frame.zaxis, plane1.normal, deg=True)
        Inclination2 = angle_vectors(ref_frame.zaxis, plane2.normal, deg=True)

        self.btlx_params_main = {
            "Orientation": self.ends[str(self.main_beam.guid)],
            "StartX": StartX,
            "StartY": StartY,
            "Angle1": Angle1,
            "Inclination1": Inclination1,
            "Angle2": Angle2,
            "Inclination2": Inclination2,
            "ReferencePlaneID": ref_frame_id,
        }
