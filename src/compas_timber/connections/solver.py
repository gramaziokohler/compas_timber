import itertools
import math

from compas.data import Data
from compas.geometry import Line
from compas.geometry import Point
from compas.geometry import Vector
from compas.geometry import angle_vectors
from compas.geometry import distance_point_line
from compas.geometry import distance_point_point
from compas.geometry import dot_vectors
from compas.geometry import intersection_plane_plane
from compas.geometry import intersection_segment_polyline
from compas.geometry import is_parallel_line_line
from compas.plugins import pluggable
from compas.tolerance import TOL

from compas_timber.utils import distance_segment_segment_points
from compas_timber.utils import get_segment_overlap
from compas_timber.utils import is_point_in_polyline


@pluggable(category="solvers")
def find_neighboring_elements(elements, inflate_by=0.0):
    """Finds neighboring pairs of beams in the given list of beams, using R-tree search.

    The inputs to the R-tree algorithm are the axis-aligned bounding boxes of the beams (beam.aabb), enlarged by the `inflate_by` amount.
    The returned elements are sets containing pairs of Beam objects.

    Parameters
    ----------
    beams : list(:class:`~compas_timer.part.Beam`)
        The list of beams in which neighboring beams should be identified.
    inflate_by : optional, float
        A value in design units by which the regarded bounding boxes should be inflated.

    Returns
    -------
    list(set(:class:`~compas_timber.part.Beam`, :class:`~compas_timber.part.Beam`))

    Notes
    -----
    This is a `pluggable`. In order to use this function, a compatible `plugin` has to be available.
    For example, in Rhino, the function :func:`~compas_timber.rhino.find_neighboring_elements` will be used.

    """
    raise NotImplementedError


class JointTopology(object):
    """Enumeration of the possible joint topologies.

    Attributes
    ----------
    TOPO_UNKNOWN
    TOPO_I - end-to-end joint between two parallel beams
    TOPO_L - end-to-end joint between two non-parallel beams
    TOPO_T - end-to-middle joint between two beams
    TOPO_X - middle-to-middle joint between two beams
    TOPO_Y - joint between three or more beams where all beams meet at their ends
    TOPO_K - joint between three or more beams where at least one beam meet in the middle
    TOPO_EDGE_EDGE  - joint between two plates where the edges of both plates are aligned
    TOPO_EDGE_FACE  - joint between two plates where one plate is aligned with the face of the other

    """

    TOPO_UNKNOWN = 0
    TOPO_I = 1
    TOPO_L = 2
    TOPO_T = 3
    TOPO_X = 4
    TOPO_Y = 5
    TOPO_K = 6
    TOPO_EDGE_EDGE = 7
    TOPO_EDGE_FACE = 8

    @classmethod
    def get_name(cls, value):
        """Returns the string representation of given topology value.

        For use in logging.

        Parameters
        ----------
        value : int
            One of [JointTopology.TOPO_I, JointTopology.TOPO_L, JointTopology.TOPO_T, JointTopology.TOPO_X, JointTopology.TOPO_Y,
            JointTopology.TOPO_K, JointTopology.TOPO_EDGE_EDGE, JointTopology.TOPO_EDGE_FACE, JointTopology.TOPO_UNKNOWN]

        Returns
        -------
        str
            One of ["TOPO_I", "TOPO_L", "TOPO_T", "TOPO_X", "TOPO_Y", "TOPO_K", "TOPO_EDGE_EDGE", "TOPO_EDGE_FACE", "TOPO_UNKNOWN"]

        """
        try:
            return {v: k for k, v in JointTopology.__dict__.items() if k.startswith("TOPO_")}[value]
        except KeyError:
            return "TOPO_UNKNOWN"


class ConnectionSolver(object):
    """Provides tools for detecting beam intersections and joint topologies."""

    TOLERANCE = 1e-6

    @classmethod
    def find_intersecting_pairs(cls, beams, rtree=False, max_distance=0.0):
        """Finds pairs of intersecting beams in the given list of beams.

        Parameters
        ----------
        beams : list(:class:`~compas_timber.elements.Beam`)
            A list of beam objects.
        rtree : bool
            When set to True R-tree will be used to search for neighboring beams.
        max_distance : float, optional
            When `rtree` is True, an additional distance apart with which
            non-touching beams are still considered intersecting.

        Returns
        -------
        list(set(:class:`~compas_timber.elements.Beam`, :class:`~compas_timber.elements.Beam`))
            List containing sets or neightboring pairs beams.

        """
        return find_neighboring_elements(beams, inflate_by=max_distance) if rtree else itertools.combinations(beams, 2)

    def find_topology(self, beam_a, beam_b, max_distance=None):
        """If `beam_a` and `beam_b` intersect within the given `max_distance`, return the topology type of the intersection.

        If the topology is role-sensitive, the method outputs the beams in a consistent specific order
        (e.g. main beam first, cross beam second), otherwise, the beams are outputted in the same
        order as they were inputted.

        Parameters
        ----------
        beam_a : :class:`~compas_timber.elements.Beam`
            First beam from intersecting pair.
        beam_b : :class:`~compas_timber.elements.Beam`
            Second beam from intersecting pair.
        max_distance : float, optional
            Maximum distance, in design units, at which two beams are considered intersecting.

        Returns
        -------
        :class:`~compas_timber.connections.BeamSolverResult`
            The topology results of the intersection between the two beams.
        """
        # first check if the beams are close enough to be considered intersecting and get the closest points on the segments
        max_distance = max_distance or TOL.absolute  # TODO: change to a unit-sensitive value
        dist, point_a, point_b = distance_segment_segment_points(beam_a.centerline, beam_b.centerline)
        if dist > max_distance:
            return BeamSolverResult(JointTopology.TOPO_UNKNOWN, beam_a, beam_b, None, None)
        point_a = Point(*point_a)
        point_b = Point(*point_b)

        # see if beams are parallel
        if TOL.is_zero(angle_vectors(beam_a.centerline.direction, beam_b.centerline.direction) % math.pi):
            # beams are parallel
            # if parallel overlap on beam_a means that beam_b is overlapped by beam_a. Only need to perform the check on beam_a
            overlap_on_a = get_segment_overlap(beam_a.centerline, beam_b.centerline)
            if overlap_on_a is None:
                return BeamSolverResult(JointTopology.TOPO_I, beam_a, beam_b, dist, (point_a + point_b) / 2.0)
            if overlap_on_a[1] < max_distance:  # overlaps on beam_a start
                pt = beam_b.endpoint_closest_to_point(beam_a.centerline.start)[1]
                dist = distance_point_point(pt, beam_a.centerline.start)
                return BeamSolverResult(JointTopology.TOPO_I, beam_a, beam_b, dist, (beam_a.centerline.start + pt) / 2.0)
            if abs(overlap_on_a[0] - beam_a.length) < max_distance:  # overlaps on beam_a end
                pt = beam_b.endpoint_closest_to_point(beam_a.centerline.end)[1]
                dist = distance_point_point(pt, beam_a.centerline.end)
                return BeamSolverResult(JointTopology.TOPO_I, beam_a, beam_b, dist, (beam_a.centerline.end + pt) / 2.0)
            else:
                return BeamSolverResult(JointTopology.TOPO_UNKNOWN, beam_a, beam_b)

        _, a_end_pt = beam_a.endpoint_closest_to_point(point_b)
        _, b_end_pt = beam_b.endpoint_closest_to_point(point_a)

        a_end = distance_point_point(a_end_pt, point_a) < max_distance
        b_end = distance_point_point(b_end_pt, point_b) < max_distance
        location = (point_a + point_b) / 2.0
        if a_end and b_end:
            return BeamSolverResult(JointTopology.TOPO_L, beam_a, beam_b, dist, location)
        if a_end:
            return BeamSolverResult(JointTopology.TOPO_T, beam_a, beam_b, dist, location)
        if b_end:
            return BeamSolverResult(JointTopology.TOPO_T, beam_b, beam_a, dist, location)
        return BeamSolverResult(JointTopology.TOPO_X, beam_a, beam_b, dist, location)


class PlateConnectionSolver(ConnectionSolver):
    """Provides tools for detecting plate intersections and joint topologies."""

    TOLERANCE = 1e-6

    def find_topology(self, plate_a, plate_b, max_distance=TOLERANCE, tol=TOLERANCE):
        """Calculates the topology of the intersection between two plates. requires that one edge of a plate lies on the plane of the other plate.
        When TOPOLOGY_EDGE_FACE is found, the plates are returned in reverse order, with the main plate first and the cross plate second.

        parameters
        ----------
        plate_a : :class:`~compas_timber.elements.Plate`
            First potential intersecting plate.
        plate_b : :class:`~compas_timber.elements.Plate`
            Second potential intersecting plate.
        tol : float
            General tolerance to use for mathematical computations.
        max_distance : float, optional
            Maximum distance, in desigen units, at which two plates are considered intersecting.

        Returns
        -------
        :class:`~compas_timber.connections.PlateSolverResult`
        """
        plate_a_segment_index, plate_b_segment_index, dist, pt = self._find_plate_segment_indices(plate_a, plate_b, max_distance=max_distance, tol=tol)
        if plate_a_segment_index is None and plate_b_segment_index is None:
            return PlateSolverResult(JointTopology.TOPO_UNKNOWN, plate_a, plate_b, plate_a_segment_index, plate_b_segment_index, dist, pt)
        if plate_a_segment_index is not None and plate_b_segment_index is None:
            return PlateSolverResult(JointTopology.TOPO_EDGE_FACE, plate_a, plate_b, plate_a_segment_index, plate_b_segment_index, dist, pt)
        if plate_a_segment_index is None and plate_b_segment_index is not None:
            return PlateSolverResult(JointTopology.TOPO_EDGE_FACE, plate_b, plate_a, plate_b_segment_index, plate_a_segment_index, dist, pt)
        if plate_a_segment_index is not None and plate_b_segment_index is not None:
            return PlateSolverResult(JointTopology.TOPO_EDGE_EDGE, plate_a, plate_b, plate_a_segment_index, plate_b_segment_index, dist, pt)

    @staticmethod
    def _find_plate_segment_indices(plate_a, plate_b, max_distance=None, tol=TOL):
        """Finds the indices of the outline segments of `polyline_a` and `polyline_b`. used to determine connection Topology"""

        i_a, i_b, dist, pt = PlateConnectionSolver._get_l_topo_segment_indices(plate_a, plate_b, max_distance=max_distance, tol=tol)
        if i_a is not None:
            return i_a, i_b, dist, pt
        i_a, dist, pt = PlateConnectionSolver._get_t_topo_segment_index(plate_a, plate_b, max_distance=max_distance, tol=tol)
        if i_a is not None:
            return i_a, None, dist, pt
        i_b, dist, pt = PlateConnectionSolver._get_t_topo_segment_index(plate_b, plate_a, max_distance=max_distance, tol=tol)
        if i_b is not None:
            return None, i_b, dist, pt
        return None, None, None, None

    @staticmethod
    def _get_l_topo_segment_indices(plate_a, plate_b, max_distance=None, tol=TOL):
        """Finds the indices of the outline segments of `polyline_a` and `polyline_b` that are colinear.
        Used to find segments that join in L_TOPO Topology"""

        if max_distance is None:
            max_distance = max(plate_a.thickness, plate_b.thickness)
        for pair in itertools.product(plate_a.outlines, plate_b.outlines):
            for i, seg_a in enumerate(pair[0].lines):
                for j, seg_b in enumerate(pair[1].lines):  # TODO: use rtree?
                    seg_a_midpt = seg_a.point_at(0.5)
                    dist = distance_point_line(seg_a_midpt, seg_b)
                    if dist <= max_distance:
                        if is_parallel_line_line(seg_a, seg_b, tol=tol):
                            if PlateConnectionSolver.do_segments_overlap(seg_a, seg_b):
                                return i, j, dist, seg_a_midpt
        return None, None, None, None

    @staticmethod
    def _get_t_topo_segment_index(main_plate, cross_plate, max_distance=None, tol=TOL):
        """Finds the indices of the outline segments of `polyline_a` and `polyline_b` that are colinear.
        Used to find segments that join in L_TOPO Topology"""

        if max_distance is None:
            max_distance = min(main_plate.thickness, cross_plate.thickness)
        for pline_a, plane_a in zip(main_plate.outlines, main_plate.planes):
            for pline_b, plane_b in zip(cross_plate.outlines, cross_plate.planes):
                line = Line(*intersection_plane_plane(plane_a, plane_b))
                for i, seg_a in enumerate(pline_a.lines):  # TODO: use rtree?
                    seg_a_midpt = seg_a.point_at(0.5)
                    dist = distance_point_line(seg_a_midpt, line)
                    if dist <= max_distance:
                        if is_parallel_line_line(seg_a, line, tol=tol):
                            if PlateConnectionSolver.does_segment_intersect_outline(seg_a, pline_b):
                                return i, dist, seg_a_midpt
        return None, None, None

    @staticmethod
    def do_segments_overlap(segment_a, segment_b):
        """Checks if two segments overlap.

        Parameters
        ----------
        seg_a : :class:`~compas.geometry.Segment`
            The first segment.
        seg_b : :class:`~compas.geometry.Segment`
            The second segment.
        tol : float, optional
            Tolerance for overlap check.

        Returns
        -------
        bool
            True if the segments overlap, False otherwise.
        """
        for pt_a in [segment_a.start, segment_a.end, segment_a.point_at(0.5)]:
            dot_start = dot_vectors(segment_b.direction, Vector.from_start_end(segment_b.start, pt_a))
            dot_end = dot_vectors(segment_b.direction, Vector.from_start_end(segment_b.end, pt_a))
            if dot_start > 0 and dot_end < 0:
                return True
        for pt_b in [segment_b.start, segment_b.end, segment_b.point_at(0.5)]:
            dot_start = dot_vectors(segment_a.direction, Vector.from_start_end(segment_a.start, pt_b))
            dot_end = dot_vectors(segment_a.direction, Vector.from_start_end(segment_a.end, pt_b))
            if dot_start > 0 and dot_end < 0:
                return True
        return False

    @staticmethod
    def does_segment_intersect_outline(segment, polyline, tol=TOL):
        """Checks if a segment intersects with the outline of a polyline.

        Parameters
        ----------
        segment : :class:`~compas.geometry.Segment`
            The segment to check for intersection.
        polyline : :class:`~compas.geometry.Polyline`
            The polyline whose outline is checked for intersection.
        tol : float, optional
            Tolerance for intersection check.

        Returns
        -------
        bool
            True if the segment intersects with the outline of the polyline, False otherwise.
        """
        if intersection_segment_polyline(segment, polyline, tol.absolute)[0]:
            return True
        return is_point_in_polyline(segment.point_at(0.5), polyline, in_plane=False, tol=tol)


class BeamSolverResult(Data):
    """Data structure to hold the results of beam connection topology analysis.

    Parameters
    ----------
    topology : :class:`~compas_timber.connections.JointTopology`
        The topology of the intersection.
    beam_a : :class:`~compas_timber.elements.Beam`
        The first beam involved in the intersection.
    beam_b : :class:`~compas_timber.elements.Beam`
        The second beam involved in the intersection.
    distance : float
        The distance between the closest points of the two beams.
    location : :class:`~compas.geometry.Point`
        The location of the intersection.

    Attributes
    ----------
    topology : :class:`~compas_timber.connections.JointTopology`
        The topology of the intersection.
    beam_a : :class:`~compas_timber.elements.Beam`
        The first beam involved in the intersection.
    beam_b : :class:`~compas_timber.elements.Beam`
        The second beam involved in the intersection.
    distance : float
        The distance between the closest points of the two beams.
    location : :class:`~compas.geometry.Point`
        The location of the intersection.

    """

    def __init__(self, topology, beam_a, beam_b, distance=None, location=None):
        super(BeamSolverResult, self).__init__()
        self.topology = topology
        self.beam_a = beam_a
        self.beam_b = beam_b
        self.distance = distance
        self.location = location

    @property
    def __data__(self):
        return {
            "topology": self.topology,
            "beam_a": self.beam_a,
            "beam_b": self.beam_b,
            "distance": self.distance,
            "location": self.location,
        }

    def __repr__(self):
        return "BeamSolverResult(topology={}, beam_a={}, beam_b={}, distance={}, location={})".format(
            self.topology, self.beam_a.name, self.beam_b.name, self.distance, self.location
        )


class PlateSolverResult(Data):
    """Data structure to hold the results of plate connection topology analysis.
    Parameters
    ----------
    topology : :class:`~compas_timber.connections.JointTopology`
        The topology of the intersection.
    plate_a : :class:`~compas_timber.elements.Plate`
        The first plate involved in the intersection.
    plate_b : :class:`~compas_timber.elements.Plate`
        The second plate involved in the intersection.
    a_segment_index : int, optional
        The index of the segment in `plate_a` where the intersection occurs.
    b_segment_index : int, optional
        The index of the segment in `plate_b` where the intersection occurs.
    distance : float, optional
        The calculated distance between the location points of the two plates.
    location : :class:`~compas.geometry.Point`, optional
        The location of the intersection.

    Attributes
    ----------
    topology : :class:`~compas_timber.connections.JointTopology`
        The topology of the intersection.
    plate_a : :class:`~compas_timber.elements.Plate`
        The first plate involved in the intersection.
    plate_b : :class:`~compas_timber.elements.Plate`
        The second plate involved in the intersection.
    a_segment_index : int, optional
        The index of the segment in `plate_a` where the intersection occurs.
    b_segment_index : int, optional
        The index of the segment in `plate_b` where the intersection occurs.
    distance : float, optional
        The calculated distance between the location points of the two plates.
    location : :class:`~compas.geometry.Point`, optional
        The location of the intersection.
    """

    def __init__(self, topology, plate_a, plate_b, a_segment_index=None, b_segment_index=None, distance=None, location=None):
        """Initializes the PlateSolverResult with the given parameters."""

        super(PlateSolverResult, self).__init__()
        self.topology = topology
        self.plate_a = plate_a
        self.plate_b = plate_b
        self.a_segment_index = a_segment_index
        self.b_segment_index = b_segment_index
        self.distance = distance
        self.location = location

    @property
    def __data__(self):
        """Returns the data representation of the PlateSolverResult."""
        return {
            "topology": self.topology,
            "plate_a": self.plate_a,
            "plate_b": self.plate_b,
            "a_segment_index": self.a_segment_index,
            "b_segment_index": self.b_segment_index,
            "distance": self.distance,
            "location": self.location,
        }

    def __repr__(self):
        """Returns a string representation of the PlateSolverResult."""
        return "PlateSolverResult(topology={}, plate_a={}, plate_b={}, a_segment_index={}, b_segment_index={}, distance={}, location={})".format(
            self.topology,
            self.plate_a.name,
            self.plate_b.name,
            self.a_segment_index,
            self.b_segment_index,
            self.distance,
            self.location,
        )
