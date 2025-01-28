from compas.geometry import Vector
from compas.geometry import Point
from compas.geometry import Plane
from compas.geometry import Frame

from compas_timber.elements import beam
from compas_timber.utils import intersection_line_line_param
from compas_timber.connections import Joint
from compas_timber.connections import JointTopology
from compas_timber.connections.utilities import beam_ref_side_incidence
from compas_timber.errors import BeamJoiningError
from compas_timber.fabrication import JackRafterCut
from compas_timber.fabrication import Lap
from compas_timber.fabrication.double_cut import DoubleCut


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
        The depth of the pocket to be milled in the cross beam.

    Attributes
    ----------
    main_beam : :class:`~compas_timber.parts.Beam`
        The main beam to be joined.
    cross_beams : :class:`~compas_timber.parts.Beam`
        The cross beam to be joined.
    mill_depth : float
        The depth of the pocket to be milled in the cross beam.

    """

    SUPPORTED_TOPOLOGY = JointTopology.TOPO_UNKNOWN
    MIN_ELEMENT_COUNT = 3
    MAX_ELEMENT_COUNT = 3

    @property
    def __data__(self):
        data = super(YButtJoint, self).__data__
        data["main_beam_guid"] = self.main_beam_guid
        data["cross_beam_guids"] = self.cross_beam_guids
        data["mill_depth"] = self.mill_depth
        return data

    def __init__(self, main_beam=None, cross_beams=None, mill_depth=None, **kwargs):
        super(YButtJoint, self).__init__(**kwargs)
        self.main_beam = main_beam
        self.cross_beams = cross_beams
        self.main_beam_guid = kwargs.get("main_beam_guid", None) or str(main_beam.guid)
        self.cross_beam_guids = kwargs.get("cross_beam_guids", None) or [str(beam.guid) for beam in cross_beams]
        self.mill_depth = mill_depth
        self.features = []

    @property
    def beams(self):
        return [self.main_beam] + self.cross_beams

    @property
    def elements(self):
        return self.beams

    @classmethod
    def create(cls, model, *elements, **kwargs):
        """Creates an instance of the BallNodeJoint and creates the new connection in `model`.

        This differs fom the generic `Joint.create()` method in that it passes the `beams` to
        the constructor of the BallNodeJoint as a list instead of as separate arguments.

        `beams` are expected to have been added to `model` before calling this method.

        This code does not verify that the given beams are adjacent and/or lie in a topology which allows connecting
        them. This is the responsibility of the calling code.

        A `ValueError` is raised if `beams` contains less than two `Beam` objects.

        Parameters
        ----------
        model : :class:`~compas_timber.model.TimberModel`
            The model to which the beams and this joing belong.
        beams : list(:class:`~compas_timber.parts.Beam`)
            A list containing beams that whould be joined together

        Returns
        -------
        :class:`compas_timber.connections.Joint`
            The instance of the created joint.

        """
        elements = list(elements)
        joint = cls(elements[0], elements[1:], **kwargs)
        model.add_joint(joint)
        return joint


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
        [pxA, tA], [pxB, tB] = intersection_line_line_param(
            beam_a.centerline,
            beam_b.centerline,
            max_distance=float("inf"),
            limit_to_segments=False,
        )
        # TODO: add error-trap + solution for I-miter joints

        p = (pxA + pxB) * 0.5
        print(beam_a.endpoint_closest_to_point(p)[1], beam_a.midpoint)
        # makes sure they point outward of a joint point
        va = Vector.from_start_end(beam_a.endpoint_closest_to_point(p)[1], beam_a.midpoint)
        vb = Vector.from_start_end(beam_b.endpoint_closest_to_point(p)[1], beam_b.midpoint)

        print("va", va)
        print("vb", vb)
        va.unitize()
        vb.unitize()
        v_bisector = va + vb
        # get frame
        v_perp = Vector(*v_bisector.cross(va))
        v_normal = Vector(*v_bisector.cross(v_perp))
        print("v_normal", v_normal)

        plnA = Plane(p, v_normal)
        plnB = Plane(p, v_normal * -1.0)
        print("plnA", plnA)
        return plnA, plnB

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

        """get the cutting planes for the main beam"""
        planes = []
        for beam in self.cross_beams:
            cutting_plane = beam.ref_sides[self.cross_beam_ref_side_index(beam)]
            if self.mill_depth:
                cutting_plane.translate(-cutting_plane.normal * self.mill_depth)
            planes.append(cutting_plane)
        print("planes", planes)
        main_feature = DoubleCut.from_planes_and_beam(planes, self.main_beam)
        self.main_beam.add_features(main_feature)
        self.features = [main_feature]

        """apply the pockets on the cross beams"""
        if self.mill_depth:
            for beam in self.cross_beams:
                cross_cutting_plane = self.main_beam.ref_sides[self.main_beam_ref_side_index(beam)]
                lap_length = self.main_beam.get_dimensions_relative_to_side(self.main_beam_ref_side_index(beam))[1]

                cross_feature = Lap.from_plane_and_beam(
                    cross_cutting_plane,
                    beam,
                    lap_length,
                    self.mill_depth,
                    is_pocket=True,
                    ref_side_index=self.cross_beam_ref_side_index(beam),
                )
                beam.add_features(cross_feature)
                self.features.append(cross_feature)

        """add miter features on cross_beams"""
        try:
            plane_a, plane_b = self.get_miter_planes(*self.cross_beams)
        except Exception as ex:
            raise BeamJoiningError(self.elements, self, debug_info=str(ex))
        print("Here1")
        cut1 = JackRafterCut.from_plane_and_beam(plane_a, self.cross_beams[0])
        cut2 = JackRafterCut.from_plane_and_beam(plane_b, self.cross_beams[1])
        self.cross_beams[0].add_features(cut1)
        self.cross_beams[1].add_features(cut2)
        self.features = [cut1, cut2]


    def restore_beams_from_keys(self, model):
        """After de-serialization, restores references to the main and cross beams saved in the model."""
        self.main_beam = model.element_by_guid(self.main_beam_guid)
        self.cross_beams = [model.element_by_guid(guid) for guid in self.cross_beam_guids]
