from math import fabs
from typing import Optional

from compas.datastructures import Mesh
from compas.geometry import Plane
from compas.geometry import Point
from compas.geometry import Vector
from compas.geometry import Polyline
from compas.geometry import Polygon
from compas.geometry import Line
from compas.geometry import angle_vectors
from compas.geometry import intersection_line_line
from compas.geometry import is_point_in_polygon_xy
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
from compas.geometry import intersection_line_plane
from compas.geometry import closest_point_on_segment
from compas.geometry import intersection_segment_segment

from compas.tolerance import TOL

try:
    from enum import StrEnum  # type: ignore
except ImportError:
    # not there yet in python3.9
    from enum import Enum

    class StrEnum(str, Enum):
        pass


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
    pta, ptb = intersection_segment_segment(segment_a, segment_b)
    if pta and ptb:
        return distance_point_point(pta, ptb)

    dists = []
    for pt in [segment_a.start, segment_a.end]:
        dists.append(distance_point_point(pt, closest_point_on_segment(pt, segment_b)))
    for pt in [segment_b.start, segment_b.end]:
        dists.append(distance_point_point(pt, closest_point_on_segment(pt, segment_a)))
    return min(dists)


def distance_segment_segment_points(segment_a, segment_b):
    """Computes the distance between two segments.

    Parameters
    ----------
    segment_a : tuple(tuple(float, float, float), tuple(float, float, float))
        The first segment, defined by two points.
    segment_b : tuple(tuple(float, float, float), tuple(float, float, float))
        The second segment, defined by two points.

    Returns
    -------

    tuple(float, :class:`~compas.geometry.Point`, :class:`~compas.geometry.Point`)
        The distance between the two segments, and the closest points on each segment.

    """
    pta, ptb = intersection_segment_segment(segment_a, segment_b)
    if pta and ptb:
        return distance_point_point(pta, ptb), pta, ptb

    dists = []
    closest_pts = []
    for pt in [segment_a.start, segment_a.end]:
        cp = closest_point_on_segment(pt, segment_b)
        dists.append(distance_point_point(pt, cp))
        closest_pts.append((pt, cp))
    for pt in [segment_b.start, segment_b.end]:
        cp = closest_point_on_segment(pt, segment_a)
        dists.append(distance_point_point(pt, cp))
        closest_pts.append((cp, pt))
    min_index = dists.index(min(dists))
    return dists[min_index], closest_pts[min_index][0], closest_pts[min_index][1]


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


def get_polyline_segment_perpendicular_vector(polyline, segment_index):
    """Get the vector perpendicular to a polyline segment. This vector points outside of the polyline.
    The polyline must be closed.

    Parameters
    ----------
    polyline : :class:`compas.geometry.Polyline`
        The polyline to check. Must be closed.
    segment_index : int
        The index of the segment in the polyline.

    Returns
    -------
    :class:`compas.geometry.Vector`
        The vector perpendicular to the segment, pointing outside of the polyline.

    """
    plane = Plane.from_points(polyline.points)
    pt = polyline.lines[segment_index].point_at(0.5)
    perp_vector = Vector(*cross_vectors(polyline.lines[segment_index].direction, plane.normal))
    point = pt + (perp_vector * 0.1)
    if is_point_in_polyline(point, polyline):
        return Vector.from_start_end(point, pt).unitized()
    return Vector.from_start_end(pt, point).unitized()


def is_point_in_polyline(point, polyline, in_plane=True, tol=TOL):
    """Check if a point is inside a polyline. Polyline must be closed. The polyline must be closed, planar, and not self-intersecting.

    Parameters
    ----------
    point : :class:`compas.geometry.Point`
        The point to check.
    polyline : :class:`compas.geometry.Polyline`
        The polyline to check against.
    in_plane : bool, optional
        If True, the point must be in the same plane as the polyline. Default is True.
    tol : float, optional
        The tolerance used for calculation. Default is TOL.

    Returns
    -------
    bool
        True if the point is inside the polyline, False otherwise.
    """
    pts = list(polyline.points)
    a = pts[0]
    b = None
    c = None
    # find b: the first point that is not coincident with a, so that a-b defines a valid direction
    for pt in pts[1:]:
        if not TOL.is_allclose(pt, a):
            b = pt
            break
    if b is None:
        # all points are coincident / cannot define a plane
        return False
    # find c: the first point that is not collinear with a and b,
    # so that a, b, c define a valid plane (non-zero cross product)
    for pt in pts:
        cross = cross_vectors(subtract_vectors(b, a), subtract_vectors(pt, a))
        if not TOL.is_allclose(cross, [0, 0, 0]):
            c = pt
            break
    if c is None:
        # all points are collinear / cannot define a plane
        return False
    frame = Frame.from_points(a, b, c)
    xform = Transformation.from_frame_to_frame(frame, Frame.worldXY())
    pgon = Polygon([pt.transformed(xform) for pt in polyline.points[:-1]])
    pt = point.transformed(xform)
    if in_plane and not tol.is_zero(pt[2]):
        return False
    return is_point_in_polygon_xy(pt, pgon)


def do_segments_overlap(segment_a, segment_b):
    """Checks if two segments overlap.

    Parameters
    ----------
    seg_a : :class:`~compas.geometry.Segment`
        The first segment.
    seg_b : :class:`~compas.geometry.Segment`
        The second segment.

    Returns
    -------
    bool
        True if the segments overlap, False otherwise.
    """
    a_end_dot = dot_vectors(segment_a.direction, Vector.from_start_end(segment_a.start, segment_a.end))
    for pt in [segment_b.start, segment_b.end, segment_b.point_at(0.5)]:
        b_dot = dot_vectors(segment_a.direction, Vector.from_start_end(segment_a.start, pt))
        if b_dot > 0 and b_dot < a_end_dot:
            return True

    b_end_dot = dot_vectors(segment_b.direction, Vector.from_start_end(segment_b.start, segment_b.end))
    for pt in [segment_a.start, segment_a.end, segment_a.point_at(0.5)]:
        a_dot = dot_vectors(segment_b.direction, Vector.from_start_end(segment_b.start, pt))
        if a_dot > 0 and a_dot < b_end_dot:
            return True

    return False


def get_segment_overlap(segment_a, segment_b, unitize=False):
    """gets the length parameters of the overlap between two segments.

    Parameters
    ----------
    segment_a : :class:`~compas.geometry.Segment`
        The segment upon which the overlap is tested.
    segment_b : :class:`~compas.geometry.Segment`
        The segment that is overlapped on segment_a.
    unitize : bool, optional
        If True, the returned parameters are normalized to the length of segment_a. Default is False

    Returns
    -------
    tuple(float, float) or None
        A tuple containing the start and end parameters of the overlap on segment_a.
        If there is no overlap, None is returned.
    """
    dots = []
    for pt in segment_b:
        dots.append(dot_vectors(segment_a.direction, Vector.from_start_end(segment_a.start, pt)))
    length = segment_a.length
    dots.sort()
    if dots[0] >= length or dots[1] <= 0.0:
        return None

    if dots[0] < 0.0:
        dots[0] = 0.0
    if dots[1] > length:
        dots[1] = length
    if unitize:
        dots[0] /= length
        dots[1] /= length

    return (dots[0], dots[1])


def move_polyline_segment_to_plane(polyline, segment_index, plane):
    """Move a segment of a polyline to lay on a given plane. this is accomplished by extending the adjacent segments to intersect with the plane.
    Parameters
    ----------
    polyline : :class:`~compas.geometry.Polyline`
        The polyline to modify.
    segment_index : int
        The index of the segment to move.
    plane : :class:`~compas.geometry.Plane`
        The plane to intersect with.
    """
    start_pt = intersection_line_plane(polyline.lines[segment_index - 1], plane)
    if start_pt:
        polyline[segment_index] = start_pt
        if segment_index == 0:
            polyline[-1] = start_pt
    end_pt = intersection_line_plane(polyline.lines[(segment_index + 1) % len(polyline.lines)], plane)
    if end_pt:
        polyline[segment_index + 1] = end_pt
        if segment_index + 1 == len(polyline.lines):
            polyline[0] = end_pt


def planar_surface_point_at(surface, u, v):
    """
    Returns the point at parameters u, v on a planar surface transformed using the surface's transformation.
    The domain of u and v is assumed to be [0.0 => surface.xsize] and [0.0 => surface.ysize] respectively.

    Parameters
    ----------
    surface : :class:`~compas.geometry.PlanarSurface`
        The planar surface.
    u : float
        The first parameter.
    v : float
        The second parameter.

    Returns
    -------
    :class:`compas.geometry.Point`
        A point on the planar surface.

    Note
    ----
    This is a re-implementation of `PlanarSurface.point_at` which takes u and v in un-normalized coordinates.
    Starting with COMPAS 2.15.0, `PlanarSurface.point_at` expects u and v to be normalized.
    This method exists because life is hard and we believe
    backwards compatibility is a value worth protecting,
    together with freedom of speech, right of self-determination,
    democracy, and bodily autonomy.

    """
    point = Point(u, v, 0)
    point.transform(surface.transformation)
    return point


def move_polyline_segment_to_line(polyline, segment_index, line):
    """Move a segment of a polyline to lay colinear to the projection of a line on that polyline.
    This is accomplished by extending the adjacent segments to intersect with the line.
    Parameters
    ----------
    polyline : :class:`~compas.geometry.Polyline`
        The polyline to modify.
    segment_index : int
        The index of the segment to move.
    line : :class:`~compas.geometry.Line`
        The line to intersect with.
    """
    start_pt = intersection_line_line(polyline.lines[segment_index - 1], line)[0]
    if start_pt:
        polyline[segment_index] = start_pt
        if segment_index == 0:
            polyline[-1] = start_pt
    end_pt = intersection_line_line(polyline.lines[(segment_index + 1) % len(polyline.lines)], line)[0]
    if end_pt:
        polyline[segment_index + 1] = end_pt
        if segment_index + 1 == len(polyline.lines):
            polyline[0] = end_pt


def join_polyline_segments(segments: list[Line], close_loop: bool = False):
    """Join segments into one or more polylines.

    Parameters
    ----------
    segments : list of :class:`~compas.geometry.Line`
        the line segments to be joined
    close_loop : bool
        if True, each returned Polyline will be closed by appending the first point to the end, if not already the case.

    Returns
    -------
    tuple(list[:class:`~compas.geometry.Polyline`], list[:class:`~compas.geometry.Line`])
        A tuple with a list of joined Polylines and a list of segments that could not be joined.
    """

    # helper to add a segment to an existing ordered points list if it connects
    def add_seg_to_points(seg: Line, points: list) -> bool:
        if seg.start == points[-1]:
            points.append(seg.end)
            return True
        if seg.end == points[-1]:
            points.append(seg.start)
            return True
        if seg.end == points[0]:
            points.insert(0, seg.start)
            return True
        if seg.start == points[0]:
            points.insert(0, seg.end)
            return True
        return False

    if not segments:
        return [], []

    # filter out degenerate segments (start == end) before joining
    segments = [seg for seg in segments if not TOL.is_allclose(seg.start, seg.end)]
    if not segments:
        return [], []

    remaining = segments[:]  # copy so we don't mutate caller's list
    polylines: list[Polyline] = []
    unjoined: list[Line] = []

    while remaining:
        # start a new chain from the first remaining segment
        start_seg = remaining.pop(0)
        points = [start_seg.start, start_seg.end]

        extended = True
        while extended and remaining:
            extended = False
            for seg in remaining:
                if add_seg_to_points(seg, points):
                    remaining.remove(seg)
                    extended = True
                    break

        if len(points) == 2:  # no segments joined, points to unjoined
            unjoined.append(start_seg)
        else:
            if close_loop and not TOL.is_allclose(points[0], points[-1]):
                points.append(points[0])
            polylines.append(Polyline(points))

    return polylines, unjoined


def polyline_from_brep_loop(loop):
    """Creates a Polyline from a BrepLoop.

    Only straight (linear) edges are supported. Curved edges are treated as straight
    lines between their start and end vertices. If your brep contains curved faces,
    tessellate them to polygon faces before passing them to this function.

    Uses :func:`join_polyline_segments` internally to handle edges whose start/end
    points may be in any order or orientation, as can occur in polyhedron-style breps.
    Degenerate edges (start == end) are automatically filtered by :func:`join_polyline_segments`.

    Parameters
    ----------
    loop : :class:`~compas.geometry.BrepLoop`
        The BrepLoop to convert to a polyline.

    Returns
    -------
    :class:`~compas.geometry.Polyline` or None
        The Polyline resulting from joining the BrepLoop edges, or None if the edges
        cannot be joined into a single closed polyline.
    """
    segments = [Line(edge.start_vertex.point, edge.end_vertex.point) for edge in loop.edges]

    # join_polyline_segments handles any edge order / orientation, and filters degenerate segments
    polylines, _ = join_polyline_segments(segments, close_loop=True)

    if not polylines:
        return None
    # a valid closed polyline needs at least 4 points (3 unique vertices + 1 closing point);
    # 3 points would yield only 2 overlapping line segments
    if len(polylines[0].points) < 4:
        return None
    return polylines[0]


def polylines_from_brep_face(face):
    """Extract polylines from a BRep face.
    Parameters
    ----------
    face : :class:`~compas.geometry.BrepFace`
        The Brep face to extract polylines from.
    Returns
    -------
    tuple (`~compas.geometry.Polyline`, list: :class:`~compas.geometry.Polyline`)
        The extracted polylines.
    """
    outer = None
    openings = []
    for loop in face.loops:
        if loop.is_outer:
            outer = polyline_from_brep_loop(loop)
        else:
            opening = polyline_from_brep_loop(loop)
            if opening is not None:
                openings.append(opening)

    if outer is None:
        raise ValueError("Could not extract outer boundary polyline from BRep face")

    return outer, openings


def get_plate_geometry_outlines_from_brep(brep):
    """Extract the two parallel face outlines from a plate-like brep.

    Converts the brep to a :class:`~compas.datastructures.Mesh` via
    :func:`mesh_from_brep`. The two main faces are identified by polygon
    vertex count with a normal dot-product tiebreaker for the rectangular case.
    Vertex correspondence is resolved via shared edges on side faces.
    Openings are retrieved from the matching brep face.

    Parameters
    ----------
    brep : :class:`~compas.geometry.Brep`
        A brep representing a plate geometry.  Must contain at least 2 faces.

    Returns
    -------
    tuple(:class:`~compas.geometry.Polyline`, :class:`~compas.geometry.Polyline`, list[:class:`~compas.geometry.Polyline`] or None)
        ``outline_a``, ``outline_b``, and any inner opening polylines extracted
        from the primary face (or ``None`` if there are no openings).

    Raises
    ------
    ValueError
        If the brep has fewer than 2 faces or the two main faces cannot be identified.
    """
    if len(brep.faces) < 2:
        raise ValueError("Brep must have at least 2 faces, got {}.".format(len(brep.faces)))

    def pt_key(coords):
        return tuple(round(c, 6) for c in coords)

    mesh = mesh_from_brep(brep)
    face_keys = list(mesh.faces())

    # edge → list of adjacent face keys
    edge_to_faces = {}
    for f in face_keys:
        verts = mesh.face_vertices(f)
        n = len(verts)
        for i in range(n):
            e = frozenset([verts[i], verts[(i + 1) % n]])
            edge_to_faces.setdefault(e, []).append(f)

    face_neighbors = {f: set() for f in face_keys}
    for shared_faces in edge_to_faces.values():
        if len(shared_faces) == 2:
            a, b = shared_faces
            face_neighbors[a].add(b)
            face_neighbors[b].add(a)

    # main faces have the highest vertex count; side faces always have 4
    face_vcount = {f: len(mesh.face_vertices(f)) for f in face_keys}
    max_count = max(face_vcount.values())
    main_candidates = [f for f in face_keys if face_vcount[f] == max_count]

    def _face_normal(fkey):
        pts = [mesh.vertex_coordinates(v) for v in mesh.face_vertices(fkey)]
        v1 = subtract_vectors(pts[1], pts[0])
        v2 = subtract_vectors(pts[2], pts[0])
        n = cross_vectors(v1, v2)
        length = length_vector(n)
        return normalize_vector(n) if length > TOL.absolute else None

    if len(main_candidates) == 2 and max_count != 4:
        face_a_key, face_b_key = main_candidates
    else:
        # rectangular or ambiguous: pick the most parallel non-adjacent pair
        non_adjacent = [
            (face_keys[i], face_keys[j])
            for i in range(len(face_keys))
            for j in range(i + 1, len(face_keys))
            if face_keys[j] not in face_neighbors[face_keys[i]]
        ]
        if not non_adjacent:
            raise ValueError("Could not identify the two main faces: no non-adjacent face pair found.")
        best_pair = max(
            non_adjacent,
            key=lambda ij: abs(dot_vectors(
                _face_normal(ij[0]) or [0, 0, 0],
                _face_normal(ij[1]) or [0, 0, 0],
            )),
        )
        face_a_key, face_b_key = best_pair

    verts_a = mesh.face_vertices(face_a_key)
    verts_b = mesh.face_vertices(face_b_key)
    pts_a = [Point(*mesh.vertex_coordinates(v)) for v in verts_a]
    pts_b = [Point(*mesh.vertex_coordinates(v)) for v in verts_b]
    outline_a = Polyline(pts_a + [pts_a[0]])
    outline_b = Polyline(pts_b + [pts_b[0]])  # fallback

    # align outline_b to outline_a using shared edges on side faces
    set_a = set(verts_a)
    set_b = set(verts_b)
    a_pos = {v: i for i, v in enumerate(verts_a)}
    b_at_a_pos = {}

    for f in face_keys:
        if f in (face_a_key, face_b_key):
            continue
        fv = mesh.face_vertices(f)
        n = len(fv)
        for k in range(n):
            u, v = fv[k], fv[(k + 1) % n]
            if u in set_a and v in set_b:
                b_at_a_pos[a_pos[u]] = v
            elif u in set_b and v in set_a:
                b_at_a_pos[a_pos[v]] = u

    if len(b_at_a_pos) == len(verts_a):
        aligned_pts = [Point(*mesh.vertex_coordinates(b_at_a_pos[i])) for i in range(len(verts_a))]
        aligned_pts.append(aligned_pts[0])
        outline_b = Polyline(aligned_pts)

    # retrieve openings from the matching brep face
    pts_a_key_set = set(pt_key(mesh.vertex_coordinates(v)) for v in verts_a)
    openings = None
    for brep_face in brep.faces:
        outer_loop = next((loop for loop in brep_face.loops if loop.is_outer), None)
        if outer_loop is None:
            continue
        brep_face_pts = set()
        for edge in outer_loop.edges:
            brep_face_pts.add(pt_key(edge.start_vertex.point))
            brep_face_pts.add(pt_key(edge.end_vertex.point))
        if brep_face_pts == pts_a_key_set:
            opening_polylines = [polyline_from_brep_loop(loop) for loop in brep_face.loops if not loop.is_outer]
            opening_polylines = [o for o in opening_polylines if o is not None]
            openings = opening_polylines if opening_polylines else None
            break

    return outline_a, outline_b, openings


def get_polyline_normal_vector(polyline: Polyline, normal_direction: Optional[Vector] = None) -> Vector:
    """Get the vector normal to a polyline. if no normal direction is given, the normal is determined based on the polyline's winding order.
    parameters
    ----------
    polyline : :class:`compas.geometry.Polyline`
        The polyline to get the normal vector from.
    normal_direction : :class:`compas.geometry.Vector`, optional
        A vector indicating the desired normal direction.

    Returns
    -------
    :class:`compas.geometry.Vector`
        The normal vector of the polyline.
    """
    offset_vector = Frame.from_points(polyline[0], polyline[1], polyline[-2]).normal  # gets frame perpendicular to outline
    if normal_direction:
        if normal_direction.dot(offset_vector) < 0:  # if vector is given and points in the opposite direction
            offset_vector = -offset_vector
    elif not is_polyline_clockwise(polyline, offset_vector):  # if no vector and outline is not clockwise, flip the offset vector
        offset_vector = -offset_vector
    return offset_vector.unitized()


def combine_parallel_segments(polyline, tol=TOL):
    for i in range(len(polyline) - 2, 0, -1):
        v1 = Vector.from_start_end(polyline[i - 1], polyline[i])
        v2 = Vector.from_start_end(polyline[i], polyline[i + 1])
        if tol.is_zero(angle_vectors(v1, v2)):
            polyline.points.pop(i)


def _brep_loop_vertex_indices(loop, brep):
    """Return ordered vertex indices of a brep loop's outer boundary.

    Tries ``native_vertex.VertexIndex`` (Rhino) first; falls back to
    ``TOL.is_allclose`` point comparison against ``brep.vertices``.
    """
    face_vertex_indices = []
    for edge in loop.edges:
        try:
            for idx in (edge.start_vertex.native_vertex.VertexIndex, edge.end_vertex.native_vertex.VertexIndex):
                if idx not in face_vertex_indices:
                    face_vertex_indices.append(idx)
        except Exception:
            for i, v in enumerate(brep.vertices):
                if TOL.is_allclose(edge.start_vertex.point, v.point) and i not in face_vertex_indices:
                    face_vertex_indices.append(i)
                if TOL.is_allclose(edge.end_vertex.point, v.point) and i not in face_vertex_indices:
                    face_vertex_indices.append(i)
    return face_vertex_indices


def mesh_from_brep(brep):
    """Build a :class:`~compas.datastructures.Mesh` from a Brep's face structure.

    Each Brep face becomes one non-triangulated mesh face (outer loop only).
    Curved edges are treated as straight lines between their endpoints.

    Parameters
    ----------
    brep : :class:`~compas.geometry.Brep`
        A polyhedral Brep with planar faces and straight edges.

    Returns
    -------
    :class:`~compas.datastructures.Mesh`
    """
    faces = []
    for face in brep.faces:
        outer_loop = next((loop for loop in face.loops if loop.is_outer), None)
        if outer_loop is None:
            continue
        indices = _brep_loop_vertex_indices(outer_loop, brep)
        if len(indices) >= 3:
            faces.append(indices)

    return Mesh.from_vertices_and_faces([v.point for v in brep.vertices], faces)


def get_mesh_shape_values(mesh):
    """Return flat XYZ coordinates and face-index list (``-1`` sentinel per face) from a mesh.

    Parameters
    ----------
    mesh : :class:`~compas.datastructures.Mesh`

    Returns
    -------
    tuple(list[float], list[int])
        Flat ``[x, y, z, ...]`` point list and ``[i, j, k, -1, ...]`` face list.
    """
    points = []
    for v in mesh.vertices():
        points.extend(mesh.vertex_attributes(v, "xyz"))

    face_indices = []
    for f in mesh.faces():
        face_indices.extend(mesh.face_vertices(f))
        face_indices.append(-1)

    return points, face_indices


__all__ = [
    "intersection_line_line_param",
    "intersection_line_plane_param",
    "intersection_line_beam_param",
    "distance_segment_segment",
    "is_polyline_clockwise",
    "correct_polyline_direction",
    "get_polyline_segment_perpendicular_vector",
    "is_point_in_polyline",
    "do_segments_overlap",
    "get_segment_overlap",
    "move_polyline_segment_to_plane",
    "planar_surface_point_at",
    "StrEnum",
    "move_polyline_segment_to_line",
    "join_polyline_segments",
    "polyline_from_brep_loop",
    "polylines_from_brep_face",
    "get_plate_geometry_outlines_from_brep",
    "get_polyline_normal_vector",
    "combine_parallel_segments",
    "mesh_from_brep",
    "get_mesh_shape_values",
]
