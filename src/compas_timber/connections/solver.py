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

from compas_timber.geometry import get_segment_range_on_polyline
from compas_timber.utils import distance_segment_segment_points
from compas_timber.utils import get_segment_overlap
from compas_timber.utils import is_point_in_polyline

from .topology_info import BeamTopologyInfo
from .topology_info import PlateTopologyInfo
from .topology_info import TopologyInfo
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
        :class:`~compas_timber.connections.TopologyInfo`
            The topology results of the intersection between the two beams.
        """
        # first check if the beams are close enough to be considered intersecting and get the closest points on the segments
        max_distance = max_distance or TOL.absolute  # TODO: change to a unit-sensitive value
        dist, point_a, point_b = distance_segment_segment_points(beam_a.centerline, beam_b.centerline)
        if dist > max_distance:
            return TopologyInfo(
                JointTopology.TOPO_UNKNOWN,
                element_topo_info={str(beam_a.guid): BeamTopologyInfo(), str(beam_b.guid): BeamTopologyInfo()},
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
                beam_a_info = BeamTopologyInfo(role="main", end=end_a, location_parameter=_beam_location_parameter(beam_a, point_a))
                beam_b_info = BeamTopologyInfo(role="main", end=end_b, location_parameter=_beam_location_parameter(beam_b, point_b))
                return TopologyInfo(
                    JointTopology.TOPO_I,
                    distance=dist,
                    location=(point_a + point_b) / 2.0,
                    element_topo_info={
                        str(beam_a.guid): beam_a_info,
                        str(beam_b.guid): beam_b_info,
                    },
                )
            if overlap_on_a[1] < max_distance:  # overlaps on beam_a start
                pt = beam_b.endpoint_closest_to_point(beam_a.centerline.start)[1]
                end_b, _ = beam_b.endpoint_closest_to_point(beam_a.centerline.start)
                dist = distance_point_point(pt, beam_a.centerline.start)
                beam_a_info = BeamTopologyInfo(role="main", end="start", location_parameter=0.0)
                beam_b_info = BeamTopologyInfo(role="main", end=end_b, location_parameter=_beam_location_parameter(beam_b, pt))
                return TopologyInfo(
                    JointTopology.TOPO_I,
                    distance=dist,
                    location=(beam_a.centerline.start + pt) / 2.0,
                    element_topo_info={
                        str(beam_a.guid): beam_a_info,
                        str(beam_b.guid): beam_b_info,
                    },
                )
            if abs(overlap_on_a[0] - beam_a.length) < max_distance:  # overlaps on beam_a end
                pt = beam_b.endpoint_closest_to_point(beam_a.centerline.end)[1]
                end_b, _ = beam_b.endpoint_closest_to_point(beam_a.centerline.end)
                dist = distance_point_point(pt, beam_a.centerline.end)
                beam_a_info = BeamTopologyInfo(role="main", end="end", location_parameter=beam_a.length)
                beam_b_info = BeamTopologyInfo(role="main", end=end_b, location_parameter=_beam_location_parameter(beam_b, pt))
                return TopologyInfo(
                    JointTopology.TOPO_I,
                    distance=dist,
                    location=(beam_a.centerline.end + pt) / 2.0,
                    element_topo_info={
                        str(beam_a.guid): beam_a_info,
                        str(beam_b.guid): beam_b_info,
                    },
                )
            else:
                return TopologyInfo(
                    JointTopology.TOPO_UNKNOWN,
                    element_topo_info={str(beam_a.guid): BeamTopologyInfo(), str(beam_b.guid): BeamTopologyInfo()},
                )

        a_end_label, a_end_pt = beam_a.endpoint_closest_to_point(point_b)
        b_end_label, b_end_pt = beam_b.endpoint_closest_to_point(point_a)

        a_end = distance_point_point(a_end_pt, point_a) < max_distance
        b_end = distance_point_point(b_end_pt, point_b) < max_distance
        location = (point_a + point_b) / 2.0
        ref_side_index_a = _beam_ref_side_index(beam_a, beam_b)
        ref_side_index_b = _beam_ref_side_index(beam_b, beam_a)
        beam_a_info = BeamTopologyInfo(role="main", end=a_end_label, ref_side_index=ref_side_index_a, location_parameter=_beam_location_parameter(beam_a, point_a))
        beam_b_info = BeamTopologyInfo(role="main", end=b_end_label, ref_side_index=ref_side_index_b, location_parameter=_beam_location_parameter(beam_b, point_b))
        if a_end and b_end:
            return TopologyInfo(
                JointTopology.TOPO_L,
                distance=dist,
                location=location,
                element_topo_info={
                    str(beam_a.guid): beam_a_info,
                    str(beam_b.guid): beam_b_info,
                },
            )
        if a_end:
            beam_a_info = BeamTopologyInfo(role="main", end=a_end_label, ref_side_index=ref_side_index_a, location_parameter=_beam_location_parameter(beam_a, point_a))
            beam_b_info = BeamTopologyInfo(role="cross", ref_side_index=ref_side_index_b, location_parameter=_beam_location_parameter(beam_b, point_b))
            return TopologyInfo(
                JointTopology.TOPO_T,
                distance=dist,
                location=location,
                element_topo_info={
                    str(beam_a.guid): beam_a_info,
                    str(beam_b.guid): beam_b_info,
                },
            )
        if b_end:
            beam_a_info = BeamTopologyInfo(role="cross", ref_side_index=ref_side_index_a, location_parameter=_beam_location_parameter(beam_a, point_a))
            beam_b_info = BeamTopologyInfo(role="main", end=b_end_label, ref_side_index=ref_side_index_b, location_parameter=_beam_location_parameter(beam_b, point_b))
            return TopologyInfo(
                JointTopology.TOPO_T,
                distance=dist,
                location=location,
                element_topo_info={
                    str(beam_a.guid): beam_a_info,
                    str(beam_b.guid): beam_b_info,
                },
            )

        beam_a_info = BeamTopologyInfo(role="cross", ref_side_index=ref_side_index_a, location_parameter=_beam_location_parameter(beam_a, point_a))
        beam_b_info = BeamTopologyInfo(role="cross", ref_side_index=ref_side_index_b, location_parameter=_beam_location_parameter(beam_b, point_b))
        return TopologyInfo(
            JointTopology.TOPO_X,
            distance=dist,
            location=location,
            element_topo_info={
                str(beam_a.guid): beam_a_info,
                str(beam_b.guid): beam_b_info,
            },
        )

    def update_location(self, beam_a, beam_b, topology_info):
        """Recomputes the location of an existing connection between `beam_a` and `beam_b` from their current geometry.

        The location is the midpoint between the closest points of the two centerlines, the same
        definition used by :meth:`find_topology`. Only the location info of `topology_info` is
        updated in place, i.e. `TopologyInfo.location` and the `location_parameter` of each beam's
        `BeamTopologyInfo`. The topology type, roles, ends and reference side indices are left
        untouched, as is `TopologyInfo.distance`.

        Parameters
        ----------
        beam_a : :class:`~compas_timber.elements.Beam`
            First beam of the connection.
        beam_b : :class:`~compas_timber.elements.Beam`
            Second beam of the connection.
        topology_info : :class:`~compas_timber.connections.TopologyInfo`
            The topology info to update. Must contain entries for both beams.

        Returns
        -------
        :class:`~compas.geometry.Point`
            The updated location.

        Raises
        ------
        ValueError
            If `topology_info` does not contain an entry for both beams.

        """
        info_a = topology_info.info_for(beam_a)
        info_b = topology_info.info_for(beam_b)
        if info_a is None or info_b is None:
            raise ValueError("Both beams must be present in the given topology info.")

        _, point_a, point_b = distance_segment_segment_points(beam_a.centerline, beam_b.centerline)
        point_a = Point(*point_a)
        point_b = Point(*point_b)

        info_a.location_parameter = _beam_location_parameter(beam_a, point_a)
        info_b.location_parameter = _beam_location_parameter(beam_b, point_b)
        topology_info.location = (point_a + point_b) / 2.0
        return topology_info.location


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
        :class:`~compas_timber.connections.TopologyInfo`
            The topology results of the intersection between the two plates.

        """
        plate_a_edge, plate_b_edge, dist, loc_a, loc_b = self._find_plate_segment_indices(plate_a, plate_b, max_distance=max_distance, tol=tol)
        a_ref_side_index, a_segment_index = plate_a_edge if plate_a_edge else (None, None)
        b_ref_side_index, b_segment_index = plate_b_edge if plate_b_edge else (None, None)
        location = self._joint_location(loc_a, loc_b)
        if a_segment_index is None and b_segment_index is None:
            return TopologyInfo(
                JointTopology.TOPO_UNKNOWN,
                distance=dist,
                location=location,
                element_topo_info={str(plate_a.guid): PlateTopologyInfo(), str(plate_b.guid): PlateTopologyInfo()},
            )
        if a_segment_index is not None and b_segment_index is None:
            plate_a_info = PlateTopologyInfo(role="edge", edge_index=a_segment_index, ref_side_index=a_ref_side_index, location=loc_a)
            plate_b_info = PlateTopologyInfo(role="face", ref_side_index=b_ref_side_index, location=loc_b)
            return TopologyInfo(
                JointTopology.TOPO_EDGE_FACE,
                distance=dist,
                location=location,
                element_topo_info={
                    str(plate_a.guid): plate_a_info,
                    str(plate_b.guid): plate_b_info,
                },
            )
        if a_segment_index is None and b_segment_index is not None:
            plate_a_info = PlateTopologyInfo(role="face", ref_side_index=a_ref_side_index, location=loc_a)
            plate_b_info = PlateTopologyInfo(role="edge", edge_index=b_segment_index, ref_side_index=b_ref_side_index, location=loc_b)
            return TopologyInfo(
                JointTopology.TOPO_EDGE_FACE,
                distance=dist,
                location=location,
                element_topo_info={
                    str(plate_a.guid): plate_a_info,
                    str(plate_b.guid): plate_b_info,
                },
            )
        if a_segment_index is not None and b_segment_index is not None:
            plate_a_info = PlateTopologyInfo(role="edge", edge_index=a_segment_index, ref_side_index=a_ref_side_index, location=loc_a)
            plate_b_info = PlateTopologyInfo(role="edge", edge_index=b_segment_index, ref_side_index=b_ref_side_index, location=loc_b)
            return TopologyInfo(
                JointTopology.TOPO_EDGE_EDGE,
                distance=dist,
                location=location,
                element_topo_info={
                    str(plate_a.guid): plate_a_info,
                    str(plate_b.guid): plate_b_info,
                },
            )

    def update_location(self, plate_a, plate_b, topology_info):
        """Recomputes the location of an existing connection between `plate_a` and `plate_b` from their current geometry.

        The connecting edges are not searched for again: they are looked up from the `ref_side_index`
        and `edge_index` already stored in `topology_info`, and only the location along them is solved
        anew, using the same definition as :meth:`find_topology`: each plate's `location` is the
        midpoint of the overlap of the two edges measured on its own edge for `TOPO_EDGE_EDGE`, and the
        midpoint of the portion of the edge that lies on the cross plate's outline, measured on the edge
        and on the cross plate's face respectively, for `TOPO_EDGE_FACE`. `TopologyInfo.location` is the
        midpoint of the two per-plate locations. These are updated in place; topology type, roles and indices are left untouched,
        as is `TopologyInfo.distance`.

        Parameters
        ----------
        plate_a : :class:`~compas_timber.elements.Plate`
            First plate of the connection.
        plate_b : :class:`~compas_timber.elements.Plate`
            Second plate of the connection.
        topology_info : :class:`~compas_timber.connections.TopologyInfo`
            The topology info to update. Must contain entries for both plates.

        Returns
        -------
        :class:`~compas.geometry.Point` or None
            The updated location, or ``None`` if the topology is unknown or the stored edges no longer
            overlap, in which case `topology_info` is left unchanged.

        Raises
        ------
        ValueError
            If `topology_info` does not contain an entry for both plates.

        """
        info_a = topology_info.info_for(plate_a)
        info_b = topology_info.info_for(plate_b)
        if info_a is None or info_b is None:
            raise ValueError("Both plates must be present in the given topology info.")

        if topology_info.topology == JointTopology.TOPO_EDGE_EDGE:
            locations = self._edge_edge_locations(self._plate_edge_segment(plate_a, info_a), self._plate_edge_segment(plate_b, info_b))
            if locations is None:
                return None
            loc_a, loc_b = locations
        elif topology_info.topology == JointTopology.TOPO_EDGE_FACE:
            if info_a.role == "edge":
                main_plate, main_info, cross_plate, cross_info = plate_a, info_a, plate_b, info_b
            else:
                main_plate, main_info, cross_plate, cross_info = plate_b, info_b, plate_a, info_a
            locations = self._edge_face_locations(
                self._plate_edge_segment(main_plate, main_info),
                cross_plate.outlines[cross_info.ref_side_index],
                cross_plate.planes[cross_info.ref_side_index],
            )
            if locations is None:
                return None
            main_location, cross_location = locations
            loc_a, loc_b = (main_location, cross_location) if main_plate is plate_a else (cross_location, main_location)
        else:
            return None

        info_a.location = loc_a
        info_b.location = loc_b
        topology_info.location = self._joint_location(loc_a, loc_b)
        return topology_info.location

    @staticmethod
    def _joint_location(loc_a, loc_b):
        """The location of the connection as a whole: the midpoint of the two per-plate locations."""
        if loc_a is None or loc_b is None:
            return None
        return (loc_a + loc_b) / 2.0

    @staticmethod
    def _plate_edge_segment(plate, plate_topo_info):
        """The outline segment of `plate` that takes part in the connection described by `plate_topo_info`."""
        return plate.outlines[plate_topo_info.ref_side_index].lines[plate_topo_info.edge_index]

    @staticmethod
    def _edge_edge_locations(seg_a, seg_b):
        """Per-plate locations of an edge-edge connection: the midpoint of the overlap of the two
        colinear edges, measured on each edge. ``None`` if they no longer overlap.

        Returns
        -------
        tuple(:class:`~compas.geometry.Point`, :class:`~compas.geometry.Point`) or None
            The location on `seg_a` and the location on `seg_b`.

        """
        overlap_a = get_segment_overlap(seg_a, seg_b, unitize=True)
        overlap_b = get_segment_overlap(seg_b, seg_a, unitize=True)
        if overlap_a is None or overlap_b is None:
            return None
        return seg_a.point_at(sum(overlap_a) / 2.0), seg_b.point_at(sum(overlap_b) / 2.0)

    @staticmethod
    def _edge_face_locations(segment, outline, plane, tol=TOL.absolute):
        """Per-plate locations of an edge-face connection: the midpoint of the portion of the edge
        `segment` that lies on the face `outline`, measured on the face (`segment` projected onto
        `plane`, the plane of `outline`) and on the edge itself. ``None`` if there is no overlap.

        Returns
        -------
        tuple(:class:`~compas.geometry.Point`, :class:`~compas.geometry.Point`) or None
            The location on the edge plate and the location on the face plate.

        """
        projected = Line(plane.projected_point(segment.start), plane.projected_point(segment.end))
        pts = get_segment_range_on_polyline(projected, outline, tol)
        if pts is None:
            return None
        face_location = (pts[0] + pts[1]) / 2.0
        edge_location = Point(*segment.closest_point(face_location))
        return edge_location, face_location

    @staticmethod
    def _find_plate_segment_indices(plate_a, plate_b, max_distance=None, tol=TOL):
        """Finds the connecting edges of `plate_a` and `plate_b`. used to determine connection Topology.

        Returns
        -------
        tuple(tuple(int, int) or None, tuple(int, int) or None, float or None, :class:`~compas.geometry.Point` or None, :class:`~compas.geometry.Point` or None)
            For each plate a `(ref_side_index, edge_index)` pair, where `edge_index` is ``None`` for the
            face side of an edge-face connection, followed by the distance between the plates and the
            location of the connection on `plate_a` and on `plate_b`. All ``None`` when the plates do not connect.

        """

        edge_a, edge_b, dist, locations = PlateConnectionSolver._get_l_topo_segment_indices(plate_a, plate_b, max_distance=max_distance, tol=tol)
        if edge_a is not None:
            loc_a, loc_b = locations or (None, None)
            return edge_a, edge_b, dist, loc_a, loc_b
        edge_a, ref_side_b, dist, locations = PlateConnectionSolver._get_t_topo_segment_index(plate_a, plate_b, max_distance=max_distance, tol=tol)
        if edge_a is not None:
            loc_a, loc_b = locations or (None, None)
            return edge_a, (ref_side_b, None), dist, loc_a, loc_b
        edge_b, ref_side_a, dist, locations = PlateConnectionSolver._get_t_topo_segment_index(plate_b, plate_a, max_distance=max_distance, tol=tol)
        if edge_b is not None:
            loc_b, loc_a = locations or (None, None)
            return (ref_side_a, None), edge_b, dist, loc_a, loc_b
        return None, None, None, None, None

    @staticmethod
    def _get_l_topo_segment_indices(plate_a, plate_b, max_distance=None, tol=TOL):
        """Finds the outline segments of `plate_a` and `plate_b` that are colinear.
        Used to find segments that join in L_TOPO Topology.

        Returns
        -------
        tuple(tuple(int, int) or None, tuple(int, int) or None, float or None, tuple(:class:`~compas.geometry.Point`, :class:`~compas.geometry.Point`) or None)
            A `(ref_side_index, edge_index)` pair per plate, the distance between the segments and the
            location of the connection on `plate_a` and on `plate_b`. All ``None`` when no colinear
            overlapping pair is found.

        """

        if max_distance is None:
            max_distance = max(plate_a.thickness, plate_b.thickness)
        for (ref_side_a, pline_a), (ref_side_b, pline_b) in itertools.product(enumerate(plate_a.outlines), enumerate(plate_b.outlines)):
            for i, seg_a in enumerate(pline_a.lines):
                for j, seg_b in enumerate(pline_b.lines):  # TODO: use rtree?
                    seg_a_midpt = seg_a.point_at(0.5)
                    dist = distance_point_line(seg_a_midpt, seg_b)
                    if dist <= max_distance:
                        if is_parallel_line_line(seg_a, seg_b, tol=tol):
                            if PlateConnectionSolver.do_segments_overlap(seg_a, seg_b):
                                locations = PlateConnectionSolver._edge_edge_locations(seg_a, seg_b)
                                return (ref_side_a, i), (ref_side_b, j), dist, locations
        return None, None, None, None

    @staticmethod
    def _get_t_topo_segment_index(main_plate, cross_plate, max_distance=None, tol=TOL):
        """Finds the outline segment of `main_plate` that lies on an outline of `cross_plate`.
        Used to find segments that join in T_TOPO Topology.

        Returns
        -------
        tuple(tuple(int, int) or None, int or None, float or None, tuple(:class:`~compas.geometry.Point`, :class:`~compas.geometry.Point`) or None)
            The `(ref_side_index, edge_index)` pair of the main plate's connecting edge, the reference
            side index of the cross plate it lands on, the distance between the two, and the location of
            the connection on `main_plate` and on `cross_plate`. All ``None`` when no such segment is found.

        """

        if max_distance is None:
            max_distance = min(main_plate.thickness, cross_plate.thickness)
        for ref_side_a, (pline_a, plane_a) in enumerate(zip(main_plate.outlines, main_plate.planes)):
            for ref_side_b, (pline_b, plane_b) in enumerate(zip(cross_plate.outlines, cross_plate.planes)):
                line = Line(*intersection_plane_plane(plane_a, plane_b))
                for i, seg_a in enumerate(pline_a.lines):  # TODO: use rtree?
                    seg_a_midpt = seg_a.point_at(0.5)
                    dist = distance_point_line(seg_a_midpt, line)
                    if dist <= max_distance:
                        if is_parallel_line_line(seg_a, line, tol=tol):
                            if PlateConnectionSolver.does_segment_intersect_outline(seg_a, pline_b):
                                locations = PlateConnectionSolver._edge_face_locations(seg_a, pline_b, plane_b)
                                return (ref_side_a, i), ref_side_b, dist, locations
        return None, None, None, None

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
