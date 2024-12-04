from compas_timber._fabrication import Lap
from compas_timber.connections.utilities import beam_ref_side_incidence_with_vector

from .joint import BeamJoinningError
from .joint import Joint
from .solver import JointTopology

from compas.geometry import Plane
from compas.tolerance import TOL


class LHalfLapJoint(Joint):
    """Represents a L-Lap type joint which joins the ends of two beams,
    trimming the main beam.

    This joint type is compatible with beams in L topology.

    Please use `LHalfLapJoint.create()` to properly create an instance of this class and associate it with an model.

    Parameters
    ----------
    main_beam : :class:`~compas_timber.parts.Beam`
        The main beam to be joined.
    cross_beam : :class:`~compas_timber.parts.Beam`
        The cross beam to be joined.
    flip_lap_side : bool
        If True, the lap is flipped to the other side of the beams.
    cut_plane_bias : float
        Allows lap to be shifted deeper into one beam or the other. Value should be between 0 and 1.0 without completely cutting through either beam. Default is 0.5.

    Attributes
    ----------
    beams : list(:class:`~compas_timber.parts.Beam`)
        The beams joined by this joint.
    main_beam : :class:`~compas_timber.parts.Beam`
        The main beam to be joined.
    cross_beam : :class:`~compas_timber.parts.Beam`
        The cross beam to be joined.
    flip_lap_side : bool
        If True, the lap is flipped to the other side of the beams.
    cut_plane_bias : float
        Allows lap to be shifted deeper into one beam or the other. Value should be between 0 and 1.0 without completely cutting through either beam. Default is 0.5.
    """

    SUPPORTED_TOPOLOGY = JointTopology.TOPO_L

    @property
    def __data__(self):
        data = super(LHalfLapJoint, self).__data__
        data["main_beam_guid"] = self.main_beam_guid
        data["cross_beam_guid"] = self.cross_beam_guid
        data["flip_lap_side"] = self.flip_lap_side
        data["cut_plane_bias"] = self.cut_plane_bias
        return data

    def __init__(self, main_beam=None, cross_beam=None, flip_lap_side=None, cut_plane_bias=None, **kwargs):
        super(LHalfLapJoint, self).__init__(**kwargs)
        self.main_beam = main_beam
        self.cross_beam = cross_beam
        self.main_beam_guid = kwargs.get("main_beam_guid", None) or str(main_beam.guid)
        self.cross_beam_guid = kwargs.get("cross_beam_guid", None) or str(cross_beam.guid)

        self.flip_lap_side = flip_lap_side
        self.cut_plane_bias = 0.5 if cut_plane_bias is None else cut_plane_bias
        self.features = []

        self.cross_vector = self.main_beam.centerline.direction.cross(self.cross_beam.centerline.direction)
        self.main_width = self.main_beam.width if self.main_ref_side_index % 2 == 0 else self.main_beam.height
        self.cross_width = self.cross_beam.width if self.cross_ref_side_index % 2 == 0 else self.cross_beam.height

    @property
    def beams(self):
        return [self.main_beam, self.cross_beam]

    @property
    def cross_ref_side_index(self):
        ref_side_dict = beam_ref_side_incidence_with_vector(self.cross_beam, self.cross_vector, ignore_ends=True)
        if self.flip_lap_side:
            return max(ref_side_dict, key=ref_side_dict.get)
        else:
            return min(ref_side_dict, key=ref_side_dict.get)

    @property
    def main_ref_side_index(self):
        ref_side_dict = beam_ref_side_incidence_with_vector(self.main_beam, self.cross_vector, ignore_ends=True)
        if self.flip_lap_side:
            return min(ref_side_dict, key=ref_side_dict.get)
        else:
            return max(ref_side_dict, key=ref_side_dict.get)

    @property
    def cross_cutting_surface(self):
        index = self.main_ref_side_index
        if self.flip_lap_side:
            index += 1
        else:
            index -= 1
        return self.main_beam.side_as_surface(index % 4)

    @property
    def main_cutting_surface(self):
        index = self.cross_ref_side_index
        if self.flip_lap_side:
            index += 1
        else:
            index -= 1
        return self.cross_beam.side_as_surface(index % 4)

    @property
    def cross_lap_depth(self):
        return ((self.cross_cutting_surface.ysize + self.main_cutting_surface.ysize) / 2) * (1 - self.cut_plane_bias)

    @property
    def main_lap_depth(self):
        return ((self.cross_cutting_surface.ysize + self.main_cutting_surface.ysize) / 2) * self.cut_plane_bias

    def add_extensions(self):
        """Calculates and adds the necessary extensions to the beams.

        This method is automatically called when joint is created by the call to `Joint.create()`.

        Raises
        ------
        BeamJoinningError
            If the extension could not be calculated.

        """
        assert self.cross_beam and self.main_beam
        start_a, start_b = None, None
        try:
            main_plane = Plane.from_frame(self.main_cutting_surface.frame)
            cross_plane = Plane.from_frame(self.cross_cutting_surface.frame)
            start_a, end_a = self.cross_beam.extension_to_plane(main_plane)
            start_b, end_b = self.beam_b.extension_to_plane(cross_plane)
        except AttributeError as ae:
            # I want here just the plane that caused the error
            geometries = [cross_plane] if start_a is not None else [main_plane]
            raise BeamJoinningError(self.beams, self, debug_info=str(ae), debug_geometries=geometries)
        except Exception as ex:
            raise BeamJoinningError(self.beams, self, debug_info=str(ex))
        self.cross_beam.add_blank_extension(start_a, end_a, self.cross_beam_guid)
        self.main_beam.add_blank_extension(start_b, end_b, self.main_beam_guid)

    def add_features(self):
        """Adds the required extension and trimming features to both beams.

        This method is automatically called when joint is created by the call to `Joint.create()`.

        """
        assert self.main_beam and self.cross_beam

        if self.features:
            self.main_beam.remove_features(self.features)
            self.cross_beam.remove_features(self.features)

        # check if the geometry is valid
        self.check_geometry()

        # cross Lap feature
        cross_feature = Lap.from_plane_and_beam(
            self.cross_cutting_surface.frame,
            self.cross_beam,
            self.main_width,
            self.cross_lap_depth,
            ref_side_index=self.cross_ref_side_index,
        )
        self.cross_beam.add_features(cross_feature)

        # main Lap feature
        main_feature = Lap.from_plane_and_beam(
            self.main_cutting_surface.frame,
            self.main_beam,
            self.cross_width,
            self.main_lap_depth,
            ref_side_index=self.main_ref_side_index,
        )
        self.main_beam.add_features(main_feature)

        # register features to the joint
        self.features = [cross_feature, main_feature]

    def check_geometry(self):
        """Checks if the geometry of the beams is valid for the joint.

        Raises
        ------
        BeamJoinningError
            If the geometry is invalid.

        """
        # check if the beams are aligned
        for beam in self.beams:
            beam_normal = beam.frame.normal.unitized()
            dot = abs(beam_normal.dot(self.cross_vector.unitized()))
            if not (TOL.is_zero(dot) or TOL.is_close(dot, 1)):
                raise BeamJoinningError(
                    self.main_beam,
                    self.cross_beam,
                    debug_info="The the two beams are not aligned to create a Half Lap joint.",
                )

    def restore_beams_from_keys(self, model):
        """After de-serialization, restores references to the main and cross beams saved in the model."""
        self.main_beam = model.element_by_guid(self.main_beam_guid)
        self.cross_beam = model.element_by_guid(self.cross_beam_guid)
