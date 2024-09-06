from compas_timber.elements import CutFeature
from compas_timber.elements import MillVolume

from .butt_joint import ButtJoint
from .joint import BeamJoinningError
from .solver import JointTopology


class LButtJoint(ButtJoint):
    """Represents an L-Butt type joint which joins two beam in their ends, trimming the main beam.

    This joint type is compatible with beams in L topology.

    Please use `LButtJoint.create()` to properly create an instance of this class and associate it with an model.

    Parameters
    ----------
    main_beam : :class:`~compas_timber.parts.Beam`
        The main beam to be joined.
    cross_beam : :class:`~compas_timber.parts.Beam`
        The cross beam to be joined.
    small_beam_butts : bool, default False
        If True, the beam with the smaller cross-section will be trimmed. Otherwise, the main beam will be trimmed.
    modify_cross : bool, default True
        If True, the cross beam will be extended to the opposite face of the main beam and cut with the same plane.
    reject_i : bool, default False
        If True, the joint will be rejected if the beams are not in I topology (i.e. main butts at crosses end).

    Attributes
    ----------
    main_beam : :class:`~compas_timber.parts.Beam`
        The main beam to be joined.
    cross_beam : :class:`~compas_timber.parts.Beam`
        The cross beam to be joined.
    small_beam_butts : bool, default False
        If True, the beam with the smaller cross-section will be trimmed. Otherwise, the main beam will be trimmed.
    modify_cross : bool, default True
        If True, the cross beam will be extended to the opposite face of the main beam and cut with the same plane.
    reject_i : bool, default False
        If True, the joint will be rejected if the beams are not in I topology (i.e. main butts at crosses end).

    """

    SUPPORTED_TOPOLOGY = JointTopology.TOPO_L

    @property
    def __data__(self):
        data = super(LButtJoint, self).__data__
        data["small_beam_butts"] = self.small_beam_butts
        data["modify_cross"] = self.modify_cross
        data["reject_i"] = self.reject_i
        return data

    def __init__(
        self,
        main_beam=None,
        cross_beam=None,
        mill_depth=0,
        small_beam_butts=False,
        modify_cross=True,
        reject_i=False,
        **kwargs
    ):
        if small_beam_butts and main_beam and cross_beam:
            if main_beam.width * main_beam.height > cross_beam.width * cross_beam.height:
                main_beam, cross_beam = cross_beam, main_beam
        super(LButtJoint, self).__init__(main_beam, cross_beam, mill_depth, **kwargs)
        self.modify_cross = modify_cross
        self.small_beam_butts = small_beam_butts
        self.reject_i = reject_i

    def get_cross_cutting_plane(self):
        assert self.main_beam and self.cross_beam
        _, cfr = self.get_face_most_towards_beam(self.cross_beam, self.main_beam, ignore_ends=True)
        return cfr

    def get_main_cutting_plane(self):
        assert self.main_beam and self.cross_beam

        index, _ = self.get_face_most_towards_beam(self.main_beam, self.cross_beam, ignore_ends=False)
        if self.reject_i and index in [4, 5]:
            raise BeamJoinningError(
                beams=self.beams, joint=self, debug_info="Beams are in I topology and reject_i flag is True"
            )
        return super(LButtJoint, self).get_main_cutting_plane()

    def add_extensions(self):
        assert self.main_beam and self.cross_beam  # should never happen

        try:
            main_cutting_plane = self.get_main_cutting_plane()[0]
            start_main, end_main = self.main_beam.extension_to_plane(main_cutting_plane)
            extension_tolerance = 0.01  # TODO: this should be proportional to the unit used
            self.main_beam.add_blank_extension(
                start_main + extension_tolerance, end_main + extension_tolerance, self.guid
            )

            if self.modify_cross:
                cross_cutting_plane = self.get_cross_cutting_plane()
                start_cross, end_cross = self.cross_beam.extension_to_plane(cross_cutting_plane)
                self.cross_beam.add_blank_extension(
                    start_cross + extension_tolerance, end_cross + extension_tolerance, self.guid
                )
        except Exception as ex:
            debug_info = getattr(ex, "debug_info", str(ex))
            raise BeamJoinningError(beams=self.beams, joint=self, debug_info=debug_info)

    def add_features(self):
        """Adds the required extension and trimming features to both beams.

        This method is automatically called when joint is created by the call to `Joint.create()`.

        """
        assert self.main_beam and self.cross_beam  # should never happen
        if self.features:
            self.main_beam.remove_features(self.features)

        try:
            main_cutting_plane = self.get_main_cutting_plane()[0]
            cross_cutting_plane = self.get_cross_cutting_plane()
        except Exception as ex:
            debug_info = getattr(ex, "debug_info", str(ex))
            raise BeamJoinningError(beams=self.beams, joint=self, debug_info=debug_info)

        if self.modify_cross:
            f_cross = CutFeature(cross_cutting_plane)
            self.cross_beam.add_features(f_cross)
            self.features.append(f_cross)

        f_main = CutFeature(main_cutting_plane)
        if self.mill_depth:
            self.cross_beam.add_features(MillVolume(self.subtraction_volume()))
        self.main_beam.add_features(f_main)
        self.features.append(f_main)
