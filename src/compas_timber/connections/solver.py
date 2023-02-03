from compas.geometry import intersection_segment_segment
from compas.plugins import pluggable

from compas_timber.utils import intersection_line_line_3D


@pluggable(category="solvers")
def find_neighboring_beams(beams):
    """Uses RTree to find neighboring pairs of beams in the given list of beams.
    The returned elements are sets containing pairs of Beam objects.

    """
    raise NotImplementedError


class JointTopology:
    """Enumeration of the possible joint topologies."""

    L = 0
    T = 1
    X = 2


class ConnectionSolver(object):
    """Provides tools for detecting beam intersections and joint topologies."""

    TOLERANCE = 1e-6

    @classmethod
    def find_intersecting_pairs(cls, beams):
        """Naive implementation, can/should be optimized"""
        intersecting_pairs = []
        combinations = find_neighboring_beams(beams)
        for beam_pair in combinations:
            beam_a, beam_b = tuple(beam_pair)  # beam_pair is a set
            p1, p2 = intersection_segment_segment(beam_a.centerline, beam_b.centerline)
            if p1 and p2:
                intersecting_pairs.append(beam_pair)
        return intersecting_pairs

    def find_topology(self, beam_a, beam_b, tol=TOLERANCE, max_distance=None):
        if max_distance is None:
            max_distance = beam_a.height + beam_b.height

        (_, ta), (_, tb) = intersection_line_line_3D(
            beam_a.centerline, beam_b.centerline, max_distance, limit_to_segments=True, tol=self.TOLERANCE
        )

        xa = self.is_near_end(ta)
        xb = self.is_near_end(tb)

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
