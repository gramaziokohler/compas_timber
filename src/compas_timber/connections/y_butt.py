from compas.geometry import Plane
from compas.geometry import Vector
from compas.geometry import dot_vectors
from compas.tolerance import TOL

from compas_timber.connections import Joint
from compas_timber.connections import JointTopology
from compas_timber.connections.utilities import are_beams_aligned_with_cross_vector
from compas_timber.connections.utilities import beam_ref_side_incidence
from compas_timber.errors import BeamJoiningError
from compas_timber.fabrication import JackRafterCut
from compas_timber.fabrication import Lap
from compas_timber.fabrication.double_cut import DoubleCut
from compas_timber.utils import intersection_line_line_param


class YButtJoint(Joint):
    """Represents a Y-Butt type joint which joins the ends of three beams,
    trimming the main beam with a double cut and the cross beams with a miter cut.

    Please use `YButtJoint.create()` to properly create an instance of this class and associate it with a model.

    Parameters
    ----------
    main_beam : :class:`~compas_timber.parts.Beam`
        The main beam to be joined.
    cross_beams : list of :class:`~compas_timber.parts.Beam`
        The cross beams to be joined.
    mill_depth : float
        The depth of the pocket to be milled in the cross beams.

    Attributes
    ----------
    main_beam : :class:`~compas_timber.parts.Beam`
        The main beam to be joined.
    cross_beams : :class:`~compas_timber.parts.Beam`
        The cross beam to be joined.
    mill_depth : float
        The depth of the pocket to be milled in the cross beams.

    """

    # TODO: implement Y and K topologies
    SUPPORTED_TOPOLOGY = JointTopology.TOPO_UNKNOWN
    MIN_ELEMENT_COUNT = 3
    MAX_ELEMENT_COUNT = 3

    @property
    def __data__(self):
        data = super(YButtJoint, self).__data__
        data["main_beam_guid"] = self.main_beam_guid
        data["cross_beam_a_guid"] = self.cross_beam_a_guid
        data["cross_beam_b_guid"] = self.cross_beam_b_guid
        data["mill_depth"] = self.mill_depth
        return data

    def __init__(self, main_beam=None, cross_beam_a=None, cross_beam_b=None, mill_depth=None, **kwargs):
        super(YButtJoint, self).__init__(**kwargs)
        self.main_beam = main_beam
        self.cross_beams = [cross_beam_a, cross_beam_b]
        self.main_beam_guid = kwargs.get("main_beam_guid", None) or str(main_beam.guid)
        self.cross_beam_a_guid = kwargs.get("cross_beam_a_guid", None) or str(cross_beam_a.guid)
        self.cross_beam_b_guid = kwargs.get("cross_beam_b_guid", None) or str(cross_beam_b.guid)
        self.mill_depth = mill_depth
        self.features = []

    @property
    def beams(self):
        return [self.main_beam] + self.cross_beams

    @property
    def elements(self):
        return self.beams

    def check_elements_compatibility(self):
        """Checks if the elements are compatible for the creation of the joint.

        For the Y-Butt joint, this method checks if the two cross beams are coplanar and have the same dimensions.

        Raises
        ------
        BeamJoiningError
            If the elements are not compatible for the creation of the joint.
        """

        if not are_beams_aligned_with_cross_vector(*self.cross_beams):
            raise BeamJoiningError(
                beams=self.cross_beams,
                joint=self,
                debug_info="The two cross beams are not coplanar to create a Y-Butt joint.",
            )
        # calculate widths and heights of the cross beams
        else:
            dimensions = []
            for beam in self.cross_beams:
                ref_side_index = self.cross_beam_ref_side_index(beam)
                dimensions.append(beam.get_dimensions_relative_to_side(ref_side_index)[0])  # beams only need a miter that meets in the corner. width can be different
            # check if the dimensions of both cross beams match
            if dimensions[0] != dimensions[1]:
                raise BeamJoiningError(self.cross_beams, self, debug_info="The two cross beams must have the same dimensions to create a Y-Butt joint.")

    def cross_beam_ref_side_index(self, beam):
        ref_side_dict = beam_ref_side_incidence(self.main_beam, beam, ignore_ends=True)
        ref_side_index = min(ref_side_dict, key=ref_side_dict.get)
        return ref_side_index

    def main_beam_ref_side_index(self, beam):
        ref_side_dict = beam_ref_side_incidence(beam, self.main_beam, ignore_ends=True)
        ref_side_index = min(ref_side_dict, key=ref_side_dict.get)
        return ref_side_index

    def get_miter_planes(self, beam_a, beam_b):
        # intersection point (average) of both centrelines
        [px_a, _], [px_b, _] = intersection_line_line_param(
            beam_a.centerline,
            beam_b.centerline,
            max_distance=float("inf"),
            limit_to_segments=False,
        )

        parallel = False
        if px_a is None or px_b is None:  # beams are parallel
            parallel = True
            px_a = beam_a.endpoint_closest_to_point(beam_b.midpoint)[1]
            px_b = beam_b.endpoint_closest_to_point(beam_a.midpoint)[1]

        p = (px_a + px_b) * 0.5
        # makes sure they point outward of a joint point
        va = Vector.from_start_end(beam_a.endpoint_closest_to_point(p)[1], beam_a.midpoint)
        vb = Vector.from_start_end(beam_b.endpoint_closest_to_point(p)[1], beam_b.midpoint)

        va.unitize()
        vb.unitize()
        v_bisector = va + vb
        # get frame
        if parallel:
            pln_a = Plane(p, va)
            pln_b = Plane(p, vb)
        else:
            v_perp = Vector(*v_bisector.cross(va))
            v_normal = Vector(*v_bisector.cross(v_perp))

            pln_a = Plane(p, v_normal)
            pln_b = Plane(p, v_normal * -1.0)
        return pln_a, pln_b

    def add_extensions(self):
        """Calculates and adds the necessary extensions to the beams.

        This method is automatically called when joint is created by the call to `Joint.create()`.

        Raises
        ------
        BeamJoiningError
            If the extension could not be calculated.

        """
        assert self.main_beam and self.cross_beams[0] and self.cross_beams[1]
        extensions = []
        for beam in self.cross_beams:
            try:
                cutting_plane = beam.ref_sides[self.cross_beam_ref_side_index(beam)]
                if self.mill_depth:
                    cutting_plane.translate(-cutting_plane.normal * self.mill_depth)
                extensions.append(self.main_beam.extension_to_plane(cutting_plane))
            except AttributeError as ae:
                raise BeamJoiningError(beams=self.elements, joint=self, debug_info=str(ae), debug_geometries=[cutting_plane])
            except Exception as ex:
                raise BeamJoiningError(beams=self.elements, joint=self, debug_info=str(ex))
        start_main, end_main = max(extensions[0][0], extensions[1][0]), max(extensions[0][1], extensions[1][1])
        extension_tolerance = 0.01  # TODO: this should be proportional to the unit used
        self.main_beam.add_blank_extension(
            start_main + extension_tolerance,
            end_main + extension_tolerance,
            self.guid,
        )

        start_a, start_b = None, None
        plane_a, plane_b, start_a, end_a, start_b, end_b = None, None, None, None, None, None
        try:
            plane_a, plane_b = self.get_miter_planes(*self.cross_beams)
            start_a, end_a = self.cross_beams[0].extension_to_plane(plane_a)
            start_b, end_b = self.cross_beams[1].extension_to_plane(plane_b)
        except AttributeError as ae:
            # I want here just the plane that caused the error
            geometries = [plane_b] if start_a is not None else [plane_a]
            raise BeamJoiningError(self.elements, self, debug_info=str(ae), debug_geometries=geometries)
        except Exception as ex:
            raise BeamJoiningError(self.elements, self, debug_info=str(ex))
        self.cross_beams[0].add_blank_extension(start_a, end_a, self.guid)
        self.cross_beams[1].add_blank_extension(start_b, end_b, self.guid)

    def add_features(self):
        """Adds the required extension and trimming features to both beams.

        This method is automatically called when joint is created by the call to `Joint.create()`.

        """

        assert self.main_beam and self.cross_beams[0] and self.cross_beams[1]
        if self.features:
            self.main_beam.remove_features(self.features)
            self.cross_beams[0].remove_features(self.features)
            self.cross_beams[1].remove_features(self.features)

        # get the cutting planes for the main beam
        planes = []
        for beam in self.cross_beams:
            cutting_plane = Plane.from_frame(beam.ref_sides[self.cross_beam_ref_side_index(beam)])
            if self.mill_depth:
                cutting_plane.translate(-cutting_plane.normal * self.mill_depth)
            planes.append(cutting_plane)
        for pl, b in zip(planes, self.cross_beams):
            pl.point = pl.closest_point(b.midpoint)
        if TOL.is_close(dot_vectors(planes[0].normal, planes[1].normal), 1.0):
            main_feature = JackRafterCut.from_plane_and_beam(Plane(planes[0].point, -planes[0].normal), self.main_beam)
        else:
            main_feature = DoubleCut.from_planes_and_beam(planes, self.main_beam)
        self.main_beam.add_features(main_feature)
        self.features = [main_feature]

        # apply the pockets on the cross beams
        if self.mill_depth:
            for beam in self.cross_beams:
                ref_side_index = self.main_beam_ref_side_index(beam)
                cross_cutting_plane = self.main_beam.ref_sides[ref_side_index]
                lap_length = self.main_beam.get_dimensions_relative_to_side(ref_side_index)[1]
                cross_feature = Lap.from_plane_and_beam(
                    cross_cutting_plane,
                    beam,
                    lap_length,
                    self.mill_depth,
                    ref_side_index=self.cross_beam_ref_side_index(beam),
                )
                beam.add_features(cross_feature)
                self.features.append(cross_feature)

        # add miter features on cross_beams
        try:
            plane_a, plane_b = self.get_miter_planes(*self.cross_beams)
        except Exception as ex:
            raise BeamJoiningError(self.elements, self, debug_info=str(ex))
        cut1 = JackRafterCut.from_plane_and_beam(plane_a, self.cross_beams[0])
        cut2 = JackRafterCut.from_plane_and_beam(plane_b, self.cross_beams[1])
        self.cross_beams[0].add_features(cut1)
        self.cross_beams[1].add_features(cut2)
        self.features = [cut1, cut2]

    def restore_beams_from_keys(self, model):
        """After de-serialization, restores references to the main and cross beams saved in the model."""
        self.main_beam = model.element_by_guid(self.main_beam_guid)
        self.cross_beams = [model.element_by_guid(self.cross_beam_a_guid), model.element_by_guid(self.cross_beam_b_guid)]
