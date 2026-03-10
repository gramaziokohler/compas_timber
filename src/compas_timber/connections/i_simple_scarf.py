import math

from compas.tolerance import TOL

from compas.geometry import Translation
from compas.geometry import Plane
from compas.geometry import Point
from compas.geometry import Plane
from compas.geometry import Frame
from compas.geometry import Vector

from compas_timber.errors import BeamJoiningError
from compas_timber.fabrication import SimpleScarf
from compas_timber.fabrication.btlx import OrientationType

from .joint import Joint
from .solver import JointTopology
from .utilities import beam_ref_side_incidence
from .utilities import beam_ref_side_incidence_with_vector
from compas_timber.utils import distance_segment_segment_points


class ISimpleScarf(Joint):

    SUPPORTED_TOPOLOGY = JointTopology.TOPO_I

    @property
    def __data__(self):
        data = super(ISimpleScarf, self).__data__
        data["main_beam_guid"] = self.main_beam_guid
        data["cross_beam_guid"] = self.cross_beam_guid
        data["length"] = self.length
        data["num_drill_hole"] = self.num_drill_hole
        data["drill_hole_diam_1"] = self.drill_hole_diam_1
        data["drill_hole_diam_2"] = self.drill_hole_diam_2
        data["cutting_plane"] = self.cutting_plane

        return data

    # fmt: off
    def __init__(
        self,
        main_beam=None,
        cross_beam=None,
        length=None,
        depth_ref_side=None,
        depth_opp_side=None,
        num_drill_hole=0,
        drill_hole_diam_1=20.0, 
        drill_hole_diam_2=20.0,
        cutting_plane=None,
        ref_side_index=None,
        **kwargs
    ):
        super(ISimpleScarf, self).__init__(**kwargs)
        self.main_beam = main_beam
        self.cross_beam = cross_beam
        self.main_beam_guid = kwargs.get("main_beam_guid", None) or str(main_beam.guid)
        self.cross_beam_guid = kwargs.get("cross_beam_guid", None) or str(cross_beam.guid)
        self.length = length 
        self.depth_ref_side = main_beam.height / 3.0 if depth_ref_side is None else depth_ref_side
        self.depth_opp_side = main_beam.height / 3.0 if depth_opp_side is None else depth_opp_side
        self.num_drill_hole = num_drill_hole if num_drill_hole is not None else 0
        self.drill_hole_diam_1 = drill_hole_diam_1 if drill_hole_diam_1 is not None else 20.0
        self.drill_hole_diam_2 = drill_hole_diam_2 if drill_hole_diam_2 is not None else 20.0

        self.cutting_plane = cutting_plane if cutting_plane is not None else None
        self.ref_side_index = ref_side_index if ref_side_index is not None else 0
        self.features = []

    @property
    def elements(self):
        return [self.main_beam, self.cross_beam]
    
    @property
    def main_beam_ref_side_index(self):
        ref_side_dict = beam_ref_side_incidence_with_vector(self.main_beam, self.main_cutting_plane.normal, ignore_ends=True)
        ref_side_index = min(ref_side_dict, key=ref_side_dict.get)
        main_ref_side_angle = abs(min(ref_side_dict.values()))
        height_side_index = (ref_side_index + 1) % 4
        vertical_height = self.main_beam.ref_edges[ref_side_index].start.distance_to_point(self.main_beam.ref_edges[height_side_index].start)
        depth_ref_side = vertical_height / 4.0
        depth_opp_side = vertical_height / 4.0
        self.length = (vertical_height - (depth_ref_side + depth_opp_side)) / math.tan(main_ref_side_angle)
        return ref_side_index
    
    @property
    def cross_beam_ref_side_index(self):
        ref_side_dict = beam_ref_side_incidence_with_vector(self.cross_beam, self.cross_cutting_plane.normal, ignore_ends=True)
        self.cross_ref_side_angle = abs(min(ref_side_dict.values()))
        return min(ref_side_dict, key=ref_side_dict.get)
    
    def _calculate_main_and_cross_cutting_plane(self):
        assert self.main_beam
        if self.cutting_plane:
            dot = self.cutting_plane.normal.dot(self.main_beam.centerline.direction)
            if TOL.is_close(dot, -1.0) or TOL.is_close(dot, 0.0) or TOL.is_close(dot, 1.0):
                self.cutting_plane = None
            else:
                self.main_cutting_plane = self.cutting_plane.copy()
                self.cross_cutting_plane = self.cutting_plane.copy()
                if dot < 0 and self.main_beam_orientation == "start" or dot > 0 and self.main_beam_orientation == "end":
                    self.main_cutting_plane.normal *= -1
                if dot < 0 and self.cross_beam_orientation == "start" or dot > 0 and self.cross_beam_orientation == "end":
                    self.cross_cutting_plane.normal *= -1
                self.main_beam_ref_side_index
                
        

    @property
    def main_beam_orientation(self):
        assert self.main_beam and self.cutting_plane
        dis = self.cutting_plane.point.distance_to_point(self.main_beam.centerline.start)
        die = self.cutting_plane.point.distance_to_point(self.main_beam.centerline.end)
        if TOL.is_close(dis, 0.0):
            return "start"
        elif TOL.is_close(die, 0.0):
            return "end"
        else:
            raise BeamJoiningError(self.elements, self, debug_info="The cutting plane does not intersect with the main beam's centerline.")

    @property
    def cross_beam_orientation(self):
        assert self.cross_beam and self.cutting_plane
        dis = self.cutting_plane.point.distance_to_point(self.cross_beam.centerline.start)
        die = self.cutting_plane.point.distance_to_point(self.cross_beam.centerline.end)
        if TOL.is_close(dis, 0.0):
            return "start"
        elif TOL.is_close(die, 0.0):
            return "end"
        else:
            raise BeamJoiningError(self.elements, self, debug_info="The cutting plane does not intersect with the main beam's centerline.")
    
    @property
    def extension_plane_origin(self):
        dist, p1, p2 = distance_segment_segment_points(self.main_beam.centerline, self.cross_beam.centerline)
        p1 = Point(*p1)
        p2 = Point(*p2)
        return (p1 + p2) * 0.5

    def extension_plane(self, beam, point):
        side, _ = beam.endpoint_closest_to_point(point)
        if side == "start":
            ext_side_index = 4
        else:
            ext_side_index = 5
        return beam.ref_sides[ext_side_index]

    def add_extensions(self):
        assert self.main_beam and self.cross_beam
        self._calculate_main_and_cross_cutting_plane()
        if not self.cutting_plane:
            self.length = self.main_beam.height * 3.0 if self.length is None else self.length
        try:
            ext_plane_origin = self.extension_plane_origin
            main_extension_frame = self.extension_plane(self.main_beam, ext_plane_origin)
            main_extension_frame.translate(main_extension_frame.normal * (self.length/2))
            other_extension_frame = self.extension_plane(self.cross_beam, ext_plane_origin)
            other_extension_frame.translate(other_extension_frame.normal * (self.length/2))
            start_a, end_a = self.main_beam.extension_to_plane(Plane.from_frame(main_extension_frame))
            start_b, end_b = self.cross_beam.extension_to_plane(Plane.from_frame(other_extension_frame))
        #not sure about how the errors should be handled for two beams
        except AttributeError as ae:
            raise BeamJoiningError(self.elements, self, debug_info=str(ae), debug_geometries=[main_extension_frame])
        except Exception as ex:
            raise BeamJoiningError(self.elements, self, debug_info=str(ex))
        self.main_beam.add_blank_extension(start_a, end_a, self.main_beam_guid)
        self.cross_beam.add_blank_extension(start_b, end_b, self.cross_beam_guid)

    def add_features(self):
        assert self.main_beam and self.cross_beam

        if self.features:
            self.main_beam.remove_features(self.features)
            self.cross_beam.remove_features(self.features)

        

        if not self.cutting_plane:
            main_feature = SimpleScarf.from_beams(
                self.main_beam,
                self.cross_beam,
                length=self.length,
                depth_ref_side = self.depth_ref_side,
                depth_opp_side = self.depth_opp_side,
                num_drill_hole=self.num_drill_hole,
                drill_hole_diam_1=self.drill_hole_diam_1,
                drill_hole_diam_2=self.drill_hole_diam_2,
                ref_side_index=self.ref_side_index
                )
            
            cross_feature = SimpleScarf.from_beams(
                self.cross_beam,
                self.main_beam,
                length=self.length,
                depth_ref_side = self.depth_opp_side,
                depth_opp_side = self.depth_ref_side,
                num_drill_hole=self.num_drill_hole,
                drill_hole_diam_1=self.drill_hole_diam_1,
                drill_hole_diam_2=self.drill_hole_diam_2,
                ref_side_index=((main_feature.ref_side_index+2)%4)
                # ref_side_index=2
                )
        else:
            main_feature = SimpleScarf.from_plane_and_beam(
                self.main_beam,
                self.main_cutting_plane
                )
            
            cross_feature = SimpleScarf.from_plane_and_beam(
                self.cross_beam,
                self.cross_cutting_plane
                )

        self.main_beam.add_features(main_feature)
        self.cross_beam.add_features(cross_feature)
        self.features.extend([main_feature, cross_feature])

    @classmethod
    def check_elements_compatibility(cls, elements, raise_error=False):
        """Checks if the cluster of beams complies with the requirements for the ISimpleScarf joint.

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
        dot = abs(elements[0].centerline.direction.dot(elements[1].centerline.direction))
        if not TOL.is_close(dot, 1):
            if not raise_error:
                return False
            raise BeamJoiningError(elements, cls, debug_info="The the two beams are not parallel to create a Simple Scarf joint.")

        return True

    def restore_beams_from_keys(self, model):
        """After de-serialization, restores references to the main and other beams saved in the model."""
        self.main_beam = model.element_by_guid(self.main_beam_guid)
        self.cross_beam = model.element_by_guid(self.cross_beam_guid)
