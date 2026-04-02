from compas.geometry import Plane
from compas.geometry import Point
from compas.geometry import intersection_line_line

from compas_timber.elements import Beam
from compas_timber.errors import BeamJoiningError
from compas_timber.fabrication import DoubleCut
from compas_timber.fabrication import JackRafterCutProxy
from compas_timber.fabrication import Lap
from compas_timber.fabrication import Pocket
from compas_timber.utils import polyhedron_from_box_planes

from .joint import Joint
from .solver import JointTopology
from .utilities import angle_and_dot_product_main_beam_and_cross_beam
from .utilities import are_beams_aligned_with_cross_vector
from .utilities import beam_ref_side_incidence
from .utilities import parse_cross_beams_and_main_beams_from_cluster


class KButtJoint(Joint):
    """Represents a K-Butt type joint which joins the ends of two beams along the length of another beam.

    This joint type is compatible with beams in K topology. The two main beams are trimmed at their
    ends to meet the cross beam. If the three beams are coplanar, the cross beam receives a
    :class:`~compas_timber.fabrication.Pocket` feature; otherwise, the joint uses
    :class:`~compas_timber.connections.t_butt.TButtJoint` features.

    Parameters
    ----------
    cross_beam : :class:`~compas_timber.elements.Beam`, optional
        The cross beam to be joined. This beam is connected along its length.
    *main_beams : :class:`~compas_timber.elements.Beam`
        The two main beams to be joined. These beams connect at their ends to the cross beam.
    mill_depth : float, optional
        The depth of the pocket to be milled in the cross beam, by default 0.
    force_pocket : bool, optional
        If True, forces the use of a `Pocket` BTLx processing instead of a `Lap` in the cross beam. Default is False.
    conical_tool : bool, optional
        If True, the pocket allows overhangs that require a conical tool to be milled. Default is False.
    **kwargs : dict
        Additional keyword arguments passed to the parent :class:`~compas_timber.connections.Joint` class.

    Attributes
    ----------
    cross_beam : :class:`~compas_timber.elements.Beam`
        The cross beam to be joined.
    main_beams : list of :class:`~compas_timber.elements.Beam`
        The two main beams to be joined.
    main_beam_a : :class:`~compas_timber.elements.Beam`
        The first main beam.
    main_beam_b : :class:`~compas_timber.elements.Beam`
        The second main beam.
    mill_depth : float
        The depth of the pocket to be milled in the cross beam.
    force_pocket : bool
        If True, forces the use of a `Pocket` BTLx processing instead of a `Lap` in the cross beam. Default is False.
    conical_tool : bool
        If True, the pocket allows overhangs that require a conical tool to be milled. Default is False.
    cross_beam_guid : str
        The GUID of the cross beam.
    main_beams_guids : list of str
        The GUIDs of the main beams.
    features : list
        List of fabrication features added to the beams.

    """

    SUPPORTED_TOPOLOGY = JointTopology.TOPO_K
    MIN_ELEMENT_COUNT = 3
    MAX_ELEMENT_COUNT = 3

    @property
    def __data__(self):
        data = super().__data__
        data["cross_beam_guid"] = self.cross_beam_guid
        data["main_beams_guids"] = self.main_beams_guids
        data["mill_depth"] = self.mill_depth
        data["force_pocket"] = self.force_pocket
        data["conical_tool"] = self.conical_tool
        return data

    def __init__(self, cross_beam: Beam = None, *main_beams: Beam, mill_depth: float = 0, force_pocket=False, conical_tool=False, **kwargs):
        super().__init__(**kwargs)

        self.cross_beam = cross_beam
        self.main_beams = list(main_beams)
        self.cross_beam_guid = kwargs.get("cross_beam_guid", None) or str(cross_beam.guid)
        self.main_beams_guids = [str(beam.guid) for beam in main_beams]
        self.mill_depth = mill_depth
        self.force_pocket = force_pocket
        self.conical_tool = conical_tool
        self.features = []

        if self.cross_beam and self.main_beams:
            self._sort_main_beams()

    @property
    def beams(self):
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
        return Point(*(intersection_line_line(self.main_beams[0].centerline, self.main_beams[1].centerline)[0]))

    @classmethod
    def promote_cluster(cls, model, cluster, reordered_elements=None, **kwargs):
        """Create an instance of this joint from a cluster of elements.
        Automatically parse the elements in the cluster to identify the cross beam and the two main beams.

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
        :class:`~compas_timber.connections.KButtJoint`
            The created joint instance.
        """
        cross_beams, main_beams = parse_cross_beams_and_main_beams_from_cluster(cluster)
        elements = list(cross_beams) + list(main_beams)
        return cls.create(model, *elements, **kwargs)

    @property
    def cross_beam_ref_side_index(self):
        ref_side_dict = beam_ref_side_incidence(self.main_beams[0], self.cross_beam, ignore_ends=True)
        ref_side_index = min(ref_side_dict, key=ref_side_dict.get)
        return ref_side_index

    @property
    def main_beams_ref_side_indices(self):
        ref_side_indices = []
        for beam_to_cut, beam_cutter in zip(self.main_beams, self.main_beams[1:]):
            ref_side_dict = beam_ref_side_incidence(beam_to_cut, beam_cutter, ignore_ends=True)
            ref_side_index = min(ref_side_dict, key=ref_side_dict.get)
            ref_side_indices.append(ref_side_index)
        return ref_side_indices

    @property
    def cross_cutting_plane(self):
        first_main_beam = self.main_beams[0]
        ref_side_dict = beam_ref_side_incidence(self.cross_beam, first_main_beam, ignore_ends=True)
        ref_side_index = max(ref_side_dict, key=ref_side_dict.get)
        cutting_plane = first_main_beam.ref_sides[ref_side_index]
        return Plane.from_frame(cutting_plane)

    @property
    def butt_plane(self):
        butt_plane = self.cross_beam.ref_sides[self.cross_beam_ref_side_index]
        butt_plane.xaxis = -butt_plane.xaxis
        if self.mill_depth:
            butt_plane.translate(butt_plane.normal * self.mill_depth)
        return Plane.from_frame(butt_plane)

    def main_cutting_planes(self, index):
        """Return the cutting plane for main beam at ``index`` in open-chain ordering.
        The cutting plane is the ref_side of the next main beam that faces the beam to cut. The plane is flipped to face towards the beam to cut.

        Parameters
        ----------
        index : int
            The index of the main beam to cut. Valid range is ``0`` to
            ``len(self.main_beams) - 2``.

        Returns
        -------
        :class:`~compas.geometry.Plane`
            The cutting plane for the main beam at the specified index.

        """
        if index < 0 or index >= len(self.main_beams_ref_side_indices):
            raise IndexError("index must be in range [0, len(main_beams) - 2] for open-chain cutting")

        ref_side_index = self.main_beams_ref_side_indices[index]
        cutting_plane = self.main_beams[index + 1].ref_sides[ref_side_index]

        butt_plane = self.cross_beam.ref_sides[self.cross_beam_ref_side_index]
        # butt_plane = butt_plane.translated(-butt_plane.normal * self.mill_depth)
        # TODO: this for now causes issues. Once you add offset for the pocket, the beams don't butt to eachother in a successive way.
        return [Plane.from_frame(cutting_plane), Plane.from_frame(butt_plane)]

    def add_extensions(self):
        """
        Calculates and adds the necessary extensions to the main beams.
        It accounts for the mill depth in the cross beam.

        This method is automatically called when the joint is created by the call to `Joint.create()`.

        Raises
        ------
        BeamJoiningError
            If the extension could not be calculated.
        """
        assert self.main_beams and self.cross_beam
        try:
            for main_beam in self.main_beams:
                start, end = main_beam.extension_to_plane(self.butt_plane)
                main_beam.add_blank_extension(start, end, self.guid)
        except AttributeError as ae:
            raise BeamJoiningError(beams=[main_beam, self.cross_beam], joint=self, debug_info=str(ae), debug_geometries=[self.butt_plane])

    def add_features(self):
        """
        Adds the required extension and trimming features to the three beams.

        This method is called by `model.process_joinery()`.
        """
        assert self.main_beams and self.cross_beam

        # add features to main beams
        for i, main_beam in enumerate(self.main_beams):
            if i < len(self.main_beams) - 1:
                # For all but the last main beam, add a double cut feature that cuts the beam with both the adjacent main beam's cutting plane and the butt plane.
                feature = DoubleCut.from_planes_and_beam(self.main_cutting_planes(i), main_beam)
            else:
                # For the last main beam, add a jack rafter cut feature that cuts the beam with the butt plane only.
                feature = JackRafterCutProxy.from_plane_and_beam(self.butt_plane, main_beam)
            main_beam.add_feature(feature)
            self.features.append(feature)

        # apply lap or pocket on the cross beam
        if self.mill_depth:
            if self.force_pocket:
                milling_volume = self._get_milling_volume_for_pocket()
                cross_feature = Pocket.from_volume_and_element(milling_volume, self.cross_beam, allow_undercut=self.conical_tool, ref_side_index=self.cross_beam_ref_side_index)
            else:
                lap_width = self._get_lap_width_for_main_beams()

                cross_feature = Lap.from_plane_and_beam(
                    self.cross_cutting_plane,
                    self.cross_beam,
                    lap_width,
                    self.mill_depth,
                    ref_side_index=self.cross_beam_ref_side_index,
                )
            self.cross_beam.add_features(cross_feature)
            self.features.append(cross_feature)

    def restore_beams_from_keys(self, model):
        """After de-serialization, restores references to the main and cross beams saved in the model."""
        self.cross_beam = model.element_by_guid(self.cross_beam_guid)
        self.main_beams = [model.element_by_guid(guid) for guid in self.main_beams_guids]
        self._sort_main_beams()

    def _sort_main_beams(self):
        dots = []
        for main_beam in self.main_beams:
            _, dot = angle_and_dot_product_main_beam_and_cross_beam(main_beam, self.cross_beam, self)
            dots.append(dot)
        # Sort main_beams based on dots (ascending order)
        sorted_indices = sorted(range(len(dots)), key=lambda i: dots[i])
        sorted_beams = [self.main_beams[i] for i in sorted_indices]
        self.main_beams = sorted_beams

    def _get_milling_volume_for_pocket(self):
        top_plane = Plane.from_frame(self.cross_beam.ref_sides[self.cross_beam_ref_side_index])
        bottom_plane = self.butt_plane
        side_a_plane = self.cross_cutting_plane
        side_b_plane = Plane.from_frame(self.main_beams[-1].opp_side(self.main_beams_ref_side_indices[-1]))
        end_a_plane = Plane.from_frame(self.main_beams[-1].front_side(self.main_beams_ref_side_indices[-1]))
        end_b_plane = Plane.from_frame(self.main_beams[-1].back_side(self.main_beams_ref_side_indices[-1]))

        return polyhedron_from_box_planes(bottom_plane, top_plane, side_a_plane, side_b_plane, end_a_plane, end_b_plane)

    def _get_lap_width_for_main_beams(self):
        lap_width = 0.0
        for main_beam in self.main_beams:
            ref_side_dict = beam_ref_side_incidence(self.cross_beam, main_beam, ignore_ends=True)
            main_beam_ref_side_index = min(ref_side_dict, key=ref_side_dict.get)
            lap_width += main_beam.get_dimensions_relative_to_side(main_beam_ref_side_index)[1]
        return lap_width
