import math
import warnings
from copy import deepcopy

from compas.geometry import Plane
from compas.geometry import Vector
from compas.geometry import angle_vectors
from compas.geometry import cross_vectors
from compas.geometry import dot_vectors
from compas.geometry import intersection_plane_plane_plane
from compas.tolerance import TOL

from compas_timber.errors import BeamJoiningError
from compas_timber.fabrication import StepShapeType
from compas_timber.fabrication.birds_mouth import BirdsMouth
from compas_timber.fabrication.double_cut import DoubleCut
from compas_timber.fabrication.jack_cut import JackRafterCut

from .joint import Joint
from .solver import JointTopology
from .utilities import are_beams_aligned_with_cross_vector
from .utilities import beam_ref_side_incidence
from .utilities import beam_ref_side_incidence_with_vector


class TMultiStepJoint(Joint):
    """Represents an T-MultiStep type joint which joins two beams, one of them at it's end (main) and the other one along it's centerline (cross).
    Two or more cuts are is made on the main beam and a notch is made on the cross beam to fit the main beam.

    This joint type is compatible with beams in T topology.

    Please use `TMultiStepJoint.create()` to properly create an instance of this class and associate it with a model.

    Parameters
    ----------
    main_beam : :class:`~compas_timber.elements.Beam`
        First beam to be joined.
    cross_beam : :class:`~compas_timber.elements.Beam`
        Second beam to be joined.
    step_shape : str
        The shape of the step cut. One of :class:`~compas_timber.fabrication.StepShapeType`: STEP or HEEL.
        Defaults to ``StepShapeType.STEP``.
    step_depth : float, optional
        Targeted depth of the step or heel cut, in model units. Provide either ``step_depth`` or ``step_count``, not both.
        If neither is provided, defaults to one quarter of the cross beam height.
        The actual depth may differ slightly from the target because it is adjusted to fit an integer number of steps.
    riser_angle : float, optional
        Angle of the riser face in degrees. Defaults to 90° (vertical riser).
        For ``StepShapeType.HEEL``, the riser is always perpendicular to the tread by geometric definition;
        any provided value will be ignored and a :class:`UserWarning` will be issued.
    step_count : int, optional
        Exact number of steps to create. Provide either ``step_count`` or ``step_depth``, not both.
        When provided, ``step_depth`` is derived exactly from the beam geometry with no rounding.
        If both are given, ``step_count`` takes priority and a :class:`UserWarning` is issued.
    do_refine_cut : bool, optional
        If True, an additional cut is added to the main beam to clean up the protruding portion of the cut if the beams are not perfectly aligned.
        This may be desirable for aesthetic reasons when the joint is visible, but could potentially add an unnecessary cut if there is no significant misalignment.
        Defaults to False.


    Attributes
    ----------
    main_beam : :class:`~compas_timber.elements.Beam`
        First beam to be joined.
    cross_beam : :class:`~compas_timber.elements.Beam`
        Second beam to be joined.
    step_shape : str
        The shape of the step cut. One of :class:`~compas_timber.fabrication.StepShapeType`: STEP or HEEL.
    step_depth : float
        Resolved depth of each step or heel cut, in model units. May differ from the constructor argument
        when it was adjusted to fit an integer number of steps along the strut contact length.
    riser_angle : float
        Angle of the riser face in degrees. Always 90° for ``StepShapeType.HEEL``.
    step_count : int
        Resolved number of steps. Always a positive integer.
    do_refine_cut : bool
        If True, an additional cut is added to the main beam to clean up the protruding portion of the cut if the beams are not perfectly aligned.

    """

    SUPPORTED_TOPOLOGY = JointTopology.TOPO_T

    @property
    def __data__(self):
        data = super(TMultiStepJoint, self).__data__
        data["step_shape"] = self.step_shape
        data["riser_angle"] = self.riser_angle
        data["step_count"] = self.step_count
        data["step_depth"] = self.step_depth
        data["do_refine_cut"] = self.do_refine_cut
        return data

    # fmt: off
    def __init__(
        self,
        main_beam=None,
        cross_beam=None,
        step_shape=None,
        step_depth=None,
        riser_angle=None,
        step_count=None,
        do_refine_cut=False,
        **kwargs
    ):
        super(TMultiStepJoint, self).__init__(elements=(main_beam,cross_beam), **kwargs)
        self.step_shape = step_shape or StepShapeType.STEP
        self.step_depth = step_depth
        if self.step_shape == StepShapeType.HEEL and riser_angle is not None and not TOL.is_close(riser_angle, 90.0):
            warnings.warn(
                "riser_angle is always 90° for HEEL shape by geometric definition. "
                "The provided value ({:.1f}°) will be ignored.".format(riser_angle)
            )
        # user input attributes, resolved ones are stored in private attributes
        self.riser_angle = riser_angle
        self.step_count = step_count
        self.do_refine_cut = do_refine_cut


        self._cross_beam_ref_side_index = None
        self._main_beam_ref_side_index = None

        self._riser_angle = None
        self._step_depth = None
        self._step_count = None
        self._step_delta = None
        self._strut_inclination = None

        self._base_planes = None

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
        if self._cross_beam_ref_side_index is None:
            ref_side_dict = beam_ref_side_incidence(self.main_beam, self.cross_beam, ignore_ends=True)
            self._cross_beam_ref_side_index = min(ref_side_dict, key=ref_side_dict.get)
        return self._cross_beam_ref_side_index

    @property
    def main_beam_ref_side_index(self):
        if self._main_beam_ref_side_index is None:
            cross_beam_ref_side = self.cross_beam.ref_sides[self.cross_beam_ref_side_index]
            ref_side_dict = beam_ref_side_incidence_with_vector(
                self.main_beam, cross_beam_ref_side.normal, ignore_ends=True
            )
            self._main_beam_ref_side_index = min(ref_side_dict, key=ref_side_dict.get)
        return self._main_beam_ref_side_index

    def _set_unset_attributes(self):
        """Sets default values for step_depth, riser_angle, and step_count if not provided, resolving conflicts."""
        assert self.cross_beam and self.main_beam
        cross_height = self.cross_beam.get_dimensions_relative_to_side(self.cross_beam_ref_side_index)[1]
        if self.step_count is not None and self.step_depth is not None:
            warnings.warn(
                "Both step_count and step_depth were provided. "
                "step_count takes priority; step_depth will be derived from the geometry."
            )
        if self.step_count is None and self.step_depth is None:
            self.step_depth = cross_height / 4
        self._riser_angle = 90.0 if self.step_shape == StepShapeType.HEEL else (self.riser_angle or 90.0)
        self._resolve_steps()

    def _resolve_steps(self):
        """Calculate and store the step count, step delta vector, and adjusted step depth.

        K converts step_depth to the horizontal step_interval along the strut contact line:
        step_interval = step_depth * K, where K is derived from the two triangle angles at the
        tread/riser junction (tread_angle on the tread side, complementary angle on the riser side).
        """
        main_ref_side = self.main_beam.ref_sides[self.main_beam_ref_side_index]
        cross_ref_side = self.cross_beam.ref_sides[self.cross_beam_ref_side_index]

        strut_vector = Vector(*cross_vectors(main_ref_side.yaxis, cross_ref_side.zaxis)).unitized()
        if TOL.is_positive(dot_vectors(main_ref_side.normal, strut_vector)):
            strut_vector = -strut_vector

        self._strut_inclination =  angle_vectors(self.point_centerline_towards_joint(self.main_beam), strut_vector, deg=True)
        strut_height = self.main_beam.get_dimensions_relative_to_side(self.main_beam_ref_side_index)[1]
        strut_length = strut_height / math.sin(math.radians(self._strut_inclination))

        if self.step_shape == StepShapeType.HEEL:
            tread_angle = math.radians(self._strut_inclination - 90.0)
        else:
            tread_angle = math.radians(self._strut_inclination / 2.0)

        riser_complement = math.radians(180.0 - self._riser_angle) - tread_angle
        K = 1.0 / math.tan(tread_angle) + 1.0 / math.tan(riser_complement)

        if self.step_count is not None:
            self._step_count = int(self.step_count)
            step_interval = strut_length / self._step_count
            self._step_depth = step_interval / K
        else:
            target_depth = self.step_depth
            self._step_count = max(1, int(round(strut_length / (target_depth * K))))
            step_interval = strut_length / self._step_count
            self._step_depth = step_interval / K
            if abs(self._step_depth - target_depth) > 1e-6:
                warnings.warn(
                    "step_depth adjusted from {:.4f} to {:.4f} to fit {:d} step(s).".format(
                        target_depth, self._step_depth, self._step_count
                    )
                )

        self._step_delta = strut_vector * step_interval

    def _compute_step_displacements(self):
        """Compute per-step BTLx coordinate shifts from the resolved strut vector and step interval."""
        main_ref_side = self.main_beam.ref_sides[self.main_beam_ref_side_index]
        step_dx = dot_vectors(self._step_delta, main_ref_side.xaxis)
        step_dy = dot_vectors(self._step_delta, -main_ref_side.zaxis)
        return step_dx, step_dy

    def _compute_notch_displacements(self):
        """Compute per-notch BTLx coordinate shifts from the resolved strut vector and step interval."""
        cross_ref_side = self.cross_beam.ref_sides[self.cross_beam_ref_side_index]
        notch_dx = dot_vectors(self._step_delta, cross_ref_side.xaxis)
        notch_dy = dot_vectors(self._step_delta, cross_ref_side.yaxis)
        return notch_dx, notch_dy

    def _compute_riser_and_tread_lengths(self):
        """Compute the horizontal lengths of the tread and riser faces from the step depth and angles."""
        if self.step_shape == StepShapeType.HEEL:
            angle = 180.0 - self._strut_inclination
        else:
            angle = self._strut_inclination / 2.0
        riser_length = abs(self._step_depth / math.sin(math.radians(angle)))
        tread_length = abs(self._step_depth / math.cos(math.radians(angle)))
        return riser_length, tread_length

    def _compute_base_planes(self):
        """Compute anchor geometry for all steps.

        Calls ``_resolve_steps()`` (which also calls ``_compute_step_displacements()``) then
        builds the two template planes that all other step geometry is derived from::

            tread_0  — at the strut contact corner (position 0)
            riser_0  — pre-translated by one ``_step_interval`` (position +1)

        Returns
        -------
        tuple(:class:`~compas.geometry.Plane`, :class:`~compas.geometry.Plane`)
            ``(tread_0, riser_0)``

        """
        if self._base_planes:
            return self._base_planes

        main_ref_side = self.main_beam.ref_sides[self.main_beam_ref_side_index]
        cross_ref_side = self.cross_beam.ref_sides[self.cross_beam_ref_side_index]

        # Corner point where beam bottom, cross beam contact face, and beam front face all meet.
        intersection_point = intersection_plane_plane_plane(
            Plane.from_frame(main_ref_side),
            Plane.from_frame(cross_ref_side),
            Plane.from_frame(self.main_beam.front_side(self.main_beam_ref_side_index)),
        )

        # rotation_axis lies along the strut contact line.
        rotation_axis = Vector.cross(main_ref_side.normal, cross_ref_side.normal).unitized()

        # Template planes for step 0, anchored at intersection_point.
        if self.step_shape == StepShapeType.HEEL:
            # For a heel cut, the tread plane is parallel to the cross beam's contact face, and the riser plane is parallel to the main beam's end face.
            tread_0 = Plane(intersection_point, cross_vectors(rotation_axis, main_ref_side.normal))
        else:
            tread_0 = Plane(intersection_point, (cross_ref_side.normal - main_ref_side.normal).unitized())
        riser_0 = tread_0.rotated(math.radians(180.0 - self._riser_angle), -rotation_axis, intersection_point)
        # riser_0 lives at position +1×step_interval so it is co-located with tread_1.
        riser_0.translate(self._step_delta)

        self._base_planes = (tread_0, riser_0)
        return self._base_planes

    def _get_cut_planes(self):
        """Returns the two single endpoint cut planes (leading tread and the trailing riser).
        One in the case of HEEL shape, two in the case of STEP shape.

        """
        tread_0, riser_0 = self._compute_base_planes()
        if self.step_shape == StepShapeType.HEEL:
            planes = [tread_0]
        else:
            riser_last = riser_0.translated(self._step_delta * (self._step_count - 1))
            planes = [tread_0, riser_last]
        return [Plane(plane.point, -plane.normal) for plane in planes]

    def _get_step_planes(self):
        """Returns the anchor plane pair for the first DoubleCut forming the valley of the first V-cut (riser_0, tread_1)."""
        tread_0, riser_0 = self._compute_base_planes()
        tread_1 = tread_0.translated(self._step_delta)
        return riser_0, tread_1

    def _get_notch_planes(self):
        """Returns the anchor plane pair for the first BirdsMouth notch (tread_0, riser_0)."""
        return self._compute_base_planes()

    def _get_butt_plane(self):
        """Calculates the butt plane that creates the flat surface on the end of the main beam to which the cross beam will be joined.
        It is defined by the cross beam's ref side and is parallel to the main beam's end face.

        """
        cross_ref_side = self.cross_beam.ref_sides[self.cross_beam_ref_side_index]
        butt_plane = Plane(cross_ref_side.point, -cross_ref_side.normal)
        return butt_plane.translated(butt_plane.normal * self._step_depth)

    def _get_refine_cut_plane(self):
        # get end point offset direction
        _, point = self.main_beam.endpoint_closest_to_point(self.location)
        offset_vector = Vector.from_start_end(self.location, point)
        ref_side_dict = beam_ref_side_incidence_with_vector(self.cross_beam, offset_vector, ignore_ends=True)
        refinement_cut_side_index = min(ref_side_dict, key=ref_side_dict.get)
        return self.cross_beam.ref_sides[refinement_cut_side_index]

    def add_extensions(self):
        """Calculates and adds the necessary extensions to the beams.

        This method is automatically called when joint is created by the call to `Joint.create()`.

        Raises
        ------
        BeamJoiningError
            If the extension could not be calculated.

        """
        assert self.cross_beam and self.main_beam

        plane_a = self._get_butt_plane()
        try:
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

        cut_planes = self._get_cut_planes()      # one or two single-plane end cuts
        step_planes = self._get_step_planes()    # DoubleCut anchor: first V-cut valley
        notch_planes = self._get_notch_planes()  # BirdsMouth anchor: first notch

        riser_length, tread_length = self._compute_riser_and_tread_lengths() # compute riser and tread lengths for feature dimensions and debug info

        # -- butt cut on main beam end face --
        butt_plane = self._get_butt_plane()
        cut = JackRafterCut.from_plane_and_beam(butt_plane, self.main_beam, name="Roughing_Cut")
        self.main_beam.add_features(cut)
        self.features.append(cut)

        # -- single endpoint cuts --
        for plane in cut_planes:
            cut = JackRafterCut.from_plane_and_beam(plane, self.main_beam)
            self.main_beam.add_features(cut)
            self.features.append(cut)

        # -- N-1 DoubleCut V-cuts on main beam --
        # First V-cut is computed from geometry; the rest are copies shifted by one step interval each.
        if self._step_count > 1:
            first_step = DoubleCut.from_planes_and_beam(step_planes, self.main_beam, reorder_planes=False, ref_side_index=(self.main_beam_ref_side_index-1)%4)
            first_step.user_attributes["riser_length"] = riser_length
            first_step.user_attributes["tread_length"] = tread_length
            self.main_beam.add_features(first_step)
            self.features.append(first_step)

            step_dx, step_dy = self._compute_step_displacements()
            for i in range(1, self._step_count - 1):
                next_step = deepcopy(first_step)
                next_step.start_x += i * step_dx  # shift along beam axis
                next_step.start_y += i * step_dy  # shift across face (non-zero for skewed joints)
                self.main_beam.add_features(next_step)
                self.features.append(next_step)


        # -- N BirdsMouth notches on cross beam --
        # First notch is computed from geometry; the rest are copies shifted by one step interval each.
        first_notch = BirdsMouth.from_planes_and_beam(notch_planes, self.cross_beam, ref_side_index=self.cross_beam_ref_side_index)
        first_notch.user_attributes["riser_length"] = riser_length
        first_notch.user_attributes["tread_length"] = tread_length
        self.cross_beam.add_features(first_notch)
        self.features.append(first_notch)

        notch_dx, notch_dy = self._compute_notch_displacements()
        for i in range(1, self._step_count):
            next_notch = deepcopy(first_notch)
            next_notch.start_x += i * notch_dx  # shift along beam axis
            next_notch.start_y += i * notch_dy  # shift across face (non-zero for skewed joints)
            self.cross_beam.add_features(next_notch)
            self.features.append(next_notch)

        # -- non_coplanar cut to the main beam --
        if self.do_refine_cut:
            if not are_beams_aligned_with_cross_vector(self.main_beam, self.cross_beam):
                refine_cut_plane = self._get_refine_cut_plane()
                cut = JackRafterCut.from_plane_and_beam(refine_cut_plane, self.main_beam, name="Refinement_Cut")
                self.main_beam.add_features(cut)
                self.features.append(cut)

    @classmethod
    def check_elements_compatibility(cls, elements, raise_error=True):
        """Checks if the cluster of beams complies with the requirements for the TMultiStepJoint.

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
        dir_a = elements[0].centerline.direction.unitized()
        dir_b = elements[1].centerline.direction.unitized()
        if TOL.is_zero(abs(dot_vectors(dir_a, dir_b))):
            if not raise_error:
                return False
            raise BeamJoiningError(
                elements,
                cls,
                debug_info="TMultiStepJoint requires the beams to meet at a non-perpendicular angle. "
                           "Use TButtJoint for perpendicular configurations.",
            )

        return True
