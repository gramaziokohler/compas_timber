from compas_timber.connections import Joint
from compas_timber.connections.l_miter import LMiterJoint
from compas_timber.connections.solver import JointTopology
from compas_timber.connections.t_butt import ButtJoint
from compas_timber.connections.utilities import angle_and_dot_product_main_beam_and_cross_beam
from compas_timber.connections.utilities import are_beams_aligned_with_cross_vector
from compas_timber.connections.utilities import beam_ref_side_incidence
from compas_timber.connections.utilities import extend_main_beam_to_cross_beam
from compas_timber.connections.utilities import parse_cross_beam_and_main_beams_from_cluster
from compas_timber.elements.beam import Beam
from compas_timber.errors import BeamJoiningError


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
    MAX_ELEMENT_COUNT = 100

    @property
    def __data__(self):
        data = super().__data__
        data["cross_beam_guid"] = self.cross_beam_guid
        data["main_beams_guids"] = self.main_beams_guids
        data["mill_depth"] = self.mill_depth
        data["conical_tool"] = self.conical_tool
        return data

    def __init__(self, cross_beam: Beam = None, *main_beams: Beam, mill_depth: float = 0, force_pocket: bool = False, conical_tool=False, **kwargs):
        super().__init__(main_beams=list(main_beams), cross_beam=cross_beam, **kwargs)
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
        cross_beams, main_beams = parse_cross_beam_and_main_beams_from_cluster(cluster)
        if len(cross_beams) != 1:
            raise BeamJoiningError(cross_beams, cls, "K-Miter joints require exactly one cross beam.")
        elements = list(cross_beams) + list(main_beams)
        return cls.create(model, *elements, **kwargs)

    def cross_beam_ref_side_index(self, beam):
        ref_side_dict = beam_ref_side_incidence(self.cross_beam, beam, ignore_ends=True)
        ref_side_index = min(ref_side_dict, key=ref_side_dict.get)
        return ref_side_index

    def main_beam_ref_side_index(self, beam):
        ref_side_dict = beam_ref_side_incidence(beam, self.cross_beam, ignore_ends=True)
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
            extend_main_beam_to_cross_beam(beam, self.cross_beam, mill_depth=self.mill_depth)

    def add_features(self):
        """
        Adds the required extension and trimming features to the three beams.

        This method is called by `model.process_joinery()`..
        """
        assert self.main_beams and self.cross_beam

        # self.main_beams is sorted based on their dot product with the cross beam direction
        sorted_angles, sorted_dots = self._sort_main_beams()

        if self.force_pocket and self.mill_depth:
            # Merge the last and first pocket together
            p1 = ButtJoint.get_pocket_on_cross_beam(self.cross_beam, self.main_beams[0], mill_depth=self.mill_depth, conical_tool=self.conical_tool)
            p2 = ButtJoint.get_pocket_on_cross_beam(self.cross_beam, self.main_beams[-1], mill_depth=self.mill_depth, conical_tool=self.conical_tool)
            p1.length = p2.start_x + p2.length - p1.start_x
            p1.tilt_end_side = p2.tilt_end_side
            self.cross_beam.add_feature(p1)
            self.features.append(p1)

        elif self.mill_depth:
            # Merge the two laps in on lap
            l1 = ButtJoint.get_lap_on_cross_beam(self.cross_beam, self.main_beams[0], self.mill_depth)
            l2 = ButtJoint.get_lap_on_cross_beam(self.cross_beam, self.main_beams[-1], self.mill_depth)

            assert l1 and l2
            assert l1.start_x and l2.start_x
            assert l1.length and l2.length

            lap = None
            if l1.orientation == "start" and l2.orientation == "start":
                lap = l1
                lap.length = l2.start_x + l2.length - l1.start_x
            elif l1.orientation == "start" and l2.orientation == "end":
                lap = l1
                lap.length = l2.start_x - l1.start_x
            elif l1.orientation == "end" and l2.orientation == "start":
                lap = l2
                lap.length = l2.start_x + l2.length - (l1.start_x - l1.length)
                lap.start_x = l1.start_x - l1.length
            elif l1.orientation == "end" and l2.orientation == "end":
                lap = l2
                lap.length = l2.start_x - (l1.start_x - l1.length)

            assert lap
            self.cross_beam.add_feature(lap)
            self.features.append(lap)

        for i in range(len(self.main_beams) - 1):
            beam_1 = self.main_beams[i]
            beam_2 = self.main_beams[i + 1]

            # NOTE: LMiter currently going under refactor
            # TODO: FixMe after LMiter refactoring
            L_joint = LMiterJoint(beam_1, beam_2)
            L_joint.add_features()

        # Apply Jack Rafter Cuts to the main beams
        for beam in self.main_beams:
            feature = ButtJoint.get_cut_main_beam(self.cross_beam, beam, mill_depth=self.mill_depth)
            beam.add_feature(feature)
            self.features.append(feature)

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

    def restore_beams_from_keys(self, model):
        """After de-seriallization, restores references to the main and cross beams saved in the model."""
        self.cross_beam = model.element_by_guid(self.cross_beam_guid)
        self.main_beams = [model.element_by_guid(guid) for guid in self.main_beams_guids]
