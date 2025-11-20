
import math

from compas.geometry import Point
from compas.geometry import Vector
from compas.geometry import Plane
from compas.geometry import Frame
from compas.geometry import Line
from compas.geometry import intersection_line_line
from compas.geometry import intersection_plane_plane
from compas.geometry import angle_vectors
from compas.geometry import dot_vectors

from compas_timber.connections import Joint
from compas_timber.connections import JointTopology   
from compas_timber.connections.utilities import beam_ref_side_incidence
from compas_timber.elements.beam import Beam
from compas_timber.fabrication import DoubleCut
from compas_timber.fabrication import Pocket
from compas_timber.fabrication import MachiningLimits






class KTrussButtJoint(Joint):


    SUPPORTED_TOPOLOGY = JointTopology.TOPO_K
    MIN_ELEMENT_COUNT = 3
    MAX_ELEMENT_COUNT = 3

    @property
    def __data__(self):
        data = super().__data__()
        data["main_beam_a_guid"] = self.main_beam_a.guid
        data["main_beam_b_guid"] = self.main_beam_b.guid
        data["cross_beam_guid"] = self.cross_beam.guid
        data["mill_depth"] = self.mill_depth    
        return data


    def __init__(self, cross_beam: Beam = None, main_beams: list[Beam] = None, mill_depth: float = 0, **kwargs):
        super().__init__(main_beams=main_beams, cross_beam=cross_beam, **kwargs)

        self.cross_beam = cross_beam
        self.main_beams = main_beams 
        self.mill_depth = mill_depth
        self.cross_beam_guid = kwargs.get("cross_beam_guid", None)
        self.main_beam_a_guid = kwargs.get("main_beam_a_guid", None)
        self.main_beam_b_guid = kwargs.get("main_beam_b_guid", None)
        self.features = []



    @property
    def beams(self) -> list[Beam]:
        return [self.cross_beam] + self.main_beams
    
    @property
    def elements(self):
        return self.beams
    


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
        assert self.cross_beam and len(self.main_beams) == 2
        for beam in self.main_beams:
            self._extend_beam(beam)



    def _extend_beam(self, beam: Beam):
        cutting_plane = self.cross_beam.ref_sides[self.cross_beam_ref_side_index(beam)]
        if self.mill_depth:
            cutting_plane.translate(-cutting_plane.normal * self.mill_depth)
        start_extension, end_extesion = beam.extension_to_plane(cutting_plane)
        extension_tolerance = 0.01
        beam.add_blank_extension(start_extension + extension_tolerance, end_extesion + extension_tolerance)










    def add_features(self):
        
        beam_1, beam_2 = self._sort_main_beams()

        mid_cutting_plane = self._compute_middle_cutting_plane(beam_1, beam_2)

        self._cut_main_beam(beam_1, mid_cutting_plane, second_beam = False)
       
        self._cut_main_beam(beam_2, mid_cutting_plane, second_beam = True)


        self._cut_cross_beam(beam_1, beam_2)
    






    def _cut_main_beam(self, beam: Beam, mid_cutting_plane: Plane, second_beam: bool):
        
        cross_cutting_frame = self.cross_beam.ref_sides[self.main_beam_ref_side_index(beam)]
        cross_cutting_plane = Plane.from_frame(cross_cutting_frame)


        if self.mill_depth:
            cross_cutting_plane.point -= cross_cutting_plane.normal * self.mill_depth


        # adjust cutting plane position to ensure correct orientation of the double cut
        intersection = intersection_plane_plane(mid_cutting_plane, cross_cutting_plane)
        intersection_line = Line(intersection[0], intersection[1])
        if intersection_line.direction.dot(cross_cutting_frame.yaxis) > 0:
            cross_cutting_plane.point += cross_cutting_frame.xaxis * self.cross_beam.length
        else:
            mid_cutting_plane.normal *= -1

        if second_beam:
            mid_cutting_plane.normal *= -1 


        double_cut = DoubleCut.from_planes_and_beam([cross_cutting_plane, mid_cutting_plane], beam)
        
        beam.add_feature(double_cut)
        self.features.append(double_cut)
    
        
        
        



    def _sort_main_beams(self):
        angle_a, dot_a = self._compute_angle_and_dot_between_cross_beam_and_main_beam(self.main_beams[0])
        angle_b, dot_b = self._compute_angle_and_dot_between_cross_beam_and_main_beam(self.main_beams[1])

        if dot_a < dot_b:
            # Beam B first
            return self.main_beams[0], self.main_beams[1]
        elif dot_a > dot_b:
            # Beam A first
            return self.main_beams[1], self.main_beams[0]
        else:
            raise ValueError("The two main beams cannot be parallel to each other.")





    def _compute_angle_and_dot_between_cross_beam_and_main_beam(self, main_beam: Beam):
        p1x,  _ = intersection_line_line(main_beam.centerline, self.cross_beam.centerline)
        if p1x is None:
            raise ValueError("Main beam and cross beam do not intersect.")
        end, _ = main_beam.endpoint_closest_to_point(Point(*p1x))

        if end == "start":
            main_beam_direction = main_beam.centerline.vector
        else:
            main_beam_direction = main_beam.centerline.vector * -1
        
        angle = angle_vectors(main_beam_direction, self.cross_beam.centerline.direction)
        dot = dot_vectors(main_beam_direction, self.cross_beam.centerline.direction)

        return angle, dot





    def _compute_middle_cutting_plane(self, beam_1, beam_2) -> Plane:
        intersection_point, _ = intersection_line_line(beam_1.centerline, beam_2.centerline)
        if intersection_point is None:
            raise ValueError("Main beams do not intersect.")

        # Get normalized direction vectors
        dir1 = Vector(*beam_1.centerline.direction).unitized()
        dir2 = Vector(*beam_2.centerline.direction).unitized()
        
        # The bisector direction is the normalized sum of both directions
        bisector_direction = (dir1 + dir2).unitized()

        # Create rotation plane of the bisector
        roatation_plane = Plane.from_point_and_two_vectors(intersection_point, dir1, dir2)

        # Compute normal of the cutting plane
        cutting_plane_normal = bisector_direction.rotated(math.pi/2, roatation_plane.normal, intersection_point)

        # Create plane perpendicular to the bisector at the intersection point
        mid_cutting_plane = Plane(intersection_point, cutting_plane_normal)
        mid_cutting_plane.point += bisector_direction * max(self.cross_beam.height, self.cross_beam.width)

        return mid_cutting_plane




    def _cut_cross_beam(self, beam_1: Beam, beam_2: Beam):
        # find intersection points between cross beame and main beams
        P1, _ = intersection_line_line(self.cross_beam.centerline, beam_1.centerline)
        P2, _ = intersection_line_line(self.cross_beam.centerline, beam_2.centerline)   

        angle_1, _ = self._compute_angle_and_dot_between_cross_beam_and_main_beam(beam_1)
        angle_2, _ = self._compute_angle_and_dot_between_cross_beam_and_main_beam(beam_2)

        tilt_start_side =  angle_1
        tilt_end_side = math.pi - angle_2
        start_x = self._find_start_x(P1, angle_1, beam_1)
        length = self._find_length(P2, start_x, angle_2, beam_2)
        width = self._find_width(beam_1, beam_2)
        start_y = self._find_start_y(width, beam_1)


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


























    @classmethod
    def check_elements_compatibility(cls, elements, raise_error=False):
        pass
        
