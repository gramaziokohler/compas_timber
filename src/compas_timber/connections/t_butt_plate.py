import math
from compas_timber.connections.butt_joint import ButtJoint
from compas_timber.elements import CutFeature
from compas_timber.elements import MillVolume
from compas_timber.elements import DrillFeature
from compas_timber.elements import Beam
from compas.geometry import cross_vectors
from compas.geometry import angle_vectors
from compas.geometry import distance_point_plane
from compas.geometry import Plane
from compas.geometry import Line
from compas.tolerance import Tolerance
from compas.geometry import Frame
from compas_timber.elements.plate_fastener import PlateFastener
from compas_timber.utils import intersection_line_line_param
from compas.geometry import Transformation
from compas.data import json_load
import os


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

    def __init__(self, main_beam=None, cross_beam=None, mill_depth=0, fastener = None, **kwargs):
        super(TButtPlateJoint, self).__init__(main_beam, cross_beam, mill_depth, fastener, **kwargs)
        if main_beam and cross_beam:
            self.check_compatiblity()
            path = os.path.dirname(__file__)
            path_parts = path.split("\\")
            path = "/".join(path_parts[:-1])
            path += "/elements/fasteners/t_butt_plate.json"
            self.fastener = json_load(path)
            if fastener.shape:
                self._fasteners = [PlateFastener(fastener.shape), PlateFastener(fastener.shape)]
            else:
                self._fasteners = [PlateFastener(), PlateFastener()]
            self.place_fasteners()
            self.test = []

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

    @property
    def elements(self):
        return [self.main_beam, self.cross_beam] + list(self._fasteners)

#================================================================================================================================================================
# class methods
#================================================================================================================================================================
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
        joint = cls(*beams, **kwargs)
        for fastener in joint.fasteners:
            model.add_element(fastener)
        model.add_joint(joint)

        return joint

    def add_extensions(self):
        """Calculates and adds the necessary extensions to the beams.

        This method is automatically called when joint is created by the call to `Joint.create()`.

        Raises
        ------
        BeamJoinningError
            If the extension could not be calculated.

        """
        assert self.main_beam and self.cross_beam
        try:
            cutting_plane = self.get_main_cutting_plane()[0]
            start_main, end_main = self.main_beam.extension_to_plane(cutting_plane)
        except AttributeError as ae:
            raise BeamJoinningError(beams=self.beams, joint=self, debug_info=str(ae), debug_geometries=[cutting_plane])
        except Exception as ex:
            raise BeamJoinningError(beams=self.beams, joint=self, debug_info=str(ex))
        extension_tolerance = 0.01  # TODO: this should be proportional to the unit used
        self.main_beam.add_blank_extension(start_main + extension_tolerance, end_main + extension_tolerance, self.guid)

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
        self.apply_drill_features()
        self.features = [trim_feature]




    def place_fasteners(self):
        """Adds the fasteners to the joint.

        This method is automatically called when joint is created by the call to `Joint.create()`.

        """
        frames = self.get_fastener_frames()
        for frame, fastener in zip(frames, self.fasteners):
            fastener.frame = frame



    def check_compatiblity(self):
        """Checks if the beams are compatible with the joint and sets the front and back face indices.

        Raises
        ------
        BeamJoinningError
            If the beams are not compatible.

        """
        if not TOL.is_zero(angle_vectors(self.main_beam.frame.xaxis, self.cross_beam.frame.xaxis)-math.pi/2):
            raise BeamJoinningError(beams=self.beams, joint=self, debug_info="Beams are not perpendicular")

        cross_vector = cross_vectors(self.main_beam.centerline.direction, self.cross_beam.centerline.direction)
        main_faces = Beam.angle_beam_side_normal_to_vector(self.main_beam, cross_vector)
        cross_faces = Beam.angle_beam_side_normal_to_vector(self.cross_beam, cross_vector)

        self.front_face_index = min(main_faces, key=main_faces.get)
        cross_face_index = min(cross_faces, key=cross_faces.get)

        if not TOL.is_zero(main_faces[self.front_face_index]):
            raise BeamJoinningError(beams=self.beams, joint=self, debug_info="Main beam is not perpendicular to the cross vector")
        if not TOL.is_zero(cross_faces[cross_face_index]):
            raise BeamJoinningError(beams=self.beams, joint=self, debug_info="Cross beam is not perpendicular to the cross vector")
        if not TOL.is_zero(distance_point_plane(self.main_beam.faces[self.front_face_index].point, Plane.from_frame(self.cross_beam.faces[cross_face_index]))):
            raise BeamJoinningError(beams=self.beams, joint=self, debug_info="beam faces are not coplanar")

        self.back_face_index = (self.front_face_index + 2) % 4
        cross_back_face_index = (cross_face_index + 2) % 4
        if not TOL.is_zero(distance_point_plane(self.main_beam.faces[self.back_face_index].point, Plane.from_frame(self.cross_beam.faces[cross_back_face_index]))):
            raise BeamJoinningError(beams=self.beams, joint=self, debug_info="beam faces are not coplanar")



    def get_fastener_frames(self):
        """Calculates the frames of the fasteners.

        Returns
        -------
        :class:`~compas.geometry.Frame`
            The frames of the fasteners with the x-axis along the main_beam.centerline and the y-axis along the cross_beam.centerline, offset to lay on the beam_faces.

        """
        (main_point, main_param), (cross_point, _) = intersection_line_line_param(self.main_beam.centerline, self.cross_beam.centerline)
        int_point = (main_point + cross_point) * 0.5
        front_face = self.main_beam.faces[self.front_face_index]
        front_point = Plane.from_frame(front_face).closest_point(int_point)

        front_frame = Frame(front_point, self.main_beam.centerline.direction if main_param < 0.5 else -self.main_beam.centerline.direction, front_face.normal)
        front_frame.rotate(-math.pi/2, front_frame.xaxis, front_point)
        back_face = self.main_beam.faces[self.back_face_index]
        back_point = Plane.from_frame(back_face).closest_point(int_point)

        back_frame = Frame(back_point, self.main_beam.centerline.direction if main_param < 0.5 else -self.main_beam.centerline.direction, back_face.normal)
        back_frame.rotate(-math.pi/2, back_frame.xaxis, back_point)
        return [front_frame, back_frame]

    def apply_drill_features(self):
        """Returns the drill features of the joint."""
        fastener = list(self.fasteners)[0]
        transformation = Transformation.from_frame_to_frame(Frame.worldXY(), fastener.frame)
        if self.front_face_index%2 == 0:
            depth = self.main_beam.width
        else:
            depth = self.main_beam.height
        for beam, hole_list in zip([self.main_beam, self.cross_beam], self.fastener.holes):
            for hole in hole_list:
                point = hole[0].copy()
                point.transform(transformation)
                drill_feature = DrillFeature(Line.from_point_direction_length(point, -fastener.frame.zaxis, depth), hole[1], depth)
                beam.add_features(drill_feature)
                self.test.append(Line.from_point_direction_length(point, -fastener.frame.zaxis, depth))
