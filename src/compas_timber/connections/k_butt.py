
from compas.geometry import Plane
from compas.geometry import Vector


from compas_timber.elements import Beam
from compas_timber.elements import Fastener
from compas_timber.connections import Joint
from compas_timber.connections import JointTopology
from compas_timber.connections.utilities import are_beams_aligned_with_cross_vector
from compas_timber.connections.utilities import beam_ref_side_incidence
from compas_timber.fabrication import JackRafterCutProxy
from compas_timber.fabrication import DoubleCut
from compas_timber.fabrication import PocketProxy
from compas_timber.fabrication import Pocket
from compas_timber.fabrication import LapProxy
from compas_timber.fabrication import Lap
from compas_timber.errors import BeamJoiningError  







class KButtJoint(Joint):
    """
    Represets a K-Butt type joint which joins the ends of two beams along the length of a another beam, trimming the two main beams. 

    This joint type is compatible with beams in K topology.

    Parameters 
    ----------
    cross_beam : :class:`~compas_timber.parts.Beam`
        The cross beam to be joined. The beam connected along its length.
    main_beam_1 : :class:`~compas_timber.parts.Beam`
        The first main beam to be joined. Worked with a JackRafterCut
    main_beam_2 : :class:`~compas_timber.parts.Beam`
        The second main beam to be joined. Workd with a DoubleCut
    mill_depth : float
        The depth of the pocket to be milled in the cross beam.
    butt_plane : :class:`~compas.geometry.Plane`, optional
        The plane used to cut the main beams. If not provided, the closest side of the cross beam will be used.
    fastener : :class:`~compas_timber.parts.Fastener`, optional
        The fastener to be used in the joint.

    
    Attributes
    ----------
    cross_beam : :class:`~compas_timber.parts.Beam`
        The cross beam to be joined.
    main_beam_1 : :class:`~compas_timber.parts.Beam`
        The first main beam to be joined.
    main_beam_2 : :class:`~compas_timber.parts.Beam`
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


    def __init__(self, cross_beam: Beam = None, main_beam_a: Beam = None, main_beam_b: Beam = None, mill_depth: float = None, **kwargs):
        
        super().__init__(**kwargs)

        self.cross_beam = cross_beam
        self.main_beam_a = main_beam_a
        self.main_beam_b = main_beam_b
        self.cross_beam_guid = kwargs.get('cross_beam_guid', None) or str(cross_beam.guid)
        self.main_beam_a_guid = kwargs.get('main_beam_a_guid', None) or str(main_beam_a.guid)
        self.main_beam_b_guid = kwargs.get('main_beam_b_guid', None) or str(main_beam_b.guid)
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

        This method is automatically called when joint is creat by the call to `Joint.create()`. 

        Raises
        ------
        BeamJoingingError
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
        self.main_beam_a.add_blank_extension( start_main + 0.01, end_main + 0.01, self.guid) 
        


    def _extend_main_beam_b(self):
        cutting_plane_B = self.cross_beam.ref_sides[self.cross_beam_ref_side_index(self.main_beam_b)]
        if self.mill_depth:
            cutting_plane_B.translate(-cutting_plane_B.normal * self.mill_depth)
        start_main, end_main = self.main_beam_b.extension_to_plane(cutting_plane_B)
        self.main_beam_b.add_blank_extension( start_main + 0.01, end_main + 0.01, self.guid)




    def add_features(self):
        self._cut_beam_a()
        self._cut_beam_b()
        self._cut_cross_beam()




    def _cut_beam_a(self):
        # jack rafter cut with 
        cutting_plane = Plane.from_frame(self.cross_beam.ref_sides[self.cross_beam_ref_side_index(self.main_beam_a)])
        if self.mill_depth:
            cutting_plane.translate(-cutting_plane.normal * self.mill_depth)
        
        cutting_plane.normal *= -1  # invert normal to point towards the main beam
        jack_rafter_cut = JackRafterCutProxy.from_plane_and_beam(cutting_plane, self.main_beam_a)
        self.main_beam_a.add_feature(jack_rafter_cut)
        self.features.append(jack_rafter_cut)




    def _cut_beam_b(self):
        cutting_plane_cross_beam = Plane.from_frame(self.cross_beam.ref_sides[self.cross_beam_ref_side_index(self.main_beam_b)])
        if self.mill_depth:
            cutting_plane_cross_beam.translate(-cutting_plane_cross_beam.normal * self.mill_depth)

        cutting_plane_main_beam_A = Plane.from_frame(self.main_beam_a.ref_sides[self.main_beam_ref_side_index(self.main_beam_a)])

        cutting_planes = [cutting_plane_cross_beam, cutting_plane_main_beam_A]
        double_cut = DoubleCut.from_planes_and_beam(cutting_planes, self.main_beam_b)
        self.main_beam_b.add_feature(double_cut)
        self.features.append(double_cut)




    def _cut_cross_beam(self):
        cutting_plane = self.main_beam_a.ref_sides[self.main_beam_ref_side_index(self.main_beam_a)]
        lap_width = self.main_beam_a.get_dimensions_relative_to_side(self.main_beam_ref_side_index(self.main_beam_a))[1]
        lap = Lap.from_plane_and_beam(
            cutting_plane, 
            self.cross_beam,
            lap_width,
            self.mill_depth,
            ref_side_index=self.cross_beam_ref_side_index(self.main_beam_a)
        )
        self.cross_beam.add_feature(lap)    
        self.features.append(lap)





    @classmethod
    def check_elements_compatibility(cls, elements, raise_error=False):
        """
        Checks if the cluster fo  beams complies with the requirements for the YButtJoint.

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

        # the 2 main beams have to be complanar between temselves
        if not are_beams_aligned_with_cross_vector(*elements[1:3]):

            if not raise_error:
                return False
            
            if raise_error:
                raise BeamJoiningError(
                    beams = elements[1:3], 
                    joint = cls, 
                    debug_info="The two main beams are not coplanar."
                )
        
        return True
        