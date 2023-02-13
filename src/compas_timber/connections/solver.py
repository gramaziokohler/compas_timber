import itertools
import math

from compas.geometry import Point
from compas.geometry import add_vectors
from compas.geometry import angle_vectors
from compas.geometry import closest_point_on_line
from compas.geometry import cross_vectors
from compas.geometry import distance_point_point
from compas.geometry import dot_vectors
from compas.geometry import scale_vector
from compas.geometry import subtract_vectors
from compas.plugins import pluggable


@pluggable(category="solvers")
def find_neighboring_beams(beams):
    """Uses RTree to find neighboring pairs of beams in the given list of beams.
    The returned elements are sets containing pairs of Beam objects.

    """
    raise NotImplementedError


class JointTopology(object):
    """Enumeration of the possible joint topologies."""

    L = "L"
    T = "T"
    X = "X"
    I = "I"
    NO_INTERSECTION = "NO"


class ConnectionSolver(object):
    """Provides tools for detecting beam intersections and joint topologies."""

    TOLERANCE = 1e-6

    def find_connections(self, beams, rtree=True, max_distance=None):
        connections = []
        candidate_pairs = self._find_pair_candidates(beams, rtree)
        for beamA, beamB in candidate_pairs:
            topo, beams_pair = self.centerline_intersection(beamA, beamB, max_distance)
            if topo is not JointTopology.NO_INTERSECTION:
                connections.append([topo, beams_pair])
        return connections

    def _find_pair_candidates(self, beams, rtree=False):
        """From a list of beams, find beam pairs to later check if their intersect. Uses R-Tree or simple two-combinations."""
        if rtree:
            pairs = find_neighboring_beams(beams)
        else:
            pairs = itertools.combinations(beams, 2)
        return pairs

    def centerline_intersection(self, beamA, beamB, max_distance=None):
        """For a pair of beams, checks if their centerlines intersect (within a max_distance, optional), and determines topology of this intersection (using max_distance cutoff, optional)."""
        tol = self.TOLERANCE  # TODO: change to a unit-sensitive value
        angtol = 1e-3

        a1, a2 = beamA.centerline
        b1, b2 = beamB.centerline
        va = subtract_vectors(a2, a1)
        vb = subtract_vectors(b2, b1)

        # check if centerlines parallel
        ang = angle_vectors(va, vb)
        if ang < angtol or ang > math.pi - angtol:
            parallel = True
        else:
            parallel = False

        if parallel:
            # if centerlines parallel:
            #   check if distance < max_dist:
            #       if yes : check if I-topology: lines cannot overlap and should "meet" at one and only one of ends
            #           if yes: return I-topology
            #       if no: return NO_INTERSECTION, [None, None]

            pa = a1
            pb = closest_point_on_line(a1, [b1, b2])
            if self._exceed_max_distance(pa, pb, max_distance, tol):
                return JointTopology.NO_INTERSECTION, [None, None]

            # check if any ends meet
            comb = [[0, 0], [0, 1], [1, 0], [1, 1]]
            meet = [not self._exceed_max_distance([a1, a2][ia], [b1, b2][ib], max_distance, tol) for ia, ib in comb]
            if sum(meet) != 1:
                return JointTopology.NO_INTERSECTION, [None, None]

            # check if overlap: find meeting ends -> compare vectors outgoing from these points
            meeting_ends_idx = [c for c, m in zip(comb, meet) if m is True][0]
            ia, ib = meeting_ends_idx
            pa1 = [a1, a2][ia]
            pa2 = [a1, a2][not ia]
            pb1 = [b1, b2][ib]
            pb2 = [b1, b2][not ib]
            vA = subtract_vectors(pa2, pa1)
            vB = subtract_vectors(pb2, pb1)
            ang = angle_vectors(vA, vB)
            if ang < tol:
                # vectors pointing in the same direction -> beams are overlapping
                return JointTopology.NO_INTERSECTION, [None, None]
            else:
                return JointTopology.I, [beamA, beamB]

        # if not parallel:
        #   calculate line-line-intersection --> get points pA, pB and t-params tA,tB
        #   from points, calculate if distance(pA,pB) < max_distance,
        #       if not: return NO_INTERSECTION, [None, None]
        #   from t-params, determine if T, L or X topology
        #       if both tA and tB are not (close to) 0 or 1: return X-topology, [beamA, beamB]
        #       if both tA and tB are (close to) 0 or 1: return L-topology, [beamA, beamB]
        #       if tA is (close to) 0 or 1 but not tB: return T-topology, [beamA, beamB]
        #       if tB is (close to) 0 or 1 but not tA: return T-topology, [beamB, beamA]

        vn = cross_vectors(va, vb)
        vna = cross_vectors(va, vn)
        vnb = cross_vectors(vb, vn)

        ta = self._calc_t([a1, a2], [b1, vnb])
        pa = Point(*add_vectors(a1, scale_vector(va, ta)))
        tb = self._calc_t([b1, b2], [a1, vna])
        pb = Point(*add_vectors(b1, scale_vector(vb, tb)))

        # for max_distance calculations, limit intersection point to line segment
        if ta < 0:
            pa = a1
        if ta > 1:
            pa = a2
        if tb < 0:
            pb = b1
        if tb > 1:
            pb = b2

        if self._exceed_max_distance(pa, pb, max_distance, tol):
            return JointTopology.NO_INTERSECTION, [None, None]

        # topologies:
        xa = self._is_near_end(ta, beamA.centerline.length, max_distance or 0, tol)
        xb = self._is_near_end(tb, beamB.centerline.length, max_distance or 0, tol)

        # L-joint (both meeting at ends)
        if xa and xb:
            return JointTopology.L, [beamA, beamB]

        # T-joint (one meeting with the end along the other)
        if xa:
            # A:main, B:cross
            return JointTopology.T, [beamA, beamB]
        if xb:
            # B:main, A:cross
            return JointTopology.T, [beamB, beamA]

        # X-joint (both meeting somewhere along the line)
        return JointTopology.X, [beamA, beamB]

    @staticmethod
    def _calc_t(line, plane):
        a, b = line
        o, n = plane
        ab = subtract_vectors(b, a)
        dotv = dot_vectors(n, ab)  # lines parallel to plane (dotv=0) filtered out already
        oa = subtract_vectors(a, o)
        t = -dot_vectors(n, oa) / dotv
        return t

    @staticmethod
    def _exceed_max_distance(pa, pb, max_distance, tol):
        d = distance_point_point(pa, pb)
        if max_distance is not None and d > max_distance:
            return True
        if max_distance is None and d > tol:
            return True
        return False

    @staticmethod
    def _is_near_end(t, length, max_distance, tol):
        return abs(t) * length < max_distance + tol or abs(1.0 - t) * length < max_distance + tol
