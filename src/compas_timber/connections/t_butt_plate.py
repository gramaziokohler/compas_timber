import math
import os

from compas.geometry import Frame
from compas.geometry import Plane
from compas.geometry import angle_vectors
from compas.geometry import cross_vectors
from compas.geometry import distance_point_plane
from compas.tolerance import Tolerance

from compas_timber.connections.butt_joint import ButtJoint
from compas_timber.elements import Beam
from compas_timber.elements import CutFeature
from compas_timber.elements import MillVolume
from compas_timber.utils import intersection_line_line_param

from .joint import BeamJoinningError
from .solver import JointTopology

TOL = Tolerance()


class TButtPlateJoint(ButtJoint):
    """Represents a T-Butt type joint which joins the end of a beam along the length of another beam,
    trimming the main beam.

    This joint type is compatible with beams in T topology.

    Please use `TButtJoint.create()` to properly create an instance of this class and associate it with an model.

    Parameters
    ----------
    main_beam : :class:`~compas_timber.parts.Beam`
        The main beam to be joined.
    cross_beam : :class:`~compas_timber.parts.Beam`
        The cross beam to be joined.

    Attributes
    ----------
    main_beam : :class:`~compas_timber.parts.Beam`
        The main beam to be joined.
    cross_beam : :class:`~compas_timber.parts.Beam`
        The cross beam to be joined.

    """

    SUPPORTED_TOPOLOGY = JointTopology.TOPO_T
    HERE = os.path.dirname(os.path.normpath(os.path.normpath(__file__)))

    def __init__(self, main_beam=None, cross_beam=None, mill_depth=0, fastener=None, **kwargs):
        super(TButtPlateJoint, self).__init__(**kwargs)
        self.main_beam = main_beam
        self.cross_beam = cross_beam
        self.mill_depth = mill_depth
        if main_beam and cross_beam:
            self.elements.extend([main_beam, cross_beam])
        if fastener:
            self.fastener = fastener
            self.front_face_index, self.back_face_index = TButtPlateJoint.validate_fastener_beam_compatibility(
                self.fastener, [main_beam, cross_beam]
            )
            self.place_fasteners()

    def restore_beams_from_keys(self, model):
        """After de-serialization, restores references to the main and cross beams saved in the model."""
        self.main_beam = model.element_by_guid(self.main_beam_guid)
        self.cross_beam = model.element_by_guid(self.cross_beam_guid)

    @property
    def interactions(self):
        """Returns interactions between elements used by this joint."""
        interactions = []
        interactions.append((self.main_beam, self.cross_beam, self))
        for fastener in self.fasteners:
            interactions.append((self.main_beam, fastener, self))
            interactions.append((self.cross_beam, fastener, self))

        return interactions

    # ================================================================================================================================================================
    # class methods
    # ================================================================================================================================================================
    @classmethod
    def create(cls, model, *beams, **kwargs):
        """Creates a T-Butt type joint between the beams.

        Parameters
        ----------
        model : :class:`~compas_timber.model.TimberModel`
            The model to which the joint belongs.
        beams : :class:`~compas_timber.parts.Beam`
            The beams to be joined.
        mill_depth : float, optional
            The depth to mill the cross beam.
        fastener : :class:`~compas_timber.elements.PlateFastener`, optional
            The fastener to be used in the joint.

        Returns
        -------
        :class:`~compas_timber.connections.TButtPlateJoint`
            The created joint.

        """
        joint = TButtPlateJoint(*beams, **kwargs)
        for fastener in joint.fasteners:
            model.add_element(fastener)
        model.add_joint(joint)
        return joint

    def add_features(self):
        """Adds the trimming plane to the main beam (no features for the cross beam).

        This method is automatically called when joint is created by the call to `Joint.create()`.

        """
        assert self.main_beam and self.cross_beam  # should never happen

        if self.features:
            self.main_beam.remove_features(self.features)

        cutting_plane = None
        try:
            cutting_plane = self.get_main_cutting_plane()[0]
        except AttributeError as ae:
            raise BeamJoinningError(beams=self.beams, joint=self, debug_info=str(ae), debug_geometries=[cutting_plane])
        except Exception as ex:
            raise BeamJoinningError(beams=self.beams, joint=self, debug_info=str(ex))

        trim_feature = CutFeature(cutting_plane)
        if self.mill_depth:
            self.cross_beam.add_features(MillVolume(self.subtraction_volume()))
        self.main_beam.add_features(trim_feature)
        self.apply_interface_features()
        self.features = [trim_feature]

    def place_fasteners(self):
        """Adds the fasteners to the joint.

        This method is automatically called when joint is created by the call to `Joint.create()`.

        """
        frames = self.get_fastener_frames()
        for frame in frames:
            fastener = self.fastener.copy()
            fastener.frame = Frame(frame.point, frame.xaxis, frame.yaxis)
            for interface, element in zip(fastener.interfaces, self.beams):
                interface.element = element
            self.elements.append(fastener)

    @classmethod
    def validate_fastener_beam_compatibility(cls, fastener, beams):
        """Checks if the beams are compatible with the joint and sets the front and back face indices.

        returns the front and back face indices of the cross beam.

        Raises
        ------
        BeamJoinningError
            If the beams are not compatible.

        """
        main_beam, cross_beam = beams
        if not TOL.is_zero(angle_vectors(main_beam.frame.xaxis, cross_beam.frame.xaxis) - fastener.angle):
            raise BeamJoinningError(
                beams=[main_beam, cross_beam], joint=cls(), debug_info="Beams are not perpendicular"
            )

        cross_vector = cross_vectors(main_beam.centerline.direction, cross_beam.centerline.direction)
        main_faces = Beam.angle_beam_face_vector(main_beam, cross_vector)
        cross_faces = Beam.angle_beam_face_vector(cross_beam, cross_vector)

        front_face_index = min(main_faces, key=main_faces.get)
        cross_face_index = min(cross_faces, key=cross_faces.get)

        if not TOL.is_zero(main_faces[front_face_index]):
            raise BeamJoinningError(
                beams=[main_beam, cross_beam],
                joint=cls(),
                debug_info="Main beam is not perpendicular to the cross vector",
            )
        if not TOL.is_zero(cross_faces[cross_face_index]):
            raise BeamJoinningError(
                beams=[main_beam, cross_beam],
                joint=cls(),
                debug_info="Cross beam is not perpendicular to the cross vector",
            )
        if not TOL.is_zero(
            distance_point_plane(
                main_beam.faces[front_face_index].point,
                Plane.from_frame(cross_beam.faces[cross_face_index]),
            )
        ):
            raise BeamJoinningError(
                beams=[main_beam, cross_beam], joint=cls(), debug_info="beam faces are not coplanar"
            )
        back_face_index = (front_face_index + 2) % 4
        cross_back_face_index = (cross_face_index + 2) % 4
        if not TOL.is_zero(
            distance_point_plane(
                main_beam.faces[back_face_index].point,
                Plane.from_frame(cross_beam.faces[cross_back_face_index]),
            )
        ):
            raise BeamJoinningError(beams=[main_beam, cross_beam], joint=cls, debug_info="beam faces are not coplanar")
        return front_face_index, back_face_index

    def get_fastener_frames(self):
        """Calculates the frames of the fasteners.

        Returns
        -------
        :class:`~compas.geometry.Frame`
            The frames of the fasteners with the x-axis along the main_beam.centerline and the y-axis along the cross_beam.centerline, offset to lay on the beam_faces.

        """
        (main_point, main_param), (cross_point, _) = intersection_line_line_param(
            self.main_beam.centerline, self.cross_beam.centerline
        )
        int_point = (main_point + cross_point) * 0.5
        front_face = self.main_beam.faces[self.front_face_index]
        front_point = Plane.from_frame(front_face).closest_point(int_point)
        front_frame = Frame(
            front_point,
            self.main_beam.centerline.direction if main_param < 0.5 else -self.main_beam.centerline.direction,
            front_face.normal,
        )
        front_frame.rotate(-math.pi / 2, front_frame.xaxis, front_point)
        back_face = self.main_beam.faces[self.back_face_index]
        back_point = Plane.from_frame(back_face).closest_point(int_point)

        back_frame = Frame(
            back_point,
            self.main_beam.centerline.direction if main_param < 0.5 else -self.main_beam.centerline.direction,
            back_face.normal,
        )
        back_frame.rotate(-math.pi / 2, back_frame.xaxis, back_point)
        return [front_frame, back_frame]

    def apply_interface_features(self):
        """Applies the drill features of the joint to the beams.
        Drill features are defined by `fastener.holes`
        This assumes the same fastener on each side of the joint.
        """
        for fastener in self.fasteners:
            for beam, interface in zip([self.main_beam, self.cross_beam], fastener.interfaces):
                interface.element = beam
                interface.add_features()
