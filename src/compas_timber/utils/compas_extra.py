from compas.geometry import Frame
from compas.geometry import Line
from compas.geometry import Plane
from compas.geometry import Point
from compas.geometry import cross_vectors
from compas.geometry import distance_point_point
from compas.geometry import subtract_vectors
from compas.geometry import length_vector, add_vectors, scale_vector, dot_vectors
from math import fabs
from compas.geometry import normalize_vector


def intersection_line_line_3D(
    line1, line2, max_distance=1e-6, limit_to_segments=True, tol=1e-6
):
    # adapted from: https://github.com/compas-dev/compas/blob/9052b90cad5a8d2ddbdbaae91712c568f3d3c926/src/compas/geometry/intersections/intersections.py
    """
    inputs:
        * two Lines (compas)
        * max_distance: between the lines to count as an apparent intersection
        * tol: numerical precision

    for each, returns:
        * None if no intersection with the other line (if lines parallel or outside of segment if limit_to_segments=True)
        * Point of the apparent intersection on this line
        * t parameter of the line (if return_t = True)
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
    x1, t1 = intersection_line_plane(line1, pln2, tol)
    x2, t2 = intersection_line_plane(line2, pln1, tol)

    # double-check for parallels, should not happen:
    if t1 == None or t2 == None:
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


def intersection_line_plane(line, plane, tol=1e-6):
    """Computes the intersection point of a line and a plane
    Parameters
    ----------
    line : [point, point] | :class:`~compas.geometry.Line`
        Two points defining the line.
    plane : [point, vector] | :class:`~compas.geometry.Plane`
        The base point and normal defining the plane.
    tol : float, optional
        A tolerance for membership verification.
    Returns
    -------
    [float, float, float] | None
        The intersection point between the line and the plane,
        or None if the line and the plane are parallel.
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


if __name__ == "__main__":

    import random
    import time

    # def randomx():
    #     return random.random()*2.0-1.0

    # t0 = time.time()
    # for i in range(250000):
    #     p1 = Point(randomx(), randomx(), randomx())
    #     p2 = Point(randomx(), randomx(), randomx())
    #     p3 = Point(randomx(), randomx(), randomx())
    #     p4 = Point(randomx(), randomx(), randomx())
    #     intersection_line_line_3D(Line(p1,p2), Line(p3,p4), max_distance=random.random()*0.1, limit_to_segments = random.choice([True, False]), tol = random.random()*1e-3)

    # t1 = time.time()
    # dt = (t1 - t0)
    # print(dt,"s")
