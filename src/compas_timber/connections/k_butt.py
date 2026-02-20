from compas_timber.connections import Joint
from compas_timber.connections import JointTopology
from compas_timber.connections.butt_joint import ButtJoint
from compas_timber.connections.utilities import are_beams_aligned_with_cross_vector
from compas_timber.connections.utilities import beam_ref_side_incidence
from compas_timber.connections.utilities import extend_main_beam_to_cross_beam
from compas_timber.connections.utilities import parse_cross_beam_and_main_beams_from_cluster
from compas_timber.elements import Beam


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
        data["conical_tool"] = self.conical_tool
        return data

    def __init__(self, cross_beam: Beam = None, *main_beams: Beam, mill_depth: float = 0, force_pocket=False, conical_tool=False, **kwargs):
        super().__init__(main_beams=list(main_beams), cross_beam=cross_beam, **kwargs)

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
        return [self.cross_beam, self.main_beam_a, self.main_beam_b]

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
    def main_beam_a(self):
        return self.main_beams[0]

    @property
    def main_beam_b(self):
        return self.main_beams[1]

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
        cross_beams, main_beams = parse_cross_beam_and_main_beams_from_cluster(cluster)
        elements = list(cross_beams) + list(main_beams)
        return cls.create(model, *elements, **kwargs)

    def cross_beam_ref_side_index(self, beam):
        ref_side_dict = beam_ref_side_incidence(beam, self.cross_beam, ignore_ends=True)
        ref_side_index = min(ref_side_dict, key=ref_side_dict.get)
        return ref_side_index

    def main_beam_ref_side_index(self, beam):
        ref_side_dict = beam_ref_side_incidence(self.cross_beam, beam, ignore_ends=True)
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
        assert self.main_beam_a and self.main_beam_b and self.cross_beam
        extend_main_beam_to_cross_beam(self.main_beam_a, self.cross_beam, self.mill_depth)
        extend_main_beam_to_cross_beam(self.main_beam_b, self.cross_beam, self.mill_depth)

    def add_features(self):
        """
        Adds the required extension and trimming features to the three beams.

        This method is called by `model.process_joinery()`.
        """
        assert self.main_beam_a and self.main_beam_b and self.cross_beam

        if self.mill_depth:
            if self.force_pocket:
                # Merge the two pockets together
                p1 = ButtJoint.get_pocket_on_cross_beam(self.cross_beam, self.main_beam_a, mill_depth=self.mill_depth, conical_tool=self.conical_tool)
                p2 = ButtJoint.get_pocket_on_cross_beam(self.cross_beam, self.main_beam_b, mill_depth=self.mill_depth, conical_tool=self.conical_tool)
                p1.length = p2.start_x + p2.length - p1.start_x
                p1.tilt_end_side = p2.tilt_end_side
                self.cross_beam.add_feature(p1)
                self.features.append(p1)

            else:
                # Merge the two laps in on lap
                l1 = ButtJoint.get_lap_on_cross_beam(self.cross_beam, self.main_beam_a, self.mill_depth)
                l2 = ButtJoint.get_lap_on_cross_beam(self.cross_beam, self.main_beam_b, self.mill_depth)

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

        feature = ButtJoint.get_cut_main_beam(self.cross_beam, self.main_beam_a, self.mill_depth)
        self.main_beam_a.add_feature(feature)
        self.features.append(feature)

        feature = ButtJoint.get_cut_main_beam(self.cross_beam, self.main_beam_b, self.mill_depth)
        self.main_beam_b.add_feature(feature)
        self.features.append(feature)

        feature = ButtJoint.get_cut_main_beam(self.main_beam_a, self.main_beam_b, mill_depth=0)
        self.main_beam_b.add_feature(feature)
        self.features.append(feature)

    def restore_beams_from_keys(self, model):
        """After de-serialization, restores references to the main and cross beams saved in the model."""
        self.cross_beam = model.element_by_guid(self.cross_beam_guid)
        self.main_beams = [model.element_by_guid(guid) for guid in self.main_beams_guids]
