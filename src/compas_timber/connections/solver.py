import itertools
import math

from compas.data import Data
from compas.geometry import Line
from compas.geometry import Plane
from compas.geometry import Point
from compas.geometry import Polyline
from compas.geometry import Vector
from compas.geometry import angle_vectors
from compas.geometry import distance_point_line
from compas.geometry import distance_point_plane
from compas.geometry import distance_point_point
from compas.geometry import dot_vectors
from compas.geometry import intersection_line_plane
from compas.geometry import intersection_plane_plane
from compas.geometry import is_parallel_line_line
from compas.plugins import pluggable
from compas.tolerance import TOL
from compas.tolerance import Tolerance

from compas_timber.utils import distance_segment_segment_points
from compas_timber.utils import do_segments_overlap
from compas_timber.utils import does_segment_overlap_outline
from compas_timber.utils import get_segment_overlap
from compas_timber.utils import is_point_in_polyline


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
    TOPO_FACE_FACE  - joint between a beam and a plate/panel where a beam face lies flush on a main face of the plate/panel
    TOPO_END_FACE  - joint between a beam and a plate/panel where the beam's end butts into a main face of the plate/panel
    TOPO_END_EDGE  - joint between a beam and a plate/panel where the beam's end meets an edge of the plate/panel
    TOPO_MIDDLE_EDGE  - joint between a beam and a plate/panel where an edge of the plate/panel meets the beam's side, mid-span
    TOPO_THROUGH_FACE  - joint between a beam and a plate/panel where the beam passes through both main faces of the plate/panel
    TOPO_ALONG_EDGE  - joint between a beam and a plate/panel where the beam lies along and parallel to an edge of the plate/panel

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
    TOPO_FACE_FACE = 9
    TOPO_END_FACE = 10
    TOPO_END_EDGE = 11
    TOPO_MIDDLE_EDGE = 12
    TOPO_THROUGH_FACE = 13
    TOPO_ALONG_EDGE = 14

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
            # centerlines are too far apart for I/L/T/X, but the beams might still be flush face-to-face
            # (e.g. sistered/stacked beams), which centerline distance alone can't detect.
            result = self._test_face_face(beam_a, beam_b, max_distance)
            if result is not None:
                distance, location = result
                return BeamSolverResult(JointTopology.TOPO_FACE_FACE, beam_a, beam_b, distance, location)
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

    def _test_face_face(self, beam_a, beam_b, tol):
        """Checks whether a long face of `beam_a` lies coplanar, anti-parallel, and overlapping with a long face of `beam_b`."""
        for i in range(4):
            face_a = beam_a.ref_sides[i]
            corners_a = self._surface_corners(beam_a.side_as_surface(i))
            for j in range(4):
                face_b = beam_b.ref_sides[j]
                if dot_vectors(face_a.zaxis, face_b.zaxis) > -1 + tol:
                    continue  # not anti-parallel
                distance = dot_vectors(Vector.from_start_end(face_b.point, face_a.point), face_b.zaxis)
                if abs(distance) > tol:
                    continue  # not coplanar
                corners_b = self._surface_corners(beam_b.side_as_surface(j))
                outline_b = Polyline(corners_b + [corners_b[0]])
                if self._rectangle_overlaps_outline(corners_a, outline_b, tol):
                    centroid = Point(*[sum(c[axis] for c in corners_a) / 4.0 for axis in range(3)])
                    return distance, centroid
        return None

    @staticmethod
    def _surface_corners(surface):
        """Returns the 4 corner points of a `PlanarSurface`, in order."""
        frame = surface.frame
        x, y = surface.xsize, surface.ysize
        return [
            frame.point,
            frame.point + frame.xaxis * x,
            frame.point + frame.xaxis * x + frame.yaxis * y,
            frame.point + frame.yaxis * y,
        ]

    @staticmethod
    def _rectangle_overlaps_outline(corners, outline, tol):
        """Checks whether a coplanar rectangle (given by its 4 `corners`) overlaps `outline` (partial overlap counts)."""
        tol_obj = Tolerance(absolute=tol)
        for i in range(4):
            edge = Line(corners[i], corners[(i + 1) % 4])
            if does_segment_overlap_outline(edge, outline, tol=tol_obj):
                return True
        return False


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
                            if do_segments_overlap(seg_a, seg_b):
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
                            if does_segment_overlap_outline(seg_a, pline_b):
                                return i, dist, seg_a_midpt
        return None, None, None


class BeamPlateConnectionSolver(ConnectionSolver):
    """Provides tools for detecting beam-to-plate/panel intersections and joint topologies.

    Classifies a beam/plate (or beam/panel) pair into one of six topologies (`TOPO_FACE_FACE`,
    `TOPO_END_FACE`, `TOPO_END_EDGE`, `TOPO_MIDDLE_EDGE`, `TOPO_THROUGH_FACE`, `TOPO_ALONG_EDGE`) by
    first classifying the beam centerline's two endpoints against the plate's main-face depth range,
    then resolving the remaining ambiguity with a small set of per-segment geometric tests. Edge-related
    topologies are always attempted before face-related ones; the first matching plate outline segment
    wins.

    """

    TOLERANCE = 1e-6

    def find_topology(self, beam, plate, max_distance=None, tol=None):
        """Classifies the topology of the intersection between a beam and a plate/panel.

        Parameters
        ----------
        beam : :class:`~compas_timber.elements.Beam`
            The beam to test.
        plate : :class:`~compas_timber.elements.Plate` or :class:`~compas_timber.elements.Panel`
            The plate or panel to test.
        max_distance : float, optional
            Maximum distance, in design units, at which the beam and plate/panel are considered intersecting.
        tol : float, optional
            General tolerance used for the underlying geometric checks.

        Returns
        -------
        :class:`~compas_timber.connections.BeamPlateSolverResult`

        """
        max_distance = max_distance if max_distance is not None else self.TOLERANCE
        tol = tol if tol is not None else self.TOLERANCE

        centerline = beam.centerline
        thickness = plate.thickness
        depth_start = self._endpoint_depth(centerline.start, plate)
        depth_end = self._endpoint_depth(centerline.end, plate)
        side_start = self._classify_depth(depth_start, thickness, max_distance)
        side_end = self._classify_depth(depth_end, thickness, max_distance)

        if side_start != 0 and side_end != 0:
            if side_start == side_end:
                # both endpoints on the same side: beam-face possibly flush against a main face
                result = self._test_face_face(beam, plate, tol)
                if result is not None:
                    distance, location = result
                    return BeamPlateSolverResult(JointTopology.TOPO_FACE_FACE, beam, plate, distance=distance, location=location)
                return BeamPlateSolverResult(JointTopology.TOPO_UNKNOWN, beam, plate)

            # endpoints on opposite sides: beam crosses the slab's depth range somewhere along its length
            n_segments = len(plate.outline_a.points) - 1
            for i in range(n_segments):
                result = self._test_middle_edge(beam, plate, i, tol)
                if result is not None:
                    distance, location = result
                    return BeamPlateSolverResult(JointTopology.TOPO_MIDDLE_EDGE, beam, plate, segment_index=i, distance=distance, location=location)
            result = self._test_through_face(beam, plate, tol)
            if result is not None:
                distance, location = result
                return BeamPlateSolverResult(JointTopology.TOPO_THROUGH_FACE, beam, plate, distance=distance, location=location)
            return BeamPlateSolverResult(JointTopology.TOPO_UNKNOWN, beam, plate)

        if side_start == 0 and side_end == 0:
            # both endpoints within the slab's depth range: try ALONG_EDGE first (both endpoints
            # close to the same segment's edge plane).
            n_segments = len(plate.outline_a.points) - 1
            for i in range(n_segments):
                edge_plane = plate.edge_planes[i]
                d_start = distance_point_plane(centerline.start, edge_plane)
                d_end = distance_point_plane(centerline.end, edge_plane)
                if d_start <= tol and d_end <= tol:
                    result = self._test_along_edge(beam, plate, i, tol)
                    if result is not None:
                        distance, location = result
                        return BeamPlateSolverResult(JointTopology.TOPO_ALONG_EDGE, beam, plate, segment_index=i, distance=distance, location=location)

            # otherwise, END_EDGE requires exactly one endpoint to land in an edge quad, and the
            # other to land in none — if each endpoint hits a (possibly different) edge, the beam
            # doesn't have a single, unambiguous edge relationship.
            start_match = None
            end_match = None
            for i in range(n_segments):
                if start_match is None:
                    start_match = self._test_end_edge_at_point(centerline.start, plate, i, tol)
                    if start_match is not None:
                        start_match = (i,) + start_match
                if end_match is None:
                    end_match = self._test_end_edge_at_point(centerline.end, plate, i, tol)
                    if end_match is not None:
                        end_match = (i,) + end_match
                if start_match is not None and end_match is not None:
                    break

            if start_match is not None and end_match is None:
                i, distance, location = start_match
                return BeamPlateSolverResult(JointTopology.TOPO_END_EDGE, beam, plate, segment_index=i, distance=distance, location=location)
            if end_match is not None and start_match is None:
                i, distance, location = end_match
                return BeamPlateSolverResult(JointTopology.TOPO_END_EDGE, beam, plate, segment_index=i, distance=distance, location=location)
            return BeamPlateSolverResult(JointTopology.TOPO_UNKNOWN, beam, plate)

        # asymmetric: exactly one endpoint is within the slab's depth range
        between_point = centerline.start if side_start == 0 else centerline.end
        n_segments = len(plate.outline_a.points) - 1
        for i in range(n_segments):
            result = self._test_end_edge_at_point(between_point, plate, i, tol)
            if result is not None:
                distance, location = result
                return BeamPlateSolverResult(JointTopology.TOPO_END_EDGE, beam, plate, segment_index=i, distance=distance, location=location)
        result = self._test_end_face(between_point, plate, tol)
        if result is not None:
            distance, location = result
            return BeamPlateSolverResult(JointTopology.TOPO_END_FACE, beam, plate, distance=distance, location=location)
        return BeamPlateSolverResult(JointTopology.TOPO_UNKNOWN, beam, plate)

    # ------------------------------------------------------------------
    # shared geometric primitives
    # ------------------------------------------------------------------

    @staticmethod
    def _endpoint_depth(point, plate):
        """Signed depth of `point` along the plate's main-face axis: 0 at `ref_sides[0]`, `thickness` at `ref_sides[2]`."""
        ref = plate.ref_sides[0]
        axis = ref.zaxis * -1
        return dot_vectors(Vector.from_start_end(ref.point, point), axis)

    @staticmethod
    def _classify_depth(depth, thickness, tol):
        """Classifies a depth value as below (-1), within (0), or above (1) the plate's main-face range."""
        if depth < -tol:
            return -1
        if depth > thickness + tol:
            return 1
        return 0

    @staticmethod
    def _edge_quad(plate, i):
        """Returns the closed, planar quad spanning outline segment `i`'s full length and thickness."""
        oa = plate.outline_a.points
        ob = plate.outline_b.points
        return Polyline([oa[i], oa[i + 1], ob[i + 1], ob[i], oa[i]])

    # `_surface_corners` and `_rectangle_overlaps_outline` are inherited from `ConnectionSolver`.

    # ------------------------------------------------------------------
    # per-topology tests
    # ------------------------------------------------------------------

    def _test_face_face(self, beam, plate, tol):
        """Checks whether a beam long-face lies coplanar, anti-parallel, and overlapping with a plate main face."""
        for plate_face, outline in ((plate.ref_sides[0], plate.outline_a), (plate.ref_sides[2], plate.outline_b)):
            for i in range(4):
                beam_face = beam.ref_sides[i]
                if dot_vectors(beam_face.zaxis, plate_face.zaxis) > -1 + tol:
                    continue  # not anti-parallel
                distance = dot_vectors(Vector.from_start_end(plate_face.point, beam_face.point), plate_face.zaxis)
                if abs(distance) > tol:
                    continue  # not coplanar
                corners = self._surface_corners(beam.side_as_surface(i))
                if self._rectangle_overlaps_outline(corners, outline, tol):
                    centroid = Point(*[sum(c[axis] for c in corners) / 4.0 for axis in range(3)])
                    return distance, centroid
        return None

    def _test_end_face(self, point, plate, tol):
        """Checks whether `point` (already confirmed within the slab's depth range) falls inside the plate's outline."""
        if not is_point_in_polyline(point, plate.outline_a, in_plane=False, tol=Tolerance(absolute=tol)):
            return None
        depth = self._endpoint_depth(point, plate)
        distance = min(abs(depth), abs(plate.thickness - depth))
        return distance, point

    def _test_end_edge_at_point(self, point, plate, i, tol):
        """Checks whether `point` falls inside outline segment `i`'s bounded edge quad."""
        if not is_point_in_polyline(point, self._edge_quad(plate, i), in_plane=True, tol=Tolerance(absolute=tol)):
            return None
        distance = distance_point_plane(point, plate.edge_planes[i])
        return distance, point

    def _test_along_edge(self, beam, plate, i, tol):
        """Checks whether the beam's centerline is parallel to and overlaps outline segment `i` (both endpoints already confirmed close to `edge_planes[i]`)."""
        seg_a = Line(plate.outline_a.points[i], plate.outline_a.points[i + 1])
        seg_b = Line(plate.outline_b.points[i], plate.outline_b.points[i + 1])
        if not is_parallel_line_line(seg_a, seg_b, tol=tol):
            return None  # segment is not well-defined as a planar edge
        centerline = beam.centerline
        if not is_parallel_line_line(centerline, seg_a, tol=tol):
            return None
        if get_segment_overlap(seg_a, centerline) is None:
            return None
        distance = distance_point_plane(centerline.start, plate.edge_planes[i])
        location = (centerline.start + centerline.end) / 2.0
        return distance, location

    def _test_middle_edge(self, beam, plate, i, tol):
        """Checks whether the beam's centerline crosses outline segment `i`'s edge plane at a point that isn't near either beam endpoint."""
        centerline = beam.centerline
        crossing = intersection_line_plane(centerline, plate.edge_planes[i])
        if crossing is None:
            return None
        crossing = Point(*crossing)
        if distance_point_point(crossing, centerline.start) <= tol or distance_point_point(crossing, centerline.end) <= tol:
            return None  # too close to an endpoint: this is END_EDGE's territory, not a mid-span crossing
        if not is_point_in_polyline(crossing, self._edge_quad(plate, i), in_plane=True, tol=Tolerance(absolute=tol)):
            return None
        return 0.0, crossing

    def _test_through_face(self, beam, plate, tol):
        """Checks whether the beam's centerline crosses both main faces of the plate within its outline (endpoints already confirmed on opposite sides)."""
        centerline = beam.centerline
        crossings = []
        for plate_face, outline in ((plate.ref_sides[0], plate.outline_a), (plate.ref_sides[2], plate.outline_b)):
            crossing = intersection_line_plane(centerline, Plane(plate_face.point, plate_face.zaxis))
            if crossing is None:
                return None
            crossing = Point(*crossing)
            if not is_point_in_polyline(crossing, outline, in_plane=True, tol=Tolerance(absolute=tol)):
                return None
            crossings.append(crossing)
        location = (crossings[0] + crossings[1]) / 2.0
        return 0.0, location

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


class BeamPlateSolverResult(Data):
    """Data structure to hold the results of beam-to-plate/panel connection topology analysis.

    Parameters
    ----------
    topology : :class:`~compas_timber.connections.JointTopology`
        The topology of the intersection.
    beam : :class:`~compas_timber.elements.Beam`
        The beam involved in the intersection.
    plate : :class:`~compas_timber.elements.Plate` or :class:`~compas_timber.elements.Panel`
        The plate or panel involved in the intersection.
    segment_index : int, optional
        The index of the outline segment in `plate` where the intersection occurs. Only set for the
        edge-related topologies (`TOPO_END_EDGE`, `TOPO_MIDDLE_EDGE`, `TOPO_ALONG_EDGE`); `None` otherwise.
    distance : float, optional
        The raw geometric gap/coplanarity distance found by whichever check matched.
    location : :class:`~compas.geometry.Point`, optional
        The location of the intersection.

    Attributes
    ----------
    topology : :class:`~compas_timber.connections.JointTopology`
        The topology of the intersection.
    beam : :class:`~compas_timber.elements.Beam`
        The beam involved in the intersection.
    plate : :class:`~compas_timber.elements.Plate` or :class:`~compas_timber.elements.Panel`
        The plate or panel involved in the intersection.
    segment_index : int, optional
        The index of the outline segment in `plate` where the intersection occurs.
    distance : float, optional
        The raw geometric gap/coplanarity distance found by whichever check matched.
    location : :class:`~compas.geometry.Point`, optional
        The location of the intersection.
    """

    def __init__(self, topology, beam, plate, segment_index=None, distance=None, location=None):
        super(BeamPlateSolverResult, self).__init__()
        self.topology = topology
        self.beam = beam
        self.plate = plate
        self.segment_index = segment_index
        self.distance = distance
        self.location = location

    @property
    def __data__(self):
        return {
            "topology": self.topology,
            "beam": self.beam,
            "plate": self.plate,
            "segment_index": self.segment_index,
            "distance": self.distance,
            "location": self.location,
        }

    def __repr__(self):
        return "BeamPlateSolverResult(topology={}, beam={}, plate={}, segment_index={}, distance={}, location={})".format(
            self.topology,
            self.beam.name,
            self.plate.name,
            self.segment_index,
            self.distance,
            self.location,
        )

