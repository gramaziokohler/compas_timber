from compas.geometry import Frame
from compas_timber.parts import CutFeature

from .joint import BeamJoinningError
from .joint import Joint
from .solver import JointTopology


class LButtJoint(Joint):
    """Represents an L-Butt type joint which joins two beam in their ends, trimming the main beam.

    This joint type is compatible with beams in L topology.

    Please use `LButtJoint.create()` to properly create an instance of this class and associate it with an assembly.

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

    def __init__(
        self, main_beam=None, cross_beam=None, small_beam_butts=False, modify_cross=True, reject_i=False, **kwargs
    ):
        super(LButtJoint, self).__init__(beams=(main_beam, cross_beam), **kwargs)

        if small_beam_butts and main_beam and cross_beam:
            if main_beam.width * main_beam.height > cross_beam.width * cross_beam.height:
                main_beam, cross_beam = cross_beam, main_beam

        self.main_beam = main_beam
        self.cross_beam = cross_beam
        self.main_beam_key = main_beam.key if main_beam else None
        self.cross_beam_key = cross_beam.key if cross_beam else None
        self.modify_cross = modify_cross
        self.small_beam_butts = small_beam_butts
        self.reject_i = reject_i
        self.features = []

    @property
    def __data__(self):
        data_dict = {
            "main_beam_key": self.main_beam_key,
            "cross_beam_key": self.cross_beam_key,
            "small_beam_butts": self.small_beam_butts,
            "modify_cross": self.modify_cross,
            "reject_i": self.reject_i,
        }
        data_dict.update(super(LButtJoint, self).__data__)
        return data_dict

    @classmethod
    def __from_data__(cls, value):
        instance = cls(
            frame=Frame.__from_data__(value["frame"]),
            key=value["key"],
            small_beam_butts=value["small_beam_butts"],
            modify_cross=value["modify_cross"],
            reject_i=value["reject_i"],
        )
        instance.main_beam_key = value["main_beam_key"]
        instance.cross_beam_key = value["cross_beam_key"]
        return instance

    def get_main_cutting_plane(self):
        assert self.main_beam and self.cross_beam

        index, _ = self.get_face_most_towards_beam(self.main_beam, self.cross_beam, ignore_ends=False)
        if self.reject_i and index in [4, 5]:
            raise BeamJoinningError(
                beams=self.beams, joint=self, debug_info="Beams are in I topology and reject_i flag is True"
            )

        index, cfr = self.get_face_most_ortho_to_beam(self.main_beam, self.cross_beam, ignore_ends=True)
        cfr = Frame(cfr.point, cfr.xaxis, cfr.yaxis * -1.0)  # flip normal
        return cfr

    def get_cross_cutting_plane(self):
        assert self.main_beam and self.cross_beam
        _, cfr = self.get_face_most_towards_beam(self.cross_beam, self.main_beam, ignore_ends=True)
        return cfr

    def restore_beams_from_keys(self, assemly):
        """After de-serialization, resotres references to the main and cross beams saved in the assembly."""
        self.main_beam = assemly.find_by_key(self.main_beam_key)
        self.cross_beam = assemly.find_by_key(self.cross_beam_key)
        self._beams = (self.main_beam, self.cross_beam)

    def add_features(self):
        """Adds the required extension and trimming features to both beams.

        This method is automatically called when joint is created by the call to `Joint.create()`.

        """
        assert self.main_beam and self.cross_beam  # should never happen
        if self.features:
            self.main_beam.remove_features(self.features)
        start_main, start_cross = None, None

        try:
            main_cutting_plane = self.get_main_cutting_plane()
            cross_cutting_plane = self.get_cross_cutting_plane()
            start_main, end_main = self.main_beam.extension_to_plane(main_cutting_plane)
            start_cross, end_cross = self.cross_beam.extension_to_plane(cross_cutting_plane)
        except BeamJoinningError as be:
            raise be
        except AttributeError as ae:
            # I want here just the plane that caused the error
            geometries = [cross_cutting_plane] if start_main is not None else [main_cutting_plane]
            raise BeamJoinningError(beams=self.beams, joint=self, debug_info=str(ae), debug_geometries=geometries)
        except Exception as ex:
            raise BeamJoinningError(beams=self.beams, joint=self, debug_info=str(ex))

        extension_tolerance = 0.01  # TODO: this should be proportional to the unit used

        if self.modify_cross:
            self.cross_beam.add_blank_extension(
                start_cross + extension_tolerance, end_cross + extension_tolerance, self.key
            )
            f_cross = CutFeature(cross_cutting_plane)
            self.cross_beam.add_features(f_cross)
            self.features.append(f_cross)

        self.main_beam.add_blank_extension(start_main + extension_tolerance, end_main + extension_tolerance, self.key)

        f_main = CutFeature(main_cutting_plane)
        self.main_beam.add_features(f_main)
        self.features.append(f_main)
