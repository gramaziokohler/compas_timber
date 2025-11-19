import math

from compas.geometry import Brep
from compas.geometry import Line
from compas.geometry import Plane
from compas.geometry import Point
from compas.geometry import angle_vectors
from compas.geometry import dot_vectors
from compas.geometry import intersection_line_line
from compas.geometry import intersection_plane_plane

from compas_timber.connections import Joint
from compas_timber.connections import JointTopology
from compas_timber.connections.utilities import are_beams_aligned_with_cross_vector
from compas_timber.connections.utilities import beam_ref_side_incidence
from compas_timber.elements import Beam
from compas_timber.errors import BeamJoiningError
from compas_timber.fabrication import DoubleCut
from compas_timber.fabrication import JackRafterCutProxy
from compas_timber.fabrication import MachiningLimits
from compas_timber.fabrication import Pocket


class KButtJoint(Joint):
    """
    Represents a K-Butt type joint which joins the ends of two beams along the length of another beam, trimming the two main beams.
    A `Pocket` feature is applied to the cross beam.

    This joint type is compatible with beams in K topology.

    The three beams must be coplanar and the two main beams must be on the same side of the cross beam.
    A double cut is applied to `main_beam_b`; if it fails to intersect both other beams, a JackRafterCut is applied instead.

    Parameters
    ----------
    cross_beam : :class:`~compas_timber.parts.Beam`
        The cross beam to be joined. The beam connected along its length.
    main_beam_a : :class:`~compas_timber.parts.Beam`
        The first main beam to be joined. Worked with a JackRafterCut.
    main_beam_b : :class:`~compas_timber.parts.Beam`
        The second main beam to be joined. Worked with a DoubleCut.
    mill_depth : float
        The depth of the pocket to be milled in the cross beam.



    Attributes
    ----------
    cross_beam : :class:`~compas_timber.parts.Beam`
        The cross beam to be joined.
    main_beam_a : :class:`~compas_timber.parts.Beam`
        The first main beam to be joined.
    main_beam_b : :class:`~compas_timber.parts.Beam`
        The second main beam to be joined.

    """

    SUPPORTED_TOPOLOGY = JointTopology.TOPO_K
    MIN_ELEMENT_COUNT = 3
    MAX_ELEMENT_COUNT = 3

    @property
    def __data__(self):
        data = super().__data__
        data["cross_beam_guid"] = self.cross_beam_guid
        data["main_beam_a_guid"] = self.main_beam_a_guid
        data["main_beam_b_guid"] = self.main_beam_b_guid
        data["mill_depth"] = self.mill_depth
        return data

    def __init__(self, cross_beam: Beam = None, main_beam_a: Beam = None, main_beam_b: Beam = None, mill_depth: float = 0, **kwargs):
        super().__init__(**kwargs)

        self.cross_beam = cross_beam
        self.main_beam_a = main_beam_a
        self.main_beam_b = main_beam_b
        self.cross_beam_guid = kwargs.get("cross_beam_guid", None) or str(cross_beam.guid)
        self.main_beam_a_guid = kwargs.get("main_beam_a_guid", None) or str(main_beam_a.guid)
        self.main_beam_b_guid = kwargs.get("main_beam_b_guid", None) or str(main_beam_b.guid)
        self.mill_depth = mill_depth
        self.features = []

    @property
    def beams(self):
        return [self.cross_beam, self.main_beam_a, self.main_beam_b]

    @property
    def elements(self):
        return self.beams

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

        This method is automatically called when the joint is created by the call to `Joint.create()`.
        """
        assert self.main_beam_a and self.main_beam_b and self.cross_beam
        self._cut_beam_b()
        self._cut_beam_a()
        self._cut_cross_beam()

    def _cut_beam_a(self):
        """
        Adds the cutting features to the first main beam.
        """
        # jack rafter cut with
        cutting_plane = Plane.from_frame(self.cross_beam.ref_sides[self.cross_beam_ref_side_index(self.main_beam_a)])
        if self.mill_depth:
            cutting_plane.translate(-cutting_plane.normal * self.mill_depth)

        cutting_plane.normal *= -1  # invert normal to point towards the main beam
        jack_rafter_cut = JackRafterCutProxy.from_plane_and_beam(cutting_plane, self.main_beam_a)
        self.main_beam_a.add_feature(jack_rafter_cut)
        self.features.append(jack_rafter_cut)

    def _cut_beam_b(self):
        """
        Adds the cutting features to the second main beam.
        """
        cutting_frame_cross_beam = self.cross_beam.ref_sides[self.cross_beam_ref_side_index(self.main_beam_b)]
        cutting_plane_cross_beam = Plane.from_frame(cutting_frame_cross_beam)
        if self.mill_depth:
            cutting_plane_cross_beam.translate(-cutting_plane_cross_beam.normal * self.mill_depth)

        ref_side_dict = beam_ref_side_incidence(self.main_beam_b, self.main_beam_a, ignore_ends=True)
        ref_side_index = min(ref_side_dict, key=ref_side_dict.get)
        cutting_plane_main_beam_A = Plane.from_frame(self.main_beam_a.ref_sides[ref_side_index])

        # Adjust the cutting plane's position to ensure correct orientation of the double cut
        intersection = intersection_plane_plane(cutting_plane_cross_beam, cutting_plane_main_beam_A)
        intersection_line = Line(intersection[0], intersection[1])
        if intersection_line.direction.dot(cutting_frame_cross_beam.yaxis) > 0:
            cutting_plane_cross_beam.point += cutting_frame_cross_beam.xaxis * self.cross_beam.length

        # Create the double cut; if it fails, a JackRafterCut is added instead
        cutting_planes = [cutting_plane_main_beam_A, cutting_plane_cross_beam]

        try:
            # The double cut feature is successful only if main beam B intersects both the cross beam and main beam A
            double_cut = DoubleCut.from_planes_and_beam(cutting_planes, self.main_beam_b)
            self.main_beam_b.add_feature(double_cut)
            self.features.append(double_cut)

        except Exception:
            # If double cut fails, add a simple JackRafterCut to main beam B
            intersection = Brep.from_boolean_intersection(self.main_beam_a.geometry, self.main_beam_b.geometry)

            if not intersection:
                cutting_plane_cross_beam.normal *= -1  # invert normal to point towards the main beam
                jack_rafter_cut = JackRafterCutProxy.from_plane_and_beam(cutting_plane_cross_beam, self.main_beam_b)
                self.main_beam_b.add_feature(jack_rafter_cut)
                self.features.append(jack_rafter_cut)

            else:
                raise BeamJoiningError(
                    beams=[self.main_beam_b],
                    joint=self.__class__,
                    debug_info="Could not create DoubleCut or JackRafterCut for main beam B in KButtJoint. Main beam B intersects only main beam A.",
                )

    def _cut_cross_beam(self):
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

        elif dot_a < dot_b:
            # Beam A first
            tilt_start_side = angle_a
            tilt_end_side = math.pi - angle_b
            start_x = self._find_start_x(Pa, angle_a, self.main_beam_a)
            length = self._find_length(Pb, start_x, angle_b, self.main_beam_b)

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

    @classmethod
    def check_elements_compatibility(cls, elements, raise_error=False):
        """
        Checks if the cluster of beams complies with the requirements for the KButtJoint.

        Parameters
        ----------
        elements : list of :class:`~compas_timber.parts.Beam`
            The beams to be checked.
        raise_error : bool, optional
            If True, raises `BeamJoiningError` if the requirements are not met. Default is False.

        Returns
        -------
        bool
            True if the requirements are met, False otherwise.
        """

        # For this joint, the beams have to be coplanar
        if not (
            are_beams_aligned_with_cross_vector(elements[0], elements[1])
            and are_beams_aligned_with_cross_vector(elements[1], elements[2])
            and are_beams_aligned_with_cross_vector(elements[0], elements[2])
        ):
            if not raise_error:
                return False

            if raise_error:
                raise BeamJoiningError(beams=elements[1:3], joint=cls, debug_info="The three beams have to be coplanar.")

        return True
