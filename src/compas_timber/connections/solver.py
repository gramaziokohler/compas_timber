import itertools
import math

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

from .topology_data import BeamTopologyData
from .topology_data import PlateTopologyData
from .topology_data import TopologyData
from .utilities import beam_ref_side_incidence


@pluggable(category="solvers")
def find_neighboring_elements(elements, inflate_by=0.0):
    """Finds neighboring pairs of beams in the given list of beams, using R-tree search.

    The inputs to the R-tree algorithm are the axis-aligned bounding boxes of the beams (beam.aabb), enlarged by the `inflate_by` amount.
    The returned elements are sets containing pairs of Beam objects.

    Parameters
    ----------
    elements : list(:class:`~compas_timber.elements.Beam`)
        The list of beams in which neighboring beams should be identified.
    inflate_by : optional, float
        A value in design units by which the regarded bounding boxes should be inflated.

    Returns
    -------
    list(set(:class:`~compas_timber.elements.Beam`, :class:`~compas_timber.elements.Beam`))

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


def _beam_ref_side_index(this_beam, other_beam):
    """Index of `this_beam`'s ref side that faces `other_beam`, or ``None`` if not computable (e.g. parallel beams)."""
    # TODO: move to beam method or connections.utilities.py or make public.
    try:
        ref_side_angles = beam_ref_side_incidence(other_beam, this_beam, ignore_ends=True)
    except ValueError:
        return None
    return min(ref_side_angles, key=ref_side_angles.get)


def _beam_location_parameter(beam, point):
    # TODO: make this a beam method, e.g. `beam.location_parameter(point)`
    """Absolute distance, in model units, from `beam.centerline.start` to `point` along the centerline.

    `point` is expected to already lie on the centerline (e.g. a closest-point or endpoint result).
    """
    return distance_point_point(beam.centerline.start, point)


class ConnectionSolver(object):
    """Provides tools for detecting beam intersections and joint topologies."""

    TOLERANCE = 1e-6

    @classmethod
    def find_intersecting_pairs(cls, beams, rtree=False, max_distance=0.0):
        """Generates candidate pairs of beams for topology checking.

        This method does not test for intersection. When `rtree` is True, candidates are pairs of beams
        whose axis-aligned bounding boxes overlap; when False, all possible pairs are returned and the
        geometry is not consulted.

        Parameters
        ----------
        beams : list(:class:`~compas_timber.elements.Beam`)
            A list of beam objects.
        rtree : bool
            When set to True R-tree will be used to search for neighboring beams.
        max_distance : float, optional
            When `rtree` is True, beams whose bounding boxes are up to this distance apart are still
            considered neighboring. Ignored when `rtree` is False.

        Returns
        -------
        iterable
            Candidate pairs of beams. A list of sets of two beams when `rtree` is True, an iterator of
            all possible pairs as tuples otherwise.

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
        :class:`~compas_timber.connections.TopologyData`
            The topology results of the intersection between the two beams.
        """
        # first check if the beams are close enough to be considered intersecting and get the closest points on the segments
        max_distance = max_distance or TOL.absolute  # TODO: change to a unit-sensitive value
        dist, point_a, point_b = distance_segment_segment_points(beam_a.centerline, beam_b.centerline)
        if dist > max_distance:
            return TopologyData(
                JointTopology.TOPO_UNKNOWN,
                element_topo_data={str(beam_a.guid): BeamTopologyData(), str(beam_b.guid): BeamTopologyData()},
            )
        point_a = Point(*point_a)
        point_b = Point(*point_b)

        # see if beams are parallel
        if TOL.is_zero(angle_vectors(beam_a.centerline.direction, beam_b.centerline.direction) % math.pi):
            # beams are parallel
            # if parallel overlap on beam_a means that beam_b is overlapped by beam_a. Only need to perform the check on beam_a
            overlap_on_a = get_segment_overlap(beam_a.centerline, beam_b.centerline)
            if overlap_on_a is None:
                end_a, _ = beam_a.endpoint_closest_to_point(point_a)
                end_b, _ = beam_b.endpoint_closest_to_point(point_b)
                beam_a_data = BeamTopologyData(role="main", end=end_a, location_parameter=_beam_location_parameter(beam_a, point_a))
                beam_b_data = BeamTopologyData(role="main", end=end_b, location_parameter=_beam_location_parameter(beam_b, point_b))
                return TopologyData(
                    JointTopology.TOPO_I,
                    distance=dist,
                    location=(point_a + point_b) / 2.0,
                    element_topo_data={
                        str(beam_a.guid): beam_a_data,
                        str(beam_b.guid): beam_b_data,
                    },
                )
            if overlap_on_a[1] < max_distance:  # overlaps on beam_a start
                pt = beam_b.endpoint_closest_to_point(beam_a.centerline.start)[1]
                end_b, _ = beam_b.endpoint_closest_to_point(beam_a.centerline.start)
                dist = distance_point_point(pt, beam_a.centerline.start)
                beam_a_data = BeamTopologyData(role="main", end="start", location_parameter=0.0)
                beam_b_data = BeamTopologyData(role="main", end=end_b, location_parameter=_beam_location_parameter(beam_b, pt))
                return TopologyData(
                    JointTopology.TOPO_I,
                    distance=dist,
                    location=(beam_a.centerline.start + pt) / 2.0,
                    element_topo_data={
                        str(beam_a.guid): beam_a_data,
                        str(beam_b.guid): beam_b_data,
                    },
                )
            if abs(overlap_on_a[0] - beam_a.length) < max_distance:  # overlaps on beam_a end
                pt = beam_b.endpoint_closest_to_point(beam_a.centerline.end)[1]
                end_b, _ = beam_b.endpoint_closest_to_point(beam_a.centerline.end)
                dist = distance_point_point(pt, beam_a.centerline.end)
                beam_a_data = BeamTopologyData(role="main", end="end", location_parameter=beam_a.length)
                beam_b_data = BeamTopologyData(role="main", end=end_b, location_parameter=_beam_location_parameter(beam_b, pt))
                return TopologyData(
                    JointTopology.TOPO_I,
                    distance=dist,
                    location=(beam_a.centerline.end + pt) / 2.0,
                    element_topo_data={
                        str(beam_a.guid): beam_a_data,
                        str(beam_b.guid): beam_b_data,
                    },
                )
            else:
                return TopologyData(
                    JointTopology.TOPO_UNKNOWN,
                    element_topo_data={str(beam_a.guid): BeamTopologyData(), str(beam_b.guid): BeamTopologyData()},
                )

        a_end_label, a_end_pt = beam_a.endpoint_closest_to_point(point_b)
        b_end_label, b_end_pt = beam_b.endpoint_closest_to_point(point_a)

        a_end = distance_point_point(a_end_pt, point_a) < max_distance
        b_end = distance_point_point(b_end_pt, point_b) < max_distance
        location = (point_a + point_b) / 2.0
        ref_side_index_a = _beam_ref_side_index(beam_a, beam_b)
        ref_side_index_b = _beam_ref_side_index(beam_b, beam_a)
        beam_a_data = BeamTopologyData(role="main", end=a_end_label, ref_side_index=ref_side_index_a, location_parameter=_beam_location_parameter(beam_a, point_a))
        beam_b_data = BeamTopologyData(role="main", end=b_end_label, ref_side_index=ref_side_index_b, location_parameter=_beam_location_parameter(beam_b, point_b))
        if a_end and b_end:
            return TopologyData(
                JointTopology.TOPO_L,
                distance=dist,
                location=location,
                element_topo_data={
                    str(beam_a.guid): beam_a_data,
                    str(beam_b.guid): beam_b_data,
                },
            )
        if a_end:
            beam_a_data = BeamTopologyData(role="main", end=a_end_label, ref_side_index=ref_side_index_a, location_parameter=_beam_location_parameter(beam_a, point_a))
            beam_b_data = BeamTopologyData(role="cross", ref_side_index=ref_side_index_b, location_parameter=_beam_location_parameter(beam_b, point_b))
            return TopologyData(
                JointTopology.TOPO_T,
                distance=dist,
                location=location,
                element_topo_data={
                    str(beam_a.guid): beam_a_data,
                    str(beam_b.guid): beam_b_data,
                },
            )
        if b_end:
            beam_a_data = BeamTopologyData(role="cross", ref_side_index=ref_side_index_a, location_parameter=_beam_location_parameter(beam_a, point_a))
            beam_b_data = BeamTopologyData(role="main", end=b_end_label, ref_side_index=ref_side_index_b, location_parameter=_beam_location_parameter(beam_b, point_b))
            return TopologyData(
                JointTopology.TOPO_T,
                distance=dist,
                location=location,
                element_topo_data={
                    str(beam_b.guid): beam_b_data,
                    str(beam_a.guid): beam_a_data,
                },
            )

        beam_a_data = BeamTopologyData(role="cross", ref_side_index=ref_side_index_a, location_parameter=_beam_location_parameter(beam_a, point_a))
        beam_b_data = BeamTopologyData(role="cross", ref_side_index=ref_side_index_b, location_parameter=_beam_location_parameter(beam_b, point_b))
        return TopologyData(
            JointTopology.TOPO_X,
            distance=dist,
            location=location,
            element_topo_data={
                str(beam_a.guid): beam_a_data,
                str(beam_b.guid): beam_b_data,
            },
        )


class PlateConnectionSolver(ConnectionSolver):
    """Provides tools for detecting plate intersections and joint topologies."""

    TOLERANCE = 1e-6

    def find_topology(self, plate_a, plate_b, max_distance=TOLERANCE, tol=TOLERANCE):
        """Calculates the topology of the intersection between two plates. requires that one edge of a plate lies on the plane of the other plate.
        When TOPOLOGY_EDGE_FACE is found, the plates are returned in reverse order, with the main plate first and the cross plate second.

        Parameters
        ----------
        plate_a : :class:`~compas_timber.elements.Plate`
            First potential intersecting plate.
        plate_b : :class:`~compas_timber.elements.Plate`
            Second potential intersecting plate.
        tol : float
            General tolerance to use for mathematical computations.
        max_distance : float, optional
            Maximum distance, in design units, at which two plates are considered intersecting.

        Returns
        -------
        :class:`~compas_timber.connections.TopologyData`
            The topology results of the intersection between the two plates.

        """
        plate_a_segment_index, plate_b_segment_index, dist, pt = self._find_plate_segment_indices(plate_a, plate_b, max_distance=max_distance, tol=tol)
        if plate_a_segment_index is None and plate_b_segment_index is None:
            return TopologyData(
                JointTopology.TOPO_UNKNOWN,
                distance=dist,
                location=pt,
                element_topo_data={str(plate_a.guid): PlateTopologyData(), str(plate_b.guid): PlateTopologyData()},
            )
        if plate_a_segment_index is not None and plate_b_segment_index is None:
            plate_a_data = PlateTopologyData(role="edge", edge_index=plate_a_segment_index, location=pt)
            plate_b_data = PlateTopologyData(role="face", location=pt)
            return TopologyData(
                JointTopology.TOPO_EDGE_FACE,
                distance=dist,
                location=pt,
                element_topo_data={
                    str(plate_a.guid): plate_a_data,
                    str(plate_b.guid): plate_b_data,
                },
            )
        if plate_a_segment_index is None and plate_b_segment_index is not None:
            plate_a_data = PlateTopologyData(role="face", location=pt)
            plate_b_data = PlateTopologyData(role="edge", edge_index=plate_b_segment_index, location=pt)
            return TopologyData(
                JointTopology.TOPO_EDGE_FACE,
                distance=dist,
                location=pt,
                element_topo_data={
                    str(plate_b.guid): plate_b_data,
                    str(plate_a.guid): plate_a_data,
                },
            )
        if plate_a_segment_index is not None and plate_b_segment_index is not None:
            plate_a_data = PlateTopologyData(role="edge", edge_index=plate_a_segment_index, location=pt)
            plate_b_data = PlateTopologyData(role="edge", edge_index=plate_b_segment_index, location=pt)
            return TopologyData(
                JointTopology.TOPO_EDGE_EDGE,
                distance=dist,
                location=pt,
                element_topo_data={
                    str(plate_a.guid): plate_a_data,
                    str(plate_b.guid): plate_b_data,
                },
            )

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
        segment_a : :class:`~compas.geometry.Segment`
            The first segment.
        segment_b : :class:`~compas.geometry.Segment`
            The second segment.

        Returns
        -------
        bool
            True if the segments overlap, False otherwise.
        """
        # TODO: move to compas.geometry and add unit tests
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
        # TODO: move to compas.geometry and add unit tests
        if intersection_segment_polyline(segment, polyline, tol.absolute)[0]:
            return True
        return is_point_in_polyline(segment.point_at(0.5), polyline, in_plane=False, tol=tol)

