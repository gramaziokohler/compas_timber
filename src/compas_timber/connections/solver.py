import itertools

from compas.geometry import close
from compas.geometry import distance_point_point
from compas.geometry import intersection_segment_segment

from compas_timber.utils import intersection_line_line_3D


class JointTopology(object):
    """Enumeration of the possible joint topologies."""

    L = 0
    T = 1
    X = 2
    NO_INTERSECTION = 3


class ConnectionSolver(object):
    """Provides tools for detecting beam intersections and joint topologies."""

    TOLERANCE = 1e-6

    @classmethod
    def find_intersecting_pairs(cls, beams):
        """Naive implementation, can/should be optimized"""
        intersecting_pairs = []
        for beam_pair in itertools.combinations(beams, 2):
            beam_a, beam_b = beam_pair
            if cls._intersect_with_tolerance(beam_a.centerline, beam_b.centerline):
                intersecting_pairs.append(beam_pair)
        return intersecting_pairs

    @staticmethod
    def _intersect_with_tolerance(line_a, line_b, tolerance=TOLERANCE):
            p1, p2 = intersection_segment_segment(line_a, line_b)
            if p1 is None or p2 is None:
                return False
            distance = distance_point_point(p1, p2)
            return close(distance, tolerance)

    def find_topology(self, beam_a, beam_b, tol=TOLERANCE, max_distance=None):
        if max_distance is None:
            max_distance = beam_a.height + beam_b.height

        (_, ta), (_, tb) = intersection_line_line_3D(
            beam_a.centerline, beam_b.centerline, max_distance, limit_to_segments=True, tol=self.TOLERANCE
        )

        if ta is None or tb is None:
            return JointTopology.NO_INTERSECTION

        xa = self.is_near_end(ta, tol)
        xb = self.is_near_end(tb, tol)

        if xa and xb:
            # L-joint (both meeting at ends) TODO: this could also be an I-joint (splice) -> will need to check for angle between beams
            return JointTopology.L, beam_a, beam_b
        # T-joint (one meeting with the end along the other)
        if xa:
            # A:main, B:cross
            return JointTopology.T, beam_a, beam_b
        if xb:
            # B:main, A:cross
            return JointTopology.T, beam_b, beam_a
        # X-joint (both meeting somewhere along the line)
        return JointTopology.X, beam_a, beam_b

    @staticmethod
    def is_near_end(t, tol=TOLERANCE):
        return abs(t) < tol or abs(1.0 - t) < tol  # is almost 0 or almost 1
