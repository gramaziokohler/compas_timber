import itertools

from compas.plugins import pluggable

from compas_timber.utils import intersection_line_line_3D


@pluggable(category="solvers")
def find_neighboring_beams(beams):
    """Uses RTree to find neighboring pairs of beams in the given list of beams.
    The returned elements are sets containing pairs of Beam objects.

    """
    raise NotImplementedError


class JointTopology(object):
    """Enumeration of the possible joint topologies."""

    TOPO_L = 0
    TOPO_T = 1
    TOPO_X = 2
    TOPO_UNKNOWN = 3

    @classmethod
    def get_name(cls, value):
        """Should be used for debug/logging purposes only!

        Returns the string representation of given topology value.

        Parameters
        ----------
        value : int
            One of [JointTopology.TOPO_L, JointTopology.TOPO_T, JointTopology.TOPO_X, JointTopology.TOPO_UNKNOWN]

        Returns
        -------
        str
            One of ["TOPO_L", "TOPO_T", "TOPO_X", "TOPO_UNKNOWN"]

        """
        try:
            {v: k for k, v in JointTopology.__dict__.items() if k.startswith("TOPO_")}[value]
        except KeyError:
            return "TOPO_UNKNOWN"


class ConnectionSolver(object):
    """Provides tools for detecting beam intersections and joint topologies."""

    TOLERANCE = 1e-6

    @classmethod
    def find_intersecting_pairs(cls, beams, rtree=False):
        """Finds pairs of intersecting beams in the given list of beams.

        Parameters
        ----------
        beams : list(:class:`compas_timber.parts.Beam`)
            A list of beam objects.
        rtree : bool
            When set to True RTree will be used to search for neighboring beams.

        Returns
        -------
        list(set(:class:`compas_timber.parts.Beam`, :class:`compas_timber.parts.Beam`))
            List containing sets or neightboring pairs beams.

        """
        return find_neighboring_beams(beams) if rtree else itertools.combinations(beams, 2)

    def find_topology(self, beam_a, beam_b, tol=TOLERANCE, max_distance=None):
        if max_distance is None:
            max_distance = beam_a.height + beam_b.height

        (_, ta), (_, tb) = intersection_line_line_3D(
            beam_a.centerline, beam_b.centerline, max_distance, limit_to_segments=True, tol=self.TOLERANCE
        )

        if ta is None or tb is None:
            return JointTopology.TOPO_UNKNOWN, beam_a, beam_b

        xa = self.is_near_end(ta, tol)
        xb = self.is_near_end(tb, tol)

        if xa and xb:
            # L-joint (both meeting at ends) TODO: this could also be an I-joint (splice) -> will need to check for angle between beams
            return JointTopology.TOPO_L, beam_a, beam_b
        # T-joint (one meeting with the end along the other)
        if xa:
            # A:main, B:cross
            return JointTopology.TOPO_T, beam_a, beam_b
        if xb:
            # B:main, A:cross
            return JointTopology.TOPO_T, beam_b, beam_a
        # X-joint (both meeting somewhere along the line)
        return JointTopology.TOPO_X, beam_a, beam_b

    @staticmethod
    def is_near_end(t, tol=TOLERANCE):
        return abs(t) < tol or abs(1.0 - t) < tol  # is almost 0 or almost 1
