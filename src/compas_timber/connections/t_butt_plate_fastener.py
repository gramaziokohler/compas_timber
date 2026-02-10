from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Optional

from compas.geometry import Frame
from compas.geometry import Plane
from compas.geometry import cross_vectors

from compas_timber.connections.joint_fastener import JointFastener
from compas_timber.connections.t_butt import TButtJoint
from compas_timber.connections.utilities import beam_ref_side_incidence_with_vector
from compas_timber.utils import intersection_line_line_param

if TYPE_CHECKING:
    from compas_timber.fasteners.fastener import Fastener


class TButtJointPlateFastener(JointFastener, TButtJoint):
    def __init__(self, main_beam=None, cross_beam=None, mill_depth=None, butt_plane=None, base_fastener: Optional[Fastener] = None, **kwargs):
        super().__init__(
            main_beam=main_beam,
            cross_beam=cross_beam,
            mill_depth=mill_depth,
            butt_plane=butt_plane,
            base_fastener=base_fastener,
            **kwargs,
        )

    def add_features(self) -> None:
        super().add_features()
        if self.fasteners:
            for fastener in self.fasteners:
                fastener.apply_processings(self)

    def place_fasteners_instances(self) -> None:
        """
        Places fastener instances in the T-Butt joint based on the base fastener and the computed target frames.
        """
        if not self.base_fastener:
            return
        for frame in self.compute_fastener_target_frames():
            fastener_instance = self.base_fastener.compute_joint_instance(frame)
            self._fasteners.append(fastener_instance)

    def compute_fastener_target_frames(self) -> list[Frame]:
        """
        Computes the frames for placing fasteners in the T-Butt joint.

        Returns
        -------
        list[:class:`compas.geometry.Frame`]
        """
        # Find front_face_index and back_face_index
        cross_vector = cross_vectors(self.cross_beam.centerline.direction, self.main_beam.centerline.direction)
        cross_faces = beam_ref_side_incidence_with_vector(self.cross_beam, cross_vector)
        front_face_index = min(cross_faces, key=cross_faces.get)  # type: ignore
        back_face_index = (front_face_index + 2) % 4

        # Compute Front Frame
        (cross_point, cross_param), (main_point, main_param) = intersection_line_line_param(self.cross_beam.centerline, self.main_beam.centerline)
        intersection_point = (main_point + cross_point) * 0.5  # type: ignore
        front_face = self.cross_beam.ref_sides[front_face_index]
        front_point = Plane.from_frame(front_face).closest_point(intersection_point)
        front_frame = Frame(point=front_point, xaxis=self.cross_beam.centerline.direction, yaxis=front_face.yaxis)

        # Compute Back Frame
        back_face = self.cross_beam.ref_sides[back_face_index]
        back_point = Plane.from_frame(back_face).closest_point(intersection_point)
        back_frame = Frame(point=back_point, xaxis=-self.cross_beam.centerline.direction, yaxis=-back_face.yaxis)
        return [front_frame, back_frame]
