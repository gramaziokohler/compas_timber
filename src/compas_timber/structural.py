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
from compas.geometry import Frame
from compas.geometry import Line
from compas.geometry import Point
from compas.geometry import Vector
from compas.geometry import closest_point_on_segment
from compas.geometry import distance_point_point
from compas.geometry import intersection_segment_segment
from compas.itertools import pairwise
from compas.tolerance import TOL

from compas_timber.utils import StrEnum

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


class SimpleBeamSegmentGenerator(BeamSegmentGenerator):
    """Generates structural segments by splitting the beam centerline at joint locations."""

    def generate_segments(self, beam: Beam, joints: Sequence[Joint]) -> List[StructuralSegment]:
        split_points_with_distances = []
        for joint in joints:
            point_on_segment = Point(*closest_point_on_segment(joint.location, beam.centerline))
            distance_from_start = distance_point_point(beam.centerline.start, point_on_segment)
            distance_from_end = beam.length - distance_from_start

            if TOL.is_zero(distance_from_start) or TOL.is_zero(distance_from_end):
                # joints at start and end do not require splitting, as they are already segment boundaries
                continue

            split_points_with_distances.append((distance_from_start, point_on_segment))

        # sort split points along the centerline
        split_points_with_distances.sort(key=lambda x: x[0])

        split_points = [v[1] for v in split_points_with_distances]

        split_segments = []
        for p1, p2 in pairwise([beam.centerline.start] + split_points + [beam.centerline.end]):
            split_segments.append(Line(p1, p2))

        return [StructuralSegment(line=seg, frame=Frame(seg.start, beam.frame.xaxis, beam.frame.yaxis), cross_section=(beam.width, beam.height)) for seg in split_segments]


class SimpleJointConnectorGenerator(JointConnectorGenerator):
    """Generates connector segments as virtual lines between non-intersecting beam centerlines."""

    def generate_connectors(self, joint: Joint) -> List[Tuple[Beam, Beam, List[StructuralSegment]]]:
        results = []
        for beam_a, beam_b in joint.interactions:
            p1, p2 = intersection_segment_segment(beam_a.centerline, beam_b.centerline)

            # NOTE: based on the documentation if the segments do not intersect, p1 and p2 are None
            # however, it seems that even if they are parallel but adjacent, p1 and p2 are simply the closest points on each segment
            if p1 is None or p2 is None:
                continue

            if TOL.is_zero(distance_point_point(p1, p2)):
                # no need to create a virtual segment if centerlines intersect
                continue

            virtual_segment = Line(p1, p2)

            # TODO: this is a guess, not sure what the frame of a virtual segment should be. this needs updating when we find out.
            frame = Frame(p1, Vector.Xaxis(), Vector.Yaxis())
            results.append((beam_a, beam_b, [StructuralSegment(line=virtual_segment, frame=frame)]))
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
