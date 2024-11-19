from compas_timber._fabrication import StepJoint
from compas_timber._fabrication import StepJointNotch
from compas_timber.connections.utilities import are_beams_coplanar
from compas_timber.connections.utilities import beam_ref_side_incidence
from compas_timber.connections.utilities import beam_ref_side_incidence_with_vector
from compas_timber.connections.utilities import check_beam_alignment

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
    step_shape : int
        Shape of the step feature. 0: step, 1: heel, 2: double.
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
    step_shape : int
        Shape of the step feature. 0: step, 1: heel, 2: double.
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
        data["step_shape"] = self.step_shape
        data["step_depth"] = self.step_depth
        data["heel_depth"] = self.heel_depth
        data["tapered_heel"] = self.tapered_heel
        data["tenon_mortise_height"] = self.tenon_mortise_height
        return data

    # fmt: off
    def __init__(
        self,
        main_beam,
        cross_beam,
        step_shape=None,
        step_depth=None,
        heel_depth=None,
        tapered_heel=None,
        tenon_mortise_height=None,
        **kwargs
    ):
        super(TStepJoint, self).__init__(**kwargs)
        self.main_beam = main_beam
        self.cross_beam = cross_beam
        self.elements.extend([main_beam, cross_beam])
        self.main_beam_guid = kwargs.get("main_beam_guid", None) or str(main_beam.guid)
        self.cross_beam_guid = kwargs.get("cross_beam_guid", None) or str(cross_beam.guid)

        self.step_shape = 0 if step_shape is None else step_shape
        self.step_depth, self.heel_depth = self.set_step_depths(step_depth, heel_depth)

        self.tapered_heel = tapered_heel
        self.tenon_mortise_height = tenon_mortise_height

        # Check alignment to determine if the width and height of the main_beam (beam_b) should be swapped
        swap_dimensions = check_beam_alignment(self.cross_beam, self.main_beam)
        # For the main beam, use width or height based on the alignment result
        main_width = self.main_beam.width if swap_dimensions else self.main_beam.height
        main_height = self.main_beam.height if swap_dimensions else self.main_beam.width

        self.start_y = (self.cross_beam.width - main_width) / 2 if self.cross_beam.width > main_width else 0.0
        self.notch_limited = main_width < self.cross_beam.width
        self.notch_width = main_width
        self.strut_height = main_height
        self.tenon_mortise_width = main_width / 4

        self.features = []

    @property
    def beams(self):
        return [self.main_beam, self.cross_beam]

    @property
    def cross_beam_ref_side_index(self):
        ref_side_dict = beam_ref_side_incidence(self.main_beam, self.cross_beam, ignore_ends=True)
        ref_side_index = min(ref_side_dict, key=ref_side_dict.get)
        return ref_side_index

    @property
    def main_beam_ref_side_index(self):
        cross_beam_ref_side = self.cross_beam.ref_sides[self.cross_beam_ref_side_index]
        ref_side_dict = beam_ref_side_incidence_with_vector(
            self.main_beam, cross_beam_ref_side.normal, ignore_ends=True
        )
        ref_side_index = max(ref_side_dict, key=ref_side_dict.get)
        return ref_side_index

    def set_step_depths(self, step_depth=None, heel_depth=None):
        """Sets the default step and heel depths based on the joint type if they are not provided."""
        if self.step_shape == 0:  # 'step' shape
            step_depth = step_depth if step_depth is not None else self.cross_beam.height / 4
            heel_depth = 0.0
        elif self.step_shape == 1:  # 'heel' shape
            step_depth = 0.0
            heel_depth = heel_depth if heel_depth is not None else self.cross_beam.height / 4
        elif self.step_shape == 2:  # 'double' shape
            step_depth = step_depth if step_depth is not None else self.cross_beam.height / 6
            heel_depth = heel_depth if heel_depth is not None else self.cross_beam.height / 4
        else:
            raise ValueError("Step shape must be ether: 0:step, 1:heel, 2:double.")

        return step_depth, heel_depth

    def add_features(self):
        """Adds the required trimming features to both beams.

        This method is automatically called when joint is created by the call to `Joint.create()`.

        """
        # TODO: In the future the step, heel and tenon mortise depths should be proportional to the cross beam section wheareas the proportions are defined by the national norms.
        # TODO: As well the step shape should maybe be defined automatically by the shear reqirements of the joint.

        assert self.main_beam and self.cross_beam  # should never happen
        assert are_beams_coplanar(
            self.main_beam, self.cross_beam
        ), "The beams are not coplanar, the joint cannot be created."

        if self.features:
            self.main_beam.remove_features(self.features)
            self.cross_beam.remove_features(self.features)

        main_beam_ref_side = self.main_beam.ref_sides[self.main_beam_ref_side_index]
        cross_beam_ref_side = self.cross_beam.ref_sides[self.cross_beam_ref_side_index]

        # generate step joint notch features
        cross_feature = StepJointNotch.from_plane_and_beam(
            main_beam_ref_side,
            self.cross_beam,
            self.start_y,
            self.notch_limited,
            self.notch_width,
            self.step_depth,
            self.heel_depth,
            self.strut_height,
            self.tapered_heel,
            self.cross_beam_ref_side_index,
        )

        # generate step joint features
        main_feature = StepJoint.from_plane_and_beam(
            cross_beam_ref_side,
            self.main_beam,
            self.step_depth,
            self.heel_depth,
            self.tapered_heel,
            self.main_beam_ref_side_index,
        )

        # generate tenon and mortise features
        if self.tenon_mortise_height:
            cross_feature.add_mortise(self.tenon_mortise_width, self.tenon_mortise_height, self.cross_beam)
            main_feature.add_tenon(self.tenon_mortise_width, self.tenon_mortise_height)
        # add features to beams
        self.main_beam.add_features(main_feature)
        self.cross_beam.add_features(cross_feature)
        # add features to joint
        self.features = [cross_feature, main_feature]

    def restore_beams_from_keys(self, model):
        """After de-serialization, restores references to the main and cross beams saved in the model."""
        self.main_beam = model.element_by_guid(self.main_beam_guid)
        self.cross_beam = model.element_by_guid(self.cross_beam_guid)
