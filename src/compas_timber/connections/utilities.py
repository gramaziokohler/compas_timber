from compas.geometry import Point
from compas.geometry import angle_vectors
from compas.geometry import intersection_line_line
from compas.tolerance import TOL


def beam_ref_side_incidence(beam_a, beam_b, ignore_ends=True):
    """Returns a map of ref_side indices of beam_b and the angle of their normal with beam_a's centerline.

    This is used to find a cutting plane when joining the two beams.

    Compared to beam_side_incidence, this function considers the ref_sides and not faces and forms part of the transition to the new implementation system

    Parameters
    ----------
    beam_a : :class:`~compas_timber.parts.Beam`
        The beam that attaches with one of its ends to the side of beam_b.
    beam_b : :class:`~compas_timber.parts.Beam`
        The other beam.
    ignore_ends : bool, optional
        If True, only the first four ref_sides of `beam_b` are considered. Otherwise all ref_sides are considered.

    Examples
    --------
    >>> ref_side_angles = Joint.beam_side_incidence(beam_a, beam_b)
    >>> closest_ref_side_index = min(ref_side_angles, key=ref_side_angles.get)
    >>> cutting_plane = beam_b.ref_sides[closest_ref_side_index]

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

    Compared to beam_side_incidence, this function considers the ref_sides and not faces and forms part of the transition to the new implementation system

    Parameters
    ----------
    beam_a : :class:`~compas_timber.parts.Beam`
        The beam that attaches with one of its ends to the side of beam_b.
    beam_b : :class:`~compas_timber.parts.Beam`
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
    beam_a : :class:`~compas_timber.parts.Beam`
        The beam for which ref_side angles will be calculated.
    vector : :class:`~compas.geometry.Vector`
        The vector to compare against the ref_sides' normals.
    ignore_ends : bool, optional
        If True, only the first four ref_sides of `beam_a` are considered. Otherwise all ref_sides are considered.

    Examples
    --------
    >>> vector = Vector(1, 0, 0)
    >>> ref_side_angles = Joint.ref_side_incidence_with_vector(beam_a, vector)
    >>> closest_ref_side_index = min(ref_side_angles, key=ref_side_angles.get)
    >>> cutting_plane = beam_a.ref_sides[closest_ref_side_index]

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


def are_beams_coplanar(beam_a, beam_b, tol=TOL):
    """
    Checks if two beams are coplanar based on the cross product of their centerline directions.

    Parameters
    ----------
    beam_a : :class:`~compas_timber.parts.Beam`
        The first beam.
    beam_b : :class:`~compas_timber.parts.Beam`
        The second beam.
    tol : :class:`compas.tolerance.Tolerance`, optional
        The tolerance for the dot product comparison.

    Returns
    -------
    bool
        True if the beams are coplanar, False otherwise.
    """
    # Compute the cross product of the centerline directions of the two beams
    cross_vector = beam_a.centerline.direction.cross(beam_b.centerline.direction)
    cross_vector.unitize()

    # Check dot products of the cross product with the normals of both beams' frames
    dot_with_beam_b_normal = abs(cross_vector.dot(beam_b.frame.normal))
    dot_with_beam_a_normal = abs(cross_vector.dot(beam_a.frame.normal))

    # Check if both dot products are close to 0 or 1 (indicating coplanarity)
    is_beam_a_normal_coplanar = tol.is_close(dot_with_beam_a_normal, 1.0) or tol.is_zero(dot_with_beam_a_normal)
    is_beam_b_normal_coplanar = tol.is_close(dot_with_beam_b_normal, 1.0) or tol.is_zero(dot_with_beam_b_normal)

    # Return True if both beams are coplanar
    return is_beam_a_normal_coplanar and is_beam_b_normal_coplanar


def check_beam_alignment(beam_a, beam_b, tol=TOL):
    """
    Checks the alignment of two beams by comparing their centerline directions and the normal of beam_b's frame.

    This function calculates the cross product of the two beams' centerline directions and checks the alignment by
    computing the dot product with the normal of beam_b's frame. The result can be used for further decisions based
    on the alignment of the beams.

    Parameters
    ----------
    beam_a : :class:`~compas_timber.parts.Beam`
        The first beam, used to check the alignment with beam_b.
    beam_b : :class:`~compas_timber.parts.Beam`
        The second beam, whose alignment is checked relative to beam_a.
    tol : :class:`compas.tolerance.Tolerance`, optional
        A tolerance value for determining near-perpendicular or near-parallel alignment.

    Returns
    -------
    bool
        True if the beams are nearly perpendicular, False if they are not.
    """
    # Compute the cross product of the centerline directions of the two beams
    cross_vector = beam_a.centerline.direction.cross(beam_b.centerline.direction)
    cross_vector.unitize()

    # Calculate the dot product of the cross vector with the normal of beam_b's frame
    dot_with_beam_b_normal = abs(cross_vector.dot(beam_b.frame.normal))

    # Return True if the beams are nearly perpendicular (dot product close to 0)
    return tol.is_zero(dot_with_beam_b_normal)


def point_centerline_towards_joint(beam_a, beam_b):
    """
    Returns the centerline vector of beam_a pointing towards the joint with beam_b.

    Parameters
    ----------
    beam_a : :class:`~compas_timber.parts.Beam`
        The beam that attaches with one of its ends to the side of beam_b.
    beam_b : :class:`~compas_timber.parts.Beam`
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
