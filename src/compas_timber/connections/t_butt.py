from compas.geometry import Frame
from compas.geometry import Plane
from compas.geometry import cross_vectors

from compas_timber.connections.utilities import beam_ref_side_incidence_with_vector
from compas_timber.utils import intersection_line_line_param

from .butt_joint import ButtJoint
from .solver import JointTopology


class TButtJoint(ButtJoint):
    """Represents a T-Butt type joint which joins the end of a beam along the length of another beam,
    trimming the main beam.

    This joint type is compatible with beams in T topology.

    Please use `TButtJoint.create()` to properly create an instance of this class and associate it with a model.

    Parameters
    ----------
    main_beam : :class:`~compas_timber.parts.Beam`
        The main beam to be joined.
    cross_beam : :class:`~compas_timber.parts.Beam`
        The cross beam to be joined.
    mill_depth : float
        The depth of the pocket to be milled in the cross beam.
    butt_plane : :class:`~compas.geometry.Plane`, optional
        The plane used to cut the main beam. If not provided, the closest side of the cross beam will be used.
    fastener : :class:`~compas_timber.parts.Fastener`, optional
        The fastener to be used in the joint.

    Attributes
    ----------
    main_beam : :class:`~compas_timber.parts.Beam`
        The main beam to be joined.
    cross_beam : :class:`~compas_timber.parts.Beam`
        The cross beam to be joined.
    mill_depth : float
        The depth of the pocket to be milled in the cross beam.

    """

    SUPPORTED_TOPOLOGY = JointTopology.TOPO_T

    def __init__(self, main_beam=None, cross_beam=None, mill_depth=None, butt_plane=None, base_fastener=None, **kwargs):
        super(TButtJoint, self).__init__(main_beam=main_beam, cross_beam=cross_beam, mill_depth=mill_depth, butt_plane=butt_plane, base_fastener=base_fastener, **kwargs)
        self.modify_cross = False

    @property
    def elements(self):
        return self.beams + self.fasteners

    @property
    def generated_elements(self):
        return self.fasteners

    @property
    def fastener_frames(self):
        return self._compute_plate_fastener_frames()

    def _compute_plate_fastener_frames(self):
        """
        Computes the frames to position a plate fastener.

        """
        # Find front_face_index and back_face_index
        cross_vector = cross_vectors(self.cross_beam.centerline.direction, self.main_beam.centerline.direction)
        cross_faces = beam_ref_side_incidence_with_vector(self.cross_beam, cross_vector)
        front_face_index = min(cross_faces, key=cross_faces.get)
        back_face_index = (front_face_index + 2) % 4

        # return front_face_index, back_face_index

        # Compute Front Frame
        (cross_point, cross_param), (main_point, main_param) = intersection_line_line_param(self.cross_beam.centerline, self.main_beam.centerline)
        intersection_point = (main_point + cross_point) * 0.5
        front_face = self.cross_beam.ref_sides[front_face_index]
        front_point = Plane.from_frame(front_face).closest_point(intersection_point)
        front_frame = Frame(point=front_point, xaxis=self.cross_beam.centerline.direction, yaxis=front_face.yaxis)

        # Compute Back Frame
        back_face = self.cross_beam.ref_sides[back_face_index]
        back_point = Plane.from_frame(back_face).closest_point(intersection_point)
        back_frame = Frame(point=back_point, xaxis=-self.cross_beam.centerline.direction, yaxis=-back_face.yaxis)
        return [front_frame, back_frame]

    # def get_fastener_frames(self, joint) -> list[Frame]:
    #     """Calculates the frames of the fasteners.

    #     Returns
    #     -------
    #     :class:`~compas.geometry.Frame`
    #         The frames of the fasteners with the x-axis along the main_beam.centerline and the y-axis along the cross_beam.centerline, offset to lay on the beam_faces.

    #     """
    #     # front_face_index, back_face_index = self.validate_fastener_beam_compatibility(joint)
    #     front_face_index, back_face_index = self._compute_plate_fastener_frames()
    #     beam_a, beam_b = joint.elements[0:2]
    #     (main_point, main_param), (cross_point, _) = intersection_line_line_param(beam_a.centerline, beam_b.centerline)
    #     int_point = (main_point + cross_point) * 0.5
    #     front_face = beam_a.ref_sides[front_face_index]
    #     front_point = Plane.from_frame(front_face).closest_point(int_point)
    #     front_frame = Frame(
    #         front_point,
    #         beam_a.centerline.direction if main_param < 0.5 else -beam_a.centerline.direction,
    #         front_face.normal,
    #     )
    #     front_frame.rotate(-math.pi / 2, front_frame.xaxis, front_point)
    #     back_face = beam_a.ref_sides[back_face_index]
    #     back_point = Plane.from_frame(back_face).closest_point(int_point)

    #     back_frame = Frame(
    #         back_point,
    #         beam_a.centerline.direction if main_param < 0.5 else -beam_a.centerline.direction,
    #         back_face.normal,
    #     )
    #     back_frame.rotate(-math.pi / 2, back_frame.xaxis, back_point)
    #     return [front_frame, back_frame]

    # def validate_fastener_beam_compatibility(self, joint) -> tuple[int, int]:
    #     """Checks if the beams are compatible with the joint and sets the front and back face indices.

    #     returns the front and back face indices of the cross beam.

    #     Returns
    #     -------
    #     tuple[int, int]
    #         The front and back face indices of the cross beam.

    #     Raises
    #     ------
    #     BeamJoiningError
    #         If the beams are not compatible.

    #     """
    #     TOL = Tolerance()

    #     beam_a, beam_b = joint.elements[0:2]
    #     if not TOL.is_zero(angle_vectors(beam_a.frame.xaxis, beam_b.frame.xaxis) - (math.pi * 0.5)):
    #         raise FastenerApplicationError(elements=[beam_a, beam_b], fastener=self, message="Beams are not perpendicular")
    #     cross_vector = cross_vectors(beam_a.centerline.direction, beam_b.centerline.direction)
    #     main_faces = beam_ref_side_incidence_with_vector(beam_a, cross_vector)
    #     cross_faces = beam_ref_side_incidence_with_vector(beam_b, cross_vector)
    #     front_face_index = min(main_faces, key=main_faces.get)  # type: ignore
    #     cross_face_index = min(cross_faces, key=cross_faces.get)  # type: ignore

    #     if not TOL.is_zero(main_faces[front_face_index]):
    #         raise FastenerApplicationError(
    #             elements=[beam_a, beam_b],
    #             fastener=self,
    #             message="beam_a is not perpendicular to the cross vector",
    #         )
    #     if not TOL.is_zero(cross_faces[cross_face_index]):
    #         raise FastenerApplicationError(
    #             elements=[beam_a, beam_b],
    #             fastener=self,
    #             message="Cross beam is not perpendicular to the cross vector",
    #         )
    #     if not TOL.is_zero(
    #         distance_point_plane(
    #             beam_a.ref_sides[front_face_index].point,
    #             Plane.from_frame(beam_b.ref_sides[cross_face_index]),
    #         )
    #     ):
    #         raise FastenerApplicationError(elements=[beam_a, beam_b], fastener=self, message="beam faces are not coplanar")

    #     back_face_index = (front_face_index + 2) % 4
    #     cross_back_face_index = (cross_face_index + 2) % 4

    #     if not TOL.is_zero(
    #         distance_point_plane(
    #             beam_a.ref_sides[back_face_index].point,
    #             Plane.from_frame(beam_b.ref_sides[cross_back_face_index]),
    #         )
    #     ):
    #         raise FastenerApplicationError(elements=[beam_a, beam_b], fastener=self, message="beam faces are not coplanar")
    #     print("from workflow:", (front_face_index, back_face_index))
    #     return front_face_index, back_face_index
