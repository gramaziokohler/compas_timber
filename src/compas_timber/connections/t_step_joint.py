import warnings

from compas.geometry import dot_vectors
from compas.tolerance import TOL

from compas_timber.errors import BeamJoiningError
from compas_timber.fabrication import StepJoint
from compas_timber.fabrication import StepJointNotch
from compas_timber.fabrication import StepShapeType

from .joint import Joint
from .solver import JointTopology
from .utilities import beam_ref_side_incidence
from .utilities import beam_ref_side_incidence_with_vector


class TStepJoint(Joint):
    """Represents an T-Step type joint which joins two beams, one of them at it's end (main) and the other one along it's centerline (cross).
    Two or more cuts are is made on the main beam and a notch is made on the cross beam to fit the main beam.

    This joint type is compatible with beams in T topology.

    Please use `TStepJoint.create()` to properly create an instance of this class and associate it with a model.

    Parameters
    ----------
    main_beam : :class:`~compas_timber.elements.Beam`
        First beam to be joined.
    cross_beam : :class:`~compas_timber.elements.Beam`
        Second beam to be joined.
    step_shape : str
        The shape of the step cut. One of :class:`~compas_timber.fabrication.StepShapeType`: STEP, HEEL, TAPERED_HEEL, or DOUBLE.
        The shape type takes priority: depths irrelevant to the chosen shape are ignored and forced to zero. Defaults to ``StepShapeType.STEP``.
    step_depth : float, optional
        Depth of the step cut. Applicable only to shape types with a step component (STEP, DOUBLE).
        Defaults to a value proportional to the cross beam's cross-section.
    heel_depth : float, optional
        Depth of the heel cut. Applicable only to shape types with a heel component (HEEL, TAPERED_HEEL, DOUBLE).
        Defaults to a value proportional to the cross beam's cross-section.
    tenon_mortise_height : float, optional
        Height of the tenon/mortise feature. If None, no tenon or mortise is created.

    Attributes
    ----------
    main_beam : :class:`~compas_timber.elements.Beam`
        First beam to be joined.
    cross_beam : :class:`~compas_timber.elements.Beam`
        Second beam to be joined.
    step_shape : str
        The shape of the step cut. One of :class:`~compas_timber.fabrication.StepShapeType`: STEP, HEEL, TAPERED_HEEL, or DOUBLE.
    step_depth : float
        Depth of the step cut. Applicable only to shape types with a step component (STEP, DOUBLE). Zero otherwise.
    heel_depth : float
        Depth of the heel cut. Applicable only to shape types with a heel component (HEEL, TAPERED_HEEL, DOUBLE). Zero otherwise.
    tenon_mortise_height : float
        Height of the tenon/mortise feature. None if not created.

    """

    SUPPORTED_TOPOLOGY = JointTopology.TOPO_T

    @property
    def __data__(self):
        data = super(TStepJoint, self).__data__
        data["step_shape"] = self.step_shape
        data["step_depth"] = self.step_depth
        data["heel_depth"] = self.heel_depth
        data["tenon_mortise_height"] = self.tenon_mortise_height
        return data

    # fmt: off
    def __init__(
        self,
        main_beam=None,
        cross_beam=None,
        step_shape=None,
        step_depth=None,
        heel_depth=None,
        tenon_mortise_height=None,
        **kwargs
    ):
        super(TStepJoint, self).__init__(elements=(main_beam,cross_beam), **kwargs)
        self.step_shape = step_shape or StepShapeType.STEP
        self._tapered_heel = self.step_shape == StepShapeType.TAPERED_HEEL

        self.step_depth = step_depth
        self.heel_depth = heel_depth
        self.tenon_mortise_height = tenon_mortise_height

        self.features = []
        if self.main_beam and self.cross_beam:
            self._set_unset_attributes()  # resolve defaults at init if beams are provided

    @property
    def main_beam(self):
        return self.element_a

    @property
    def cross_beam(self):
        return self.element_b

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

    @property
    def main_extension_plane(self):
        ref_side_dict = beam_ref_side_incidence(self.main_beam, self.cross_beam, ignore_ends=True)
        ref_side_index = min(ref_side_dict, key=ref_side_dict.get)
        return self.cross_beam.opp_side(ref_side_index)

    def _check_depths(self):
        """Warns if a depth relevant to the chosen shape is zero or negative; default will be used instead."""
        if self.step_shape not in (StepShapeType.STEP, StepShapeType.HEEL, StepShapeType.TAPERED_HEEL, StepShapeType.DOUBLE):
            raise ValueError("step_shape must be one of StepShapeType: STEP, HEEL, TAPERED_HEEL, DOUBLE. Got: {}".format(self.step_shape))

        has_step = self.step_shape in (StepShapeType.STEP, StepShapeType.DOUBLE)
        has_heel = self.step_shape in (StepShapeType.HEEL, StepShapeType.TAPERED_HEEL, StepShapeType.DOUBLE)

        if has_step and self.step_depth is not None and self.step_depth <= 0.0:
            warnings.warn(
                "step_depth cannot be zero or negative for shape type '{}'. A default value will be used.".format(self.step_shape)
            )
            self.step_depth = None
        if has_heel and self.heel_depth is not None and self.heel_depth <= 0.0:
            warnings.warn(
                "heel_depth cannot be zero or negative for shape type '{}'. A default value will be used.".format(self.step_shape)
            )
            self.heel_depth = None

    def _set_unset_attributes(self):
        """Resolves step and heel depths from cross beam geometry where not explicitly set.

        Shape type takes priority: depths not applicable to the chosen shape are forced to zero.
        """
        assert self.cross_beam and self.main_beam
        self._check_depths()

        if self.step_shape == StepShapeType.STEP:
            self.step_depth = self.step_depth or self.cross_beam.height / 4
            self.heel_depth = 0.0

        elif self.step_shape in (StepShapeType.HEEL, StepShapeType.TAPERED_HEEL):
            self.step_depth = 0.0
            self.heel_depth = self.heel_depth or self.cross_beam.height / 4

        elif self.step_shape == StepShapeType.DOUBLE:
            self.step_depth = self.step_depth or self.cross_beam.height / 6
            self.heel_depth = self.heel_depth or self.cross_beam.height / 4

    def add_extensions(self):
        """Calculates and adds the necessary extensions to the beams.

        This method is automatically called when joint is created by the call to `Joint.create()`.

        Raises
        ------
        BeamJoiningError
            If the extension could not be calculated.

        """
        assert self.cross_beam and self.main_beam
        start_a = None
        try:
            plane_a = self.main_extension_plane
            start_a, end_a = self.main_beam.extension_to_plane(plane_a)
        except AttributeError as ae:
            # I want here just the plane that caused the error
            raise BeamJoiningError(self.main_beam, self, debug_info=str(ae), debug_geometries=plane_a)
        except Exception as ex:
            raise BeamJoiningError(self.main_beam, self, debug_info=str(ex))
        self.main_beam.add_blank_extension(start_a, end_a, self.guid)

    def add_features(self):
        """Adds the required trimming features to both beams.

        This method is automatically called when joint is created by the call to `Joint.create()`.

        """
        assert self.main_beam and self.cross_beam  # should never happen

        if self.features:
            self.main_beam.remove_features(self.features)
            self.cross_beam.remove_features(self.features)

        # get dimensions for main and cross beams
        main_width, main_height = self.main_beam.get_dimensions_relative_to_side(self.main_beam_ref_side_index)
        cross_width, _ = self.cross_beam.get_dimensions_relative_to_side(self.cross_beam_ref_side_index)

        # generate step joint features
        main_feature = StepJoint.from_plane_and_beam(
            self.cross_beam.ref_sides[self.cross_beam_ref_side_index],
            self.main_beam,
            step_depth=self.step_depth,
            heel_depth=self.heel_depth,
            tapered_heel=self._tapered_heel,
            ref_side_index=self.main_beam_ref_side_index,
        )

        # generate step joint notch features
        cross_feature = StepJointNotch.from_plane_and_beam(
            self.main_beam.ref_sides[self.main_beam_ref_side_index],
            self.cross_beam,
            start_y=(cross_width - main_width) / 2 if cross_width > main_width else 0.0,
            notch_width=main_width,
            step_depth=self.step_depth,
            heel_depth=self.heel_depth,
            strut_height=main_height,
            tapered_heel=self._tapered_heel,
            ref_side_index=self.cross_beam_ref_side_index,
        )

        # add tenon and mortise features
        if self.tenon_mortise_height:
            tenon_mortise_width = main_width/4
            cross_feature.add_mortise(tenon_mortise_width, self.tenon_mortise_height)
            main_feature.add_tenon(tenon_mortise_width, self.tenon_mortise_height)

        # add features to beams
        self.main_beam.add_features(main_feature)
        self.cross_beam.add_features(cross_feature)
        # add features to joint
        self.features = [cross_feature, main_feature]

    @classmethod
    def check_elements_compatibility(cls, elements, raise_error=False):
        """Checks if the cluster of beams complies with the requirements for the TStepJoint.

        Parameters
        ----------
        elements : list of :class:`~compas_timber.model.TimberElement`
            The cluster of elements to be checked.
        raise_error : bool, optional
            Whether to raise an error if the elements are not compatible.
            If False, the method will return False instead of raising an error.

        Returns
        -------
        bool
            True if the cluster complies with the requirements, False otherwise.

        """
        cross_vect = elements[0].centerline.direction.cross(elements[1].centerline.direction)
        for beam in elements:
            beam_normal = beam.frame.normal.unitized()
            dot = abs(beam_normal.dot(cross_vect.unitized()))
            if not (TOL.is_zero(dot) or TOL.is_close(dot, 1)):
                if not raise_error:
                    return False
                raise BeamJoiningError(elements, cls, debug_info="The the two beams are not aligned to create a Step joint.")

        dir_a = elements[0].centerline.direction.unitized()
        dir_b = elements[1].centerline.direction.unitized()
        if TOL.is_zero(abs(dot_vectors(dir_a, dir_b))):
            if not raise_error:
                return False
            raise BeamJoiningError(
                elements,
                cls,
                debug_info="TStepJoint requires the beams to meet at a non-perpendicular angle. "
                           "Use TButtJoint for perpendicular configurations.",
            )

        return True
