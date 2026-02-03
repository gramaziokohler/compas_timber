from compas.tolerance import TOL

from compas.geometry import Translation
from compas.geometry import Plane
from compas.geometry import Point

from compas_timber.errors import BeamJoiningError
from compas_timber.fabrication import SimpleScarf

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
        data["other_beam_guid"] = self.other_beam_guid
        data["length"] = self.length
        data["num_drill_hole"] = self.num_drill_hole
        data["drill_hole_diam_1"] = self.drill_hole_diam_1
        data["drill_hole_diam_2"] = self.drill_hole_diam_2
        return data

    # fmt: off
    def __init__(
        self,
        main_beam=None,
        other_beam=None,
        length=None,
        num_drill_hole=0,
        drill_hole_diam_1=20.0, 
        drill_hole_diam_2=20.0,
        **kwargs
    ):
        super(ISimpleScarf, self).__init__(**kwargs)
        self.main_beam = main_beam
        self.other_beam = other_beam
        self.main_beam_guid = kwargs.get("main_beam_guid", None) or str(main_beam.guid)
        self.other_beam_guid = kwargs.get("other_beam_guid", None) or str(other_beam.guid)
        self.length = main_beam.height * 3.0 if length is None else length
        self.num_drill_hole = num_drill_hole if num_drill_hole is not None else 0
        self.drill_hole_diam_1 = drill_hole_diam_1 if drill_hole_diam_1 is not None else 20.0
        self.drill_hole_diam_2 = drill_hole_diam_2 if drill_hole_diam_2 is not None else 20.0

        self.features = []

    @property
    def elements(self):
        return [self.main_beam, self.other_beam]

    @property
    def extension_plane_origin(self):
        dist, p1, p2 = distance_segment_segment_points(self.main_beam.centerline, self.other_beam.centerline)
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
        assert self.main_beam and self.other_beam
        try:
            ext_plane_origin = self.extension_plane_origin
            main_extension_frame = self.extension_plane(self.main_beam, ext_plane_origin)
            main_extension_frame.translate(main_extension_frame.normal * (self.length/2))
            other_extension_frame = self.extension_plane(self.other_beam, ext_plane_origin)
            other_extension_frame.translate(other_extension_frame.normal * (self.length/2))
            start_a, end_a = self.main_beam.extension_to_plane(Plane.from_frame(main_extension_frame))
            start_b, end_b = self.other_beam.extension_to_plane(Plane.from_frame(other_extension_frame))
        #nor sure about how the errors should be handled for two beams
        except AttributeError as ae:
            raise BeamJoiningError(self.elements, self, debug_info=str(ae), debug_geometries=[main_extension_frame])
        except Exception as ex:
            raise BeamJoiningError(self.elements, self, debug_info=str(ex))
        self.main_beam.add_blank_extension(start_a, end_a, self.main_beam_guid)
        self.other_beam.add_blank_extension(start_b, end_b, self.other_beam_guid)

    def add_features(self):
        assert self.main_beam and self.other_beam

        if self.features:
            self.main_beam.remove_features(self.features)
            self.other_beam.remove_features(self.features)

        main_feature = SimpleScarf.from_beams(
            self.main_beam,
            self.other_beam,
            length=self.length,
            # num_drill_hole=self.num_drill_hole,
            # drill_hole_diam_1=self.drill_hole_diam_1,
            # drill_hole_diam_2=self.drill_hole_diam_2
            )
        
        other_feature = SimpleScarf.from_beams(
            self.other_beam,
            self.main_beam,
            ref_side_index=2,
            length=self.length,
            # num_drill_hole=self.num_drill_hole,
            # drill_hole_diam_1=self.drill_hole_diam_1,
            # drill_hole_diam_2=self.drill_hole_diam_2
            )

        self.main_beam.add_features(main_feature)
        self.other_beam.add_features(other_feature)
        self.features.extend([main_feature, other_feature])

    def restore_beams_from_keys(self, model):
        """After de-serialization, restores references to the main and other beams saved in the model."""
        self.main_beam = model.element_by_guid(self.main_beam_guid)
        self.other_beam = model.element_by_guid(self.other_beam_guid)
