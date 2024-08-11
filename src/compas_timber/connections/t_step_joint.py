from compas_timber._fabrication import StepJoint
from compas_timber._fabrication import StepJointNotch

from .joint import Joint
from .solver import JointTopology


class TStepJoint(Joint):
    """Represents an T-Step type joint which joins two beams, one of them at it's end (main) and the other one along it's centerline (cross).
    Two or more cuts are is made on the main beam and a notch is made on the cross beam to fit the main beam.

    This joint type is compatible with beams in T topology.

    Please use `TStepJoint.create()` to properly create an instance of this class and associate it with an model.

    Parameters
    ----------
    main_beam : :class:`~compas_timber.parts.Beam`
        First beam to be joined.
    cross_beam : :class:`~compas_timber.parts.Beam`
        Second beam to be joined.
    step_depth : float
        Depth of the step cut. Combined with a heel cut it generates a double step cut.
    heel_depth : float
        Depth of the heel cut. Combined with a step cut it generates a double step cut.
    tapered_heel : bool
        If True, the heel cut is tapered.
    tenon_mortise_height : float
        Height of the tenon (main beam) mortise (cross beam) of the Step Joint. If None, the tenon and mortise featrue is not created.

    Attributes
    ----------
    main_beam : :class:`~compas_timber.parts.Beam`
        First beam to be joined.
    cross_beam : :class:`~compas_timber.parts.Beam`
        Second beam to be joined.
    step_depth : float
        Depth of the step cut. Combined with a heel cut it generates a double step cut.
    heel_depth : float
        Depth of the heel cut. Combined with a step cut it generates a double step cut.
    tapered_heel : bool
        If True, the heel cut is tapered.
    tenon_mortise_height : float
        Height of the tenon (main beam) mortise (cross beam) of the Step Joint. If None, the tenon and mortise featrue is not created.

    """

    SUPPORTED_TOPOLOGY = JointTopology.TOPO_T

    @property
    def __data__(self):
        data = super(TStepJoint, self).__data__
        data["main_beam"] = self.main_beam_guid
        data["cross_beam"] = self.cross_beam_guid
        data["step_depth"] = self.step_depth
        data["heel_depth"] = self.heel_depth
        data["tapered_heel"] = self.tapered_heel
        data["tenon_mortise_height"] = self.tenon_mortise_height
        return data

    def __init__(
        self,
        main_beam=None,
        cross_beam=None,
        step_depth=None,
        heel_depth=None,
        tapered_heel=None,
        tenon_mortise_height=None,
    ):
        super(TStepJoint, self).__init__()
        self.main_beam = main_beam
        self.cross_beam = cross_beam
        self.main_beam_guid = str(main_beam.guid) if main_beam else None
        self.cross_beam_guid = str(cross_beam.guid) if cross_beam else None

        self.step_depth = step_depth
        self.heel_depth = heel_depth
        self.tapered_heel = tapered_heel
        self.tenon_mortise_height = tenon_mortise_height

        self.start_y = (
            (self.cross_beam.width - self.main_beam.width) / 2 if self.cross_beam.width > self.main_beam.width else 0.0
        )
        self.notch_limited = False if self.main_beam.width >= self.cross_beam.width else True
        self.notch_width = self.main_beam.width
        self.strut_height = self.main_beam.height
        self.tenon_mortise_width = self.main_beam.width / 4

        self.features = []

    @property
    def beams(self):
        return [self.main_beam, self.cross_beam]

    @property
    def cross_beam_ref_face_index(self):
        face_dict = self._beam_side_incidence(self.main_beam, self.cross_beam, ignore_ends=True)
        face_index = min(face_dict, key=face_dict.get)
        return face_index

    @property
    def main_beam_ref_face_index(self):
        face_dict = self._beam_side_incidence(self.cross_beam, self.main_beam, ignore_ends=True)
        face_index = max(face_dict, key=face_dict.get)
        return face_index

    def add_features(self):
        """Adds the required trimming features to both beams.

        This method is automatically called when joint is created by the call to `Joint.create()`.

        """
        assert self.main_beam and self.cross_beam  # should never happen

        if self.features:
            self.main_beam.remove_features(self.features)
            self.cross_beam.remove_features(self.features)

        main_beam_ref_face = self.main_beam.faces(self.main_beam_ref_face_index)
        cross_beam_ref_face = self.cross_beam.faces(self.cross_beam_ref_face_index)

        # generate step joint notch features
        cross_feature = StepJointNotch.from_plane_and_beam(
            main_beam_ref_face,
            self.cross_beam,
            self.start_y,
            self.notch_limited,
            self.notch_width,
            self.step_depth,
            self.heel_depth,
            self.tapered_heel,
            self.strut_height,
            self.cross_beam_ref_face_index,
        )
        # generate step joint features
        main_feature = StepJoint.from_plane_and_beam(
            cross_beam_ref_face,
            self.main_beam,
            self.step_depth,
            self.heel_depth,
            self.tapered_heel,
            self.main_beam_ref_face_index,
        )
        # generate tenon and mortise features
        if self.tenon_mortise_height:
            cross_feature.add_mortise(self.tenon_mortise_height, self.tenon_mortise_width, self.cross_beam)
            main_feature.add_tenon(self.tenon_mortise_height, self.tenon_mortise_width)

        # add features to beams
        print(cross_feature)
        self.main_beam.add_features(main_feature)
        self.cross_beam.add_features(cross_feature)
        # add features to joint
        self.features = [cross_feature, main_feature]

    def restore_beams_from_keys(self, model):
        """After de-serialization, restores references to the main and cross beams saved in the model."""
        self.main_beam = model.elementdict[self.main_beam_guid]
        self.cross_beam = model.elementdict[self.cross_beam_guid]
