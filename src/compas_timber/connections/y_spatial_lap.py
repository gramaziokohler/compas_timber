from __future__ import annotations

from typing import TYPE_CHECKING

from compas.geometry import Plane
from compas.geometry import Point
from compas.geometry import Polyhedron
from compas.geometry import intersection_plane_plane_plane

from compas_timber.connections.joint import Joint
from compas_timber.connections.utilities import beam_ref_side_incidence
from compas_timber.elements import Beam
from compas_timber.fabrication import JackRafterCut
from compas_timber.fabrication import Lap
from compas_timber.fabrication.btlx import MachiningLimits

if TYPE_CHECKING:
    from compas_timber.elements import TimberModel


class YSpatialLapJoint(Joint):
    def __init__(self, cross_beam: Beam, *main_beams: Beam, cut_plane_bias_a: float = 0.5, cut_plane_bias_b: float = 0.5, **kwargs):
        super().__init__(**kwargs)
        self.cross_beam: Beam = cross_beam
        self.main_beams: list[Beam] = list(main_beams)

        # TODO: add the features based on the biases
        self.cut_plane_bias_a: float = 0.5
        self.cut_plane_bias_b: float = 0.4

    @property
    def __data__(self):
        raise NotImplementedError

    @property
    def beams(self):
        return [self.cross_beam] + self.main_beams

    @property
    def elements(self) -> list[Beam]:
        return self.beams

    @property
    def beam_a(self) -> Beam:
        return self.main_beams[0]

    @property
    def beam_b(self) -> Beam:
        return self.main_beams[1]

    def cross_beam_ref_side_inde(self, beam: Beam):
        raise NotImplementedError

    def main_beam_ref_side_index(self, beam: Beam):
        raise NotImplementedError

    def ref_side_index(self, beam: Beam, ref_beam: Beam) -> int:
        ref_side_dict = beam_ref_side_incidence(ref_beam, beam, ignore_ends=True)
        ref_side_index = min(ref_side_dict, key=lambda k: ref_side_dict.get(k, float("inf")))
        return ref_side_index

    def add_extensions(self) -> None:
        """
        Calculates and adds the necessary extensions to the beams.
        """
        self._extend_cross_beam()
        self._extend_main_beam(self.main_beams[0], self.main_beams[1])
        self._extend_main_beam(self.main_beams[1], self.main_beams[0])
        # Extend the cross beam, to the plane created by the two main_beam

    def _extend_cross_beam(self) -> None:
        ext_plane_a = self.beam_a.ref_sides[(self.ref_side_index(self.beam_a, self.cross_beam) + 2) % 4]
        blank_a = self.cross_beam.extension_to_plane(ext_plane_a)

        ext_plane_b = self.beam_b.ref_sides[(self.ref_side_index(self.beam_b, self.cross_beam) + 2) % 4]
        blank_b = self.cross_beam.extension_to_plane(ext_plane_b)

        blank = [0.0, 0.0]

        if blank_a[0] > blank_b[0]:
            blank[0] = blank_a[0]
        elif blank_a[0] == blank_b[0] and blank_a[0] == 0:
            blank[0] = 0
        else:
            blank[0] = blank_b[0]

        if blank_a[1] > blank_b[1]:
            blank[1] = blank_a[1]
        elif blank_a[1] == blank_b[1] and blank_a[1] == 0:
            blank[1] = 0
        else:
            blank[1] = blank_b[1]
        self.cross_beam.add_blank_extension(blank[0], blank[1])

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

    def _brep_from_planes(self, plane_a, plane_b, plane_c, plane_d, plane_e, plane_f) -> Polyhedron:
        v0 = Point(*intersection_plane_plane_plane(plane_a, plane_e, plane_d))  # type: ignore
        v1 = Point(*intersection_plane_plane_plane(plane_a, plane_e, plane_b))  # type: ignore
        v2 = Point(*intersection_plane_plane_plane(plane_a, plane_c, plane_b))  # type: ignore
        v3 = Point(*intersection_plane_plane_plane(plane_a, plane_c, plane_d))  # type: ignore
        v4 = Point(*intersection_plane_plane_plane(plane_f, plane_e, plane_d))  # type: ignore
        v5 = Point(*intersection_plane_plane_plane(plane_f, plane_e, plane_b))  # type: ignore
        v6 = Point(*intersection_plane_plane_plane(plane_f, plane_c, plane_b))  # type: ignore
        v7 = Point(*intersection_plane_plane_plane(plane_f, plane_c, plane_d))  # type: ignore
        vertices = [v0, v1, v2, v3, v4, v5, v6, v7]
        faces = [[0, 1, 2, 3], [4, 7, 6, 5], [0, 4, 5, 1], [1, 5, 6, 2], [2, 6, 7, 3], [3, 7, 4, 0]]
        faces = _ensure_faces_outward(vertices, faces)
        polyhedron = Polyhedron(vertices, faces)
        return polyhedron

    def _lap_on_a(self) -> Polyhedron:
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

    def _jack_rafter_cut_on_a(self) -> Plane:
        cutting_plane = Plane.from_frame(self.cross_beam.ref_sides[(self.ref_side_index(self.cross_beam, self.beam_a) + 2) % 4])
        jack_rafter_cut = JackRafterCut.from_plane_and_beam(cutting_plane, self.beam_a)
        self.beam_a.add_feature(jack_rafter_cut)
        return cutting_plane

    def _lap_on_b(self) -> Polyhedron:
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

    def _jack_rafter_cut_on_b(self) -> Plane:
        cutting_plane = Plane.from_frame(self.cross_beam.ref_sides[(self.ref_side_index(self.cross_beam, self.beam_b) + 2) % 4])
        cutting_plane.point -= 5 * cutting_plane.normal
        jack_rafter_cut = JackRafterCut.from_plane_and_beam(cutting_plane, self.beam_b)
        self.beam_b.add_feature(jack_rafter_cut)
        return cutting_plane

    def _compute_machining_limits(self, beam: Beam) -> MachiningLimits:
        mac_lim = MachiningLimits()
        mac_lim.face_limited_front = False
        mac_lim.face_limited_top = False
        if beam is self.beam_a:
            mac_lim.face_limited_back = False
        else:
            mac_lim.face_limited_back = True
        mac_lim.face_limited_end = True
        mac_lim.face_limited_bottom = True
        mac_lim.face_limited_start = False
        return mac_lim

    def _lap_a_on_cross(self) -> Polyhedron:
        plane_a = Plane.from_frame(self.beam_a.ref_sides[(self.ref_side_index(self.beam_a, self.beam_b) + 2) % 4])
        plane_e = Plane.from_frame(self.cross_beam.ref_sides[self.ref_side_index(self.cross_beam, self.beam_a)])
        plane_c = Plane.from_frame(self.cross_beam.ref_sides[(self.ref_side_index(self.cross_beam, self.beam_a) + 2) % 4])
        plane_d = Plane.from_frame(self.beam_a.ref_sides[(self.ref_side_index(self.beam_a, self.cross_beam))])
        plane_b = Plane.from_frame(self.beam_a.ref_sides[(self.ref_side_index(self.beam_a, self.cross_beam) + 2) % 4])
        plane_f = plane_a.copy()
        plane_f.normal *= -1
        plane_f.point += 5 * plane_f.normal

        negative_volume = self._brep_from_planes(plane_a, plane_b, plane_c, plane_d, plane_e, plane_f)

        mac_lim = self._compute_machining_limits(self.beam_a)

        lap_a_on_cross = Lap.from_volume_and_beam(
            volume=negative_volume, beam=self.cross_beam, ref_side_index=(self.ref_side_index(self.cross_beam, self.beam_b) + 2) % 4, machining_limits=mac_lim.limits
        )
        self.cross_beam.add_feature(lap_a_on_cross)
        return negative_volume

    def _lap_b_on_cross(self) -> Polyhedron:
        plane_a = Plane.from_frame(self.beam_b.ref_sides[(self.ref_side_index(self.beam_b, self.beam_a) + 2) % 4])
        plane_e = Plane.from_frame(self.cross_beam.ref_sides[self.ref_side_index(self.cross_beam, self.beam_b)])
        plane_c = Plane.from_frame(self.cross_beam.ref_sides[(self.ref_side_index(self.cross_beam, self.beam_b) + 2) % 4])
        plane_c.point -= (5) * plane_c.normal
        plane_d = Plane.from_frame(self.beam_b.ref_sides[(self.ref_side_index(self.beam_b, self.cross_beam))])
        plane_b = Plane.from_frame(self.beam_b.ref_sides[(self.ref_side_index(self.beam_b, self.cross_beam) + 2) % 4])
        plane_f = plane_a.copy()
        plane_f.normal *= -1
        plane_f.point += 5 * plane_f.normal

        negative_volume = self._brep_from_planes(plane_a, plane_b, plane_c, plane_d, plane_e, plane_f)

        mac_lim = self._compute_machining_limits(self.beam_b)

        lap_b_on_cross = Lap.from_volume_and_beam(
            volume=negative_volume, beam=self.cross_beam, ref_side_index=(self.ref_side_index(self.cross_beam, self.beam_a) + 2) % 4, machining_limits=mac_lim.limits
        )
        self.cross_beam.add_feature(lap_b_on_cross)
        return negative_volume

    def restore_beams_from_keys(self, model: TimberModel):
        raise NotImplementedError

    @classmethod
    def check_elements_compatibility(cls, elements, raise_error=False):
        raise NotImplementedError


def _ensure_faces_outward(vertices: list[Point], faces: list[list[int]]) -> list[list[int]]:
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
