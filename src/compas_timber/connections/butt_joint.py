from compas.geometry import Frame
from compas_timber.parts import CutFeature
from compas_timber.parts import MillVolume
from compas.geometry import intersection_plane_plane_plane
from compas.geometry import subtract_vectors
from compas.geometry import dot_vectors
from compas.geometry import closest_point_on_line
from compas.geometry import intersection_plane_plane
from compas.geometry import Plane
from compas.geometry import Line
from compas.geometry import Polyhedron
from compas.geometry import Point
from compas.geometry import angle_vectors_signed
from .joint import BeamJoinningError
from .joint import Joint


class ButtJoint(Joint):
    """Abstract Lap type joint with functions common to L-Butt and T-Butt Joints.

    Do not instantiate directly. Please use `**LapJoint.create()` to properly create an instance of lap sub-class and associate it with an assembly.

    Parameters
    ----------
    assembly : :class:`~compas_timber.assembly.TimberAssembly`
        The assembly associated with the beams to be joined.
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

    def __init__(
        self,
        main_beam=None,
        cross_beam=None,
        mill_depth=0,
        small_beam_butts=False,
        modify_cross=True,
        reject_i=False,
        **kwargs
    ):
        super(ButtJoint, self).__init__(**kwargs)

        if small_beam_butts and main_beam and cross_beam:
            if main_beam.width * main_beam.height > cross_beam.width * cross_beam.height:
                main_beam, cross_beam = cross_beam, main_beam

        self.main_beam = main_beam
        self.cross_beam = cross_beam
        self.main_beam_key = main_beam.key if main_beam else None
        self.cross_beam_key = cross_beam.key if cross_beam else None
        self.mill_depth = mill_depth
        self.modify_cross = modify_cross
        self.small_beam_butts = small_beam_butts
        self.reject_i = reject_i
        self.features = []

    @property
    def __data__(self):
        data_dict = {
            "main_beam_key": self.main_beam_key,
            "cross_beam_key": self.cross_beam_key,
            "mill_depth": self.mill_depth,
            "small_beam_butts": self.small_beam_butts,
            "modify_cross": self.modify_cross,
            "reject_i": self.reject_i,
        }
        data_dict.update(super(ButtJoint, self).__data__)
        return data_dict

    @classmethod
    def __from_data__(cls, value):
        instance = cls(
            frame=Frame.__from_data__(value["frame"]),
            key=value["key"],
            mill_depth=value["mill_depth"],
            small_beam_butts=value["small_beam_butts"],
            modify_cross=value["modify_cross"],
            reject_i=value["reject_i"],
        )
        instance.main_beam_key = value["main_beam_key"]
        instance.cross_beam_key = value["cross_beam_key"]
        return instance

    @property
    def beams(self):
        return [self.main_beam, self.cross_beam]

    @property
    def joint_type(self):
        return "Butt"

    def get_main_cutting_plane(self):
        assert self.main_beam and self.cross_beam

        index, _ = self.get_face_most_towards_beam(self.main_beam, self.cross_beam, ignore_ends=False)
        if self.reject_i and index in [4, 5]:
            raise BeamJoinningError(
                beams=self.beams, joint=self, debug_info="Beams are in I topology and reject_i flag is True"
            )

        index, cfr = self.get_face_most_ortho_to_beam(self.main_beam, self.cross_beam, ignore_ends=True)
        cross_mating_frame = cfr.copy()
        cfr = Frame(cfr.point, cfr.xaxis, cfr.yaxis * -1.0)  # flip normal
        cfr.point = cfr.point + cfr.zaxis * self.mill_depth
        return cfr, cross_mating_frame

    def restore_beams_from_keys(self, assemly):
        """After de-serialization, resotres references to the main and cross beams saved in the assembly."""
        self.main_beam = assemly.find_by_key(self.main_beam_key)
        self.cross_beam = assemly.find_by_key(self.cross_beam_key)

    def side_surfaces_cross(self):
        face_dict = Joint._beam_side_incidence(self.main_beam, self.cross_beam, ignore_ends=True)
        face_indices = face_dict.keys()
        angles = face_dict.values()
        angles, face_indices = zip(*sorted(zip(angles, face_indices)))
        return self.cross_beam.faces[face_indices[1]], self.cross_beam.faces[face_indices[2]]

    def front_back_surface_main(self):
        face_dict = Joint._beam_side_incidence(self.cross_beam, self.main_beam, ignore_ends=True)
        face_indices = face_dict.keys()
        angles = face_dict.values()
        angles, face_indices = zip(*sorted(zip(angles, face_indices)))
        return self.main_beam.faces[face_indices[0]], self.main_beam.faces[face_indices[3]]

    def back_surface_main(self):
        face_dict = Joint._beam_side_incidence(self.main_beam, self.cross_beam, ignore_ends=True)
        face_dict.sort(lambda x: x.values())
        return face_dict.values()[3]

    def subtraction_volume(self):
        dir_pts = []
        vertices = []
        sides = self.side_surfaces_cross()
        for side in sides:
            points = []
            top_frame, bottom_frame = self.get_main_cutting_plane()
            for frame in [top_frame, bottom_frame]:
                for fr in self.front_back_surface_main():
                    points.append(
                        intersection_plane_plane_plane(
                            Plane.from_frame(side), Plane.from_frame(frame), Plane.from_frame(fr)
                        )
                    )
            pv = [subtract_vectors(pt, self.cross_beam.centerline.start) for pt in points]
            dots = [dot_vectors(v, self.cross_beam.centerline.direction) for v in pv]
            dots, points = zip(*sorted(zip(dots, points)))
            min_pt, max_pt = points[0], points[-1]
            top_line = Line(*intersection_plane_plane(Plane.from_frame(side), Plane.from_frame(top_frame)))
            bottom_line = Line(*intersection_plane_plane(Plane.from_frame(side), Plane.from_frame(bottom_frame)))
            top_min = Point(*closest_point_on_line(min_pt, top_line))
            dir_pts.append(top_min)

            top_max = Point(*closest_point_on_line(max_pt, top_line))
            bottom_min = Point(*closest_point_on_line(min_pt, bottom_line))
            bottom_max = Point(*closest_point_on_line(max_pt, bottom_line))
            vertices.extend([Point(*top_min), Point(*top_max), Point(*bottom_max), Point(*bottom_min)])

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

    def add_features(self):
        """Adds the required extension and trimming features to both beams.

        This method is automatically called when joint is created by the call to `Joint.create()`.

        """
        assert self.main_beam and self.cross_beam  # should never happen
        if self.features:
            self.main_beam.remove_features(self.features)
        start_main, start_cross = None, None

        try:
            main_cutting_plane = self.get_main_cutting_plane()[0]
            cross_cutting_plane = self.get_cross_cutting_plane()
            start_main, end_main = self.main_beam.extension_to_plane(main_cutting_plane)
            start_cross, end_cross = self.cross_beam.extension_to_plane(cross_cutting_plane)
        except BeamJoinningError as be:
            raise be
        except AttributeError as ae:
            # I want here just the plane that caused the error
            geometries = [cross_cutting_plane] if start_main is not None else [main_cutting_plane]
            raise BeamJoinningError(beams=self.beams, joint=self, debug_info=str(ae), debug_geometries=geometries)
        except Exception as ex:
            raise BeamJoinningError(beams=self.beams, joint=self, debug_info=str(ex))

        extension_tolerance = 0.01  # TODO: this should be proportional to the unit used

        if self.modify_cross:
            self.cross_beam.add_blank_extension(
                start_cross + extension_tolerance, end_cross + extension_tolerance, self.key
            )
            f_cross = CutFeature(cross_cutting_plane)
            self.cross_beam.add_features(f_cross)
            self.features.append(f_cross)

        self.main_beam.add_blank_extension(start_main + extension_tolerance, end_main + extension_tolerance, self.key)

        f_main = CutFeature(main_cutting_plane)
        self.cross_beam.add_features(MillVolume(self.subtraction_volume()))
        self.main_beam.add_features(f_main)
        self.features.append(f_main)
