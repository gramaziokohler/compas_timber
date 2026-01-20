from __future__ import annotations

import typing
from typing import List

from compas.data import Data
from compas.geometry import Line
from compas.geometry import Point
from compas.geometry import closest_point_on_segment
from compas.geometry import distance_point_point
from compas.itertools import pairwise
from compas.tolerance import TOL

if typing.TYPE_CHECKING:
    from compas_timber.connections import Joint
    from compas_timber.elements import Beam
    from compas_timber.model import TimberModel


class StructuralSegment(Data):
    @property
    def __data__(self) -> dict:
        data = {"segment": self.segment}
        data.update(self.attributes)
        return data

    def __init__(self, segment: Line, **kwargs) -> None:
        super().__init__(**kwargs)
        self.attributes = {}
        self.attributes.update(kwargs)
        self.segment = segment


class StructuralElementSolver:
    """Produces structural segments for beams and joints in a timber model."""

    def add_structural_segments(self, beam: Beam, model: TimberModel) -> List[StructuralSegment]:
        """Creates and adds structural segments for a given beam to the timber model.

        These are essentially segments of the beam's centerline split at the locations of the joints.

        Parameters
        ----------
        beam : :class:`compas_timber.model.Beam`
            The beam for which to create structural segments.
        model : :class:`compas_timber.model.TimberModel`
            The timber model containing the beams and joints.

        """
        joints_for_beam = model.get_interactions_for_element(beam)
        segments = self._create_segments(beam, joints_for_beam)
        model.add_beam_structural_segments(beam, segments)
        return segments

    def _create_segments(self, beam: Beam, joints: List[Joint]) -> List[StructuralSegment]:
        # create segments between joints
        split_points_with_distances = []
        for joint in joints:
            point_on_segment = Point(*closest_point_on_segment(joint.location, beam.centerline))
            distance_from_start = distance_point_point(beam.centerline.start, point_on_segment)
            distance_from_end = distance_point_point(beam.centerline.end, point_on_segment)

            if TOL.is_zero(distance_from_start) or TOL.is_zero(distance_from_end):
                # joints at start and end do not require splitting, as they are already segment boundaries
                continue

            split_points_with_distances.append((distance_from_start, point_on_segment))

        # sort split point along the centeline
        split_points_with_distances.sort(key=lambda x: x[0])

        split_points = [v[1] for v in split_points_with_distances]

        split_segments = []
        for p1, p2 in pairwise([beam.centerline.start] + split_points + [beam.centerline.end]):
            split_segments.append(Line(p1, p2))

        return [StructuralSegment(segment=seg) for seg in split_segments]
