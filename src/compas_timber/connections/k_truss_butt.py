
from compas.geometry import Point
from compas.geometry import Vector
from compas.geometry import Plane
from compas.geometry import Frame
from compas.geometry import intersection_line_line
from compas.geometry import angle_vectors
from compas.geometry import dot_vectors

from compas_timber.connections import Joint
from compas_timber.connections import JointTopology   
from compas_timber.connections.utilities import beam_ref_side_incidence
from compas_timber.elements.beam import Beam
from compas_timber.fabrication import DoubleCut






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
    




    def _cut_main_beam(self, beam: Beam, mid_cutting_plane: Plane, second_beam: bool):
        
        cross_cutting_frame = self.cross_beam.ref_sides[self.cross_beam_ref_side_index(beam)]
        cross_cutting_plane = Plane.from_frame(cross_cutting_frame)

        if second_beam:
            cross_cutting_plane.point += cross_cutting_frame.xaxis * self.cross_beam.length

        double_cut = DoubleCut.from_planes_and_beam([cross_cutting_plane, mid_cutting_plane], beam)
        
        beam.add_feature(double_cut)
        self.features.append(double_cut)
    
        
        
        



    def _sort_main_beams(self):
        angle_a, dot_a = self._compute_angle_and_dot_between_cross_beam_and_main_beam(self.main_beams[0])
        angle_b, dot_b = self._compute_angle_and_dot_between_cross_beam_and_main_beam(self.main_beams[1])

        if dot_a > dot_b:
            # Beam B first
            return self.main_beams[1], self.main_beams[0]
        elif dot_a < dot_b:
            # Beam A first
            return self.main_beams[0], self.main_beams[1]
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

        mid_cutting_plane = Plane(intersection_point, self.cross_beam.centerline.direction)

        return mid_cutting_plane




    @classmethod
    def check_elements_compatibility(cls, elements, raise_error=False):
        pass