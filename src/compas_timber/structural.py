from __future__ import annotations

from abc import ABC
from abc import abstractmethod
from typing import TYPE_CHECKING
from typing import Iterable
from typing import List
from typing import Optional
from typing import Sequence
from typing import Tuple

from compas.data import Data
from compas.datastructures import Graph
from compas.geometry import Frame
from compas.geometry import Line
from compas.geometry import Polyline
from compas.geometry import Point
from compas.geometry import Vector
from compas.geometry import closest_point_on_segment
from compas.geometry import distance_point_point
from compas.geometry import intersection_segment_segment
from compas.geometry import Translation
from compas.itertools import pairwise
from compas.tolerance import TOL

from compas_timber.utils import StrEnum
from compas_timber.utils import distance_segment_segment_points

if TYPE_CHECKING:
    from compas_timber.connections import Joint
    from compas_timber.elements import Beam
    from compas_timber.model import TimberModel


class InteractionType(StrEnum):
    """Defines which interaction types to consider when creating structural segments.

    Attributes
    ----------
    AUTO : int
        Per connection: use joints if available, fall back to candidates.
    JOINTS : int
        Only use joints, ignore candidates.
    CANDIDATES : int
        Only use candidates, ignore joints.

    """

    AUTO = "AUTO"
    JOINTS = "JOINTS"
    CANDIDATES = "CANDIDATES"


class StructuralSegment(Data):
    @property
    def __data__(self) -> dict:
        data = {"line": self.line, "frame": self.frame, "cross_section": self.cross_section}
        data.update(self.attributes)
        return data

    def __init__(self, line: Line, frame: Frame, cross_section: Optional[Tuple[float, float]] = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self.attributes = {}
        self.attributes.update(kwargs)
        self.line = line
        self.frame = frame
        self.cross_section = cross_section

class StructuralSurface(Data):
    def __init__(
        self,
        outline: Polyline,
        frame: Frame,
        thickness: float,
        parent_plate=None,
        role="surface",
        **kwargs
    ):
        super().__init__(**kwargs)
        self.outline = outline
        self.frame = frame
        self.thickness = thickness
        self.parent_plate = parent_plate
        self.role = role
        self.attributes = kwargs

class StructuralSurfaceLine(Data):
    """Possible Line Types: boundary, internal, connection, subdivision, hinge, support"""
    def __init__(
        self,
        line: Line,
        parent_surface=None,
        parent_plate=None,
        line_type="internal",
        **kwargs
    ):
        super().__init__(**kwargs)
        self.line = line
        self.parent_surface = parent_surface
        self.parent_plate = parent_plate
        self.line_type = line_type
        self.attributes = kwargs

class BeamSegmentGenerator(ABC):
    """Base class for beam segment generators.

    Subclasses should implement ``generate_segments`` to produce structural segments
    for a beam, given its joints.

    """

    @abstractmethod
    def generate_segments(self, beam: Beam, joints: Sequence[Joint]) -> List[StructuralSegment]:
        """Generate structural segments for a beam.

        Parameters
        ----------
        beam : :class:`compas_timber.elements.Beam`
            The beam for which to generate segments.
        joints : list of :class:`compas_timber.connections.Joint`
            The joints associated with the beam.

        Returns
        -------
        list of :class:`StructuralSegment`

        """
        raise NotImplementedError

class JointConnectorGenerator(ABC):
    """Base class for joint connector segment generators.

    Subclasses should implement ``generate_connectors`` to produce structural
    connector segments for a joint.

    """

    @abstractmethod
    def generate_connectors(self, joint: Joint) -> List[Tuple[Beam, Beam, List[StructuralSegment]]]:
        """Generate connector segments for a joint.

        Parameters
        ----------
        joint : :class:`compas_timber.connections.Joint`
            The joint for which to generate connector segments.

        Returns
        -------
        list of tuple(Beam, Beam, list of :class:`StructuralSegment`)
            Each tuple contains the two beams being connected and the connector
            segments between them.

        """
        raise NotImplementedError

class PlateSurfaceGenerator(ABC):
    @abstractmethod
    def generate_surfaces(self, plate: Plate, joints: Sequence[Joint]) -> List[StructuralSurface]:
        raise NotImplementedError
class PlateConnectionGenerator(ABC):
    @abstractmethod
    def generate_connection_lines(self, joint: Joint, model: TimberModel) -> List[StructuralSurfaceLine]:
        raise NotImplementedError

class SimpleBeamSegmentGenerator(BeamSegmentGenerator):
    """Generates structural segments by splitting the beam centerline at joint and support locations."""

    def _add_split_point(self, split_points_with_distances, beam, point):
        point_on_segment = Point(*closest_point_on_segment(point, beam.centerline))
        distance_from_start = distance_point_point(beam.centerline.start, point_on_segment)
        distance_from_end = beam.length - distance_from_start

        if TOL.is_zero(distance_from_start) or TOL.is_zero(distance_from_end):
            # joints at start and end do not require splitting, as they are already segment boundaries
            return

        for existing_distance, _ in split_points_with_distances:
            if TOL.is_zero(abs(existing_distance - distance_from_start)):
                return

        split_points_with_distances.append((distance_from_start, point_on_segment))

    def _joint_points_on_beam(self, beam: Beam, joint: Joint) -> List[Point]:
        points = []

        for beam_a, beam_b in joint.interactions:
            if beam is beam_a:
                _, point_a, _ = distance_segment_segment_points(beam_a.centerline, beam_b.centerline)
                points.append(Point(*point_a))
            elif beam is beam_b:
                _, _, point_b = distance_segment_segment_points(beam_a.centerline, beam_b.centerline)
                points.append(Point(*point_b))

        if not points:
            points.append(joint.location)

        return points

    def generate_segments(self, beam: Beam, joints: Sequence[Joint]) -> List[StructuralSegment]:
        split_points_with_distances = []
        for joint in joints:
            for point in self._joint_points_on_beam(beam, joint):
                self._add_split_point(split_points_with_distances, beam, point)

        for support_point in beam.attributes.get("support_points", []):
            self._add_split_point(split_points_with_distances, beam, Point(*support_point))

        # sort split points along the centerline
        split_points_with_distances.sort(key=lambda x: x[0])

        split_points = [v[1] for v in split_points_with_distances]

        split_segments = []
        for p1, p2 in pairwise([beam.centerline.start] + split_points + [beam.centerline.end]):
            split_segments.append(Line(p1, p2))

        return [StructuralSegment(line=seg, frame=Frame(seg.start, beam.frame.xaxis, beam.frame.yaxis), cross_section=(beam.width, beam.height)) for seg in split_segments]

class SimpleJointConnectorGenerator(JointConnectorGenerator):
    """Generates connector segments as virtual lines between non-intersecting beam centerlines."""

    def __init__(self, max_candidate_connector_distance=0.05, use_candidate_connectors=True):
        self.max_candidate_connector_distance = max_candidate_connector_distance
        self.use_candidate_connectors = use_candidate_connectors

    def generate_connectors(self, joint: Joint) -> List[Tuple[Beam, Beam, List[StructuralSegment]]]:
        results = []
        is_candidate = type(joint).__name__ == "JointCandidate"

        if is_candidate and not self.use_candidate_connectors:
            return results

        for beam_a, beam_b in joint.interactions:
            distance, p1, p2 = distance_segment_segment_points(beam_a.centerline, beam_b.centerline)

            if is_candidate and distance > self.max_candidate_connector_distance:
                continue

            p1 = Point(*p1)
            p2 = Point(*p2)

            if TOL.is_zero(distance):
                # no need to create a virtual segment if centerlines intersect
                continue

            virtual_segment = Line(p1, p2)

            # TODO: this is a guess, not sure what the frame of a virtual segment should be. this needs updating when we find out.
            frame = Frame(p1, Vector.Xaxis(), Vector.Yaxis())
            results.append((beam_a, beam_b, [StructuralSegment(line=virtual_segment, frame=frame)]))
        return results

def _get_open_points(polyline):
    points = list(polyline.points)
    if points[0].distance_to_point(points[-1]) < TOL.absolute:
        points = points[:-1]
    return points

def _polyline_normal_and_direction(polyline):
    points = _get_open_points(polyline)
    nx = ny = nz = 0.0
    longest = None
    longest_length = 0.0
    for i, p0 in enumerate(points):
        p1 = points[(i + 1) % len(points)]
        nx += (p0.y - p1.y) * (p0.z + p1.z)
        ny += (p0.z - p1.z) * (p0.x + p1.x)
        nz += (p0.x - p1.x) * (p0.y + p1.y)
        
        vector = Vector.from_start_end(p0, p1)
        if vector.length > longest_length:
            longest = vector
            longest_length = vector.length

    normal = Vector(nx, ny, nz)
    normal.unitize()
    if longest:
        longest.unitize()
    return normal, longest

def _get_plate_center_outline(plate):
    pts_a = _get_open_points(plate.outline_a)
    pts_b = _get_open_points(plate.outline_b)
    center_points = []
    for pa, pb in zip(pts_a, pts_b):
        center_points.append(Point(0.5 * (pa.x + pb.x), 0.5 * (pa.y + pb.y), 0.5 * (pa.z + pb.z)))
    center_points.append(center_points[0])
    return Polyline(center_points)

class SimplePlateSurfaceGenerator(PlateSurfaceGenerator):
    """
    Generates analytical surfaces from plate centre outlines.
    It stretches the center-plane of the plate to automatically close gaps 
    to adjacent plates identified by the given joints.
    """

    def __init__(self, tolerance=2.0):
        self.split = False # We strictly don't split.
        self.tolerance = tolerance

    def generate_surfaces(self, plate, joints):
        center_outline = _get_plate_center_outline(plate)
        
        for joint in joints:
            foreign_element = None
            for element in joint.elements:
                if element is not plate and hasattr(element, "outline_a"):
                    foreign_element = element
                    break
            if not foreign_element:
                continue

            foreign_outline = _get_plate_center_outline(foreign_element)
            target_normal, _ = _polyline_normal_and_direction(foreign_outline)
            target_point = _get_open_points(foreign_outline)[0]

            points = _get_open_points(center_outline)
            _, direction = _polyline_normal_and_direction(center_outline)
            
            if not direction:
                continue

            projections = [point.x * direction.x + point.y * direction.y + point.z * direction.z for point in points]
            min_proj = min(projections)
            max_proj = max(projections)

            min_indices = [i for i, value in enumerate(projections) if abs(value - min_proj) <= self.tolerance]
            max_indices = [i for i, value in enumerate(projections) if abs(value - max_proj) <= self.tolerance]

            best = None
            for indices in [min_indices, max_indices]:
                if not indices: continue
                midpoint = Point(
                    sum(points[i].x for i in indices) / len(indices),
                    sum(points[i].y for i in indices) / len(indices),
                    sum(points[i].z for i in indices) / len(indices)
                )
                vec = Vector.from_start_end(midpoint, target_point)
                signed_dist = vec.dot(target_normal)
                dist = abs(signed_dist)

                if best is None or dist < best[0]:
                    best = (dist, signed_dist, indices, target_normal)

            if best is not None:
                dist, signed_dist, indices, target_normal = best
                thickness = plate.thickness
                if dist <= (thickness * 1.5): # allow a buffer
                    move_vector = target_normal * signed_dist
                    new_points = []
                    for index, point in enumerate(points):
                        if index in indices:
                            new_points.append(point.transformed(Translation.from_vector(move_vector)))
                        else:
                            new_points.append(point)
                    new_points.append(new_points[0])
                    center_outline = Polyline(new_points)

        normal, direction = _polyline_normal_and_direction(center_outline)
        pts = _get_open_points(center_outline)
        frame = Frame(pts[0], direction, normal)
        
        surface = StructuralSurface(
            outline=center_outline,
            frame=frame,
            thickness=plate.thickness,
            parent_plate=plate
        )
        return [surface]

class SimplePlateConnectionGenerator(PlateConnectionGenerator):
    """
    Generates interaction lines strictly from the topological intersections of 
    extended StructuralSurfaces. Assumes `StructuralSurfaces` have already been 
    generated and stored in the model.
    """
    def __init__(self, tolerance=2.0):
        self.tolerance = tolerance

    def generate_connection_lines(self, joint, model):
        plates = [el for el in joint.elements if hasattr(el, "outline_a")]
        if len(plates) < 2:
            return []

        plate_a, plate_b = plates[0], plates[1]
        
        surfs_a = model.get_plate_structural_surfaces(plate_a)
        surfs_b = model.get_plate_structural_surfaces(plate_b)
        
        if not surfs_a or not surfs_b:
            return []
            
        surf_a = surfs_a[0]
        surf_b = surfs_b[0]

        lines_on_b = []
        norm_b = surf_b.frame.normal
        origin_b = surf_b.frame.point
        
        pts_a = _get_open_points(surf_a.outline)
        for i, p0 in enumerate(pts_a):
            p1 = pts_a[(i+1)%len(pts_a)]
            d0 = Vector.from_start_end(origin_b, p0).dot(norm_b)
            d1 = Vector.from_start_end(origin_b, p1).dot(norm_b)
            
            if abs(d0) <= self.tolerance and abs(d1) <= self.tolerance:
                lines_on_b.append(Line(p0, p1))
                
        results = []
        if lines_on_b:
            # We assume the first collinear line is the joint line
            intersection_line = lines_on_b[0]
            results.append(StructuralSurfaceLine(
                line=intersection_line,
                parent_surface=surf_a,
                parent_plate=plate_a,
                line_type="connection"
            ))
            results.append(StructuralSurfaceLine(
                line=intersection_line,
                parent_surface=surf_b,
                parent_plate=plate_b,
                line_type="connection"
            ))
            
        return results

class BeamStructuralElementSolver:
    """Produces structural segments for beams and joints in a timber model.

    Parameters
    ----------
    beam_segment_generator : :class:`BeamSegmentGenerator`, optional
        Generator used to produce structural segments for beams.
        Defaults to :class:`SimpleBeamSegmentGenerator`.
    joint_connector_generator : :class:`JointConnectorGenerator`, optional
        Generator used to produce connector segments for joints.
        Defaults to :class:`SimpleJointConnectorGenerator`.
    interaction_type : :class:`InteractionSource`, optional
        Which interaction types to consider when creating structural segments.
        Defaults to ``InteractionSource.AUTO``.

    """

    def __init__(
        self,
        beam_segment_generator: Optional[BeamSegmentGenerator] = None,
        joint_connector_generator: Optional[JointConnectorGenerator] = None,
        interaction_type: Optional[InteractionType] = None,
    ) -> None:
        self.beam_segment_generator = beam_segment_generator or SimpleBeamSegmentGenerator()
        self.joint_connector_generator = joint_connector_generator or SimpleJointConnectorGenerator()
        self._interaction_type = interaction_type

    def _get_interactions(self, beam: Beam, model: TimberModel) -> list:
        interaction_type = self._interaction_type or InteractionType.AUTO
        if interaction_type == InteractionType.JOINTS:
            return model.get_joints_for_element(beam)
        elif interaction_type == InteractionType.CANDIDATES:
            return model.get_candidates_for_element(beam)

        # AUTO: prefer joints, fall back to candidates
        joints = model.get_joints_for_element(beam)
        candidates = model.get_candidates_for_element(beam)
        if joints:
            return joints
        return candidates

    def add_structural_segments(self, model: TimberModel) -> Tuple[List[StructuralSegment], Iterable[Joint]]:
        """Creates and adds structural segments for a given beam to the timber model.

        These are essentially segments of the beam's centerline split at the locations of the joints.

        Parameters
        ----------
        model : :class:`compas_timber.model.TimberModel`
            The timber model containing the beams and joints.

        Returns
        -------
        list of :class:`StructuralSegment`
            The structural segments that were created and added to the model.
        set of :class:`compas_timber.connections.Joint`
            The joints that were traversed when creating the structural segments. This is the definitive set of joints traversed when creating the beam segments,
            and should be used when creating joint connector segments to avoid duplicates.

        """
        joints_traversed = set()
        segments = []
        for beam in model.beams:
            joints_for_beam = self._get_interactions(beam, model)
            segments = self.beam_segment_generator.generate_segments(beam, joints_for_beam)
            model.add_beam_structural_segments(beam, segments)
            joints_traversed.update(joints_for_beam)
        return segments, joints_traversed

    def add_joint_structural_segments(self, model: TimberModel, joints: Iterable[Joint]) -> Iterable[StructuralSegment]:
        """Creates and adds structural segments for a given joint to the timber model.

        For joints connecting non-intersecting beams (e.g. crossing beams), this creates
        a 'virtual' element connecting the centerlines of the beams.

        Parameters
        ----------
        model : :class:`compas_timber.model.TimberModel`
            The timber model containing the beams and joints.
        joints : iterable of :class:`compas_timber.connections.Joint`
            The joints for which to create structural segments.

        Returns
        -------
        list of :class:`StructuralSegment`
            The structural segments that were created and added to the model.

        """
        results = []
        for joint in joints:
            connectors = self.joint_connector_generator.generate_connectors(joint)
            for beam_a, beam_b, segments in connectors:
                model.add_structural_connector_segments(beam_a, beam_b, segments)
                results.extend(segments)
        return results

class PlateStructuralElementSolver:
    def __init__(
        self,
        plate_surface_generator=None,
        plate_connection_generator=None,
        interaction_type=None,
        split=True,
    ):
        self.plate_surface_generator = plate_surface_generator or SimplePlateSurfaceGenerator(split=split)
        self.plate_connection_generator = plate_connection_generator or SimplePlateConnectionGenerator()
        self._interaction_type = interaction_type

    def _get_interactions(self, plate, model):
        interaction_type = self._interaction_type or InteractionType.AUTO

        if interaction_type == InteractionType.JOINTS:
            return model.get_joints_for_element(plate)

        if interaction_type == InteractionType.CANDIDATES:
            return model.get_candidates_for_element(plate)

        joints = model.get_joints_for_element(plate)
        candidates = model.get_candidates_for_element(plate)

        if joints:
            return joints

        return candidates

    def add_structural_surfaces(self, model):
        joints_traversed = set()
        surfaces = []

        for plate in model.plates:
            joints_for_plate = self._get_interactions(plate, model)
            plate_surfaces = self.plate_surface_generator.generate_surfaces(plate, joints_for_plate)

            model.add_plate_structural_surfaces(plate, plate_surfaces)

            surfaces.extend(plate_surfaces)
            joints_traversed.update(joints_for_plate)

        return surfaces, joints_traversed

    def add_joint_structural_lines(self, model, joints):
        lines = []

        for joint in joints:
            connection_lines = self.plate_connection_generator.generate_connection_lines(joint, model)

            if connection_lines:
                # Group lines by the elements they connect. For a standard joint between two plates:
                elements = list(joint.elements)
                if len(elements) >= 2:
                    model.add_structural_surface_lines(elements[0], elements[1], connection_lines)

            lines.extend(connection_lines)

        return lines
class StructuralGraph(Graph):
    """A structural graph derived from a :class:`~compas_timber.model.TimberModel`.

    Wraps a :class:`~compas.datastructures.Graph` and provides a domain-specific
    API so callers never need to touch raw graph attributes directly.

    Nodes are unique structural points (DOF locations — the endpoints of all
    structural segments, deduplicated within tolerance).  Edges are the structural
    segments themselves, each tagged as either ``"beam"`` or ``"connector"`` and
    carrying a back-reference to the originating timber model element.

    Create instances via :meth:`from_model` rather than directly.

    Attributes
    ----------
    nodes : iterator
        The node keys of all nodes in the graph.
    edges : iterator
        All ``(u, v)`` edge pairs in the graph.
    beam_edges : iterator
        ``(u, v)`` pairs for edges that represent beam-centerline segments.
    connector_edges : iterator
        ``(u, v)`` pairs for edges that represent virtual connector segments
        between non-intersecting beam centerlines.

    Examples
    --------
    >>> sg = StructuralGraph.from_model(model)
    >>> for u, v in sg.beam_edges:
    ...     pt_i = sg.node_point(u)
    ...     pt_j = sg.node_point(v)
    ...     seg = sg.segment(u, v)
    ...     beam = sg.beam(u, v)
    >>> for u, v in sg.connector_edges:
    ...     joint = sg.joint(u, v)
    >>> segs = sg.segments_for_beam(my_beam)

    """

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._cached_node_index = None  # built lazily
        self._cached_surfaces = []

    @property
    def surfaces(self):
        """Return the cached list of surface dictionaries (boundary nodes and the parent StructuralSurface)."""
        return self._cached_surfaces

    @classmethod
    def from_model(cls, model: TimberModel) -> StructuralGraph:
        """Builds a :class:`StructuralGraph` from the structural segments stored in a timber model.

        Nodes represent unique endpoints of structural segments (identified within tolerance).
        Edges represent the segments themselves.  Each edge carries:

        - ``segment`` — the :class:`StructuralSegment`;
        - ``type`` — ``"beam"`` or ``"connector"``;
        - ``beam`` — *(beam edges)* the source :class:`~compas_timber.elements.Beam`;
        - ``joint`` — *(connector edges)* the source
          :class:`~compas_timber.connections.Joint`, or ``None`` when the connector
          was derived from a candidate rather than a resolved joint.

        Parameters
        ----------
        model : :class:`~compas_timber.model.TimberModel`
            The timber model whose structural segments are used to build the graph.

        Returns
        -------
        :class:`StructuralGraph`

        Raises
        ------
        ValueError
            If no structural segments are found in the model.  Call
            :meth:`~compas_timber.model.TimberModel.create_beam_structural_segments`
            first.

        Examples
        --------
        >>> model.create_beam_structural_segments()
        >>> sg = StructuralGraph.from_model(model)
        >>> for u, v in sg.beam_edges:
        ...     print(sg.node_index(u), sg.node_index(v), sg.segment(u, v).line.length, sg.beam(u, v).name)

        """
        instance = cls(default_edge_attributes={"beam": None, "structural_segments": None, "connector": None})

        _node_positions = {}  # node_key -> Point, used for tolerance-based deduplication

        def _find_or_create_node(point):
            # type: (Point) -> object
            for node_key, existing in _node_positions.items():
                if TOL.is_zero(distance_point_point(existing, point)):
                    return node_key
            node_key = instance.add_node(x=point.x, y=point.y, z=point.z)
            _node_positions[node_key] = point
            return node_key

        # --- beam structural segments (stored per node in the model graph) ---
        for beam in model.beams:
            segments = model.get_beam_structural_segments(beam)
            for segment in segments:
                u = _find_or_create_node(segment.line.start)
                v = _find_or_create_node(segment.line.end)
                instance.add_edge(u, v, segment=segment, type="beam", beam=beam)

        # --- connector segments (stored per edge in the model graph) ---
        for edge in model._graph.edges():
            connector_segments = model._graph.edge_attribute(edge, "structural_segments")
            if not connector_segments:
                continue
            # Retrieve the joint that sits on this edge (may be None when only a candidate exists)
            joint_guid = model._graph.edge_attribute(edge, "joints")  # TODO: shouldn't joints be on nodes?
            joint = model._joints.get(joint_guid) if joint_guid else None
            for segment in connector_segments:
                u = _find_or_create_node(segment.line.start)
                v = _find_or_create_node(segment.line.end)
                instance.add_edge(u, v, segment=segment, type="connector", joint=joint)

        # --- Generate Surface Topology ---
        for plate in model.plates:
            surfaces = model.get_plate_structural_surfaces(plate)
            for surface in surfaces:
                node_ids = [_find_or_create_node(pt) for pt in surface.outline.points]
                
                # close the loop
                for u, v in pairwise(node_ids + [node_ids[0]]):
                    instance.add_edge(u, v, type="surface_boundary", surface=surface, plate=plate)
                
                instance._cached_surfaces.append({
                    "surface": surface,
                    "boundary_nodes": node_ids[:-1] # Exclude duplicated end node
                })

        # --- Generate Surface Connections ---
        for edge in model._graph.edges():
            surface_lines = model._graph.edge_attribute(edge, "structural_surface_lines")
            if not surface_lines: 
                continue
            
            for s_line in surface_lines:
                u = _find_or_create_node(s_line.line.start)
                v = _find_or_create_node(s_line.line.end)
                instance.add_edge(u, v, type=s_line.line_type, line=s_line)

        if instance.number_of_nodes() == 0:
            raise ValueError("No structural segments found in the model. Call TimberModel.create_beam_structural_segments() before building the structural graph.")

        return instance

    # ------------------------------------------------------------------
    # Node interface
    # ------------------------------------------------------------------

    def node_point(self, node):
        # type: (object) -> Point
        """Return the 3-D position of a node as a :class:`~compas.geometry.Point`.

        Parameters
        ----------
        node : object
            A node key as returned by iterating :attr:`nodes`.

        Returns
        -------
        :class:`~compas.geometry.Point`
        """
        x = self.node_attribute(node, "x")
        y = self.node_attribute(node, "y")
        z = self.node_attribute(node, "z")
        return Point(x, y, z)

    def node_index(self, node):
        # type: (object) -> int
        """Return the sequential integer index of *node*.

        The index is stable for the lifetime of this object and is suitable for
        building connectivity tables (e.g. for exporting to FEM software).

        Parameters
        ----------
        node : object
            A node key as returned by iterating :attr:`nodes`.

        Returns
        -------
        int
        """
        if self._cached_node_index is None:
            self._cached_node_index = {n: i for i, n in enumerate(self.nodes())}
        return self._cached_node_index[node]

    # ------------------------------------------------------------------
    # Edge interface
    # ------------------------------------------------------------------

    @property
    def beam_edges(self):
        # type: () -> Iterable[Tuple]
        """Iterate over ``(u, v)`` pairs for all beam-segment edges."""
        for u, v in self.edges():
            if self.edge_attribute((u, v), "type") == "beam":
                yield u, v

    @property
    def connector_edges(self):
        # type: () -> Iterable[Tuple]
        """Iterate over ``(u, v)`` pairs for all connector-segment edges."""
        for u, v in self.edges():
            if self.edge_attribute((u, v), "type") == "connector":
                yield u, v

    @property
    def surface_boundary_edges(self):
        # type: () -> Iterable[Tuple]
        """Iterate over ``(u, v)`` pairs for all surface boundary edges."""
        for u, v in self.edges():
            if self.edge_attribute((u, v), "type") == "surface_boundary":
                yield u, v

    @property
    def surface_connection_edges(self):
        # type: () -> Iterable[Tuple]
        """Iterate over ``(u, v)`` pairs for all surface connection edges."""
        for u, v in self.edges():
            if self.edge_attribute((u, v), "type") == "connection":
                yield u, v

    def segment(self, u, v):
        """Return the :class:`StructuralSegment` on the edge ``(u, v)``.

        Parameters
        ----------
        u : int, graph node
        v : int, graph node

        Returns
        -------
        :class:`StructuralSegment`
        """
        return self.edge_attribute((u, v), "segment")

    def beam(self, u, v):
        """Return the source :class:`~compas_timber.elements.Beam` for a beam edge.

        Parameters
        ----------
        u : int, graph node
        v : int, graph node

        Returns
        -------
        :class:`~compas_timber.elements.Beam` or None
            ``None`` for connector edges.
        """
        return self.edge_attribute((u, v), "beam")

    def joint(self, u, v):
        """Return the source :class:`~compas_timber.connections.Joint` for a connector edge.

        Parameters
        ----------
        u : int, graph node
        v : int, graph node

        Returns
        -------
        :class:`~compas_timber.connections.Joint` or None
            ``None`` for beam edges or when the connector was derived from a
            candidate rather than a resolved joint.
        """
        return self.edge_attribute((u, v), "joint")

        # ------------------------------------------------------------------

    # Reverse lookups  (model element → graph edges)
    # ------------------------------------------------------------------

    def segments_for_beam(self, beam):
        # type: (Beam) -> List[Tuple]
        """Return all ``(u, v)`` beam edges that belong to *beam*.

        Parameters
        ----------
        beam : :class:`~compas_timber.elements.Beam`

        Returns
        -------
        list of tuple(u, v)
        """
        return [(u, v) for u, v in self.beam_edges if self.edge_attribute((u, v), "beam") is beam]

    def segments_for_joint(self, joint):
        # type: (Joint) -> List[Tuple]
        """Return all ``(u, v)`` connector edges that were generated for *joint*.

        Parameters
        ----------
        joint : :class:`~compas_timber.connections.Joint`

        Returns
        -------
        list of tuple(u, v)
        """
        return [(u, v) for u, v in self.connector_edges if self.edge_attribute((u, v), "joint") is joint]
