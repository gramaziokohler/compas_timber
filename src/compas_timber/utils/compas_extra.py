from compas.geometry import Line, Plane, Frame, Point
from compas.geometry import subtract_vectors, cross_vectors, intersection_line_plane, distance_point_point


def is_near_end(t, tol=1e-6):
    if abs(t)<tol: return True #almost zero
    if abs(1.0-t)<tol: return True #almost 1
    return False

def __get_t(p, v, pt):
    """
    p = start point of the line, at which t=0
    v = direction of the line, t=1 at p+v
    pt = point on the line for which you want to find the t parameter
    """
    if v[0] != 0:
        return (pt[0]-p[0])/v[0]
    if v[1] != 0:
        return (pt[1]-p[1])/v[1]
    if v[2] != 0:
        return (pt[2]-p[2])/v[2]
    return None


def intersection_line_line_3D(L1, L2, max_distance=1e-6, limit_to_segments=True, return_t=False, tol=1e-6, verbose=True):

    P1 = L1[0]
    V1 = subtract_vectors(L1[1], L1[0])

    P2 = L2[0]
    V2 = subtract_vectors(L2[1], L2[0])

    N = cross_vectors(V1, V2)

    # check if lines are parallel
    if all([abs(x) < tol for x in N]):
        #raise UserWarning("The lines are parallel - no intersection.")
        return [None, None]

    pln1 = Plane.from_frame(Frame(P1, V1, N))
    pln2 = Plane.from_frame(Frame(P2, V2, N))

    # get intersection points
    X1 = intersection_line_plane(L1, pln2, tol)
    X2 = intersection_line_plane(L2, pln1, tol)
    X1 = Point(*X1)
    X2 = Point(*X2)

    # is intersection exact / within some max_distance?
    d = distance_point_point(X1, X2)
    if d > max_distance:
        return [None, None]

    # get t parameters (t parameter: 0 at start point, 1 at end point of the line segment)
    if return_t or limit_to_segments:
        #t1 = distance_point_point(P1, X1) / L1.length
        #t2 = distance_point_point(P2, X2) / L2.length
        t1 = __get_t(P1, V1, X1)
        t2 = __get_t(P2, V2, X2)

    # is intersection within the line segment? if not, override results with None
    if limit_to_segments:
        if t1 < 0.0 or t1 > 1.0:
            X1 = None
            t1 = None
        if t2 < 0.0 or t2 > 1.0:
            X2 = None
            t2 = None

    if return_t:
        return [t1, t2]
    else:
        return [X1, X2]
