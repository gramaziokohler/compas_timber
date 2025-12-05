import math

from compas.geometry import Plane
from compas.geometry import Point
from compas.geometry import angle_vectors
from compas.geometry import dot_vectors
from compas.geometry import intersection_line_line

from compas_timber.connections import Joint
from compas_timber.connections import JointTopology
from compas_timber.connections.t_butt import TButtJoint
from compas_timber.connections.utilities import are_beams_aligned_with_cross_vector
from compas_timber.connections.utilities import beam_ref_side_incidence
from compas_timber.elements import Beam
from compas_timber.fabrication import MachiningLimits
from compas_timber.fabrication import Pocket


class KButtJoint(Joint):
    """
    Represents a K-Butt type joint which joins the ends of two beams along the length of another beam, trimming the two main beams.
    A `Pocket` feature is applied to the cross beam.

    This joint type is compatible with beams in K topology.

    If the three beams are coplanare, the cross beam is cut with a :class:`~compas_timber.fabrication.Pocket` feature
    otherwise with a :class:`~compas_timber.fabrication.Lap` feature.

    Parameters
    ----------
    cross_beam : :class:`~compas_timber.parts.Beam`, optional
        The cross beam to be joined. The beam connected along its length.
    *main_beams : :class:`~compas_timber.parts.Beam`
        The two main beams to be joined.
    mill_depth : float, optional
        The depth of the pocket to be milled in the cross beam. Default is 0.
    **kwargs : dict
        Additional keyword arguments passed to the parent Joint class.

    Attributes
    ----------
    cross_beam : :class:`~compas_timber.parts.Beam`
        The cross beam to be joined.
    main_beam_a : :class:`~compas_timber.parts.Beam`
        The first main beam to be joined.
    main_beam_b : :class:`~compas_timber.parts.Beam`
        The second main beam to be joined.
    mill_depth : float
        The depth of the pocket to be milled in the cross beam.
    cross_beam_guid : str
        The GUID of the cross beam.
    main_beam_a_guid : str
        The GUID of the first main beam.
    main_beam_b_guid : str
        The GUID of the second main beam.

    """

    SUPPORTED_TOPOLOGY = JointTopology.TOPO_K
    MIN_ELEMENT_COUNT = 3

    @property
    def __data__(self):
        data = super().__data__()
        data["cross_beam_guid"] = self.cross_beam_guid
        data["main_beam_a_guid"] = self.main_beam_a_guid
        data["main_beam_b_guid"] = self.main_beam_b_guid
        data["mill_depth"] = self.mill_depth
        return data

    def __init__(self, cross_beam: Beam = None, *main_beams: Beam, mill_depth: float = 0, **kwargs):
        super().__init__(**kwargs)

        self.cross_beam = cross_beam
        self.main_beam_a = main_beams[0]
        self.main_beam_b = main_beams[1]
        self.cross_beam_guid = kwargs.get("cross_beam_guid", None) or str(cross_beam.guid)
        self.main_beam_a_guid = kwargs.get("main_beam_a_guid", None) or str(self.main_beam_a.guid)
        self.main_beam_b_guid = kwargs.get("main_beam_b_guid", None) or str(self.main_beam_b.guid)
        self.mill_depth = mill_depth
        self.features = []

    @property
    def beams(self):
        return [self.cross_beam, self.main_beam_a, self.main_beam_b]

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
        """Create an instance of this joint from a cluster of elements.
        Automatically parse the elements in the cluster to identify the cross beam and the two main beams.

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
        :class:`~compas_timber.connections.KButtJoint`
            The created joint instance.

        """
        main_beams, cross_beams = cluster.parse_main_and_cross_beams()
        elements = list(cross_beams) + list(main_beams)
        return cls.create(model, *elements, **kwargs)

    def cross_beam_ref_side_index(self, beam):
        ref_side_dict = beam_ref_side_incidence(beam, self.cross_beam, ignore_ends=True)
        ref_side_index = min(ref_side_dict, key=ref_side_dict.get)
        return ref_side_index

    def main_beam_ref_side_index(self, beam):
        ref_side_dict = beam_ref_side_incidence(self.cross_beam, beam, ignore_ends=True)
        ref_side_index = min(ref_side_dict, key=ref_side_dict.get)
        return ref_side_index

    def add_extensions(self):
        """
        Calculates and adds the necessary extensions to the main beams.
        It accounts for the mill depth in the cross beam.

        This method is automatically called when the joint is created by the call to `Joint.create()`.

        Raises
        ------
        BeamJoiningError
            If the extension could not be calculated.
        """
        assert self.main_beam_a and self.main_beam_b and self.cross_beam
        self._extend_main_beam_a()
        self._extend_main_beam_b()

    def _extend_main_beam_a(self):
        cutting_plane_A = self.cross_beam.ref_sides[self.cross_beam_ref_side_index(self.main_beam_a)]
        if self.mill_depth:
            cutting_plane_A.translate(-cutting_plane_A.normal * self.mill_depth)
        start_main, end_main = self.main_beam_a.extension_to_plane(cutting_plane_A)
        self.main_beam_a.add_blank_extension(start_main + 0.01, end_main + 0.01, self.guid)

    def _extend_main_beam_b(self):
        cutting_plane_B = self.cross_beam.ref_sides[self.cross_beam_ref_side_index(self.main_beam_b)]
        if self.mill_depth:
            cutting_plane_B.translate(-cutting_plane_B.normal * self.mill_depth)
        start_main, end_main = self.main_beam_b.extension_to_plane(cutting_plane_B)
        self.main_beam_b.add_blank_extension(start_main + 0.01, end_main + 0.01, self.guid)

    def add_features(self):
        """
        Adds the required extension and trimming features to the three beams.

        This method is called by `model.process_joinery()`.
        """
        assert self.main_beam_a and self.main_beam_b and self.cross_beam

        if self.are_beams_coplanar:
            self._add_pocket_to_cross_beam()
            cross_beam = self.cross_beam.copy()  # cut with a pocket // provides a dummy cross beam
        else:
            cross_beam = self.cross_beam  # cut with T-butt joints below

        TJoint1 = TButtJoint(self.main_beam_a, cross_beam, mill_depth=self.mill_depth)
        TJoint1.add_features()
        TJoint2 = TButtJoint(self.main_beam_b, cross_beam, mill_depth=self.mill_depth)
        TJoint2.add_features()
        LJoint = TButtJoint(self.main_beam_b, self.main_beam_a)
        LJoint.add_features()

    def _add_pocket_to_cross_beam(self):
        """
        Adds the pocket features to the cross beam.
        """
        angle_a, dot_a = self._compute_angle_and_dot_between_cross_and_main(self.main_beam_a)
        angle_b, dot_b = self._compute_angle_and_dot_between_cross_and_main(self.main_beam_b)
        # Find intersection points between cross beam and main beams
        Pa, _ = intersection_line_line(self.main_beam_a.centerline, self.cross_beam.centerline)
        Pb, _ = intersection_line_line(self.main_beam_b.centerline, self.cross_beam.centerline)
        # Dot product used to determine the order of the two main beams according to the direction
        # of the cross beam.
        # Find the BTLx pocket parameters accordingly
        if dot_a > dot_b:
            # Beam B first
            tilt_start_side = angle_b
            tilt_end_side = math.pi - angle_a
            start_x = self._find_start_x(Pb, angle_b, self.main_beam_b)
            length = self._find_length(Pa, start_x, angle_a, self.main_beam_a)
            result, alternative_length = self._check_length_feasability(length, self.main_beam_a, angle_a)
            if not result:
                diff = length - alternative_length
                start_x += diff
                length = alternative_length
        elif dot_a < dot_b:
            # Beam A first
            tilt_start_side = angle_a
            tilt_end_side = math.pi - angle_b
            start_x = self._find_start_x(Pa, angle_a, self.main_beam_a)
            length = self._find_length(Pb, start_x, angle_b, self.main_beam_b)
            result, alternative_length = self._check_length_feasability(length, self.main_beam_a, angle_a)
            if not result:
                length = alternative_length

        else:
            raise ValueError("The two main beams cannot be parallel to each other.")
        # Independent BTLx parameters
        width = self._find_width()
        start_y = self._find_start_y(width)
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
            ref_side_index=self.cross_beam_ref_side_index(self.main_beam_a),
        )
        self.cross_beam.add_feature(pocket)
        self.features.append(pocket)

    def _find_start_x(self, intersection_point, angle, beam):
        """
        Computes the start_x BTLx parameter for the pocket in the cross beam.
        """
        beam_width, beam_height = beam.get_dimensions_relative_to_side(self.cross_beam_ref_side_index(beam))
        cross_width, cross_height = self.cross_beam.get_dimensions_relative_to_side(self.cross_beam_ref_side_index(beam))
        ref_side = self.cross_beam.ref_sides[self.cross_beam_ref_side_index(beam)]
        ref_side_plane = Plane.from_frame(ref_side)
        intersection_point_projected = ref_side_plane.projected_point(intersection_point)
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
        x1 = (cross_height / 2 - self.mill_depth) / math.tan(math.pi - angle) if self.mill_depth < cross_height / 2 else 0
        x2 = (beam_height / 2) / math.sin(math.pi - angle)
        end_x += abs(x1)
        end_x += abs(x2)
        length = end_x - start_x
        if self.mill_depth >= cross_height / 2:
            x3 = (self.mill_depth - cross_height / 2) / math.tan(math.pi - angle)
            if angle < math.pi / 2:
                length -= abs(x3)
            else:
                length += abs(x3)
        return length

    def _check_length_feasability(self, length, beam, angle):
        """
        Check that the lenght parameter is bigger that the main_beam_width projected on the cross beam.
        """
        beam_width, beam_height = beam.get_dimensions_relative_to_side(self.cross_beam_ref_side_index(beam))
        touching_beam_width = beam_width / math.sin(angle)
        if length < touching_beam_width:
            return False, touching_beam_width
        return True, touching_beam_width

    def _find_width(self):
        """
        Computes the width BTLx parameter for the pocket in the cross beam.
        """
        beam_a_width, _ = self.main_beam_a.get_dimensions_relative_to_side(self.cross_beam_ref_side_index(self.main_beam_a))
        beam_b_width, _ = self.main_beam_b.get_dimensions_relative_to_side(self.cross_beam_ref_side_index(self.main_beam_b))
        width = max(beam_a_width, beam_b_width)
        return width

    def _find_start_y(self, width):
        """
        Computes the start_y BTLx parameter for the pocket in the cross beam.
        """
        cross_beam_width, _ = self.cross_beam.get_dimensions_relative_to_side(self.cross_beam_ref_side_index(self.main_beam_a))
        start_y = (cross_beam_width - width) / 2
        return start_y

    def _compute_angle_and_dot_between_cross_and_main(self, main_beam):
        """
        Computes the angle and the dot product between the cross beam and a main beam.
        """

        p1x, _ = intersection_line_line(main_beam.centerline, self.cross_beam.centerline)
        if p1x is None:
            raise ValueError("The two beams do not intersect with each other")
        end, _ = main_beam.endpoint_closest_to_point(Point(*p1x))

        if end == "start":
            main_beam_direction = main_beam.centerline.vector
        else:
            main_beam_direction = main_beam.centerline.vector * -1

        angle = angle_vectors(main_beam_direction, self.cross_beam.centerline.direction)
        dot = dot_vectors(main_beam_direction, self.cross_beam.centerline.direction)
        return angle, dot

    def restore_beams_from_keys(self, model):
        """After de-serialization, restores references to the main and cross beams saved in the model."""
        self.cross_beam = model.elemnt_by_guid(self.cross_beam_guid)
        self.main_beam_a = model.elemnt_by_guid(self.main_beam_a_guid)
        self.main_beam_b = model.elemnt_by_guid(self.main_beam_b_guid)
