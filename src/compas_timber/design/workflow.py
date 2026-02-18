from compas.tolerance import TOL

from compas_timber.connections import JointTopology
from compas_timber.connections import LMiterJoint
from compas_timber.connections import NBeamKDTreeAnalyzer
from compas_timber.connections import PlateMiterJoint
from compas_timber.connections import PlateTButtJoint
from compas_timber.connections import TButtJoint
from compas_timber.connections import XLapJoint
from compas_timber.errors import BeamJoiningError
from compas_timber.utils import intersection_line_line_param


class CollectionDef(object):
    """TODO: this should be removed since it's essentially a list."""

    def __init__(self, objs):
        objs = [_ for _ in objs if _]

        self.objs = objs
        self.keys_map = {}

        for i, obj in enumerate(objs):
            self.keys_map[i] = obj

    def __str__(self):
        return "Collection with %s items." % len(self.objs)


class ContainerDefinition(object):
    """Holds a pair of slab and its configuration set if available."""

    def __init__(self, slab, config_set=None):
        self.slab = slab
        self.config_set = config_set


class JointRuleSolver(object):
    """A class that holds a set of rules for joining elements.

    It can be used to apply the rules to a model and create joints based on the rules.

    Parameters
    ----------
    rules : list(:class:`~compas_timber.connections.JointRule`)
        A list of rules to apply to the model.
    model : :class:`~compas_timber.model.TimberModel`
        The timber model to which the rules will be applied.
    use_default_topo : bool, optional
        Whether to use the default topology rules. Defaults to False.
    max_distance : float, optional
        The maximum distance to consider two elements as intersecting. Defaults to TOL.absolute.
        This is the general model.max_distance and will be overriden by individual rule max_distances.

    """

    def __init__(self, rules, use_default_topo=False, max_distance=TOL.absolute):
        self.rules = JointRuleSolver._sort_rules(rules, use_default_topo)
        self.use_default_topo = use_default_topo
        self.max_distance = max_distance
        self.clusters = []
        self.joining_errors = []

    @staticmethod
    def _sort_rules(rules, use_default_topo=False):
        """Sorts the rules by their priority."""
        direct_rules = []
        category_rules = []
        if use_default_topo:
            topo_rules = {
                JointTopology.TOPO_L: TopologyRule(JointTopology.TOPO_L, LMiterJoint),
                JointTopology.TOPO_T: TopologyRule(JointTopology.TOPO_T, TButtJoint),
                JointTopology.TOPO_X: TopologyRule(JointTopology.TOPO_X, XLapJoint),
                JointTopology.TOPO_EDGE_EDGE: TopologyRule(JointTopology.TOPO_EDGE_EDGE, PlateMiterJoint),
                JointTopology.TOPO_EDGE_FACE: TopologyRule(JointTopology.TOPO_EDGE_FACE, PlateTButtJoint),
            }
        else:
            topo_rules = {}
        for rule in rules:
            if isinstance(rule, DirectRule):
                direct_rules.append(rule)
            if isinstance(rule, CategoryRule):
                category_rules.append(rule)
            if isinstance(rule, TopologyRule):
                topo_rules[rule.topology_type] = TopologyRule(rule.topology_type, rule.joint_type, rule.max_distance, **rule.kwargs)
        return direct_rules + category_rules + [rule for rule in topo_rules.values() if rule is not None]

    def apply_rules_to_model(self, model, handled_pairs=None):
        """Adds joints to model based on the given rules and elements.

        Parameters
        ----------
        model : :class:`~compas_timber.model.TimberModel`
            The timber model to which the rules will be applied.
        handled_pairs : list(set(:class:`~compas_timber.elements.TimberElement`, :class:`~compas_timber.elements.TimberElement`)), optional
            A list of already handled element pairs.

        Returns
        -------
        tuple(list(:class:`~compas_timber.connections.BeamJoiningError`), list(:class:`~compas_timber.connections.Cluster`), )
            A tuple containing a list of joining errors and a list of unjoined Clusters.

        """
        handled_pairs = handled_pairs or []
        max_rule_distance = max([rule.max_distance for rule in self.rules if rule.max_distance] + [self.max_distance])
        clusters = get_clusters_from_model(model, max_distance=max_rule_distance)
        clusters = self._remove_handled_pairs(clusters, handled_pairs)
        unjoined_clusters = self._joints_from_rules_and_clusters(model, self.rules, clusters, max_distance=self.max_distance)
        return self.joining_errors, unjoined_clusters

    def _remove_handled_pairs(self, clusters, handled_pairs):
        """Removes clusters from the list that have been handled."""
        remaining_clusters = []
        for cluster in clusters:
            if set(cluster.elements) not in handled_pairs:
                remaining_clusters.append(cluster)
        return remaining_clusters

    def _joints_from_rules_and_clusters(self, model, rules, clusters, max_distance=None):
        """Processes the JointRules and creates joints based on the clusters."""
        remaining_clusters = []
        for cluster in clusters:
            promoted = False
            for rule in rules:
                joint, error = rule.try_create_joint(model, cluster, max_distance=max_distance)
                if joint:
                    promoted = True
                    break
                if error:
                    self.joining_errors.append(error)  # should only happen with direct rules
                    break
            if not promoted:
                remaining_clusters.append(cluster)
        return remaining_clusters


class JointRule(object):
    """Represents a rule for creating joints between timber elements.
    Parameters
    ----------
    joint_type : :class:`~compas_timber.joints.JointType`
        The type of joint to create.
    max_distance : float, optional
        The maximum distance to consider when creating joints. This will override the global max_distance.
    **kwargs : dict, optional
        Additional keyword arguments to pass to the joint creation method.
    """

    def __init__(self, joint_type, max_distance=None, **kwargs):
        self.joint_type = joint_type
        self.max_distance = max_distance
        self.kwargs = kwargs

    def _comply_topology(self, cluster, raise_error=False):
        """Checks if the given elements comply with the given topology.

        Parameters
        ----------
        cluster : :class:`~compas_timber.connections.Cluster`
            The cluster of elements to check.
        raise_error : bool, optional
            Whether to raise an error if the elements do not comply. If False, method will return False without raising an error.

        Returns
        -------
        bool
            True if the elements comply with the topology, False otherwise.

        """
        supported_topology = self.joint_type.SUPPORTED_TOPOLOGY if isinstance(self.joint_type.SUPPORTED_TOPOLOGY, list) else [self.joint_type.SUPPORTED_TOPOLOGY]
        if cluster.topology not in supported_topology:
            if raise_error:
                raise BeamJoiningError(
                    beams=cluster.elements,
                    joint=self.joint_type,
                    debug_info="The cluster topology must be one of: {} for {}.".format([JointTopology.get_name(t) for t in supported_topology], self.joint_type.__name__),
                    debug_geometries=[e.shape for e in cluster.elements],
                )
            return False
        return True

    def _comply_distance(self, cluster, max_distance=None, raise_error=False):
        """Checks if the distance between the elements in the cluster complies with the maximum distance.

        Parameters
        ----------
        cluster : :class:`~compas_timber.connections.Cluster`
            The cluster of elements to check.
        max_distance : float, optional
            The maximum distance to consider two elements as intersecting. This is the model max_distance and will be overridden if the rule has a max_distance.
        raise_error : bool, optional
            Whether to raise an error if the elements do not comply. If False, method will return False without raising an error.

        Returns
        -------
        bool
            True if the distance complies, False otherwise.
        """
        if not max_distance:
            return True

        distance = max([j.distance for j in cluster.joints])
        if distance > max_distance:
            if raise_error:
                raise BeamJoiningError(
                    beams=cluster.elements,
                    joint=self.joint_type,
                    debug_info="The distance between the elements is greater than the maximum allowed distance of {}.".format(max_distance),
                    debug_geometries=[e.shape for e in cluster.elements],
                )
            return False
        return True

    def _comply_element_count(self, cluster, raise_error=False):
        """Checks if the number of elements in the cluster complies with the joint's requirements.
        Parameters
        ----------
        cluster : :class:`~compas_timber.connections.Cluster`
            The cluster of elements to check.
        raise_error : bool, optional
            Whether to raise an error if the elements do not comply. If False, method will return False without raising an error.

        Returns
        -------
        bool
            True if the number of elements complies, False otherwise.
        """
        if not self.joint_type.element_count_complies(cluster.elements):
            if raise_error:
                raise BeamJoiningError(
                    beams=cluster.elements,
                    joint=self.joint_type,
                    debug_info="The number of elements in the cluster does not comply with the requirements for this joint.",
                    debug_geometries=[e.shape for e in cluster.elements],
                )
            return False
        return True


class DirectRule(JointRule):
    """Creates a Joint Rule that directly joins multiple elements. This essentially replaces the JointDefinition.

    Parameters
    ----------
    joint_type : cls(:class:`~compas_timber.connections.Joint`)
        The joint type to be applied to the elements.
    elements : list(:class:`~compas_timber.elements.TimberElement`)
        The elements to be joined.
    max_distance : float, optional
        The maximum distance to consider two elements as intersecting. This will override the global max_distance.
    kwargs : dict
        The keyword arguments to be passed to the joint.
    """

    def __init__(self, joint_type, elements, max_distance=None, **kwargs):
        super(DirectRule, self).__init__(joint_type, max_distance=max_distance, **kwargs)
        self.elements = elements

    def ToString(self):
        # GH doesn't know
        return repr(self)

    def __repr__(self):
        return "{}({}, {})".format(DirectRule, self.elements, self.joint_type)

    def _matches_cluster(self, cluster):
        """Checks if the elements in this rule match the elements in the cluster.
        Parameters
        ----------
        cluster : :class:`~compas_timber.connections.Cluster`
            The cluster to check against.

        Returns
        -------
        bool
            True if the elements match, False otherwise.
        """
        return set(self.elements) == cluster.elements

    def _comply_element_order(self, cluster, raise_error=False):
        """Checks if the element order in this rule complies with the element order in the cluster.
        This check is only performed for JointTopology.TOPO_T or JointTopology.TOPO_EDGE_FACE, where the topology requires a specific element order.
        Parameters
        ----------
        cluster : :class:`~compas_timber.connections.Cluster`
            The cluster to check against.
        raise_error : bool, optional
            Whether to raise an error if the element order does not comply. If False, method will return False without raising an error.

        Returns
        -------
        bool
            True if the element order complies, False otherwise.
        """
        if cluster.topology == JointTopology.TOPO_T or cluster.topology == JointTopology.TOPO_EDGE_FACE:
            if self.elements[0] != cluster.joints[0].elements[0]:
                if not raise_error:
                    return False
                raise BeamJoiningError(
                    beams=self.elements,
                    joint=self.joint_type,
                    debug_info="Beam roles must be reversed for topology of {}, try swapping elements in joint".format(self.joint_type.__name__),
                    debug_geometries=[e.shape for e in self.elements],
                )
        return True

    def try_create_joint(self, model, cluster, max_distance=None):
        """Returns a Joint if the given cluster's elements comply with this DirectRule.

        Parameters
        ----------
        model : :class:`~compas_timber.model.TimberModel`
            The model to which the elements and this joint belong.
        cluster : :class:`~compas_timber.connections.Cluster`
            The cluster of elements attemped to be joined.
        max_distance : float, optional
            The maximum distance to consider two elements as intersecting. Defaults to TOL.absolute.
            This is the general model.max_distance and will be overriden if the rule has a max_distance.

        Returns
        -------
        :class:`~compas_timber.connections.Joint`
            The joint created from the elements and the joint type.
        :class:`~compas_timber.errors.BeamJoiningError` or None
            Error that occurred during joint creation.

        """
        max_distance = self.max_distance or max_distance or TOL.absolute
        joint = None
        error = None
        if self._matches_cluster(cluster):
            try:
                self._comply_element_count(cluster, raise_error=True)
                self._comply_topology(cluster, raise_error=True)
                self._comply_element_order(cluster, raise_error=True)
                self._comply_distance(cluster, raise_error=True, max_distance=max_distance)
                self.joint_type.check_elements_compatibility(self.elements, raise_error=True)
                joint = self.joint_type.promote_cluster(model, cluster, reordered_elements=self.elements, **self.kwargs)
            except BeamJoiningError as bje:
                error = bje
        return joint, error


class CategoryRule(JointRule):
    """Based on the category attribute attached to the elements, this rule assigns

    Parameters
    ----------
    joint_type : cls(:class:`~compas_timber.connections.Joint`)
        The joint type to be applied to the elements.
    category_a : str
        The category of the first element.
    category_b : str
        The category of the second element.
    topos : list(:class:`~compas_timber.connections.JointTopology`), optional
        The topologies that are supported by this rule.
        TODO: reconsider how to implement this. was meant to filter/override joint application based on topology.
    max_distance : float, optional
        The maximum distance to consider two elements as intersecting.
    kwargs : dict
        The keyword arguments to be passed to the joint.
    """

    def __init__(self, joint_type, category_a, category_b, topos=None, max_distance=None, **kwargs):
        super(CategoryRule, self).__init__(joint_type, max_distance=max_distance, **kwargs)
        self.category_a = category_a
        self.category_b = category_b
        self.topos = topos or []

    def ToString(self):
        return repr(self)

    def __repr__(self):
        return "{}({}, {}, {}, {})".format(CategoryRule.__name__, self.joint_type.__name__, self.category_a, self.category_b, self.topos)

    def _comply_category_order(self, cluster, raise_error=False):
        """Checks if the order of the elements in the cluster complies with the rule's categories.
                Parameters
        ----------
        cluster : :class:`~compas_timber.connections.Cluster`
            The cluster of elements to check.
        raise_error : bool, optional
            Whether to raise an error if the elements do not comply. If False, method will return False without raising an error.

        Returns
        -------
        bool
            True if the order complies, False otherwise.
        """
        self._warn_if_cluster_elemenst_missing_category(cluster)
        if cluster.topology == JointTopology.TOPO_T or cluster.topology == JointTopology.TOPO_EDGE_FACE:
            if cluster.joints[0].elements[0].attributes.get("category", None) != self.category_a:
                if not raise_error:
                    return False
                raise BeamJoiningError(
                    beams=self.elements,
                    joint=self.joint_type,
                    debug_info="Category roles must be reversed for topology of {}, try swapping categories in joint".format(self.joint_type.__name__),
                    debug_geometries=[e.shape for e in self.elements],
                )
        return True

    def _comply_categories(self, cluster):
        """Checks if the categories of the elements in the cluster are the same as the rule's categories.
        Parameters
        ----------
        cluster : :class:`~compas_timber.connections.Cluster`
            The cluster of elements to check.

        Returns
        -------
        bool
            True if the categories comply, False otherwise.
        """
        self._warn_if_cluster_elemenst_missing_category(cluster)
        return set([e.attributes.get("category") for e in cluster.elements]) == {self.category_a, self.category_b}

    def _warn_if_cluster_elemenst_missing_category(self, cluster):
        cluster_categories = [e.attributes.get("category") for e in cluster.elements]
        if not all(cluster_categories):
            # printing instead of `warn()`ing because warning behavior in Grasshopper is weird
            print("CategoryRule found elements without category attribute! Have you set element.attributes['category'] on the relevant elements?")

    def _get_ordered_elements(self, cluster):
        """Returns the elements in the order of the rule's categories.
        This assumes self._comply_categories and self._comply_category_order have been checked and passed.

        Parameters
        ----------
        cluster : :class:`~compas_timber.connections.Cluster`
            The cluster of elements to order.

        Returns
        -------
        list(:class:`~compas_timber.elements.TimberElement`)
            The ordered list of elements.
        """
        elements = list(cluster.joints[0].elements)
        if cluster.joints[0].elements[0].attributes.get("category", None) != self.category_a:
            elements.reverse()
        return elements

    def try_create_joint(self, model, cluster, max_distance=None):
        """Returns a Joint if the given cluster's elements comply with this CategoryRule.

        Parameters
        ----------
        model : :class:`~compas_timber.model.TimberModel`
            The model to which the elements and this joint belong.
        cluster : :class:`~compas_timber.connections.Cluster`
            The cluster of elements to create the joint from.
        max_distance : float, optional
            The maximum distance to consider two elements as intersecting. Defaults to TOL.absolute.
            This is the general model.max_distance and will be overriden if the rule has a max_distance.

        Returns
        -------
        :class:`~compas_timber.connections.Joint` or None
            The joint created from the elements if the elements comply with the rule,
        :class:`~compas_timber.errors.BeamJoiningError` or None
            The error raised if the elements do not comply with the rule.

        """
        max_distance = self.max_distance or max_distance or TOL.absolute

        joint = None
        error = None
        if not self._comply_categories(cluster):
            return None, None
        if not self._comply_element_count(cluster):
            return None, None
        if not self._comply_topology(cluster):
            return None, None
        if not self._comply_category_order(cluster):
            return None, None
        if not self._comply_distance(cluster, max_distance=max_distance):
            return None, None
        elements = self._get_ordered_elements(cluster)
        if not self.joint_type.check_elements_compatibility(elements):
            return None, None
        try:
            joint = self.joint_type.promote_cluster(model, cluster, reordered_elements=elements, **self.kwargs)
        except BeamJoiningError as bje:
            error = bje
        return joint, error


class TopologyRule(JointRule):
    """for a given connection topology type (L,T,X,I,K...), this rule assigns a joint type.

    parameters
    ----------
    topology_type : constant(compas_timber.connections.JointTopology)
        The topology type to which the rule is applied.
    joint_type : cls(:class:`compas_timber.connections.Joint`)
        The joint type to be applied to this topology.
    max_distance : float, optional
        The maximum distance to consider two elements as intersecting.
        This will override a global max_distance if set.
    kwargs : dict
        The keyword arguments to be passed to the joint.
    """

    def __init__(self, topology_type, joint_type, max_distance=None, **kwargs):
        super(TopologyRule, self).__init__(joint_type, max_distance=max_distance, **kwargs)
        self.topology_type = topology_type

    def ToString(self):
        # GH doesn't know
        return repr(self)

    def __repr__(self):
        return "{}({}, {})".format(
            TopologyRule,
            self.topology_type,
            self.joint_type,
        )

    def try_create_joint(self, model, cluster, max_distance=None):
        """Returns a Joint if the given cluster's elements comply with this TopologyRule.
        It checks:
        that the max_distance is not exceeded,
        that the joint supports the topology of the elements.

        Parameters
        ----------
        model : :class:`~compas_timber.models.TimberModel`
            The timber model containing the elements.
        cluster : :class:`~compas_timber.connections.Cluster`
            The cluster of elements to create the joint from.
        max_distance : float, optional
            The maximum distance to consider two elements as intersecting. Defaults to TOL.absolute.
            This is the general model.max_distance and will be overriden if the rule has a max_distance.

        Returns
        -------
        :class:`~compas_timber.connections.Joint` or None
            The joint created from the elements if the elements comply with the rule,
        :class:`~compas_timber.errors.BeamJoiningError` or None
            The error raised if the elements do not comply with the rule.
        """
        max_distance = self.max_distance or max_distance or TOL.absolute

        joint = None
        error = None
        if not self._comply_element_count(cluster):
            return None, None
        if not self._comply_topology(cluster):
            return None, None
        if not self._comply_distance(cluster, max_distance=max_distance):
            return None, None
        if not self.joint_type.check_elements_compatibility(list(cluster.elements)):
            return None, None
        try:
            joint = self.joint_type.promote_cluster(model, cluster, **self.kwargs)
        except BeamJoiningError as bje:
            error = bje
        return joint, error


class Attribute:
    def __init__(self, attr_name, attr_value):
        self.name = attr_name
        self.value = attr_value

    def __str__(self):
        return "Attribute %s: %s" % (self.name, self.value)


def guess_joint_topology_2beams(beamA, beamB, tol=1e-6, max_distance=1e-6):
    # TODO: replace default max_distance ~ zero with global project precision

    [pa, ta], [pb, tb] = intersection_line_line_param(beamA.centerline, beamB.centerline, max_distance, True, tol)

    if ta is None or tb is None:
        # lines do not intersect within max distance or they are parallel
        return [None, None]

    def is_near_end(t, tol=tol):
        if abs(t) < tol:
            return True  # almost zero
        if abs(1.0 - t) < tol:
            return True  # almost 1
        return False

    xa = is_near_end(ta)
    xb = is_near_end(tb)

    if all([xa, xb]):
        # L-joint (both meeting at ends) TODO: this could also be an I-joint (splice) -> will need to check for angle between beams
        return ["L", (beamA, beamB)]
    elif any([xa, xb]):
        # T-joint (one meeting with the end along the other)
        if xa:
            # A:main, B:cross
            return ["T", (beamA, beamB)]
        if xb:
            # B:main, A:cross
            return ["T", (beamB, beamA)]
    else:
        # X-joint (both meeting somewhere along the line)
        return ["X", (beamA, beamB)]


def set_default_joints(model, x_default="x-lap", t_default="t-butt", l_default="l-miter"):
    beams = list(model.beams)
    n = len(beams)

    connectivity = {"L": [], "T": [], "X": []}

    # find what kind of joint topology it looks like based on centerlines
    for i in range(n - 1):
        for j in range(i + 1, n):
            jointtype, beams_pair = guess_joint_topology_2beams(beams[i], beams[j])
            if jointtype:
                connectivity[jointtype].append(beams_pair)

    # Apply default joint types depending on the auto-found connectivity type:

    for beamA, beamB in connectivity["T"]:
        TButtJoint(beamA, beamB, model)

    for beamA, beamB in connectivity["L"]:
        LMiterJoint(beamA, beamB, model)

    for beamA, beamB in connectivity["X"]:
        pass


def get_clusters_from_model(model, max_distance=None):
    """Analyzes the model to find clusters of beams and plates. This will create JointCandidates and PlateJointCandidates in the model.
    Parameters
    ----------
    model : :class:`~compas_timber.model.TimberModel`
        The TimberModel to analyze.
    max_distance : float | None
        The maximum distance to consider for clustering. If None, a default distance is used.

    Returns
    -------
    list[:class:`~compas_timber.connections.Cluster`]
        A list of clusters found in the model.
    """
    model.connect_adjacent_beams(max_distance=max_distance)  # ensure that the model is connected before analyzing
    model.connect_adjacent_plates(max_distance=max_distance)  # ensure that the model is connected before analyzing
    analyzer = NBeamKDTreeAnalyzer(model, max_distance=max_distance)
    clusters = analyzer.find()
    return clusters


class DebugInfomation(object):
    """Container for debugging information allowing visual inspection of joint and features related errors.

    Attributes
    ----------
    feature_errors : list(:class:`~compas_timber.consumers.FeatureApplicationError`)
        List of errors that occured during the application of features.
    joint_errors : list(:class:`~compas_timber.connections.BeamJoiningError`)
        List of errors that occured during the joining of beams.

    See Also
    --------
    :class:`~compas_timber.consumers.FeatureApplicationError`
    :class:`~compas_timber.connections.BeamJoiningError`

    """

    def __init__(self):
        self.fastener_errors = []
        self.feature_errors = []
        self.joint_errors = []

    def __repr__(self):
        return "{}({} feature errors, {} joining errors)".format(DebugInfomation.__name__, len(self.feature_errors), len(self.joint_errors))

    def ToString(self):
        return repr(self)

    @property
    def has_errors(self):
        return self.feature_errors or self.joint_errors

    def add_fastener_error(self, error):
        if isinstance(error, list):
            self.fastener_errors.extend(error)
        else:
            self.fastener_errors.append(error)

    def add_feature_error(self, error):
        if isinstance(error, list):
            self.feature_errors.extend(error)
        else:
            self.feature_errors.append(error)

    def add_joint_error(self, error):
        if isinstance(error, list):
            self.joint_errors.extend(error)
        else:
            self.joint_errors.append(error)
