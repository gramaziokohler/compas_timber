from __future__ import annotations

import math
from typing import TYPE_CHECKING

from compas.data import Data
from compas.geometry import Plane
from compas.geometry import Point
from compas.geometry import Rotation
from compas.geometry import Vector
from compas.geometry import angle_vectors
from compas.geometry import angle_vectors_projected
from compas.geometry import dot_vectors
from compas.geometry import intersection_line_line
from compas.tolerance import TOL

if TYPE_CHECKING:
    from compas_timber.connections.joint import Joint
    from compas_timber.elements.beam import Beam


def beam_ref_side_incidence(beam_a, beam_b, ignore_ends=True):
    """Returns a map of ref_side indices of beam_b and the angle of their normal with beam_a's centerline.

    This is used to find a cutting plane when joining the two beams.

    Parameters
    ----------
    beam_a : :class:`~compas_timber.elements.Beam`
        The beam that attaches with one of its ends to the side of beam_b.
    beam_b : :class:`~compas_timber.elements.Beam`
        The other beam.
    ignore_ends : bool, optional
        If True, only the first four ref_sides of `beam_b` are considered. Otherwise all ref_sides are considered.

    Returns
    -------
    dict(int, float)
        A map of ref_side indices of beam_b and their respective angle with beam_a's centerline.

    """
    # find the orientation of beam_a's centerline so that it's pointing outward of the joint
    # find the closest end
    p1x, _ = intersection_line_line(beam_a.centerline, beam_b.centerline)
    if p1x is None:
        raise ValueError("The two beams do not intersect with each other")

    end, _ = beam_a.endpoint_closest_to_point(Point(*p1x))

    if end == "start":
        centerline_vec = beam_a.centerline.vector
    else:
        centerline_vec = beam_a.centerline.vector * -1

    if ignore_ends:
        beam_b_ref_sides = beam_b.ref_sides[:4]
    else:
        beam_b_ref_sides = beam_b.ref_sides

    ref_side_angles = {}
    for ref_side_index, ref_side in enumerate(beam_b_ref_sides):
        ref_side_angles[ref_side_index] = angle_vectors(ref_side.normal, centerline_vec)

    return ref_side_angles


def beam_ref_side_incidence_cross(beam_a, beam_b, ignore_ends=True):
    """Returns a map of ref_side indices of beam_a and the angle of their normal with the cross product of beam_a's centerline and beam_b's centerline.

    This is used to find a cutting plane when joining the two beams.

    Parameters
    ----------
    beam_a : :class:`~compas_timber.elements.Beam`
        The beam that attaches with one of its ends to the side of beam_b.
    beam_b : :class:`~compas_timber.elements.Beam`
        The other beam.
    ignore_ends : bool, optional
        If True, only the first four ref_sides of `beam_a` are considered. Otherwise all ref_sides are considered.

    Returns
    -------
    dict(int, float)
        A map of ref_side indices of beam_a and their respective angle with the cross product of it's own centerline and beam_b's centerline.

    """
    # find the orientation of beam_a's centerline so that it's pointing outward of the joint
    # find the closest end
    p1x, _ = intersection_line_line(beam_a.centerline, beam_b.centerline)
    if p1x is None:
        raise ValueError("The two beams do not intersect with each other")

    end, _ = beam_a.endpoint_closest_to_point(Point(*p1x))

    if end == "start":
        centerline_vec = beam_a.centerline.vector * -1
    else:
        centerline_vec = beam_a.centerline.vector

    if ignore_ends:
        beam_a_ref_sides = beam_a.ref_sides[:4]
    else:
        beam_a_ref_sides = beam_a.ref_sides

    cross_vector = centerline_vec.cross(beam_b.centerline.direction)

    ref_side_angles = {}
    for ref_side_index, ref_side in enumerate(beam_a_ref_sides):
        ref_side_angles[ref_side_index] = angle_vectors(ref_side.normal, cross_vector)

    return ref_side_angles


def beam_ref_side_incidence_with_vector(beam_a, vector, ignore_ends=True):
    """
    Returns a map of ref_side indices of beam_b and the angle of their normal with a given vector.

    This is used to find a cutting plane when joining two beams where one beam is represented by the normal of one of it's reference sides.

    Parameters
    ----------
    beam_a : :class:`~compas_timber.elements.Beam`
        The beam for which ref_side angles will be calculated.
    vector : :class:`~compas.geometry.Vector`
        The vector to compare against the ref_sides' normals.
    ignore_ends : bool, optional
        If True, only the first four ref_sides of `beam_a` are considered. Otherwise all ref_sides are considered.

    Returns
    -------
    dict(int, float)
        A map of ref_side indices of beam_a and their respective angle with the given vector.

    """
    if ignore_ends:
        beam_a_ref_sides = beam_a.ref_sides[:4]
    else:
        beam_a_ref_sides = beam_a.ref_sides

    ref_side_angles = {}
    for ref_side_index, ref_side in enumerate(beam_a_ref_sides):
        ref_side_angles[ref_side_index] = angle_vectors(vector, ref_side.normal)

    return ref_side_angles


def are_beams_aligned_with_cross_vector(beam_a, beam_b, tol=TOL):
    """
    Checks if two beams are coplanar based on the cross product of their centerline directions.

    Parameters
    ----------
    beam_a : :class:`~compas_timber.elements.Beam`
        The first beam.
    beam_b : :class:`~compas_timber.elements.Beam`
        The second beam.
    tol : :class:`compas.tolerance.Tolerance`, optional
        The tolerance for the dot product comparison.

    Returns
    -------
    bool
        True if the beams are coplanar, False otherwise.
    """

    beam_angle = angle_vectors(beam_a.centerline.direction, beam_b.centerline.direction)
    if TOL.is_zero(beam_angle) or TOL.is_zero(beam_angle - math.pi):  # beams are parallel
        if TOL.is_zero(angle_vectors(beam_a.frame.normal, beam_b.frame.normal) % math.pi / 2):
            return True
        return False
    # Compute the cross product of the centerline directions of the two beams
    cross_vector = beam_a.centerline.direction.cross(beam_b.centerline.direction)
    cross_vector.unitize()

    for beam in [beam_a, beam_b]:
        # Check if the cross product is parallel to the normal of the beam's frame
        dot_with_beam_normal = abs(cross_vector.dot(beam.frame.normal))
        is_beam_normal_coplanar = tol.is_close(dot_with_beam_normal, 1.0) or tol.is_zero(dot_with_beam_normal)
        if not is_beam_normal_coplanar:
            return False
    return True


def point_centerline_towards_joint(beam_a, beam_b):
    """
    Returns the centerline vector of beam_a pointing towards the joint with beam_b.

    Parameters
    ----------
    beam_a : :class:`~compas_timber.elements.Beam`
        The beam that attaches with one of its ends to the side of beam_b.
    beam_b : :class:`~compas_timber.elements.Beam`
        The other beam.

    Returns
    -------
    :class:`~compas.geometry.Vector`
        The centerline vector of beam_a pointing towards the joint with beam_b.
    """

    # find the orientation of main_beams's centerline so that it's pointing towards the joint
    # find the closest end
    p1x, _ = intersection_line_line(beam_a.centerline, beam_b.centerline)
    if p1x is None:
        raise ValueError("The two beams do not intersect with each other")
    end, _ = beam_a.endpoint_closest_to_point(Point(*p1x))
    if end == "start":
        centerline_vec = beam_a.centerline.vector * -1
    else:
        centerline_vec = beam_a.centerline.vector
    return centerline_vec


def plane_from_ref_side_angle_offset(ref_side, angle, offset):
    """Builds a plane anchored on a beam's reference side, tilted around the side's x-axis and offset along its own (tilted) normal.

    The resulting plane's line of intersection with `ref_side` stays parallel to `ref_side`'s x-axis, i.e. to the centerline of the
    beam `ref_side` belongs to. This makes it suitable for cutting planes that must remain parallel to that centerline, e.g.
    :attr:`~compas_timber.connections.ButtJoint.butt_plane`. For an unconstrained plane, see :func:`plane_from_ref_side_angles_offset`.

    Parameters
    ----------
    ref_side : :class:`~compas.geometry.Frame`
        The beam's reference side used as the anchor for the plane.
    angle : float
        Rotation angle, in radians, around `ref_side`'s x-axis.
    offset : float
        Signed distance, measured along the rotated normal, from `ref_side`'s origin to the plane.

    Returns
    -------
    :class:`~compas.geometry.Plane`

    """
    plane = Plane(ref_side.point, ref_side.normal)
    rotation = Rotation.from_axis_and_angle(ref_side.xaxis, angle, point=ref_side.point)
    plane.transform(rotation)
    plane.point = plane.point + plane.normal * offset
    return plane


def decompose_plane_to_ref_side(ref_side, plane, plane_name="plane", reference_name="the reference beam"):
    """Computes the `angle` and `offset` that reproduce `plane` via :func:`plane_from_ref_side_angle_offset`.

    Parameters
    ----------
    ref_side : :class:`~compas.geometry.Frame`
        The beam's reference side used as the anchor for the plane.
    plane : :class:`~compas.geometry.Plane`
        The plane to decompose. Its normal must be perpendicular to `ref_side`'s x-axis, i.e. parallel to the centerline of
        the beam `ref_side` belongs to.
    plane_name : str, optional
        Used to compose a helpful error message.
    reference_name : str, optional
        Used to compose a helpful error message.

    Returns
    -------
    tuple(float, float)
        The `angle` and `offset`.

    Raises
    ------
    ValueError
        If `plane`'s normal has a component along `ref_side`'s x-axis, i.e. it is not parallel to `reference_name`'s centerline.

    """
    xaxis = ref_side.xaxis.unitized()
    normal = plane.normal.unitized()
    if not TOL.is_zero(dot_vectors(normal, xaxis)):
        raise ValueError("{} must be parallel to {}'s centerline: its normal may not have a component along the reference side's x-axis.".format(plane_name, reference_name))
    angle = angle_vectors_projected(ref_side.normal, plane.normal, xaxis)
    offset = dot_vectors(Vector.from_start_end(ref_side.point, plane.point), plane.normal)
    return angle, offset


def plane_from_ref_side_angles_offset(ref_side, angle_x, angle_y, offset):
    """Builds a plane anchored on a beam's reference side, tilted around the side's x- and y-axes and offset along its own (tilted) normal.

    Unlike :func:`plane_from_ref_side_angle_offset`, the resulting plane is not constrained to remain parallel to any axis of
    `ref_side`, so it can represent any plane, e.g. :attr:`~compas_timber.connections.LMiterJoint.miter_plane`.

    Parameters
    ----------
    ref_side : :class:`~compas.geometry.Frame`
        The beam's reference side used as the anchor for the plane.
    angle_x : float
        Rotation angle, in radians, around `ref_side`'s x-axis.
    angle_y : float
        Rotation angle, in radians, around `ref_side`'s (original) y-axis, applied after `angle_x`.
    offset : float
        Signed distance, measured along the resulting normal, from `ref_side`'s origin to the plane.

    Returns
    -------
    :class:`~compas.geometry.Plane`

    """
    plane = Plane(ref_side.point, ref_side.normal)
    rotation_x = Rotation.from_axis_and_angle(ref_side.xaxis, angle_x, point=ref_side.point)
    plane.transform(rotation_x)
    rotation_y = Rotation.from_axis_and_angle(ref_side.yaxis, angle_y, point=ref_side.point)
    plane.transform(rotation_y)
    plane.point = plane.point + plane.normal * offset
    return plane


def decompose_plane_to_ref_side_angles(ref_side, plane):
    """Computes the `angle_x`, `angle_y` and `offset` that reproduce `plane` via :func:`plane_from_ref_side_angles_offset`.

    Parameters
    ----------
    ref_side : :class:`~compas.geometry.Frame`
        The beam's reference side used as the anchor for the plane.
    plane : :class:`~compas.geometry.Plane`
        The plane to decompose. Any orientation is supported.

    Returns
    -------
    tuple(float, float, float)
        The `angle_x`, `angle_y` and `offset`.

    """
    normal = plane.normal.unitized()
    tx = dot_vectors(normal, ref_side.xaxis)
    ty = dot_vectors(normal, ref_side.yaxis)
    tz = dot_vectors(normal, ref_side.normal)
    angle_x = -math.asin(max(-1.0, min(1.0, ty)))
    angle_y = math.atan2(tx, tz)
    offset = dot_vectors(Vector.from_start_end(ref_side.point, plane.point), plane.normal)
    return angle_x, angle_y, offset


def angle_and_dot_product_beam_a_and_beam_b(beam_a: Beam, beam_b: Beam, joint: Joint) -> tuple[float, float]:
    """
    Computes the angle and dot product between the `beam_a` and the `beam_b` relative to their joint.
    The angle and dot products are computed with the direction of the `beam_a` going towards the joint.

    Parameters
    ----------
    beam_a : :class:`~compas_timber.elements.Beam`
        The main beam of the joint.
    beam_b : :class:`~compas_timber.elements.Beam`
        The cross beam of the joint.
    joint : :class:`~compas_timber.connections.joint.Joint`
        The joint connecting the main beam and the cross beam.

    Returns
    -------
    tuple[float, float]
        A tuple containing the angle (in radians) and the dot product between the main beam and the cross beam relative to their joint.

    """
    main_beam_direction = joint.get_beam_direction_towards_joint(beam_a)
    angle = angle_vectors(main_beam_direction, beam_b.centerline.direction)
    dot = dot_vectors(main_beam_direction, beam_b.centerline.direction)
    return angle, dot


class CutPlaneSpec(Data):
    """A cutting plane stored relative to a beam's reference side.

    Encodes a world-coordinate plane as a ``(ref_side_index, angle, offset)`` triple, matching the
    parameterisation of :func:`plane_from_ref_side_angle_offset`.  Use the named constructors
    :meth:`from_butt_plane` and :meth:`from_back_plane` to build instances from world-coordinate planes,
    and :meth:`to_plane` to reconstruct the plane at query time.

    """

    @property
    def __data__(self):
        return {"ref_side_index": self.ref_side_index, "angle": self.angle, "offset": self.offset}

    def __init__(self, ref_side_index: int, angle: float = 0.0, offset: float = 0.0):
        super().__init__()
        self.ref_side_index = ref_side_index
        self.angle = angle
        self.offset = offset

    def to_plane(self, beam: Beam) -> Plane:
        """Reconstruct the world-coordinate plane relative to `beam`."""
        ref_side = beam.ref_sides[self.ref_side_index]
        return plane_from_ref_side_angle_offset(ref_side, self.angle, self.offset)

    @classmethod
    def from_butt_plane(cls, main_beam: Beam, cross_beam: Beam, plane: Plane) -> CutPlaneSpec:
        """Encode `plane` relative to the cross beam's face that is closest to the main beam.

        Use this when the plane is intended to cut the **main beam** (i.e. as
        :attr:`~compas_timber.connections.ButtJoint.butt_plane`).

        Parameters
        ----------
        main_beam
            Main beam of the joint.
        cross_beam
            Cross beam of the joint.
        plane
            Cutting plane in world coordinates.  Its normal must be perpendicular to the cross beam's
            centerline axis.

        """
        if not TOL.is_zero(dot_vectors(cross_beam.frame.xaxis, plane.normal)):
            raise ValueError("plane normal must be perpendicular to cross_beam centerline axis")
        ref_side_dict = beam_ref_side_incidence(main_beam, cross_beam, ignore_ends=True)
        ref_side_index = min(ref_side_dict, key=lambda k: ref_side_dict[k])
        ref_side = cross_beam.ref_sides[ref_side_index]
        angle, offset = decompose_plane_to_ref_side(ref_side, plane, plane_name="butt_plane", reference_name="cross_beam")
        return cls(ref_side_index, angle, offset)

    @classmethod
    def from_back_plane(cls, main_beam: Beam, cross_beam: Beam, plane: Plane) -> CutPlaneSpec:
        """Encode `plane` relative to the back face of the main beam (the face opposite the cross beam).

        Use this when the plane is intended to cut the **cross beam** from behind the main beam (i.e. as
        :attr:`~compas_timber.connections.LButtJoint.back_plane`).

        Parameters
        ----------
        main_beam
            Main beam of the joint.
        cross_beam
            Cross beam of the joint.
        plane
            Cutting plane in world coordinates.  Its normal must be perpendicular to the main beam's
            centerline axis.

        """
        ref_side_dict = beam_ref_side_incidence(cross_beam, main_beam, ignore_ends=True)
        facing_side_index = min(ref_side_dict, key=lambda k: ref_side_dict[k])
        back_side_index = (facing_side_index + 2) % 4  # opposite face of main_beam
        ref_side = main_beam.ref_sides[back_side_index]
        angle, offset = decompose_plane_to_ref_side(ref_side, plane, plane_name="back_plane", reference_name="main_beam")
        return cls(back_side_index, angle, offset)
