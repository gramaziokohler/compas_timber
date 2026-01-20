from typing import List

from compas.data import Data
from compas.geometry import Line
from compas.geometry import Point
from compas.geometry import closest_point_on_segment
from compas.geometry import distance_point_point
from compas.itertools import pairwise

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
    def create_structural_segments(self, beam: Beam, model: TimberModel) -> List[StructuralSegment]:
        """Create structural segments for a given beam in the timber model.

        This are essentially segments of the beam's centerline split at the locations of the joints.

        Parameters
        ----------
        beam : :class:`compas_timber.model.Beam`
            The beam for which to create structural segments.
        model : :class:`compas_timber.model.TimberModel`
            The timber model containing the beams and joints.

        Returns
        -------
        List[:class:`compas_timber.model.StructuralSegment`]
            A list of structural segments created for the beam.
        """
        joints = model.get_interactions_for_element(beam)

        # create segments between joints
        split_points_with_distances = []
        for joint in joints:
            point_on_segment = Point(*closest_point_on_segment(joint.location, beam.centerline))
            distance_from_start = distance_point_point(beam.centerline.start, point_on_segment)
            split_points_with_distances.append((distance_from_start, point_on_segment))

        # sort split point along the centeline
        split_points_with_distances.sort(key=lambda x: x[0])

        split_points = [v[1] for v in split_points_with_distances]

        split_segments = []
        for p1, p2 in pairwise([beam.centerline.start] + split_points + [beam.centerline.end]):
            split_segments.append(Line(p1, p2))

        return [StructuralSegment(segment=seg) for seg in split_segments]
