from compas.geometry import Plane
from compas.tolerance import TOL

from compas_timber.errors import BeamJoiningError
from compas_timber.fabrication import SimpleScarf

from .joint import Joint
from .solver import JointTopology
from .utilities import beam_ref_side_incidence_with_vector


class ISimpleScarf(Joint):
    """Represents a Simple Scarf joint for two parallel beams (Topology I)."""

    SUPPORTED_TOPOLOGY = JointTopology.TOPO_I

    @property
    def __data__(self):
        data = super(ISimpleScarf, self).__data__
        data["main_beam_guid"] = self.main_beam_guid
        data["cross_beam_guid"] = self.cross_beam_guid
        data["length"] = self.length
        data["depth_ref_side"] = self.depth_ref_side
        data["depth_opp_side"] = self.depth_opp_side
        data["num_drill_hole"] = self.num_drill_hole
        data["drill_hole_diam"] = self.drill_hole_diam
        data["ref_side_index"] = self.ref_side_index
        return data

    def __init__(
        self,
        main_beam=None,
        cross_beam=None,
        length=None,
        depth_ref_side=None,
        depth_opp_side=None,
        num_drill_hole=0,
        drill_hole_diam=20.0,
        ref_side_index=0,
        **kwargs
    ):
        super(ISimpleScarf, self).__init__(elements=(main_beam,cross_beam),**kwargs)
        self.main_beam = main_beam
        self.cross_beam = cross_beam
        self.main_beam_guid = kwargs.get("main_beam_guid") or (str(main_beam.guid) if main_beam else None)
        self.cross_beam_guid = kwargs.get("cross_beam_guid") or (str(cross_beam.guid) if cross_beam else None)
        
        self.length = length
        self.depth_ref_side = depth_ref_side
        self.depth_opp_side = depth_opp_side
        self.num_drill_hole = num_drill_hole
        self.drill_hole_diam = drill_hole_diam
        self.ref_side_index = ref_side_index

        self.features = []

        if self.main_beam and self.cross_beam:
            self._set_unset_attributes()

    @property
    def elements(self):
        return [self.main_beam, self.cross_beam]
    
    @property
    def main_beam_ref_side_index(self):
        return self.ref_side_index
    
    @property
    def cross_beam_ref_side_index(self):
        ref_side_dict = beam_ref_side_incidence_with_vector(self.cross_beam, self.main_beam.ref_sides[self.main_beam_ref_side_index].normal, ignore_ends=True)
        return max(ref_side_dict, key=ref_side_dict.get)
    
    @property
    def origin(self):
        return self.location

    def _get_beam_side(self, beam):
        """Finds if the cutting plane intersects the beam at its start or end."""
        side, _ = beam.endpoint_closest_to_point(self.origin)
        return side
    
    def extension_plane(self, beam):
        ext_side_index = 4 if self._get_beam_side(beam) == "start" else 5
        return ext_side_index, beam.ref_sides[ext_side_index]

    def add_extensions(self):
        """Calculates and adds the required blank extensions to both beams."""
        assert self.main_beam and self.cross_beam

        try:            
            _, main_extension_frame = self.extension_plane(self.main_beam)
            _, main_extension_frame.translate(main_extension_frame.normal * self.length/2)
            
            _, cross_extension_frame = self.extension_plane(self.cross_beam)
            _, cross_extension_frame.translate(cross_extension_frame.normal * self.length/2)

            start_a, end_a = self.main_beam.extension_to_plane(Plane.from_frame(main_extension_frame))
            start_b, end_b = self.cross_beam.extension_to_plane(Plane.from_frame(cross_extension_frame))
            
        except AttributeError as ae:
            raise BeamJoiningError(self.elements, self, debug_info=str(ae), debug_geometries=[main_extension_frame])
        except Exception as ex:
            raise BeamJoiningError(self.elements, self, debug_info=str(ex))
            
        self.main_beam.add_blank_extension(start_a, end_a, self.guid)
        self.cross_beam.add_blank_extension(start_b, end_b, self.guid)

    def add_features(self):
        """Generates and assigns the SimpleScarf fabrication features."""
        assert self.main_beam and self.cross_beam
        
        if self.features:
            self.main_beam.remove_features(self.features)
            self.cross_beam.remove_features(self.features)
            self.features = []

        main_feature = SimpleScarf.from_beam_and_side(
            self.main_beam,
            side=self._get_beam_side(self.main_beam),
            length=self.length,
            depth_ref_side=self.depth_ref_side,
            depth_opp_side=self.depth_opp_side,
            num_drill_hole=self.num_drill_hole,
            drill_hole_diam=self.drill_hole_diam,
            ref_side_index=self.ref_side_index
        )

        cross_feature = SimpleScarf.from_beam_and_side(
            self.cross_beam,
            side=self._get_beam_side(self.cross_beam),
            length=self.length,
            depth_ref_side=self.depth_opp_side,
            depth_opp_side=self.depth_ref_side,
            num_drill_hole=self.num_drill_hole,
            drill_hole_diam=self.drill_hole_diam,
            ref_side_index=self.cross_beam_ref_side_index
        )
            
        self.main_beam.add_features(main_feature)
        self.cross_beam.add_features(cross_feature)
        self.features.extend([main_feature, cross_feature])

    @classmethod
    def check_elements_compatibility(cls, elements, raise_error=False):
        """Checks if the cluster of beams complies with the requirements for the ISimpleScarf joint."""
        dot = abs(elements[0].centerline.direction.dot(elements[1].centerline.direction))
        
        if not TOL.is_close(dot, 1):
            if not raise_error:
                return False
            raise BeamJoiningError(elements, cls, debug_info="The two beams are not parallel to create a Simple Scarf joint.")
            
        return True

    def restore_beams_from_keys(self, model):
        """After de-serialization, restores references to the main and other beams saved in the model."""
        self.main_beam = model.element_by_guid(self.main_beam_guid)
        self.cross_beam = model.element_by_guid(self.cross_beam_guid)
    
    def _set_unset_attributes(self):
        """Sets attributes that were not provided at initialization based on the geometry of the beams."""
        width, height = self.main_beam.get_dimensions_relative_to_side(self.ref_side_index)
        
        if self.length is None:
            self.length = height * 3
        
        if self.depth_ref_side is None:
            self.depth_ref_side = height * 0.25
        
        if self.depth_opp_side is None:
            self.depth_opp_side = height * 0.25