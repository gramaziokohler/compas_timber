from compas.tolerance import TOL

from compas_timber.connections import JointTopology
from compas_timber.connections import LMiterJoint
from compas_timber.connections import TButtJoint
from compas_timber.connections import XLapJoint
from compas_timber.connections.analyzers import MaxNCompositeAnalyzer
from compas_timber.connections.plate_butt_joint import PlateTButtJoint
from compas_timber.connections.plate_miter_joint import PlateMiterJoint
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
    """

    def __init__(self, rules, model, use_default_topo=False, max_distance=TOL.absolute):
        self.rules = rules if isinstance(rules, list) else [rules] if rules else []
        self.use_default_topo = use_default_topo
        self.max_distance = max_distance
        self.clusters = []
        self.joining_errors = []
        self.model = model

    @property
    def direct_rules(self):
        return [rule for rule in self.rules if rule.__class__.__name__ == "DirectRule"]

    @property
    def category_rules(self):
        return [rule for rule in self.rules if rule.__class__.__name__ == "CategoryRule"]

    @property
    def topology_rules(self):
        topo_rules = {}
        if self.use_default_topo:
            topo_rules = {
                JointTopology.TOPO_L: TopologyRule(JointTopology.TOPO_L, LMiterJoint),
                JointTopology.TOPO_T: TopologyRule(JointTopology.TOPO_T, TButtJoint),
                JointTopology.TOPO_X: TopologyRule(JointTopology.TOPO_X, XLapJoint),
                JointTopology.TOPO_EDGE_EDGE: TopologyRule(JointTopology.TOPO_EDGE_EDGE, PlateMiterJoint),
                JointTopology.TOPO_EDGE_FACE: TopologyRule(JointTopology.TOPO_EDGE_FACE, PlateTButtJoint),
            }
        for rule in self.rules:  # separate category and topo and direct joint rules
            if rule.__class__.__name__ == "TopologyRule":
                topo_rules[rule.topology_type] = TopologyRule(rule.topology_type, rule.joint_type, rule.max_distance, **rule.kwargs)  # overwrites, meaning last rule wins
        return [rule for rule in topo_rules.values() if rule is not None]

    def apply_rules_to_model(self, handled_pairs=None):
        """Adds joints to model based on the given rules and elements.

        Parameters
        ----------
        rules : list(:class:`~compas_timber.connections.JointRule`)
            A list of joint rules to consider.
        elements : list(:class:`~compas_timber.elements.TimberElement`)
            A list of elements to join.
        max_distance : float
            The maximum distance to consider for joining elements.
        handled_pairs : list(set(:class:`~compas_timber.elements.TimberElement`, :class:`~compas_timber.elements.TimberElement`)), optional
            A list of already handled element pairs.

        Returns
        -------
        tuple(list(:class:`~compas_timber.connections.BeamJoiningError`), list(:class:`~compas_timber.connections.Cluster`), )
            A tuple containing a list of joining errors and a list of unjoined Clusters.

        """

        handled_pairs = handled_pairs or []
        max_rule_distance = max([rule.max_distance for rule in self.rules if rule.max_distance] + [self.max_distance])
        clusters = self.get_clusters_from_model(max_distance=max_rule_distance)
        clusters = self.remove_handled_pairs(clusters, handled_pairs)
        self.joining_errors, unjoined_clusters = self.process_clusters(clusters, max_distance=max_rule_distance)
        return self.joining_errors, unjoined_clusters

    def get_clusters_from_model(self, max_distance=None):
        self.model.connect_adjacent_beams(max_distance=max_distance)  # ensure that the model is connected before analyzing
        self.model.connect_adjacent_plates(max_distance=max_distance)  # ensure that the model is connected before analyzing
        analyzer = MaxNCompositeAnalyzer(self.model, n=len(list(self.model.elements())))
        return analyzer.find()

    def remove_handled_pairs(self, clusters, handled_pairs):
        """Removes clusters from the list that have been handled."""
        clusters_temp = [c for c in clusters]
        for cluster in clusters_temp:
            if set(cluster.elements) in handled_pairs:
                clusters.remove(cluster)
        return clusters

    def joints_from_rules_and_clusters(self, rules, clusters, max_distance=None):
        """Processes the DirectRules and creates joints based on the clusters."""
        for rule in rules:
            for cluster in [c for c in clusters]:
                joint, error = rule.try_create_joint(self.model, cluster, max_distance=self.max_distance)
                if joint:
                    clusters.remove(cluster)  # remove the cluster from the list of clusters to avoid processing it again
                if error:
                    self.joining_errors.append(error)

    def process_clusters(self, clusters, max_distance=None):
        """Processes the clusters and creates joints based on the rules."""
        unhandled_clusters = [c for c in clusters]

        self.joints_from_rules_and_clusters(self.direct_rules, unhandled_clusters, max_distance=max_distance)
        self.joints_from_rules_and_clusters(self.category_rules, unhandled_clusters, max_distance=max_distance)
        self.joints_from_rules_and_clusters(self.topology_rules, unhandled_clusters, max_distance=max_distance)

        return self.joining_errors, unhandled_clusters


class JointRule(object):
    def __init__(self, joint_type, max_distance=None, **kwargs):
        """Initializes a JointRule with the given joint type and optional max distance."""
        self.joint_type = joint_type
        self.max_distance = max_distance
        self.kwargs = kwargs

    def _comply_topology(self, cluster, raise_error=False):
        """Checks if the given elements comply with the given topology.

        Parameters
        ----------
        elements : list(:class:`~compas_timber.elements.TimberElement`)
            The elements to check.
        topology : :class:`~compas_timber.connections.JointTopology`
            The topology to check against.

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
        max_distance = self.max_distance or max_distance or None
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
        """Checks if the number of elements in the cluster complies with the joint's requirements."""
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
    """Creates a Joint Rule that directly joins multiple elements.

    Parameters
    ----------
    joint_type : cls(:class:`~compas_timber.connections.Joint`)
        The joint type to be applied to the elements.
    elements : list(:class:`~compas_timber.elements.TimberElement`)
        The elements to be joined.
    max_distance : float, optional
        The maximum distance to consider two elements as intersecting.
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
        """Checks if the elements in this rule match the elements in the cluster."""
        return set(self.elements) == cluster.elements

    def _comply_element_order(self, cluster, raise_error=False):
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
        """Creates a joint from the elements defined in this DirectRule.

        Parameters
        ----------
        model : :class:`~compas_timber.model.TimberModel`
            The model to which the elements and this joint belong.
        model_max_distance : float, optional
            The maximum distance to consider two elements as intersecting. Defaults to TOL.absolute.
            This is only used if the rule does not already have a max_distance set.

        Returns
        -------
        :class:`~compas_timber.connections.Joint`
            The joint created from the elements and the joint type.

        Raises
        ------
        BeamJoiningError
            If the distance between the elements is greater than the max_distance.

        """

        joint = None
        error = None
        if self._matches_cluster(cluster):
            try:
                if not self._comply_element_count(cluster, raise_error=True):
                    return None, None
                if not self._comply_topology(cluster, raise_error=True):
                    return None, None
                if not self._comply_element_order(cluster, raise_error=True):
                    return None, None
                if not self._comply_distance(cluster, raise_error=True, max_distance=max_distance):
                    return None, None
                if not self.joint_type.comply_elements(self.elements, raise_error=True):
                    return None, None
                joint = cluster.promote_to_joint(model, self.joint_type, elements=self.elements, **self.kwargs)
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
        # GH doesn't know
        return repr(self)

    def __repr__(self):
        return "{}({}, {}, {}, {})".format(CategoryRule.__name__, self.joint_type.__name__, self.category_a, self.category_b, self.topos)

    def _comply_category_order(self, cluster, raise_error=False):
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
        """Checks if the categories of the elements in the cluster comply with the rule's categories."""
        return set([e.attributes.get("category", None) for e in cluster.elements]) == {self.category_a, self.category_b}

    def try_create_joint(self, model, cluster, max_distance=None):
        """Creates a joint from the elements defined in this DirectRule.

        Parameters
        ----------
        model : :class:`~compas_timber.model.TimberModel`
            The model to which the elements and this joint belong.
        model_max_distance : float, optional
            The maximum distance to consider two elements as intersecting. Defaults to TOL.absolute.
            This is only used if the rule does not already have a max_distance set.

        Returns
        -------
        :class:`~compas_timber.connections.Joint`
            The joint created from the elements and the joint type.

        Raises
        ------
        BeamJoiningError
            If the distance between the elements is greater than the max_distance.

        """

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
        if not self.joint_type.comply_elements(list(cluster.elements)):
            return None, None
        try:
            joint = cluster.promote_to_joint(model, self.joint_type, **self.kwargs)
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
        """Returns a Joint if the given elements comply with this TopologyRule.
        It checks:
        that the max_distance is not exceeded,
        that the joint supports the topology of the elements.

        Parameters
        ----------
        elements : tuple(:class:`~compas_timber.elements.TimberElement`, :class:`~compas_timber.elements.TimberElement`)
            A tuple containing two elements to check.
        model_max_distance : float, optional
            The maximum distance to consider two elements as intersecting. Defaults to TOL.absolute.
            This is only used if the rule does not already have a max_distance set.

        Returns
        -------
        :class:`~compas_timber.connections.Joint` or None
            The joint created from the elements if the elements comply with the rule,

        """
        joint = None
        error = None
        if not self._comply_element_count(cluster):
            return None, None
        if not self._comply_topology(cluster):
            return None, None
        if not self._comply_distance(cluster, max_distance=max_distance):
            return None, None
        if not self.joint_type.comply_elements(cluster.elements):
            return None, None
        try:
            joint = cluster.promote_to_joint(model, self.joint_type, **self.kwargs)
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
