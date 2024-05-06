from compas.geometry import Frame
from compas.geometry import Line
from compas.geometry import Plane
from compas.geometry import Point
from compas.geometry import Polyhedron
from compas.geometry import angle_vectors_signed
from compas.geometry import closest_point_on_line
from compas.geometry import dot_vectors
from compas.geometry import intersection_plane_plane
from compas.geometry import intersection_plane_plane_plane
from compas.geometry import subtract_vectors

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

    @property
    def __data__(self):
        data_dict = {
            "main_beam_key": self.main_beam_key,
            "cross_beam_key": self.cross_beam_key,
            "mill_depth": self.mill_depth,
        }
        data_dict.update(super(ButtJoint, self).__data__)
        return data_dict

    @classmethod
    def __from_data__(cls, value):
        instance = cls(**value)
        instance.main_beam_key = value["main_beam_key"]
        instance.cross_beam_key = value["cross_beam_key"]
        return instance

    def __init__(self, main_beam=None, cross_beam=None, mill_depth=0, **kwargs):
        super(ButtJoint, self).__init__(**kwargs)
        self.main_beam = main_beam
        self.cross_beam = cross_beam
        self.main_beam_key = str(main_beam.guid) if main_beam else None
        self.cross_beam_key = str(cross_beam.guid) if cross_beam else None
        self.mill_depth = mill_depth
        self.features = []

    @property
    def beams(self):
        return [self.main_beam, self.cross_beam]

    def restore_beams_from_keys(self, model):
        """After de-serialization, resotres references to the main and cross beams saved in the assembly."""
        self.main_beam = model.elementdict[self.main_beam_key]
        self.cross_beam = model.elementdict[self.cross_beam_key]

    def side_surfaces_cross(self):
        assert self.main_beam and self.cross_beam

        face_dict = Joint._beam_side_incidence(self.main_beam, self.cross_beam, ignore_ends=True)
        face_indices = face_dict.keys()
        angles = face_dict.values()
        angles, face_indices = zip(*sorted(zip(angles, face_indices)))
        return self.cross_beam.faces[face_indices[1]], self.cross_beam.faces[face_indices[2]]

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
        assert self.main_beam and self.cross_beam
        _, cfr = self.get_face_most_ortho_to_beam(self.main_beam, self.cross_beam, ignore_ends=True)
        cross_mating_frame = cfr.copy()
        cfr = Frame(cfr.point, cfr.xaxis, cfr.yaxis * -1.0)  # flip normal
        cfr.point = cfr.point + cfr.zaxis * self.mill_depth
        return cfr, cross_mating_frame

    def subtraction_volume(self):
        dir_pts = []
        vertices = []
        sides = self.side_surfaces_cross()
        for i, side in enumerate(sides):
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
