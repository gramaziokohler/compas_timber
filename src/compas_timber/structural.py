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
from compas.geometry import Point
from compas.geometry import Polyline
from compas.geometry import Translation
from compas.geometry import Vector
from compas.geometry import closest_point_on_segment
from compas.geometry import distance_point_point
from compas.itertools import pairwise
from compas.tolerance import TOL

from compas_timber.utils import StrEnum
from compas_timber.utils import distance_segment_segment_points

if TYPE_CHECKING:
    from compas_timber.connections import Joint
    from compas_timber.elements import Beam
    from compas_timber.elements import Plate
    from compas_timber.model import TimberModel


def _joint_location(joint) -> Optional[Point]:
    # Joint.location raises ValueError (not AttributeError) when it cannot be derived,
    # e.g. for joints with more than two elements and no explicit location,
    # so getattr(joint, "location", None) is not enough here.
    try:
        return joint.location
    except (AttributeError, ValueError):
        return None


def effective_centerline(beam: Beam, max_structural_extension=300.0, include_points=None) -> Line:
    """Return the beam centerline extended by blank extensions for structural use only.

    Parameters
    ----------
    beam : :class:`compas_timber.elements.Beam`
        The beam whose centerline to extend.
    max_structural_extension : float, optional
        Maximum extension at either end, in design units (mm, like the rest of compas_timber). Defaults to 300.0.
        Blank extensions longer than this are ignored altogether, as are include points further than this beyond an end.
    include_points : list of :class:`compas.geometry.Point`, optional
        Points (e.g. joint locations) beyond the ends of the centerline which the extended centerline should reach.

    Returns
    -------
    :class:`compas.geometry.Line`

    """
    centerline = beam.centerline
    start_extension = 0.0
    end_extension = 0.0

    if hasattr(beam, "_resolve_blank_extensions"):
        start_extension, end_extension = beam._resolve_blank_extensions()
        if start_extension > max_structural_extension or end_extension > max_structural_extension:
            start_extension = 0.0
            end_extension = 0.0

    direction = centerline.direction
    include_points = include_points or []
    for point in include_points:
        vector = Vector.from_start_end(centerline.start, point)
        distance_along_centerline = vector.dot(direction)

        if distance_along_centerline < 0.0:
            extension = abs(distance_along_centerline)
            if extension <= max_structural_extension:
                start_extension = max(start_extension, extension)
        elif distance_along_centerline > centerline.length:
            extension = distance_along_centerline - centerline.length
            if extension <= max_structural_extension:
                end_extension = max(end_extension, extension)

    if TOL.is_zero(start_extension) and TOL.is_zero(end_extension):
        return centerline

    start = centerline.start - direction * start_extension
    end = centerline.end + direction * end_extension
    return Line(start, end)


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

    def __init__(self, line: Line, frame: Frame, cross_section: Optional[Tuple[float, float]] = None, name: Optional[str] = None, **kwargs) -> None:
        # `name` is consumed here rather than forwarded with the rest: Data.__init__
        # takes no other keyword, so passing **kwargs through made any segment with
        # extra attributes impossible to construct (and to deserialize), and left a
        # duplicate copy of the name in `attributes`.
        super().__init__(name=name)
        self.attributes = {}
        self.attributes.update(kwargs)
        self.line = line
        self.frame = frame
        self.cross_section = cross_section


class StructuralSurface(Data):
    """The analytical mid-surface of a plate, used for structural analysis.

    Parameters
    ----------
    outline : :class:`compas.geometry.Polyline`
        The closed outline of the surface, lying in the plate's mid-plane.
    frame : :class:`compas.geometry.Frame`
        The local frame of the surface. Its normal is the surface normal.
    thickness : float
        The thickness of the plate this surface represents.
    parent_plate : :class:`compas_timber.elements.Plate`, optional
        The plate this surface was generated from.
    role : str, optional
        The role of the surface. Defaults to ``"surface"``.
    name : str, optional
        The name of the surface.
    parent_plate_guid : str, optional
        The guid of the parent plate. Only used when deserializing, where the plate itself is not available.
        Ignored when ``parent_plate`` is given.
    **kwargs : dict, optional
        Additional attributes, stored in :attr:`attributes`.

    Attributes
    ----------
    parent_plate_guid : str or None
        The guid of the parent plate. This is what gets serialized in place of the plate itself.

    """

    @property
    def __data__(self) -> dict:
        data = {
            "outline": self.outline,
            "frame": self.frame,
            "thickness": self.thickness,
            "role": self.role,
            "parent_plate_guid": self.parent_plate_guid,
        }
        data.update(self.attributes)
        return data

    def __init__(
        self,
        outline: Polyline,
        frame: Frame,
        thickness: float,
        parent_plate: Optional[Plate] = None,
        role: str = "surface",
        name: Optional[str] = None,
        parent_plate_guid: Optional[str] = None,
        **kwargs,
    ) -> None:
        # same pattern as StructuralSegment: Data.__init__ only takes `name`
        super().__init__(name=name)
        self.attributes = {}
        self.attributes.update(kwargs)
        self.outline = outline
        self.frame = frame
        self.thickness = thickness
        self.parent_plate = parent_plate
        self.role = role
        self._parent_plate_guid = parent_plate_guid

    @property
    def parent_plate_guid(self) -> Optional[str]:
        if self.parent_plate is not None:
            return str(self.parent_plate.guid)
        return self._parent_plate_guid


class StructuralSurfaceLine(Data):
    """A line on a :class:`StructuralSurface`, e.g. where two surfaces are connected.

    Parameters
    ----------
    line : :class:`compas.geometry.Line`
        The geometry of the line.
    parent_surface : :class:`StructuralSurface`, optional
        The surface this line lies on.
    parent_plate : :class:`compas_timber.elements.Plate`, optional
        The plate of the parent surface.
    line_type : str, optional
        One of ``"boundary"``, ``"internal"``, ``"connection"``, ``"subdivision"``, ``"hinge"`` or ``"support"``.
        Defaults to ``"internal"``.
    name : str, optional
        The name of the line.
    parent_surface_guid : str, optional
        The guid of the parent surface. Only used when deserializing. Ignored when ``parent_surface`` is given.
    parent_plate_guid : str, optional
        The guid of the parent plate. Only used when deserializing. Ignored when ``parent_plate`` is given.
    **kwargs : dict, optional
        Additional attributes, stored in :attr:`attributes`.

    Attributes
    ----------
    parent_surface_guid : str or None
        The guid of the parent surface. This is what gets serialized in place of the surface itself.
    parent_plate_guid : str or None
        The guid of the parent plate. This is what gets serialized in place of the plate itself.

    """

    @property
    def __data__(self) -> dict:
        data = {
            "line": self.line,
            "line_type": self.line_type,
            "parent_surface_guid": self.parent_surface_guid,
            "parent_plate_guid": self.parent_plate_guid,
        }
        data.update(self.attributes)
        return data

    def __init__(
        self,
        line: Line,
        parent_surface: Optional[StructuralSurface] = None,
        parent_plate: Optional[Plate] = None,
        line_type: str = "internal",
        name: Optional[str] = None,
        parent_surface_guid: Optional[str] = None,
        parent_plate_guid: Optional[str] = None,
        **kwargs,
    ) -> None:
        super().__init__(name=name)
        self.attributes = {}
        self.attributes.update(kwargs)
        self.line = line
        self.parent_surface = parent_surface
        self.parent_plate = parent_plate
        self.line_type = line_type
        self._parent_surface_guid = parent_surface_guid
        self._parent_plate_guid = parent_plate_guid

    @property
    def parent_surface_guid(self) -> Optional[str]:
        if self.parent_surface is not None:
            return str(self.parent_surface.guid)
        return self._parent_surface_guid

    @property
    def parent_plate_guid(self) -> Optional[str]:
        if self.parent_plate is not None:
            return str(self.parent_plate.guid)
        return self._parent_plate_guid


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
    """Base class for plate surface generators.

    Subclasses should implement ``generate_surfaces`` to produce structural surfaces
    for a plate, given its joints.

    """

    @abstractmethod
    def generate_surfaces(self, plate: Plate, joints: Sequence[Joint]) -> List[StructuralSurface]:
        """Generate structural surfaces for a plate.

        Parameters
        ----------
        plate : :class:`compas_timber.elements.Plate`
            The plate for which to generate surfaces.
        joints : list of :class:`compas_timber.connections.Joint`
            The joints associated with the plate.

        Returns
        -------
        list of :class:`StructuralSurface`

        """
        raise NotImplementedError


class PlateConnectionGenerator(ABC):
    """Base class for plate connection line generators.

    Subclasses should implement ``generate_connection_lines`` to produce the lines
    along which the structural surfaces of two joined plates are connected.

    """

    @abstractmethod
    def generate_connection_lines(self, joint: Joint, model: TimberModel) -> List[StructuralSurfaceLine]:
        """Generate connection lines for a joint between plates.

        Parameters
        ----------
        joint : :class:`compas_timber.connections.Joint`
            The joint for which to generate connection lines.
        model : :class:`compas_timber.model.TimberModel`
            The model holding the structural surfaces of the joined plates.

        Returns
        -------
        list of :class:`StructuralSurfaceLine`

        """
        raise NotImplementedError


class SimpleBeamSegmentGenerator(BeamSegmentGenerator):
    """Generates structural segments by splitting the beam centerline at joint and support locations.

    Parameters
    ----------
    max_structural_extension : float, optional
        Passed to :func:`effective_centerline`, in design units (mm). Defaults to 300.0.

    """

    def __init__(self, max_structural_extension=300.0):
        self.max_structural_extension = max_structural_extension

    def _centerline(self, beam, include_points=None):
        return effective_centerline(beam, self.max_structural_extension, include_points)

    def _add_split_point(self, split_points_with_distances, centerline, point):
        point_on_segment = Point(*closest_point_on_segment(point, centerline))
        distance_from_start = distance_point_point(centerline.start, point_on_segment)
        distance_from_end = centerline.length - distance_from_start

        if TOL.is_zero(distance_from_start) or TOL.is_zero(distance_from_end):
            # joints at start and end do not require splitting, as they are already segment boundaries
            return

        for existing_distance, _ in split_points_with_distances:
            if TOL.is_zero(abs(existing_distance - distance_from_start)):
                return

        split_points_with_distances.append((distance_from_start, point_on_segment))

    def _joint_points_on_beam(self, beam: Beam, joint: Joint) -> List[Point]:
        points = []
        location = _joint_location(joint)
        include_points = [location] if location else None

        for beam_a, beam_b in joint.interactions:
            if not hasattr(beam_a, "centerline") or not hasattr(beam_b, "centerline"):
                # e.g. beam-to-fastener interactions, there is no centerline to intersect with
                continue

            centerline_a = self._centerline(beam_a, include_points)
            centerline_b = self._centerline(beam_b, include_points)

            if beam is beam_a:
                _, point_a, _ = distance_segment_segment_points(centerline_a, centerline_b)
                points.append(Point(*point_a))
            elif beam is beam_b:
                _, _, point_b = distance_segment_segment_points(centerline_a, centerline_b)
                points.append(Point(*point_b))

        if not points and location:
            points.append(location)

        return points

    def generate_segments(self, beam: Beam, joints: Sequence[Joint]) -> List[StructuralSegment]:
        split_points_with_distances = []
        include_points = [location for location in (_joint_location(joint) for joint in joints) if location]
        centerline = self._centerline(beam, include_points)

        for joint in joints:
            for point in self._joint_points_on_beam(beam, joint):
                self._add_split_point(split_points_with_distances, centerline, point)

        for support_point in beam.attributes.get("support_points", []):
            self._add_split_point(split_points_with_distances, centerline, Point(*support_point))

        # sort split points along the centerline
        split_points_with_distances.sort(key=lambda x: x[0])

        split_points = [v[1] for v in split_points_with_distances]

        split_segments = []
        for p1, p2 in pairwise([centerline.start] + split_points + [centerline.end]):
            split_segments.append(Line(p1, p2))

        return [StructuralSegment(line=seg, frame=Frame(seg.start, beam.frame.xaxis, beam.frame.yaxis), cross_section=(beam.width, beam.height)) for seg in split_segments]


class SimpleJointConnectorGenerator(JointConnectorGenerator):
    """Generates connector segments as virtual lines between non-intersecting beam centerlines.

    Parameters
    ----------
    max_candidate_connector_distance : float, optional
        Joint candidates whose centerlines are further apart than this get no connector, in design units (mm).
        Does not apply to joints. Defaults to 10.0.
    use_candidate_connectors : bool, optional
        If False, joint candidates get no connectors at all. Defaults to True.
    max_structural_extension : float, optional
        Passed to :func:`effective_centerline`, in design units (mm). Defaults to 300.0.

    """

    def __init__(self, max_candidate_connector_distance=10.0, use_candidate_connectors=True, max_structural_extension=300.0):
        self.max_candidate_connector_distance = max_candidate_connector_distance
        self.use_candidate_connectors = use_candidate_connectors
        self.max_structural_extension = max_structural_extension

    def _centerline(self, beam, include_points=None):
        return effective_centerline(beam, self.max_structural_extension, include_points)

    def generate_connectors(self, joint: Joint) -> List[Tuple[Beam, Beam, List[StructuralSegment]]]:
        results = []
        is_candidate = type(joint).__name__ == "JointCandidate"

        if is_candidate and not self.use_candidate_connectors:
            return results

        location = _joint_location(joint)
        include_points = [location] if location else None
        for beam_a, beam_b in joint.interactions:
            if not hasattr(beam_a, "centerline") or not hasattr(beam_b, "centerline"):
                # e.g. beam-to-fastener interactions, there is no centerline to connect to
                continue

            centerline_a = self._centerline(beam_a, include_points)
            centerline_b = self._centerline(beam_b, include_points)
            distance, p1, p2 = distance_segment_segment_points(centerline_a, centerline_b)

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


def _extreme_point_indices(points, axis, tolerance):
    # indices of the points at either end of `points` along `axis`, and the extent along it
    projections = [point.x * axis.x + point.y * axis.y + point.z * axis.z for point in points]
    min_proj = min(projections)
    max_proj = max(projections)

    min_indices = [i for i, value in enumerate(projections) if abs(value - min_proj) <= tolerance]
    max_indices = [i for i, value in enumerate(projections) if abs(value - max_proj) <= tolerance]
    return min_indices, max_indices, max_proj - min_proj


def _get_plate_center_outline(plate):
    pts_a = _get_open_points(plate.outline_a)
    pts_b = _get_open_points(plate.outline_b)
    center_points = []
    for pa, pb in zip(pts_a, pts_b):
        center_points.append(Point(0.5 * (pa.x + pb.x), 0.5 * (pa.y + pb.y), 0.5 * (pa.z + pb.z)))
    center_points.append(center_points[0])
    return Polyline(center_points)


class SimplePlateSurfaceGenerator(PlateSurfaceGenerator):
    """Generates analytical surfaces from plate centre outlines.

    It stretches the center-plane of the plate to automatically close gaps
    to adjacent plates identified by the given joints.

    This generator produces one surface per plate and never subdivides it, so
    `split` is accepted for interface compatibility but has no effect here.

    Parameters
    ----------
    tolerance : float, optional
        Distance within which outline points count as lying at the same end of the plate,
        and within which a plate counts as square, in design units (mm). Defaults to 2.0.
    split : bool, optional
        Accepted for interface compatibility, has no effect. Defaults to False.

    """

    def __init__(self, tolerance=2.0, split=False):
        self.split = split
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
            normal, direction = _polyline_normal_and_direction(center_outline)

            if not direction:
                continue

            # The plate is stretched at one of its ends along its longest edge. On a square plate
            # that edge is an arbitrary pick, so both in-plane directions are considered there.
            # TODO: revisit. Rectangular plates joined along one of their long edges are still not stretched.
            # Using the joint's segment index (a_segment_index/b_segment_index) to find the edge to move would cover both cases.
            perpendicular = normal.cross(direction)
            min_indices, max_indices, extent = _extreme_point_indices(points, direction, self.tolerance)
            candidates = [min_indices, max_indices]
            perp_min_indices, perp_max_indices, perp_extent = _extreme_point_indices(points, perpendicular, self.tolerance)
            if abs(extent - perp_extent) <= self.tolerance:
                candidates += [perp_min_indices, perp_max_indices]

            best = None
            for indices in candidates:
                if not indices:
                    continue
                midpoint = Point(
                    sum(points[i].x for i in indices) / len(indices), sum(points[i].y for i in indices) / len(indices), sum(points[i].z for i in indices) / len(indices)
                )
                vec = Vector.from_start_end(midpoint, target_point)
                signed_dist = vec.dot(target_normal)
                dist = abs(signed_dist)

                if best is None or dist < best[0]:
                    best = (dist, signed_dist, indices, target_normal)

            if best is not None:
                dist, signed_dist, indices, target_normal = best
                thickness = plate.thickness
                if dist <= (thickness * 1.5):  # allow a buffer
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
        # Frame takes two in-plane axes, the normal is derived from them
        frame = Frame(pts[0], direction, normal.cross(direction))

        surface = StructuralSurface(outline=center_outline, frame=frame, thickness=plate.thickness, parent_plate=plate)
        return [surface]


class SimplePlateConnectionGenerator(PlateConnectionGenerator):
    """Generates interaction lines strictly from the topological intersections of extended StructuralSurfaces.

    Assumes `StructuralSurfaces` have already been generated and stored in the model.

    When the joint carries the index of the joined outline segment of the first plate (``a_segment_index``,
    as plate joints and plate joint candidates do), only that segment is considered.
    Otherwise the first outline segment of the first plate lying in the plane of the second plate is used.

    Parameters
    ----------
    tolerance : float, optional
        Maximum distance of a segment's endpoints to the other surface's plane, in design units (mm). Defaults to 2.0.

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
        # the centre outline keeps the vertex order of outline_a, so the joint's segment index carries over
        segment_index = getattr(joint, "a_segment_index", None)
        indices = [segment_index] if segment_index is not None else range(len(pts_a))
        for i in indices:
            p0 = pts_a[i]
            p1 = pts_a[(i + 1) % len(pts_a)]
            d0 = Vector.from_start_end(origin_b, p0).dot(norm_b)
            d1 = Vector.from_start_end(origin_b, p1).dot(norm_b)

            if abs(d0) <= self.tolerance and abs(d1) <= self.tolerance:
                lines_on_b.append(Line(p0, p1))

        results = []
        if lines_on_b:
            # without a segment index, we assume the first coplanar line is the joint line
            intersection_line = lines_on_b[0]
            results.append(StructuralSurfaceLine(line=intersection_line, parent_surface=surf_a, parent_plate=plate_a, line_type="connection"))
            results.append(StructuralSurfaceLine(line=intersection_line, parent_surface=surf_b, parent_plate=plate_b, line_type="connection"))

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
    """Produces structural surfaces for plates and connection lines for their joints in a timber model.

    Parameters
    ----------
    plate_surface_generator : :class:`PlateSurfaceGenerator`, optional
        Generator used to produce structural surfaces for plates.
        Defaults to :class:`SimplePlateSurfaceGenerator`.
    plate_connection_generator : :class:`PlateConnectionGenerator`, optional
        Generator used to produce connection lines for joints.
        Defaults to :class:`SimplePlateConnectionGenerator`.
    interaction_type : :class:`InteractionType`, optional
        Which interaction types to consider when creating structural surfaces.
        Defaults to ``InteractionType.AUTO``.
    split : bool, optional
        Passed to the default :class:`SimplePlateSurfaceGenerator`. Defaults to True.

    """

    def __init__(
        self,
        plate_surface_generator: Optional[PlateSurfaceGenerator] = None,
        plate_connection_generator: Optional[PlateConnectionGenerator] = None,
        interaction_type: Optional[InteractionType] = None,
        split: bool = True,
    ) -> None:
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

    def add_structural_surfaces(self, model: TimberModel) -> Tuple[List[StructuralSurface], Iterable[Joint]]:
        """Creates and adds structural surfaces for all plates to the timber model.

        Parameters
        ----------
        model : :class:`compas_timber.model.TimberModel`
            The timber model containing the plates and joints.

        Returns
        -------
        list of :class:`StructuralSurface`
            The structural surfaces that were created and added to the model.
        set of :class:`compas_timber.connections.Joint`
            The joints that were traversed when creating the surfaces.
            Should be passed to :meth:`add_joint_structural_lines` to avoid duplicates.

        """
        joints_traversed = set()
        surfaces = []

        for plate in model.plates:
            joints_for_plate = self._get_interactions(plate, model)
            plate_surfaces = self.plate_surface_generator.generate_surfaces(plate, joints_for_plate)

            model.add_plate_structural_surfaces(plate, plate_surfaces)

            surfaces.extend(plate_surfaces)
            joints_traversed.update(joints_for_plate)

        return surfaces, joints_traversed

    def add_joint_structural_lines(self, model: TimberModel, joints: Iterable[Joint]) -> List[StructuralSurfaceLine]:
        """Creates and adds structural connection lines for the given joints to the timber model.

        Requires the structural surfaces to have been created with :meth:`add_structural_surfaces` first.

        Parameters
        ----------
        model : :class:`compas_timber.model.TimberModel`
            The timber model containing the plates and joints.
        joints : iterable of :class:`compas_timber.connections.Joint`
            The joints for which to create connection lines.

        Returns
        -------
        list of :class:`StructuralSurfaceLine`
            The connection lines that were created and added to the model.

        """
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
    surface_boundary_edges : iterator
        ``(u, v)`` pairs for edges on the outline of a plate structural surface.
    surface_connection_edges : iterator
        ``(u, v)`` pairs for edges along which two plate structural surfaces are connected.
    surfaces : list of dict
        One dict per plate structural surface, with the :class:`StructuralSurface` under ``"surface"``
        and its outline's node keys under ``"boundary_nodes"``.

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

        Plate structural surfaces add ``"surface_boundary"`` edges carrying ``surface``
        and ``plate``. Surface lines (e.g. connections between plates) are collected
        under ``surface_lines`` on the edge they lie on, which is usually an existing
        boundary edge; otherwise a new edge is added with ``type`` set to the line type.

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

        # --- plate structural surfaces (stored per node in the model graph) ---
        for plate in model.plates:
            surfaces = model.get_plate_structural_surfaces(plate)
            for surface in surfaces:
                # the outline is closed, its last point is the first one again
                node_ids = [_find_or_create_node(pt) for pt in _get_open_points(surface.outline)]

                # close the loop
                for u, v in pairwise(node_ids + [node_ids[0]]):
                    instance.add_edge(u, v, type="surface_boundary", surface=surface, plate=plate)

                instance._cached_surfaces.append({"surface": surface, "boundary_nodes": node_ids})

        # --- surface lines (stored per edge in the model graph) ---
        for edge in model._graph.edges():
            surface_lines = model._graph.edge_attribute(edge, "structural_surface_lines")
            if not surface_lines:
                continue

            for s_line in surface_lines:
                u = _find_or_create_node(s_line.line.start)
                v = _find_or_create_node(s_line.line.end)
                # A connection line usually coincides with a surface boundary. The graph is simple,
                # so the lines are collected on the existing edge instead of overwriting the boundary.
                if instance.has_edge((v, u)):
                    u, v = v, u
                if not instance.has_edge((u, v)):
                    instance.add_edge(u, v, type=s_line.line_type)
                lines = instance.edge_attribute((u, v), "surface_lines") or []
                lines.append(s_line)
                instance.edge_attribute((u, v), "surface_lines", lines)

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
        """Iterate over ``(u, v)`` pairs for all surface connection edges.

        A connection edge may also be a surface boundary edge, so the two iterators can overlap.
        """
        for u, v in self.edges():
            if any(line.line_type == "connection" for line in self.surface_lines(u, v)):
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

    def surface_lines(self, u, v):
        """Return the :class:`StructuralSurfaceLine` objects on the edge ``(u, v)``.

        Parameters
        ----------
        u : int, graph node
        v : int, graph node

        Returns
        -------
        list of :class:`StructuralSurfaceLine`
            Empty for edges without surface lines.
        """
        return self.edge_attribute((u, v), "surface_lines") or []

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
