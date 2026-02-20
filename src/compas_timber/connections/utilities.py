from __future__ import annotations

import math
from typing import TYPE_CHECKING
from typing import Optional

from compas.geometry import Point
from compas.geometry import angle_vectors
from compas.geometry import dot_vectors
from compas.geometry import intersection_line_line
from compas.tolerance import TOL

from compas_timber.connections.solver import JointTopology

if TYPE_CHECKING:
    from compas_timber.connections.analyzers import Cluster
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


def extend_main_beam_to_cross_beam(main_beam: Beam, cross_beam: Beam, mill_depth: Optional[float] = None, extension_tolerance: float = 0.01):
    """
    Extend the `main_beam` to the `cross_beam`.
    If a `mill_depth` is provided it ensures that the `main_beam` is extended enough to ensure enough material for the joint.

    The `main_beam` is extended in place.


    Parameter
    ---------
    main_beam : :class:`~compas_timber.elements.Beam`
        The main beam to be extended.
    cross_beam : :class:`~compas_timber.elements.Beam`
        The cross beam to which the main beam will be extended.
    mill_depth : float, optional
        The depth of the mill cut for the joint. If provided, the main beam will be extended enough to ensure enough material for the joint.
    extension_tolerance : float, optional
        A small tolerance added to the extension length. Default is 0.01 units.


    Retruns
    -------
    :class:`~compas_timber.elements.Beam`
        The main beam extended.

    """
    ref_side_dict = beam_ref_side_incidence(main_beam, cross_beam, ignore_ends=True)
    cross_beam_ref_side_index = min(ref_side_dict, key=ref_side_dict.get)
    cutting_plane = cross_beam.ref_sides[cross_beam_ref_side_index]
    if mill_depth:
        cutting_plane.translate(-cutting_plane.normal * mill_depth)
    start_main, end_main = main_beam.extension_to_plane(cutting_plane)
    main_beam.add_blank_extension(start_main + extension_tolerance, end_main + extension_tolerance)
    return main_beam


def angle_and_dot_product_main_beam_and_cross_beam(main_beam: Beam, cross_beam: Beam, joint: Joint) -> tuple[float, float]:
    """
    Computes the angle and dot product between the `main_beam` and the `cross_beam` relative to their joint.
    The angle and dot products are computed with the direction of the `main_beam` goinf towards the joint.

    Parameters
    ----------
    main_beam : :class:`~compas_timber.elements.Beam`
        The main beam of the joint.
    cross_beam : :class:`~compas_timber.elements.Beam`
        The cross beam of the joint.
    joint : :class:`~compas_timber.connections.joint.Joint`
        The joint connecting the main beam and the cross beam.

    Returns
    -------
    tuple[float, float]
        A tuple containing the angle (in radians) and the dot product between the main beam and the cross beam relative to their joint.

    """
    main_beam_direction = joint.get_beam_direction_towards_joint(main_beam)
    angle = angle_vectors(main_beam_direction, cross_beam.centerline.direction)
    dot = dot_vectors(main_beam_direction, cross_beam.centerline.direction)
    return angle, dot


def parse_cross_beam_and_main_beams_from_cluster(cluster: Cluster) -> tuple[list[Beam], list[Beam]]:
    """
    Parses cross beams and main beams from a cluster of joints.

    Parameters
    ----------
    cluster : :class:`~compas_timber.connections.analyzers.Cluster`
        The cluster of joints to parse.

    Returns
    -------
    list[:class:`~compas_timber.elements.beam.Beam`], list[:class:`~compas_timber.elements.beam.Beam`]
        Two lists containing the cross beams and main beams respectively.
    """
    cross_beams = []
    main_beams = []
    for candidate in cluster.joints:
        if candidate.topology == JointTopology.TOPO_L:
            main_beams.extend(candidate.elements)
        elif candidate.topology == JointTopology.TOPO_T:
            main_beams.append(candidate.elements[0])
            cross_beams.append(candidate.elements[1])
        elif candidate.topology == JointTopology.TOPO_X:
            cross_beams.extend(candidate.elements)
    cross_beams = list(set(cross_beams))
    main_beams = list(set(main_beams))
    return cross_beams, main_beams
