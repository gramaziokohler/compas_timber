from compas.geometry import Plane
from compas.geometry import Point
from compas.geometry import intersection_line_line
from compas.geometry import intersection_plane_plane

from compas_timber.elements import Beam
from compas_timber.fabrication import DoubleCut
from compas_timber.fabrication import JackRafterCut
from compas_timber.fabrication import Lap
from compas_timber.fabrication import Pocket
from compas_timber.utils import polyhedron_from_box_planes

from .joint import Joint
from .joint import JointTopology
from .utilities import angle_and_dot_product_main_beam_and_cross_beam
from .utilities import are_beams_aligned_with_cross_vector
from .utilities import beam_ref_side_incidence
from .utilities import extend_beam_to_plane
from .utilities import parse_cross_beams_and_main_beams_from_cluster


class KButtJoint(Joint):
    """Represents a K-Butt type joint which joins the ends of two or more beams along the length of another beam.

    This joint type is compatible with beams in K topology. The two main beams are trimmed at their
    ends to meet the cross beam.

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

    def __init__(self, cross_beam: Beam = None, *main_beams: Beam, mill_depth: float = 0, force_pocket=False, conical_tool=False, **kwargs):
        super().__init__(
            elements=(main_beams + (cross_beam,)),
            **kwargs,
        )

        self.cross_beam = cross_beam
        self.main_beams = list(main_beams)
        self.cross_beam_guid = kwargs.get("cross_beam_guid", None) or str(cross_beam.guid)
        self.main_beams_guids = [str(beam.guid) for beam in main_beams]
        self.mill_depth = mill_depth
        self.force_pocket = force_pocket
        self.conical_tool = conical_tool
        self.features = []

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
        return Point(*(intersection_line_line(self.main_beams[0].centerline, self.main_beams[-1].centerline)[0]))

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
    def main_beams_ref_side_indices(self):
        ref_side_indices = []
        for beam_to_cut, beam_cutter in zip(self.main_beams, self.main_beams[1:]):
            ref_side_dict = beam_ref_side_incidence(beam_to_cut, beam_cutter, ignore_ends=True)
            ref_side_index = min(ref_side_dict, key=ref_side_dict.get)
            ref_side_indices.append(ref_side_index)
        return ref_side_indices

    @property
    def butt_plane(self):
        butt_plane = self.cross_beam.ref_sides[self.cross_beam_ref_side_index]
        butt_plane.xaxis = -butt_plane.xaxis
        if self.mill_depth:
            butt_plane.translate(butt_plane.normal * self.mill_depth)
        return Plane.from_frame(butt_plane)

    @property
    def cross_beam_ref_side_index(self):
        ref_side_dict = beam_ref_side_incidence(self.main_beams[0], self.cross_beam, ignore_ends=True)
        ref_side_index = min(ref_side_dict, key=ref_side_dict.get)
        return ref_side_index

    def main_beam_ref_side_index(self, beam):
        ref_side_dict = beam_ref_side_incidence(self.cross_beam, beam, ignore_ends=True)
        ref_side_index = min(ref_side_dict, key=ref_side_dict.get)
        return ref_side_index

    def beam_relative_side_to_beam(self, beam, ref_beam):
        ref_side_dict = beam_ref_side_incidence(ref_beam, beam, ignore_ends=True)
        ref_side_index = min(ref_side_dict, key=ref_side_dict.get)
        return ref_side_index

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

        This method is called by `model.process_joinery()`.
        """
        assert self.main_beams and self.cross_beam

        # self.main_beams is sorted based on their dot product with the cross beam direction
        sorted_angles, sorted_dots = self._sort_main_beams()

        # processings on cross_beam
        if self.force_pocket and self.mill_depth:
            milling_volume = self._pocket_milling_volume()
            pocket = Pocket.from_volume_and_element(milling_volume, self.cross_beam, allow_undercut=self.conical_tool, ref_side_index=self.cross_beam_ref_side_index)
            self.cross_beam.add_feature(pocket)
            self.features.append(pocket)

        elif self.mill_depth:
            milling_volume = self._lap_milling_volume()
            lap = Lap.from_volume_and_beam(milling_volume, self.cross_beam)
            self.cross_beam.add_feature(lap)
            self.features.append(lap)

        # add features to main_beams
        for i, main_beam in enumerate(self.main_beams):
            if i < len(self.main_beams) - 1:
                # For all but the last main beam, add a double cut feature that cuts the beam with both
                # the adjecent main beam's cutting -lane and the butt_plane
                try:
                    feature = DoubleCut.from_planes_and_beam(self.main_cutting_planes(i), main_beam)
                except Exception as e:
                    jack_plane = self.main_cutting_planes(i)[0]
                    jack_plane.normal *= -1
                    feature = JackRafterCut.from_plane_and_beam(jack_plane, main_beam)
            else:
                # For the last main beam, add a jack rafter cut feature that cuts the beam with the butt plane only.
                feature = JackRafterCut.from_plane_and_beam(self.butt_plane, main_beam)

            main_beam.add_feature(feature)
            self.features.append(feature)

    def main_cutting_planes(self, index):
        """
        Return the cutting plane for main beam at ``index`` in open-chain ordering.

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
            raise IndexError("Index must be in range [0, len(main_beams) -2] for open-chain cutting.")

        ref_side_index = self.main_beams_ref_side_indices[index]
        cutting_plane = self.main_beams[index + 1].ref_sides[ref_side_index]

        butt_plane = self.cross_beam.ref_sides[self.cross_beam_ref_side_index]
        butt_plane = butt_plane.translated(-butt_plane.normal * self.mill_depth)
        # TODO: this for now causes issues. Once you add offset for the pocket, the beams don't butt to eachother in a successive way.
        return [Plane.from_frame(cutting_plane), Plane.from_frame(butt_plane)]

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
