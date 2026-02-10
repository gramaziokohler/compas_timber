import math

from compas.geometry import Plane
from compas.geometry import Point
from compas.geometry import angle_vectors
from compas.geometry import dot_vectors
from compas.geometry import intersection_line_line

from compas_timber.connections import Joint
from compas_timber.connections import JointTopology
from compas_timber.connections.joinery_utilities import parse_cross_beam_and_main_beams_from_cluster
from compas_timber.connections.l_miter import LMiterJoint
from compas_timber.connections.t_butt import ButtJoint
from compas_timber.connections.utilities import are_beams_aligned_with_cross_vector
from compas_timber.connections.utilities import beam_ref_side_incidence
from compas_timber.elements.beam import Beam
from compas_timber.errors import BeamJoiningError
from compas_timber.fabrication import MachiningLimits
from compas_timber.fabrication import Pocket


class KMiterJoint(Joint):
    """
    Represents a K-Miter type joint which joins the ends of multiple beams (`main_beams`) along the length of another beam (`cross_beam`).

    The main beams are joined with L-Miter joints where they meet consecutively, and each main beam is joined to the cross beam with a T-Butt joint.
    If the beams are coplanar, a :class:`~compas_timber.fabrication.Pocket` feature is created in the `cross_beam`, otherwise
    T-Butt joints are applied directly.

    This joint type is compatible with beams in K topology and supports 3 to 50 beams.

    Parameters
    ----------
    cross_beam : :class:`~compas_timber.elements.Beam`
        The cross beam to be joined. The beam connected along its length.
    *main_beams : :class:`~compas_timber.elements.Beam`
        The main beams to be joined (minimum 2). The beams connected at their ends.
    mill_depth : float, optional
        The depth of material to be milled from the cross beam at the cutting planes. Default is 0.
    **kwargs : dict
        Additional keyword arguments passed to the parent Joint class.

    Attributes
    ----------
    cross_beam : :class:`~compas_timber.elements.Beam`
        The cross beam to be joined. The beam connected along its length.
    main_beams : list of :class:`~compas_timber.elements.Beam`
        The main beams to be joined. The beams connected at their ends.
    mill_depth : float
        The depth of material to be milled from the cross beam at the cutting planes.
    features : list of :class:`~compas_timber.fabrication.Feature`
        The features added to the beams by the joint.

    """

    SUPPORTED_TOPOLOGY = JointTopology.TOPO_K
    MIN_ELEMENT_COUNT = 3
    MAX_ELEMENT_COUNT = 100

    @property
    def __data__(self):
        data = super().__data__
        data["cross_beam_guid"] = self.cross_beam_guid
        data["main_beams_guids"] = self.main_beams_guids
        data["mill_depth"] = self.mill_depth
        data["conical_tool"] = self.conical_tool
        return data

    def __init__(self, cross_beam: Beam = None, *main_beams: Beam, mill_depth: float = 0, conical_tool=False, **kwargs):
        super().__init__(main_beams=list(main_beams), cross_beam=cross_beam, **kwargs)
        self.cross_beam = cross_beam
        self.main_beams = list(main_beams)
        self.mill_depth = mill_depth
        self.conical_tool = conical_tool
        self.cross_beam_guid = kwargs.get("cross_beam_guid", None) or str(cross_beam.guid)
        self.main_beams_guids = [str(beam.guid) for beam in self.main_beams]
        self.features = []

    @property
    def beams(self) -> list[Beam]:
        return [self.cross_beam] + self.main_beams

    @property
    def elements(self):
        return self.beams

    @property
    def are_beams_coplanar(self):
        if (
            are_beams_aligned_with_cross_vector(self.elements[0], self.elements[1])
            and are_beams_aligned_with_cross_vector(self.elements[1], self.elements[2])
            and are_beams_aligned_with_cross_vector(self.elements[0], self.elements[2])
        ):
            return True
        return False

    @classmethod
    def promote_cluster(cls, model, cluster, reordered_elements=None, **kwargs):
        """Create an instance of this joint form a cluster of elements.
        Automatically parse the elements in the cluster to indentify the cross beams and the two main beams.

        Parameters
        ----------
        model : :class:`~compas_timber.model.Model`
            The model to which the joint will be added.
        cluster : :class:`~compas_timber.clusters.BeamCluster`
            The cluster of beams to be used to create the joint.
        reordered_elements : list of :class:`~compas_timber.elements.Beam`, optional
            The elements in the order required by the joint. If not provided, the elements in the cluster will be used.
        **kwargs : dict
            Additional keyword arguments passed to the joint constructor.

        Returns
        -------
        :class:`~compas_timber.connections.KMiterJoint`
            The created joint instance.
        """
        cross_beams, main_beams = parse_cross_beam_and_main_beams_from_cluster(cluster)
        if len(cross_beams) != 1:
            raise BeamJoiningError("K-Miter joints require exactly one cross beam.")
        elements = list(cross_beams) + list(main_beams)
        return cls.create(model, *elements, **kwargs)

    def cross_beam_ref_side_index(self, beam):
        ref_side_dict = beam_ref_side_incidence(self.cross_beam, beam, ignore_ends=True)
        ref_side_index = min(ref_side_dict, key=ref_side_dict.get)
        return ref_side_index

    def main_beam_ref_side_index(self, beam):
        ref_side_dict = beam_ref_side_incidence(beam, self.cross_beam, ignore_ends=True)
        ref_side_index = min(ref_side_dict, key=ref_side_dict.get)
        return ref_side_index

    def add_extensions(self):
        """
        Calculates and adds the necessary extensions to the beams.

        This method is automatically called when joint is created by the call to `Joint.create()`.

        Raises
        ------
        BeamJoiningError
            If the extension could not be calculated.

        """
        for beam in self.main_beams:
            self._extend_beam(beam)

    def _extend_beam(self, beam: Beam):
        ref_side_dict = beam_ref_side_incidence(beam, self.cross_beam, ignore_ends=True)
        cross_beam_ref_side_index = min(ref_side_dict, key=ref_side_dict.get)
        cutting_plane = self.cross_beam.ref_sides[cross_beam_ref_side_index]

        if self.mill_depth:
            cutting_plane.translate(-cutting_plane.normal * self.mill_depth)

        start_extension, end_extension = beam.extension_to_plane(cutting_plane)
        extension_tolerance = 0.01
        beam.add_blank_extension(start_extension + extension_tolerance, end_extension + extension_tolerance)

    def add_features(self):
        """
        Adds the required extension and trimming features to the three beams.

        This method is called by `model.process_joinery()`..
        """
        assert self.main_beams and self.cross_beam

        # self.main_beams is sorted based on their dot product with the cross beam direction
        sorted_angles, sorted_dots = self._sort_main_beams()

        if self.are_beams_coplanar:
            self._add_pocket_to_cross_beam(self.main_beams[0], self.main_beams[-1])
            # cross_beam = self.cross_beam.copy()  # cut with pocket // porvide a dummy cross beam the the T joints
        else:
            pass
            # cross_beam = self.cross_beam  # cut with T-butt joints below

        for i in range(len(self.main_beams) - 1):
            beam_1 = self.main_beams[i]
            beam_2 = self.main_beams[i + 1]

            # NOTE: LMiter currently going under refactor
            # TODO: FixMe after LMiter refactoring
            L_joint = LMiterJoint(beam_1, beam_2)
            L_joint.add_features()

        # Apply Jack Rafter Cuts to the main beams
        for beam in self.main_beams:
            feature = ButtJoint.cut_main_beam(self.cross_beam, beam, mill_depth=self.mill_depth)
            beam.add_feature(feature)
            self.features.append(feature)

    def _sort_main_beams(self):
        angles = []
        dots = []
        for main_beam in self.main_beams:
            angle, dot = self._compute_angle_and_dot_between_cross_beam_and_main_beam(main_beam)
            angles.append(angle)
            dots.append(dot)
        # Sort main_beams based on dots (ascending order)
        sorted_indices = sorted(range(len(dots)), key=lambda i: dots[i])
        sorted_beams = [self.main_beams[i] for i in sorted_indices]
        sorted_angles = [angles[i] for i in sorted_indices]
        sorted_dots = [dots[i] for i in sorted_indices]
        self.main_beams = sorted_beams
        return sorted_angles, sorted_dots

    def _compute_angle_and_dot_between_cross_beam_and_main_beam(self, main_beam: Beam):
        p1x, _ = intersection_line_line(main_beam.centerline, self.cross_beam.centerline)
        if p1x is None:
            raise ValueError("Main beam and cross beam do not intersect.")
        end, _ = main_beam.endpoint_closest_to_point(Point(*p1x))

        if end == "start":
            main_beam_direction = main_beam.centerline.vector
        else:
            main_beam_direction = main_beam.centerline.vector * -1
        main_beam_direction = main_beam_direction.unitized()
        angle = angle_vectors(main_beam_direction, self.cross_beam.centerline.direction)
        dot = dot_vectors(main_beam_direction, self.cross_beam.centerline.direction)
        return angle, dot

    def _add_pocket_to_cross_beam(self, beam_1: Beam, beam_2: Beam):
        # find intersection points between cross beam and main beams
        P1, _ = intersection_line_line(self.cross_beam.centerline, beam_1.centerline)
        P2, _ = intersection_line_line(self.cross_beam.centerline, beam_2.centerline)

        angle_1, _ = self._compute_angle_and_dot_between_cross_beam_and_main_beam(beam_1)
        angle_2, _ = self._compute_angle_and_dot_between_cross_beam_and_main_beam(beam_2)

        tilt_start_side = angle_1
        tilt_end_side = math.pi - angle_2
        start_x = self._find_start_x(P1, angle_1, beam_1)
        length = self._find_length(P2, start_x, angle_2, beam_2)
        width = self._find_width(beam_1, beam_2)
        start_y = self._find_start_y(width, beam_1)

        # adjust tilt  angles if conicla tool is not used
        if not self.conical_tool:
            if tilt_end_side < math.pi / 2:
                tilt_end_side = math.pi / 2
            if tilt_start_side < math.pi / 2:
                tilt_start_side = math.pi / 2

        # Create pocket feature
        machining_limits = MachiningLimits()
        pocket = Pocket(
            start_x=start_x,
            start_y=start_y,
            start_depth=self.mill_depth,
            angle=0,
            inclination=0,
            slope=0.0,
            length=length,
            width=width,
            internal_angle=90.0,
            tilt_ref_side=90.0,
            tilt_end_side=math.degrees(tilt_end_side),
            tilt_opp_side=90.0,
            tilt_start_side=math.degrees(tilt_start_side),
            machining_limits=machining_limits.limits,
            ref_side_index=self.main_beam_ref_side_index(beam_1),
        )
        self.cross_beam.add_feature(pocket)
        self.features.append(pocket)

    def _find_start_x(self, P: Point, angle: float, main_beam: Beam) -> float:
        """
        Computes the start_x BTLx parameter for the pocket in the cross beam.
        """

        beam_width, beam_height = main_beam.get_dimensions_relative_to_side(self.cross_beam_ref_side_index(main_beam))
        cross_width, cross_height = self.cross_beam.get_dimensions_relative_to_side(self.cross_beam_ref_side_index(main_beam))

        ref_side = self.cross_beam.ref_sides[self.cross_beam_ref_side_index(main_beam)]
        ref_side_plane = Plane.from_frame(ref_side)
        intersection_point_projected = ref_side_plane.projected_point(P)

        air_distance = ref_side.point.distance_to_point(intersection_point_projected)

        # Calculate start_x
        start_x = math.sqrt(air_distance**2 - (beam_width / 2) ** 2)
        x1 = (cross_height / 2 - self.mill_depth) / math.tan(math.pi - angle)
        x2 = (beam_height / 2) / math.sin(math.pi - angle)
        start_x -= x1
        start_x -= x2

        return start_x

    def _find_length(self, intersection_point, start_x, angle, beam):
        """
        Computes the length BTLx parameter for the pocket in the cross beam.
        """
        beam_width, beam_height = beam.get_dimensions_relative_to_side(self.cross_beam_ref_side_index(beam))
        cross_width, cross_height = self.cross_beam.get_dimensions_relative_to_side(self.cross_beam_ref_side_index(beam))

        ref_side = self.cross_beam.ref_sides[self.cross_beam_ref_side_index(beam)]
        ref_side_plane = Plane.from_frame(ref_side)
        intersection_point_projected = ref_side_plane.projected_point(intersection_point)

        air_distance = ref_side.point.distance_to_point(intersection_point_projected)

        # Calculate end_x
        end_x = math.sqrt(air_distance**2 - (beam_width / 2) ** 2)
        x1 = (cross_height / 2 - self.mill_depth) / math.tan(angle) if self.mill_depth < cross_height / 2 else 0
        x2 = (beam_height / 2) / math.sin(angle)

        end_x += x1
        end_x += abs(x2)

        length = end_x - start_x

        if self.mill_depth >= cross_height / 2:
            x3 = (self.mill_depth - cross_height / 2) / math.tan(math.pi - angle)

            if angle < math.pi / 2:
                length -= abs(x3)
            else:
                length += abs(x3)

        return length

    def _find_start_y(self, width, beam_1: Beam) -> float:
        """
        Computes the start_y BTLx parameter for the pocket in the cross beam.
        """
        cross_beam_width, _ = self.cross_beam.get_dimensions_relative_to_side(self.cross_beam_ref_side_index(beam_1))
        start_y = (cross_beam_width - width) / 2
        return start_y

    def _find_width(self, beam_1: Beam, beam_2: Beam) -> float:
        """
        Computes the width BTLx parameter for the pocket in the cross beam.
        """
        beam_1_width, _ = beam_1.get_dimensions_relative_to_side(self.cross_beam_ref_side_index(beam_1))
        beam_2_width, _ = beam_2.get_dimensions_relative_to_side(self.cross_beam_ref_side_index(beam_2))
        width = max(beam_1_width, beam_2_width)
        return width

    def restore_beams_from_keys(self, model):
        """After de-seriallization, restores references to the main and cross beams saved in the model."""
        self.cross_beam = model.element_by_guid(self.cross_beam_guid)
        self.main_beams = [model.element_by_guid(guid) for guid in self.main_beams_guids]
