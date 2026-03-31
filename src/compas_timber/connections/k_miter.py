from compas.geometry import Plane
from compas.geometry import Point
from compas.geometry import intersection_line_line
from compas.geometry import intersection_plane_plane

from compas_timber.elements.beam import Beam
from compas_timber.errors import BeamJoiningError
from compas_timber.fabrication import DoubleCut
from compas_timber.fabrication import JackRafterCut
from compas_timber.fabrication import Lap
from compas_timber.fabrication import Pocket
from compas_timber.utils import polyhedron_from_box_planes

from .joint import Joint
from .solver import JointTopology
from .utilities import angle_and_dot_product_main_beam_and_cross_beam
from .utilities import are_beams_aligned_with_cross_vector
from .utilities import beam_ref_side_incidence
from .utilities import extend_beam_to_plane
from .utilities import parse_cross_beams_and_main_beams_from_cluster


class KMiterJoint(Joint):
    """
    Represents a K-Miter type joint which joins the ends of multiple beams (`main_beams`) along the length of another beam (`cross_beam`).

    The main beams are joined with L-Miter joints where they meet consecutively, and each main beam is joined to the cross beam with a T-Butt joint.
    If the beams are coplanar, a :class:`~compas_timber.fabrication.Pocket` feature is created in the `cross_beam`, otherwise
    T-Butt joints are applied directly.

    This joint type is compatible with beams in K topology and supports 3 to 50 beams.

    Parameters
    ----------
    cross_beam : :class:`~compas_timber.elements.Beam`
        The cross beam to be joined. The beam connected along its length.
    *main_beams : :class:`~compas_timber.elements.Beam`
        The main beams to be joined (minimum 2). The beams connected at their ends.
    mill_depth : float, optional
        The depth of material to be milled from the cross beam at the cutting planes. Default is 0.
    force_pocket : bool, optional
            If True, forces the use of a `Pocket` BTLx processing instead of a `Lap` in the cross beam. Default is False.
    conical_tool : bool, optional
            If True, the pocket allows overhangs that require a conical tool to be milled. Default is False.
    **kwargs : dict
        Additional keyword arguments passed to the parent Joint class.

    Attributes
    ----------
    cross_beam : :class:`~compas_timber.elements.Beam`
        The cross beam to be joined. The beam connected along its length.
    main_beams : list of :class:`~compas_timber.elements.Beam`
        The main beams to be joined. The beams connected at their ends.
    mill_depth : float
        The depth of material to be milled from the cross beam at the cutting planes.
    force_pocket : bool
        If True, forces the use of a `Pocket` BTLx processing instead of a `Lap` in the cross beam. Default is False.
    conical_tool : bool
        If True, the pocket allows overhangs that require a conical tool to be milled. Default is False.
    features : list of :class:`~compas_timber.fabrication.Feature`
        The features added to the beams by the joint.

    """

    SUPPORTED_TOPOLOGY = JointTopology.TOPO_K
    MIN_ELEMENT_COUNT = 3
    MAX_ELEMENT_COUNT = 999

    @property
    def __data__(self):
        data = super().__data__
        data["cross_beam_guid"] = self.cross_beam_guid
        data["main_beams_guids"] = self.main_beams_guids
        data["mill_depth"] = self.mill_depth
        data["force_pocket"] = self.force_pocket
        data["conical_tool"] = self.conical_tool
        return data

    def __init__(self, cross_beam: Beam = None, *main_beams: Beam, mill_depth: float = 0, force_pocket: bool = False, conical_tool=False, **kwargs):
        super().__init__(
            elements=(main_beams + (cross_beam,)),
            **kwargs,
        )
        self.cross_beam = cross_beam
        self.main_beams = list(main_beams)
        self.mill_depth = mill_depth
        self.force_pocket = force_pocket
        self.conical_tool = conical_tool
        self.cross_beam_guid = kwargs.get("cross_beam_guid", None) or str(cross_beam.guid)
        self.main_beams_guids = [str(beam.guid) for beam in self.main_beams]
        self.features = []

    @property
    def beams(self) -> list[Beam]:
        return [self.cross_beam] + self.main_beams

    @property
    def elements(self):
        return self.beams

    @property
    def are_beams_coplanar(self):
        if (
            are_beams_aligned_with_cross_vector(self.elements[0], self.elements[1])
            and are_beams_aligned_with_cross_vector(self.elements[1], self.elements[2])
            and are_beams_aligned_with_cross_vector(self.elements[0], self.elements[2])
        ):
            return True
        return False

    @property
    def location(self):
        return Point(*(intersection_line_line(self.main_beams[-1].centerline, self.main_beams[0].centerline)[0]))

    @classmethod
    def promote_cluster(cls, model, cluster, reordered_elements=None, **kwargs):
        """Create an instance of this joint form a cluster of elements.
        Automatically parse the elements in the cluster to indentify the cross beams and the two main beams.

        Parameters
        ----------
        model : :class:`~compas_timber.model.Model`
            The model to which the joint will be added.
        cluster : :class:`~compas_timber.clusters.BeamCluster`
            The cluster of beams to be used to create the joint.
        reordered_elements : list of :class:`~compas_timber.elements.Beam`, optional
            The elements in the order required by the joint. If not provided, the elements in the cluster will be used.
        **kwargs : dict
            Additional keyword arguments passed to the joint constructor.

        Returns
        -------
        :class:`~compas_timber.connections.KMiterJoint`
            The created joint instance.
        """
        cross_beams, main_beams = parse_cross_beams_and_main_beams_from_cluster(cluster)
        if len(cross_beams) != 1:
            raise BeamJoiningError(cross_beams, cls, "K-Miter joints require exactly one cross beam.")
        elements = list(cross_beams) + list(main_beams)
        return cls.create(model, *elements, **kwargs)

    def cross_beam_ref_side_index(self, beam):
        ref_side_dict = beam_ref_side_incidence(beam, self.cross_beam, ignore_ends=True)
        ref_side_index = min(ref_side_dict, key=ref_side_dict.get)
        return ref_side_index

    def main_beam_ref_side_index(self, beam):
        ref_side_dict = beam_ref_side_incidence(beam, beam, ignore_ends=True)
        ref_side_index = min(ref_side_dict, key=ref_side_dict.get)
        return ref_side_index

    def beam_relative_side_to_beam(self, beam, ref_beam):
        ref_side_dict = beam_ref_side_incidence(ref_beam, beam, ignore_ends=True)
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

        for beam in self.main_beams:
            ref_side_dict = beam_ref_side_incidence(beam, self.cross_beam, ignore_ends=True)
            cross_beam_ref_side_index = min(ref_side_dict, key=ref_side_dict.get)
            cutting_plane = self.cross_beam.ref_sides[cross_beam_ref_side_index]
            if self.mill_depth:
                cutting_plane.translate(-cutting_plane.normal * self.mill_depth)
            extend_beam_to_plane(beam, cutting_plane)

    def add_features(self):
        """
        Adds the required extension and trimming features to the three beams.

        This method is called by `model.process_joinery()`..
        """
        assert self.main_beams and self.cross_beam

        # self.main_beams is sorted based on their dot product with the cross beam direction
        sorted_angles, sorted_dots = self._sort_main_beams()

        # processings on cross_beam
        if self.force_pocket and self.mill_depth:
            milling_volume = self._pocket_milling_volume()
            pocket = Pocket.from_volume_and_element(
                milling_volume, self.cross_beam, allow_undercut=self.conical_tool, ref_side_index=self.cross_beam_ref_side_index(self.main_beams[0])
            )
            self.cross_beam.add_feature(pocket)
            self.features.append(pocket)

        elif self.mill_depth:
            milling_volume = self._lap_milling_volume()
            lap = Lap.from_volume_and_beam(milling_volume, self.cross_beam)
            self.cross_beam.add_feature(lap)
            self.features.append(lap)

        # processings on beams
        for i, beam in enumerate(self.main_beams):
            prev_plane, next_plane = self._get_double_cut_planes(beam)

            try:  # Double cut!
                double_cut = DoubleCut.from_planes_and_beam([prev_plane, next_plane], beam)
                beam.add_feature(double_cut)
                self.features.append(double_cut)

            except Exception as e:  # If it fails apply two JackRafterCuts
                print(f"Couldn't apply a DoubleCut: {e}. Applying two JackRafterCuts instead.")
                prev_plane.normal *= -1
                next_plane.normal *= -1
                jrc1 = JackRafterCut.from_plane_and_beam(prev_plane, beam)
                beam.add_feature(jrc1)
                self.features.append(jrc1)

                jrc2 = JackRafterCut.from_plane_and_beam(next_plane, beam)
                beam.add_feature(jrc2)
                self.features.append(jrc2)

            if 0 < i < len(self.main_beams):
                cutting_plane = Plane.from_frame(self.cross_beam.ref_sides[self.cross_beam_ref_side_index(beam)])
                if self.mill_depth:
                    cutting_plane.translate(-cutting_plane.normal * self.mill_depth)
                cutting_plane.normal *= -1
                jrc = JackRafterCut.from_plane_and_beam(cutting_plane, beam)
                beam.add_feature(jrc)
                self.features.append(jrc)

    def _sort_main_beams(self):
        angles = []
        dots = []
        for main_beam in self.main_beams:
            angle, dot = angle_and_dot_product_main_beam_and_cross_beam(main_beam, self.cross_beam, self)
            angles.append(angle)
            dots.append(dot)
        # Sort main_beams based on dots (ascending order)
        sorted_indices = sorted(range(len(dots)), key=lambda i: dots[i])
        sorted_beams = [self.main_beams[i] for i in sorted_indices]
        sorted_angles = [angles[i] for i in sorted_indices]
        sorted_dots = [dots[i] for i in sorted_indices]
        self.main_beams = sorted_beams
        return sorted_angles, sorted_dots

    def _pocket_milling_volume(self):
        first_main_beam = self.main_beams[0]
        last_main_beam = self.main_beams[-1]

        # first beam and last beam have to be on the same side of the cross beam
        ref_side_dict = beam_ref_side_incidence(first_main_beam, self.cross_beam, ignore_ends=True)
        cross_beam_ref_side_index = min(ref_side_dict, key=ref_side_dict.get)
        cross_plane = self.cross_beam.ref_sides[cross_beam_ref_side_index]
        cross_plane_next = Plane.from_frame(self.cross_beam.ref_sides[(cross_beam_ref_side_index + 1) % 4])
        cross_plane_prev = Plane.from_frame(self.cross_beam.ref_sides[(cross_beam_ref_side_index - 1) % 4])

        # first_plane
        ref_side_dict = beam_ref_side_incidence(self.cross_beam, first_main_beam, ignore_ends=True)
        first_main_beam_ref_side_index = (min(ref_side_dict, key=ref_side_dict.get) + 2) % 4
        first_plane = Plane.from_frame(first_main_beam.ref_sides[first_main_beam_ref_side_index])

        # last_plane
        ref_side_dict = beam_ref_side_incidence(self.cross_beam, last_main_beam)
        last_main_beam_ref_side_index = min(ref_side_dict, key=ref_side_dict.get)
        last_plane = Plane.from_frame(last_main_beam.ref_sides[last_main_beam_ref_side_index])

        # adjust mill depth
        if self.mill_depth:
            cutting_plane = Plane.from_frame(cross_plane.translated(-cross_plane.normal * self.mill_depth))
        else:
            cutting_plane = Plane.from_frame(cross_plane)

        # make a plane
        cross_plane = Plane.from_frame(cross_plane)

        milling_volume = polyhedron_from_box_planes(cross_plane, cutting_plane, first_plane, last_plane, cross_plane_next, cross_plane_prev)
        return milling_volume

    def _lap_milling_volume(self):
        first_main_beam = self.main_beams[0]
        last_main_beam = self.main_beams[-1]

        # first beam and last beam have to be on the same side of the cross beam
        ref_side_dict = beam_ref_side_incidence(first_main_beam, self.cross_beam, ignore_ends=True)
        cross_beam_ref_side_index = min(ref_side_dict, key=ref_side_dict.get)
        cross_frame = self.cross_beam.ref_sides[cross_beam_ref_side_index]
        cross_plane = Plane.from_frame(cross_frame)
        cross_plane_prev = Plane.from_frame(self.cross_beam.ref_sides[(cross_beam_ref_side_index - 1) % 4])
        cross_plane_next = Plane.from_frame(self.cross_beam.ref_sides[(cross_beam_ref_side_index + 1) % 4])

        # adjust mill depth
        if self.mill_depth:
            cutting_plane = Plane.from_frame(cross_frame.translated(-cross_frame.normal * self.mill_depth))
        else:
            cutting_plane = Plane.from_frame(cross_frame)

        # first_plane
        ref_side_dict = beam_ref_side_incidence(self.cross_beam, first_main_beam, ignore_ends=True)
        first_main_beam_ref_side_index = (min(ref_side_dict, key=ref_side_dict.get) + 2) % 4
        first_plane = Plane.from_frame(first_main_beam.ref_sides[first_main_beam_ref_side_index])
        exterior_first_plane = first_plane.copy()
        exterior_first_plane.point = Point(*intersection_plane_plane(cross_plane, first_plane)[0])
        exterior_first_plane.normal = self.cross_beam.centerline.direction
        interior_first_plane = first_plane.copy()
        interior_first_plane.point = Point(*intersection_plane_plane(cutting_plane, first_plane)[0])
        interior_first_plane.normal = self.cross_beam.centerline.direction

        # last_plane
        ref_side_dict = beam_ref_side_incidence(self.cross_beam, last_main_beam)
        last_main_beam_ref_side_index = min(ref_side_dict, key=ref_side_dict.get)
        last_plane = Plane.from_frame(last_main_beam.ref_sides[last_main_beam_ref_side_index])
        exterior_last_plane = last_plane.copy()
        exterior_last_plane.point = Point(*intersection_plane_plane(cross_plane, last_plane)[0])
        exterior_last_plane.normal = self.cross_beam.centerline.direction
        interior_last_plane = last_plane.copy()
        interior_last_plane.point = Point(*intersection_plane_plane(cutting_plane, last_plane)[0])
        interior_last_plane.normal = self.cross_beam.centerline.direction

        planes = [exterior_first_plane, interior_first_plane, exterior_last_plane, interior_last_plane]
        planes = sorted(planes, key=lambda plane: plane.point.distance_to_point(self.cross_beam.centerline.start))
        first_plane = planes[0]
        last_plane = planes[-1]

        milling_volume = polyhedron_from_box_planes(cross_plane, cutting_plane, first_plane, last_plane, cross_plane_next, cross_plane_prev)
        return milling_volume

    def _get_double_cut_planes(self, beam: Beam) -> tuple[Plane, Plane]:
        if beam is self.main_beams[0]:
            prev_beam = self.cross_beam
            prev_plane = Plane.from_frame(prev_beam.ref_sides[self.beam_relative_side_to_beam(prev_beam, beam)])
            if self.mill_depth:
                prev_plane.translate(-prev_plane.normal * self.mill_depth)
        else:
            index = self.main_beams.index(beam)
            prev_beam = self.main_beams[index - 1]
            prev_beam_plane = Plane.from_frame(prev_beam.ref_sides[self.beam_relative_side_to_beam(prev_beam, beam)])
            beam_plane = Plane.from_frame(beam.ref_sides[self.beam_relative_side_to_beam(beam, prev_beam)])
            int_point1, int_point_2 = intersection_plane_plane(prev_beam_plane, beam_plane)
            new_normal = prev_beam_plane.normal - beam_plane.normal
            prev_plane = Plane(int_point1, new_normal)

        if beam is self.main_beams[-1]:
            next_beam = self.cross_beam
            next_plane = Plane.from_frame(next_beam.ref_sides[self.beam_relative_side_to_beam(next_beam, beam)])
            next_plane.translate(self.cross_beam.centerline.direction * self.cross_beam.length)
            next_plane.translate(-next_plane.normal * self.mill_depth)
        else:
            index = self.main_beams.index(beam)
            next_beam = self.main_beams[index + 1]
            next_beam_plane = Plane.from_frame(next_beam.ref_sides[self.beam_relative_side_to_beam(next_beam, beam)])
            beam_plane = Plane.from_frame(beam.ref_sides[self.beam_relative_side_to_beam(beam, next_beam)])
            int_point1, int_point_2 = intersection_plane_plane(next_beam_plane, beam_plane)
            new_normal = next_beam_plane.normal - beam_plane.normal
            next_plane = Plane(int_point1, new_normal)

        return prev_plane, next_plane
