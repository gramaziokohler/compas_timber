import math

from compas.geometry import Plane
from compas.geometry import Point
from compas.tolerance import TOL

from compas_timber.errors import BeamJoiningError
from compas_timber.fabrication import SimpleScarf
from compas_timber.utils import distance_segment_segment_points

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
        data["num_drill_hole"] = self.num_drill_hole
        data["drill_hole_diam_1"] = self.drill_hole_diam_1
        data["drill_hole_diam_2"] = self.drill_hole_diam_2
        data["cutting_plane"] = self.cutting_plane
        return data

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
        ref_side_index=0,
        **kwargs
    ):
        super(ISimpleScarf, self).__init__(**kwargs)
        self.main_beam = main_beam
        self.cross_beam = cross_beam
        self.main_beam_guid = kwargs.get("main_beam_guid") or (str(main_beam.guid) if main_beam else None)
        self.cross_beam_guid = kwargs.get("cross_beam_guid") or (str(cross_beam.guid) if cross_beam else None)
        
        self.length = length
        self.depth_ref_side = depth_ref_side if depth_ref_side is not None else (main_beam.height / 4.0 if main_beam else None)
        self.depth_opp_side = depth_opp_side if depth_opp_side is not None else (main_beam.height / 4.0 if main_beam else None)
        self.num_drill_hole = num_drill_hole if num_drill_hole is not None else 0
        self.drill_hole_diam_1 = drill_hole_diam_1 if drill_hole_diam_1 is not None else 20.0
        self.drill_hole_diam_2 = drill_hole_diam_2 if drill_hole_diam_2 is not None else 20.0

        self.cutting_plane = cutting_plane
        self.ref_side_index = ref_side_index if ref_side_index is not None else 0
        
        self.main_cutting_plane = None
        self.cross_cutting_plane = None
        
        self.features = []

    @property
    def elements(self):
        return [self.main_beam, self.cross_beam]

    def _calculate_cutting_planes(self):
        """Calculates and stores the adjusted cutting planes for main and cross beams."""
        if not self.cutting_plane:
            self.main_cutting_plane = None
            self.cross_cutting_plane = None
            return

        dot = self.cutting_plane.normal.dot(self.main_beam.centerline.direction)
        
        # If plane is completely perpendicular or parallel, it's invalid for a scarf joint
        if TOL.is_close(dot, -1.0) or TOL.is_close(dot, 0.0) or TOL.is_close(dot, 1.0):
            self.main_cutting_plane = None
            self.cross_cutting_plane = None
            return

        self.main_cutting_plane = self.cutting_plane.copy()
        self.cross_cutting_plane = self.cutting_plane.copy()

        # Adjust normals to point towards the bulk of the beam
        main_orientation = self._get_beam_orientation(self.main_beam)
        if (dot < 0 and main_orientation == "start") or (dot > 0 and main_orientation == "end"):
            self.main_cutting_plane.normal *= -1

        cross_orientation = self._get_beam_orientation(self.cross_beam)
        if (dot < 0 and cross_orientation == "start") or (dot > 0 and cross_orientation == "end"):
            self.cross_cutting_plane.normal *= -1

    def _get_beam_orientation(self, beam):
        """Finds if the cutting plane intersects the beam at its start or end."""
        # if not self.cutting_plane:
        #     return "start"
        
        dis = self.cutting_plane.point.distance_to_point(beam.centerline.start)
        die = self.cutting_plane.point.distance_to_point(beam.centerline.end)
        
        if TOL.is_close(dis, 0.0):
            return "start"
        elif TOL.is_close(die, 0.0):
            return "end"
        else:
            raise BeamJoiningError(self.elements, self, debug_info="The cutting plane does not intersect with the beam's centerline at an endpoint.")

    def get_length(self):
        """Returns the defined length or cleanly calculates it based on the cutting plane geometry."""
        if self.length is not None:
            return self.length

        if not self.main_cutting_plane:
            return self.main_beam.height * 3.0

        ref_side_dict = beam_ref_side_incidence_with_vector(self.main_beam, self.main_cutting_plane.normal, ignore_ends=True)
        ref_side_angle = abs(min(ref_side_dict.values()))
        ref_side_index = min(ref_side_dict, key=ref_side_dict.get)
        height_side_index = (ref_side_index + 1) % 4
        
        vertical_height = self.main_beam.ref_edges[ref_side_index].start.distance_to_point(self.main_beam.ref_edges[height_side_index].start)
        
        depth_ref_side = vertical_height / 4.0
        depth_opp_side = vertical_height / 4.0
        
        return (vertical_height - (depth_ref_side + depth_opp_side)) / math.tan(ref_side_angle)

    @property
    def extension_plane_origin(self):
        dist, p1, p2 = distance_segment_segment_points(self.main_beam.centerline, self.cross_beam.centerline)
        p1 = Point(*p1)
        p2 = Point(*p2)
        return (p1 + p2) * 0.5

    def extension_plane(self, beam, point):
        side, _ = beam.endpoint_closest_to_point(point)
        ext_side_index = 4 if side == "start" else 5
        return beam.ref_sides[ext_side_index]

    def add_extensions(self):
        """Calculates and adds the required blank extensions to both beams."""
        assert self.main_beam and self.cross_beam
        
        self._calculate_cutting_planes()
        ext_length = self.get_length()

        try:
            ext_plane_origin = self.extension_plane_origin
            
            main_extension_frame = self.extension_plane(self.main_beam, ext_plane_origin)
            main_extension_frame.translate(main_extension_frame.normal * (ext_length / 2.0))
            
            other_extension_frame = self.extension_plane(self.cross_beam, ext_plane_origin)
            other_extension_frame.translate(other_extension_frame.normal * (ext_length / 2.0))
            
            start_a, end_a = self.main_beam.extension_to_plane(Plane.from_frame(main_extension_frame))
            start_b, end_b = self.cross_beam.extension_to_plane(Plane.from_frame(other_extension_frame))
            
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

        length = self.get_length()

        if not self.main_cutting_plane:
            main_feature = SimpleScarf.from_beams(
                self.main_beam,
                self.cross_beam,
                length=length,
                depth_ref_side=self.depth_ref_side,
                depth_opp_side=self.depth_opp_side,
                num_drill_hole=self.num_drill_hole,
                drill_hole_diam_1=self.drill_hole_diam_1,
                drill_hole_diam_2=self.drill_hole_diam_2,
                ref_side_index=self.ref_side_index
            )
            
            cross_feature = SimpleScarf.from_beams(
                self.cross_beam,
                self.main_beam,
                length=length,
                depth_ref_side=self.depth_opp_side,
                depth_opp_side=self.depth_ref_side,
                num_drill_hole=self.num_drill_hole,
                drill_hole_diam_1=self.drill_hole_diam_1,
                drill_hole_diam_2=self.drill_hole_diam_2,
                ref_side_index=((main_feature.ref_side_index + 2) % 4)
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