from compas.geometry import Brep
from compas.geometry import Plane
from compas.geometry import Point
from compas.geometry import Polyhedron
from compas.geometry import Vector
from compas.geometry import intersection_line_line
from compas.geometry import intersection_plane_plane
from compas.geometry import intersection_plane_plane_plane
from compas.geometry import plane
from numpy import negative

from compas_timber.connections.joint import Joint
from compas_timber.connections.lap_joint import LapJoint
from compas_timber.connections.utilities import beam_ref_side_incidence
from compas_timber.elements import Beam
from compas_timber.fabrication import FrenchRidgeLap
from compas_timber.fabrication import JackRafterCut
from compas_timber.fabrication import Lap
from compas_timber.fabrication import LongitudinalCut
from compas_timber.fabrication.btlx import MachiningLimits
from compas_timber.fabrication.jack_cut import JackRafterCut


class YSpatialLapJoint(Joint):
    def __init__(self, cross_beam: Beam, *main_beams: Beam, **kwargs):
        super().__init__(**kwargs)
        self.cross_beam = cross_beam
        self.main_beams = list(main_beams)
        self.mill_depth_a = 2
        self.mill_depth_b = 4
        self.cut_plane_bias_a = 0.5
        self.cut_plane_bias_b = 0.4
        self._plane_a = None
        self._plane_b = None
        self._plane_a_lap = None
        self._plane_b_lap = None

    @property
    def __data__(self):
        raise NotImplementedError

    @property
    def beams(self):
        return [self.cross_beam] + self.main_beams

    @property
    def elements(self):
        return self.beams

    @property
    def beam_a(self):
        return self.main_beams[0]

    @property
    def beam_b(self):
        return self.main_beams[1]

    @property
    def plane_a(self):
        if not self._plane_a:
            ref_side_index = (self.ref_side_index(self.beam_a, self.beam_b) + 2) % 4
            plane_a = Plane.from_frame(self.beam_a.ref_sides[ref_side_index])
            plane_a.point += self.mill_depth_a * -plane_a.normal
            self._plane_a = plane_a
        return self._plane_a

    @property
    def plane_b(self):
        if not self._plane_b:
            ref_side_index = (self.ref_side_index(self.beam_b, self.beam_a) + 2) % 4
            plane_b = Plane.from_frame(self.beam_b.ref_sides[ref_side_index])
            plane_b.point += self.mill_depth_b * -plane_b.normal
            self._plane_b = plane_b
        return self._plane_b

    @property
    def main_beams_plane(self):
        intersection_point = intersection_line_line(self.main_beams[0].centerline, self.main_beams[1].centerline)
        point = Point(*intersection_point[0])
        plane = Plane.from_point_and_two_vectors(point, self.main_beams[0].centerline.direction, self.main_beams[1].centerline.direction)
        return plane

    def cross_beam_ref_side_inde(self, beam):
        raise NotImplementedError

    def main_beam_ref_side_index(self, beam):
        raise NotImplementedError

    def ref_side_index(self, beam, ref_beam):
        ref_side_dict = beam_ref_side_incidence(ref_beam, beam, ignore_ends=True)
        ref_side_index = min(ref_side_dict, key=ref_side_dict.get)
        return ref_side_index

    def add_extensions(self):
        """
        Calculates and adds the necessary extensions to the beams.
        """
        self._extend_cross_beam()
        self._extend_main_beam(self.main_beams[0], self.main_beams[1])
        self._extend_main_beam(self.main_beams[1], self.main_beams[0])
        # Extend the cross beam, to the plane created by the two main_beam

    def _extend_cross_beam(self):
        intersection_point = intersection_line_line(self.main_beams[0].centerline, self.main_beams[1].centerline)
        max_main_beams_height = max([beam.get_dimensions_relative_to_side(self.ref_side_index(beam, self.cross_beam))[1] for beam in self.main_beams])
        cross_beam_direction = self.cross_beam.centerline.direction
        if self.cross_beam.centerline.point.distance_to_point(Point(*intersection_point[0])) < self.cross_beam.centerline.end.distance_to_point(Point(*intersection_point[0])):
            cross_beam_direction = cross_beam_direction.scaled(-1)
        plane = self.main_beams_plane
        plane.point += max_main_beams_height / 2 * cross_beam_direction
        blank = self.cross_beam.extension_to_plane(plane)
        self.cross_beam.add_blank_extension(*blank)

    def _extend_main_beam(self, beam, other_beam):
        plane_ref_side_index = (self.ref_side_index(other_beam, beam) + 2) % 4
        plane = Plane.from_frame(other_beam.ref_sides[plane_ref_side_index])
        blank = beam.extension_to_plane(plane)
        beam.add_blank_extension(*blank)
        return beam

    def add_features(self):
        self._lap_on_a()
        self._jack_rafter_cut_on_a()
        self._lap_on_b()
        self._jack_rafter_cut_on_b()
        self._lap_a_on_cross()
        self._lap_b_on_cross()

    def _brep_from_planes(self, plane_a, plane_b, plane_c, plane_d, plane_e, plane_f):
        v0 = Point(*intersection_plane_plane_plane(plane_a, plane_e, plane_d))
        v1 = Point(*intersection_plane_plane_plane(plane_a, plane_e, plane_b))
        v2 = Point(*intersection_plane_plane_plane(plane_a, plane_c, plane_b))
        v3 = Point(*intersection_plane_plane_plane(plane_a, plane_c, plane_d))
        v4 = Point(*intersection_plane_plane_plane(plane_f, plane_e, plane_d))
        v5 = Point(*intersection_plane_plane_plane(plane_f, plane_e, plane_b))
        v6 = Point(*intersection_plane_plane_plane(plane_f, plane_c, plane_b))
        v7 = Point(*intersection_plane_plane_plane(plane_f, plane_c, plane_d))

        vertices = [v0, v1, v2, v3, v4, v5, v6, v7]
        # faces = [[0, 3, 2, 1], [4, 5, 6, 7], [0, 1, 5, 4], [1, 2, 6, 5], [2, 3, 7, 6], [3, 0, 4, 7]]
        faces = [[0, 1, 2, 3], [4, 7, 6, 5], [0, 4, 5, 1], [1, 5, 6, 2], [2, 6, 7, 3], [3, 7, 4, 0]]
        faces = _ensure_faces_outward(vertices, faces)
        polyhedron = Polyhedron(vertices, faces)
        return polyhedron
        mesh = polyhedron.to_mesh()
        return mesh

    def _lap_on_a(self):
        plane_a = Plane.from_frame(self.beam_a.ref_sides[self.ref_side_index(self.beam_a, self.beam_b)])
        plane_e = Plane.from_frame(self.beam_a.ref_sides[self.ref_side_index(self.beam_a, self.cross_beam)])
        plane_c = Plane.from_frame(self.beam_a.ref_sides[(self.ref_side_index(self.beam_a, self.cross_beam) + 2) % 4])
        plane_d = Plane.from_frame(self.cross_beam.ref_sides[self.ref_side_index(self.cross_beam, self.beam_a)])
        plane_b = Plane.from_frame(self.cross_beam.ref_sides[(self.ref_side_index(self.cross_beam, self.beam_a) + 2) % 4])
        plane_f = plane_a.copy()
        plane_f.normal *= -1
        plane_f.point += 5 * plane_f.normal
        negative_volume = self._brep_from_planes(plane_a, plane_b, plane_c, plane_d, plane_e, plane_f)
        lap_on_a = Lap.from_volume_and_beam(negative_volume, self.beam_a, ref_side_index=self.ref_side_index(self.beam_a, self.beam_b))
        self.beam_a.add_feature(lap_on_a)
        return negative_volume

    def _jack_rafter_cut_on_a(self):
        cutting_plane = Plane.from_frame(self.cross_beam.ref_sides[(self.ref_side_index(self.cross_beam, self.beam_a) + 2) % 4])
        jack_rafter_cut = JackRafterCut.from_plane_and_beam(cutting_plane, self.beam_a)
        self.beam_a.add_feature(jack_rafter_cut)

    def _lap_on_b(self):
        plane_a = Plane.from_frame(self.beam_b.ref_sides[self.ref_side_index(self.beam_b, self.beam_a)])
        plane_e = Plane.from_frame(self.beam_b.ref_sides[self.ref_side_index(self.beam_b, self.cross_beam)])
        plane_c = Plane.from_frame(self.beam_b.ref_sides[(self.ref_side_index(self.beam_b, self.cross_beam) + 2) % 4])
        plane_d = Plane.from_frame(self.cross_beam.ref_sides[self.ref_side_index(self.cross_beam, self.beam_b)])
        plane_b = Plane.from_frame(self.cross_beam.ref_sides[(self.ref_side_index(self.cross_beam, self.beam_b) + 2) % 4])
        plane_f = plane_a.copy()
        plane_f.normal *= -1
        plane_f.point += 5 * plane_f.normal
        negative_volume = self._brep_from_planes(plane_a, plane_b, plane_c, plane_d, plane_e, plane_f)
        lap_on_b = Lap.from_volume_and_beam(negative_volume, self.beam_b, ref_side_index=self.ref_side_index(self.beam_b, self.beam_a))
        self.beam_b.add_feature(lap_on_b)
        return negative_volume

    def _jack_rafter_cut_on_b(self):
        cutting_plane = Plane.from_frame(self.cross_beam.ref_sides[(self.ref_side_index(self.cross_beam, self.beam_b) + 2) % 4])
        cutting_plane.point -= 5 * cutting_plane.normal
        jack_rafter_cut = JackRafterCut.from_plane_and_beam(cutting_plane, self.beam_b)
        self.beam_b.add_feature(jack_rafter_cut)

    def _lap_a_on_cross(self):
        plane_a = Plane.from_frame(self.beam_a.ref_sides[(self.ref_side_index(self.beam_a, self.beam_b) + 2) % 4])
        plane_e = Plane.from_frame(self.cross_beam.ref_sides[self.ref_side_index(self.cross_beam, self.beam_a)])
        plane_c = Plane.from_frame(self.cross_beam.ref_sides[(self.ref_side_index(self.cross_beam, self.beam_a) + 2) % 4])
        plane_d = Plane.from_frame(self.beam_a.ref_sides[(self.ref_side_index(self.beam_a, self.cross_beam))])
        plane_b = Plane.from_frame(self.beam_a.ref_sides[(self.ref_side_index(self.beam_a, self.cross_beam) + 2) % 4])
        plane_f = plane_a.copy()
        plane_f.normal *= -1
        plane_f.point += 5 * plane_f.normal
        negative_volume = self._brep_from_planes(plane_a, plane_b, plane_c, plane_d, plane_e, plane_f)

        mac_lim = MachiningLimits()
        mac_lim.face_limited_front = False
        mac_lim.face_limited_top = False
        mac_lim.face_limited_back = False
        mac_lim.face_limited_end = False

        lap_a_on_cross = Lap.from_volume_and_beam(
            negative_volume,
            self.cross_beam,
            ref_side_index=(self.ref_side_index(self.cross_beam, self.beam_b) + 2) % 4,
            machining_limits=mac_lim.limits,
        )
        self.cross_beam.add_feature(lap_a_on_cross)
        print(lap_a_on_cross.machining_limits)
        return negative_volume

    def _lap_b_on_cross(self):
        plane_a = Plane.from_frame(self.beam_b.ref_sides[(self.ref_side_index(self.beam_b, self.beam_a) + 2) % 4])
        plane_e = Plane.from_frame(self.cross_beam.ref_sides[self.ref_side_index(self.cross_beam, self.beam_b)])
        plane_c = Plane.from_frame(self.cross_beam.ref_sides[(self.ref_side_index(self.cross_beam, self.beam_b) + 2) % 4])
        plane_c.point -= (5 - 0.1) * plane_c.normal
        plane_d = Plane.from_frame(self.beam_b.ref_sides[(self.ref_side_index(self.beam_b, self.cross_beam))])
        plane_b = Plane.from_frame(self.beam_b.ref_sides[(self.ref_side_index(self.beam_b, self.cross_beam) + 2) % 4])
        plane_f = plane_a.copy()
        plane_f.normal *= -1
        plane_f.point += 5 * plane_f.normal
        negative_volume = self._brep_from_planes(plane_a, plane_b, plane_c, plane_d, plane_e, plane_f)

        mac_lim = MachiningLimits()
        mac_lim.face_limited_front = False
        mac_lim.face_limited_top = False
        mac_lim.face_limited_back = True
        mac_lim.face_limited_end = False

        lap_b_on_cross = Lap.from_volume_and_beam(
            negative_volume, self.cross_beam, ref_side_index=(self.ref_side_index(self.cross_beam, self.beam_a) + 2) % 4, machining_limits=mac_lim.limits
        )
        self.cross_beam.add_feature(lap_b_on_cross)
        return negative_volume

    def restore_beams_from_keys(self, model):
        raise NotImplementedError

    @classmethod
    def check_elements_compatibility(cls, elements, raise_error=False):
        raise NotImplementedError


def _ensure_faces_outward(vertices, faces):
    """Reorder face indices so face normals point outward.

    vertices: list of Point or 3-tuples
    faces: list of lists of indices
    Returns: new_faces (modified in place is fine too)
    """
    # robustly extract coordinates
    coords = []
    for v in vertices:
        try:
            coords.append([v.x, v.y, v.z])
        except AttributeError:
            coords.append(list(v))

    # polyhedron centroid
    poly_centroid = [sum(c[i] for c in coords) / len(coords) for i in range(3)]

    def vec(a, b):
        return [b[i] - a[i] for i in range(3)]

    def cross(a, b):
        return [
            a[1] * b[2] - a[2] * b[1],
            a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0],
        ]

    def dot(a, b):
        return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]

    new_faces = []
    for face in faces:
        # skip degenerate faces
        if len(face) < 3:
            new_faces.append(face)
            continue
        v0 = coords[face[0]]
        v1 = coords[face[1]]
        v2 = coords[face[2]]

        e1 = vec(v0, v1)
        e2 = vec(v0, v2)
        n = cross(e1, e2)

        # face centroid
        face_centroid = [sum(coords[idx][k] for idx in face) / len(face) for k in range(3)]
        outward = vec(poly_centroid, face_centroid)

        # if dot < 0 the normal points inward — reverse vertex order
        if dot(n, outward) < 0:
            new_faces.append(list(reversed(face)))
        else:
            new_faces.append(list(face))

    return new_faces
