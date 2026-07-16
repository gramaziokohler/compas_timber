from compas.data import Data
from compas.geometry import Line
from compas.geometry import Plane
from compas.geometry import Point
from compas.geometry import Polyhedron
from compas.geometry import Vector
from compas.geometry import angle_vectors
from compas.geometry import intersection_line_line
from compas.geometry import intersection_line_plane
from compas.geometry import intersection_plane_plane_plane
from compas.tolerance import TOL

from compas_timber.errors import BeamJoiningError

from .joint import Joint
from .utilities import beam_ref_side_incidence
from .utilities import beam_ref_side_incidence_with_vector
from .utilities import decompose_plane_to_ref_side_angles
from .utilities import plane_from_ref_side_angles_offset


class LapPlaneSpec(Data):
    """A lap cutting plane stored relative to a beam's reference side.

    Translates a world-coordinate (Rhino) plane into the beam's reference-side
    coordinate system. Uses the same UNCONSTRAINED two-angle parameterisation as
    ``LMiterJoint``'s ``MiterPlaneSpec`` (``ref_side_index, angle_x, angle_y, offset``)
    so ANY plane orientation is preserved -- a lap interface may tilt in two directions,
    unlike a butt cut. Use :meth:`from_plane` to encode and :meth:`to_plane` to reconstruct.
    """

    @property
    def __data__(self):
        return {"ref_side_index": self.ref_side_index, "angle_x": self.angle_x, "angle_y": self.angle_y, "offset": self.offset}

    def __init__(self, ref_side_index, angle_x=0.0, angle_y=0.0, offset=0.0):
        super().__init__()
        self.ref_side_index = ref_side_index
        self.angle_x = angle_x
        self.angle_y = angle_y
        self.offset = offset

    def to_plane(self, beam):
        """Reconstruct the world-coordinate plane relative to ``beam``."""
        ref_side = beam.ref_sides[self.ref_side_index]
        return plane_from_ref_side_angles_offset(ref_side, self.angle_x, self.angle_y, self.offset)

    @classmethod
    def from_plane(cls, beam_a, beam_b, plane):
        """Encode ``plane`` relative to the face of ``beam_a`` closest to ``beam_b``. Any orientation allowed."""
        ref_side_dict = beam_ref_side_incidence(beam_a, beam_b, ignore_ends=True)
        ref_side_index = min(ref_side_dict, key=lambda k: ref_side_dict[k])
        ref_side = beam_a.ref_sides[ref_side_index]
        angle_x, angle_y, offset = decompose_plane_to_ref_side_angles(ref_side, plane)
        return cls(ref_side_index, angle_x, angle_y, offset)


class LapJoint(Joint):
    """Abstract Lap type joint with functions common to L-Lap, T-Lap, and X-Lap Joints.

    Do not instantiate directly. Please use `**LapJoint.create()` to properly create an instance of lap sub-class and associate it with an model.

    Parameters
    ----------
    beam_a : :class:`~compas_timber.elements.Beam`
        The first beam to be joined.
    beam_b : :class:`~compas_timber.elements.Beam`
        The second beam to be joined.
    flip_lap_side : bool
        If True, the lap is flipped to the other side of the beams.

    Attributes
    ----------
    elements : list of :class:`~compas_timber.elements.Beam`
        The beams to be joined.
    beam_a : :class:`~compas_timber.elements.Beam`
        The first beam to be joined.
    beam_b : :class:`~compas_timber.elements.Beam`
        The second beam to be joined.
    flip_lap_side : bool
        If True, the lap is flipped to the other side of the beams.

    """

    @property
    def __data__(self):
        data = super(LapJoint, self).__data__
        data["flip_lap_side"] = self.flip_lap_side
        data["cut_plane_bias"] = self.cut_plane_bias
        data["lap_plane_spec"] = self._lap_plane_spec
        return data

    def __init__(self, beam_a=None, beam_b=None, flip_lap_side=False, cut_plane_bias=0.5, lap_plane_spec=None, **kwargs):
        super(LapJoint, self).__init__(elements=(beam_a, beam_b), **kwargs)
        self.flip_lap_side = flip_lap_side
        self.cut_plane_bias = cut_plane_bias
        self._lap_plane_spec = lap_plane_spec
        self.features = []

        self._ref_side_index_a = None
        self._ref_side_index_b = None
        self._cutting_plane_a = None
        self._cutting_plane_b = None

    @property
    def beam_a(self):
        return self.element_a

    @property
    def beam_b(self):
        return self.element_b

    @property
    def lap_plane_spec(self):
        """The optional LapPlaneSpec override (world plane translated to beam coords)."""
        return self._lap_plane_spec

    @property
    def cut_plane_normal(self):
        """Normal that orients the lap interface (depth) plane, derived from the LapPlaneSpec.

        The world (Rhino) plane is stored beam-relative (like ButtJoint/Miter); here it is
        reconstructed and its normal is used to tilt the lap's interface plane. Returns
        ``None`` if no spec is set (default beam-derived stacking direction). Only the
        normal is used; face selection stays beam-derived. Raises if the normal is
        parallel to a beam centerline.
        """
        if self._lap_plane_spec is None:
            return None
        normal = self._lap_plane_spec.to_plane(self.beam_a).normal
        for beam in (self.beam_a, self.beam_b):
            if beam is not None and TOL.is_zero(normal.cross(beam.centerline.direction).length):
                raise BeamJoiningError(
                    self.elements,
                    self,
                    debug_info="lap_plane_spec normal is parallel to a beam centerline; cannot orient the lap cut.",
                )
        return normal

    @property
    def ref_side_index_a(self):
        """The reference side index of the beam_a."""
        if self._ref_side_index_a is None:
            self._ref_side_index_a = self._get_beam_ref_side_index(self.beam_a, self.beam_b, self.flip_lap_side)
        return self._ref_side_index_a

    @property
    def ref_side_index_b(self):
        """The reference side index of the beam_b."""
        if self._ref_side_index_b is None:
            self._ref_side_index_b = self._get_beam_ref_side_index(self.beam_b, self.beam_a, self.flip_lap_side)
        return self._ref_side_index_b

    @property
    def cutting_plane_a(self):
        """The face of the beam_b that cuts the beam_a, as a plane.

        Always the default face. The lap-plane-spec override applies only to the
        notch volume (see `_create_negative_volumes`), NOT to extension/cutoff,
        so trimming stays as in the original joint.
        """
        if self._cutting_plane_a is None:
            self._cutting_plane_a = self._get_cutting_plane(self.beam_b, self.beam_a)
        return self._cutting_plane_a

    @property
    def cutting_plane_b(self):
        """The face of the beam_a that cuts the beam_b, as a plane. Default face (see cutting_plane_a)."""
        if self._cutting_plane_b is None:
            self._cutting_plane_b = self._get_cutting_plane(self.beam_a, self.beam_b)
        return self._cutting_plane_b

    @staticmethod
    def _get_beam_ref_side_index(beam_a, beam_b, flip):
        """Returns the reference side index of beam_a with respect to beam_b."""
        # get the offset vector of the two centerlines, if any
        offset_vector = Vector.from_start_end(*intersection_line_line(beam_a.centerline, beam_b.centerline))
        cross_vector = beam_a.centerline.direction.cross(beam_b.centerline.direction)
        # flip the cross_vector if it is pointing in the opposite direction of the offset_vector
        if cross_vector.dot(offset_vector) < 0:
            cross_vector = -cross_vector
        ref_side_dict = beam_ref_side_incidence_with_vector(beam_a, cross_vector, ignore_ends=True)
        if flip:
            return max(ref_side_dict, key=ref_side_dict.get)
        return min(ref_side_dict, key=ref_side_dict.get)

    @staticmethod
    def _get_cutting_plane(beam_a, beam_b):
        """Returns the plane from beam_b that cuts beam_a."""
        ref_side_dict = beam_ref_side_incidence(beam_b, beam_a, ignore_ends=True)
        ref_side_index = max(ref_side_dict, key=ref_side_dict.get)
        return Plane.from_frame(beam_a.ref_sides[ref_side_index])

    @staticmethod
    def _sort_beam_planes(beam, cutplane_vector):
        # Sorts the Beam Face Planes according to the Cut Plane
        frames = beam.ref_sides[:4]
        planes = [Plane.from_frame(frame) for frame in frames]
        planes.sort(key=lambda x: angle_vectors(cutplane_vector, x.normal))
        return planes

    @staticmethod
    def _create_polyhedron(plane_a, lines, bias, cut_plane=None, top_extension=0.0):  # Hexahedron from 2 Planes and 4 Lines
        # Step 1: Get 8 Intersection Points from 2 Planes and 4 Lines
        int_points = []
        # Find the line with the biggest length
        longest_line = max(lines, key=lambda line: line.length)
        # Interface (depth) plane. When a cut_plane override is given, use it DIRECTLY:
        # it defines BOTH the orientation AND the height/position of the lap interface,
        # so cut_plane_bias is ignored. Otherwise fall back to the default: the stacking
        # direction positioned at the bias point along the corner line.
        if cut_plane is not None:
            plane = cut_plane
        else:
            plane = Plane(longest_line.point_at(bias), longest_line.direction)
        for i in lines:
            point_top = intersection_line_plane(i, plane_a)
            point_bottom = intersection_line_plane(i, plane)
            if point_top is None or point_bottom is None:
                raise ValueError(
                    "The lap cut plane does not intersect the lap region. "
                    "Use a cut plane closer to the beams' overlap / stacking direction."
                )
            point_top = Point(*point_top)
            point_bottom = Point(*point_bottom)
            # Push the top cap outward along the depth axis so the negative volume
            # always cuts fully through the beam. The excess sits outside the beam
            # (harmless) and leaves the interface (bottom) plane untouched.
            if top_extension:
                direction = Vector.from_start_end(point_bottom, point_top)
                if direction.length:
                    direction.unitize()
                    point_top = point_top + direction * top_extension
            int_points.append(point_top)
            int_points.append(point_bottom)

        # Step 2: Check if int_points Order results in an inward facing Polyhedron
        test_face_vector1 = Vector.from_start_end(int_points[0], int_points[2])
        test_face_vector2 = Vector.from_start_end(int_points[0], int_points[6])
        test_face_normal = Vector.cross(test_face_vector1, test_face_vector2)
        check_vector = Vector.from_start_end(int_points[0], int_points[1])
        # Flip int_points Order if needed
        if angle_vectors(test_face_normal, check_vector) < 1:
            a, b, c, d, e, f, g, h = int_points
            int_points = b, a, d, c, f, e, h, g

        # Step 3: Create a Hexahedron with 6 Faces from the 8 Points
        return Polyhedron(
            int_points,
            [
                [1, 7, 5, 3],  # top
                [0, 2, 4, 6],  # bottom
                [1, 3, 2, 0],  # left
                [3, 5, 4, 2],  # back
                [5, 7, 6, 4],  # right
                [7, 1, 0, 6],  # front
            ],
        )

    def _create_negative_volumes(self, cut_plane_bias):
        assert len(self.elements) == 2, "LapJoint requires two elements."
        beam_a, beam_b = self.elements

        # Get Cut Plane
        plane_cut_vector = beam_a.centerline.vector.cross(beam_b.centerline.vector)
        # flip the plane normal if the cross_vector is pointing in the opposite direction of the offset_vector
        offset_vector = Vector.from_start_end(*intersection_line_line(beam_a.centerline, beam_b.centerline))
        if plane_cut_vector.dot(offset_vector) >= 0:
            plane_cut_vector = -plane_cut_vector

        # Interface (depth) plane override from the LapPlaneSpec. When set, it defines
        # the cut orientation AND height (cut_plane_bias is ignored); else None ->
        # _create_polyhedron uses the default bias-positioned stacking plane.
        interface_plane = None
        if self._lap_plane_spec is not None and self.cut_plane_normal is not None:
            interface_plane = self._lap_plane_spec.to_plane(beam_a)

        # Get Beam Faces (Planes) in right order -- ALWAYS the original beam faces,
        # so face selection and the footprint stay robust regardless of any override.
        planes_a = self._sort_beam_planes(beam_a, plane_cut_vector)
        plane_a0, plane_a1, plane_a2, plane_a3 = planes_a

        planes_b = self._sort_beam_planes(beam_b, -plane_cut_vector)
        plane_b0, plane_b1, plane_b2, plane_b3 = planes_b

        # Lines as Frame Intersections (footprint always from the ORIGINAL beam faces)
        lines = []
        pt_a = intersection_plane_plane_plane(plane_a1, plane_b1, plane_a0)
        pt_b = intersection_plane_plane_plane(plane_a1, plane_b1, plane_b0)
        lines.append(Line(pt_a, pt_b))

        pt_a = intersection_plane_plane_plane(plane_a1, plane_b2, plane_a0)
        pt_b = intersection_plane_plane_plane(plane_a1, plane_b2, plane_b0)
        lines.append(Line(pt_a, pt_b))

        pt_a = intersection_plane_plane_plane(plane_a2, plane_b2, plane_a0)
        pt_b = intersection_plane_plane_plane(plane_a2, plane_b2, plane_b0)
        lines.append(Line(pt_a, pt_b))

        pt_a = intersection_plane_plane_plane(plane_a2, plane_b1, plane_a0)
        pt_b = intersection_plane_plane_plane(plane_a2, plane_b1, plane_b0)
        lines.append(Line(pt_a, pt_b))

        # Push the top caps through the beam so tilted cuts always cut clean.
        top_extension = 2.0 * max(beam_a.height, beam_a.width, beam_b.height, beam_b.width)

        # Create Polyhedrons. The LapPlaneSpec override (if set) replaces ONLY the
        # interface (depth) plane inside _create_polyhedron; the top faces
        # (plane_a0/plane_b0) and footprint stay original -> no trimming change.
        negative_polyhedron_beam_a = self._create_polyhedron(plane_b0, lines, cut_plane_bias, interface_plane, top_extension)
        negative_polyhedron_beam_b = self._create_polyhedron(plane_a0, lines, cut_plane_bias, interface_plane, top_extension)

        if self.flip_lap_side:
            return negative_polyhedron_beam_b, negative_polyhedron_beam_a
        return negative_polyhedron_beam_a, negative_polyhedron_beam_b
