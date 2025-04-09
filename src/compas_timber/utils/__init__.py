from itertools import product
from math import fabs

from compas.geometry import Plane
from compas.geometry import Point
from compas.geometry import Vector
from compas.geometry import Polyline
from compas.geometry import angle_vectors_signed
from compas.geometry import add_vectors
from compas.geometry import cross_vectors
from compas.geometry import distance_point_point
from compas.geometry import dot_vectors
from compas.geometry import length_vector
from compas.geometry import normalize_vector
from compas.geometry import scale_vector
from compas.geometry import subtract_vectors
from compas.geometry import Frame
from compas.geometry import Transformation
from compas.geometry import Projection
from compas.geometry import intersection_line_plane
from compas.geometry import closest_point_on_segment
from compas.geometry import intersection_line_line


def intersection_line_line_param(line1, line2, max_distance=1e-6, limit_to_segments=True, tol=1e-6):
    """Find, if exists, the intersection point of `line1` and `line2` and returns parametric information about it.

    For each of the lines, the point of intersection and a `t` parameter are returned.

    The `t` parameter is the normalized parametric value (0.0 -> 1.0) of the location of the intersection point
    in relation to the line's starting point.
    0.0 indicates intersaction near the starting point, 1.0 indicates intersection near the end.

    If no intersection is detected within the max_distance, or the intersection falls outside either of the line segments,
    [None, None], [None, None] is returned.

    Parameters
    ----------
    line1 : :class:`~compas.geometry.Line`
        First line.
    line2 : :class:`~compas.geometry.Line`
        Second line.
    max_distance : float
        Maximum distance between the lines to still consider as intersection.
    limit_to_segments : bool, defualt is True
        If True, the lines are considered intersection only if the intersection point falls whithin the given line segments for both lines.
    tol : float, default is 1e-6
        The tolerance used for floating point operations.

    Returns
    -------
    tuple(:class:`~compas.geometry.Point`, float), tuple(:class:`~compas.geometry.Point`, float)

    """
    a, b = line1
    c, d = line2

    ab = subtract_vectors(b, a)
    cd = subtract_vectors(d, c)

    n = cross_vectors(ab, cd)

    # check if lines are parallel
    if length_vector(n) < tol:  # if any([abs(x)<tol for x in n]):
        return [None, None], [None, None]

    n1 = normalize_vector(cross_vectors(ab, n))
    n2 = normalize_vector(cross_vectors(cd, n))

    pln1 = Plane(a, n1)
    pln2 = Plane(c, n2)

    # get intersection points (should never be None, only if parallel, which was errorcatched before)
    x1, t1 = intersection_line_plane_param(line1, pln2, tol)
    x2, t2 = intersection_line_plane_param(line2, pln1, tol)

    # double-check for parallels, should not happen:
    if t1 is None or t2 is None:
        print("intersection_line_plane detected parallel lines")
        return [None, None], [None, None]

    # is intersection exact / within some max_distance?
    d = distance_point_point(x1, x2)
    if d > max_distance:
        return [None, None], [None, None]

    # is intersection within the line segment? if not, override results with None
    if limit_to_segments:
        if t1 < 0.0 - tol or t1 > 1.0 + tol:
            x1 = None
            t1 = None
        if t2 < 0.0 - tol or t2 > 1.0 + tol:
            x2 = None
            t2 = None
    return [x1, t1], [x2, t2]


def intersection_line_plane_param(line, plane, tol=1e-6):
    """Computes the intersection point of a line and a plane.

    A tuple containing the intersection point and a `t` value are returned.

    The `t` parameter is the normalized parametric value (0.0 -> 1.0) of the location of the intersection point
    in relation to the line's starting point.
    0.0 indicates intersaction near the starting point, 1.0 indicates intersection near the end.

    If no intersection is found, [None, None] is returned.

    Parameters
    ----------
    line : :class:`~compas.geometry.Line`
        Two points defining the line.
    plane : :class:`~compas.geometry.Plane`
        The base point and normal defining the plane.
    tol : float, optional. Default is 1e-6.
        A tolerance for membership verification.

    Returns
    -------
    tuple(:class:`~compas.geometry.Point`, float)

    """
    a, b = line
    o, n = plane

    ab = subtract_vectors(b, a)
    dotv = dot_vectors(n, ab)

    if fabs(dotv) <= tol:
        # if the dot product (cosine of the angle between segment and plane)
        # is close to zero the line and the normal are almost perpendicular
        # hence there is no intersection
        return None, None

    # based on the ratio = -dot_vectors(n, ab) / dot_vectors(n, oa)
    # there are three scenarios
    # 1) 0.0 < ratio < 1.0: the intersection is between a and b
    # 2) ratio < 0.0: the intersection is on the other side of a
    # 3) ratio > 1.0: the intersection is on the other side of b
    oa = subtract_vectors(a, o)
    t = -dot_vectors(n, oa) / dotv
    ab = scale_vector(ab, t)
    return Point(*add_vectors(a, ab)), t


def intersection_line_beam_param(line, beam, ignore_ends=False):
    """Get the intersection of a line with a beam in the XY plane and the corresponding ref_face_indices.

    Parameters
    ----------
    line : :class:`~compas.geometry.Line`
        The line to intersect with the beam.
    beam : :class:`~compas_timber.geometry.Beam`
        The beam to intersect with the line.
    ignore_ends : bool, optional
        If True, the intersection with the beam ends is ignored. Default is False.

    Returns
    -------
    list of :class:`~compas.geometry.Point`
        list of intersection points.
    list of int
        list of indices of the reference faces of the beam that the intersection points lie on.

    """

    sides = beam.ref_sides[:4] if ignore_ends else beam.ref_sides
    pts = []
    ref_side_indices = []
    for i, face in enumerate(sides):
        intersection = intersection_line_plane(line, Plane.from_frame(face))
        if intersection:
            int_pt = Point(*intersection)
            intersection_uv = int_pt.transformed(Transformation.from_frame_to_frame(face, Frame.worldXY()))
            if intersection_uv[0] >= 0 and intersection_uv[0] < beam.side_as_surface(i).xsize and intersection_uv[1] > 0 and intersection_uv[1] < beam.side_as_surface(i).ysize:
                pts.append(intersection)
                ref_side_indices.append(i)
    return [Point(*coords) for coords in pts], ref_side_indices


def _split_into_consecutive_sequences(source, wrap_on):
    # type: (list[int], int) -> list[list[int]]
    if not source:
        return []

    sequences = []
    current_sequence = [source[0]]

    for i in range(1, len(source)):
        curr_val = source[i]
        prev_incremented = (source[i - 1] + 1) % wrap_on
        if curr_val == prev_incremented:
            current_sequence.append(curr_val)
        else:
            sequences.append(current_sequence)
            current_sequence = [curr_val]

    sequences.append(current_sequence)  # add the last sequence
    return sequences


def classify_polyline_segments(polyline, normal, direction="cw"):
    """Classify polyline segments as external or part of a cutout based on turning angles.

    Parameters
    ----------
    polyline : :class:`compas.geometry.Polyline`
        The polyline to classify.
    normal : :class:`compas.geometry.Vector`
        The normal vector of the wall. Used as reference palne for turning angles calculation.
    direction : str, optional
        The winding direction of the outline around the given normal vector. One of: ("cw", "ccw"). Default is "cw".

    Returns
    -------
    tuple(list[int], list[list[int]])
        A tuple containing two lists:
        - the first list contains the indices of outline vertices
        - the second list contains the indices of internal vertices grouped in sequences
    """
    if direction not in ("cw", "ccw"):
        raise ValueError("Direction must be either 'cw' or 'ccw'.")

    # iterate on polyline without p[0] == p[-1]
    if polyline[0] == polyline[-1]:
        polyline = polyline[:-1]

    outline_vertices = []
    internal_vertices = []

    num_points = len(polyline)

    for i in range(num_points):
        p_prev = polyline[i]
        p_curr = polyline[(i + 1) % num_points]
        p_next = polyline[(i + 2) % num_points]

        v1 = Vector.from_start_end(p_prev, p_curr)
        v2 = Vector.from_start_end(p_curr, p_next)

        angle = angle_vectors_signed(v1, v2, normal, deg=True)

        if direction == "ccw":
            angle = -angle

        if angle < 0:
            outline_vertices.append((i + 1) % num_points)
        else:
            internal_vertices.append((i + 1) % num_points)

    # vertices that lie on the outline but are at openings count as internal
    # they are removed from the outline list and added to the internal list
    internal_groups = _split_into_consecutive_sequences(internal_vertices, wrap_on=num_points)
    polyline_indices = list(range(num_points))
    for group in internal_groups:
        prev_value = polyline_indices[group[0] - 1]
        next_value = polyline_indices[(group[1] + 1) % num_points]
        group.insert(0, prev_value)
        group.append(next_value)
        outline_vertices.remove(prev_value)
        outline_vertices.remove(next_value)

    return outline_vertices, internal_groups


def distance_segment_segment(segment_a, segment_b):
    """Computes the distance between two segments.

    Parameters
    ----------
    segment_a : tuple(tuple(float, float, float), tuple(float, float, float))
        The first segment, defined by two points.
    segment_b : tuple(tuple(float, float, float), tuple(float, float, float))
        The second segment, defined by two points.

    Returns
    -------
    float
        The distance between the two segments.

    """
    pta, ptb = intersection_line_line(segment_a, segment_b)
    if not pta:  # segments are parallel
        dists = []
        for pair in product(segment_a, segment_b):
            # gets shortest distance between all 4 possible pairs of endpoints. only for L/I_Topo.
            # T_Topology cannot have paralell segments
            dists.append(distance_point_point(*pair))
        return min(dists)
    pt_seg_a = closest_point_on_segment(pta, segment_a)
    pt_seg_b = closest_point_on_segment(ptb, segment_b)
    return distance_point_point(pt_seg_a, pt_seg_b)


def angle_vectors_projected(vector_a, vector_b, normal):
    """Computes the angle between two vectors projected onto a plane defined by a normal vector.

    Parameters
    ----------
    vector_a : :class:`compas.geometry.Vector`
        The first vector.
    vector_b : :class:`compas.geometry.Vector`
        The second vector.
    normal : :class:`compas.geometry.Vector` or :class:`compas.geometry.Plane` or :class:`compas.geometry.Frame`
        The normal vector of the plane to project the vectors onto.

    Returns
    -------
    float
        The angle between the two projected vectors
    """
    if isinstance(normal, (Plane, Frame)):
        normal = normal.normal

    projection = Projection.from_plane(Plane(Point(0, 0, 0), normal))
    proj_vect_a = vector_a.transformed(projection)
    proj_vect_b = vector_b.transformed(projection)
    return angle_vectors_signed(proj_vect_a, proj_vect_b, normal, deg=True)


def is_polyline_clockwise(polyline, normal_vector):
    """Check if a polyline is clockwise. If the polyline is open, it is closed before the check.

    Parameters
    ----------
    polyline : :class:`compas.geometry.Polyline`
        The polyline to check.
    normal_vector : :class:`compas.geometry.Vector`
        The normal vector to use for the angle calculation.

    Returns
    -------
    bool
        True if the polyline is clockwise, False otherwise.

    """
    # make sure the polyline is closed
    if not polyline[0] == polyline[-1]:
        polyline = polyline[:]  # create a copy
        polyline.append(polyline[0])

    angle_sum = 0
    for i in range(len(polyline) - 1):
        u = Vector.from_start_end(polyline[i - 1], polyline[i])
        v = Vector.from_start_end(polyline[i], polyline[i + 1])
        angle = angle_vectors_signed(u, v, normal_vector)
        angle_sum += angle
    return angle_sum < 0


def correct_polyline_direction(polyline, normal_vector, clockwise=False):
    """Corrects the direction of a polyline to be counter-clockwise around a given vector.

    Parameters
    ----------
    polyline : :class:`compas.geometry.Polyline`
        The polyline to correct.

    Returns
    -------
    :class:`compas.geometry.Polyline`
        The corrected polyline.

    """
    cw = is_polyline_clockwise(polyline, normal_vector)
    if cw ^ clockwise:
        return Polyline(polyline[::-1])
    return polyline


__all__ = [
    "intersection_line_line_param",
    "intersection_line_plane_param",
    "intersection_line_beam_param",
    "classify_polyline_segments",
    "distance_segment_segment",
    "angle_vectors_projected",
    "is_polyline_clockwise",
    "correct_polyline_direction",
]
