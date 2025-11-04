from compas.tolerance import TOL

from compas.geometry import Translation

from compas_timber.errors import BeamJoiningError
from compas_timber.fabrication import SimpleScarf

from .joint import Joint
from .solver import JointTopology
from .utilities import beam_ref_side_incidence
from .utilities import beam_ref_side_incidence_with_vector

from itertools import combinations


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
        num_drill_hole=None,
        drill_hole_diam_1=None,
        drill_hole_diam_2=None,
        **kwargs
    ):
        super(ISimpleScarf, self).__init__(main_beam, other_beam, **kwargs)
        self.main_beam = main_beam
        self.other_beam = other_beam
        self.main_beam_guid = kwargs.get("main_beam_guid", None) or str(main_beam.guid)
        self.other_beam_guid = kwargs.get("other_beam_guid", None) or str(other_beam.guid)
        self.length = length
        self.num_drill_hole = num_drill_hole
        self.drill_hole_diam_1 = drill_hole_diam_1
        self.drill_hole_diam_2 = drill_hole_diam_2

        self.features = []

    @property
    def elements(self):
        return [self.main_beam, self.other_beam]

    @property
    def extension_plane_origin(self):
        main_points = [self.main_beam.centerline.start, self.main_beam.centerline.end]
        other_points = [self.other_beam.centerline.start, self.other_beam.centerline.end]

        min_dist = float("inf")
        closest_pair = None
        for i in combinations(main_points, other_points):
            dist = i[0].distance_to_point(i[1])
            if dist < min_dist:
                min_dist = dist
                closest_pair = i
        return (closest_pair[0] + closest_pair[1])/2

    @property
    def extension_plane(self, beam, point):
        if beam.endpoint_closest_to_point(point) == "start":
            ref_side_index = 5
        else:
            ref_side_index = 6
        return beam.ref_sides[ref_side_index]

    def add_extensions(self):
        assert self.main_beam and self.other_beam
        ext_plane_origin = self.extension_plane_origin
        try:
            main_extension_plane = self.extension_plane(self.main_beam, ext_plane_origin)
            main_extension_plane.transform(Translation.from_vector(main_extension_plane.normal * self.length/2))
            other_extension_plane = self.extension_plane(self.other_beam, ext_plane_origin)
            other_extension_plane.transform(Translation.from_vector(other_extension_plane.normal * self.length/2))
            start_a, end_a = self.main_beam.extension_to_plane(main_extension_plane)
            start_b, end_b = self.other_beam.extension_to_plane(other_extension_plane)
        #nor sure about how the errors should be handled for two beams
        except AttributeError as ae:
            raise BeamJoiningError(self.main_beam, self, debug_info=str(ae), debug_geometries=main_extension_plane)
        except Exception as ex:
            raise BeamJoiningError(self.main_beam, self, debug_info=str(ex))
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
            )





