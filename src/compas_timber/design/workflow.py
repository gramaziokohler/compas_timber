from itertools import combinations
from compas.geometry import distance_line_line

from compas_timber.connections import ConnectionSolver
from compas_timber.connections import JointTopology
from compas_timber.connections import LMiterJoint
from compas_timber.connections import TButtJoint
from compas_timber.connections import XHalfLapJoint
from compas_timber.elements import beam
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


class JointRule(object):
    def comply(self, elements):
        """Returns True if the provided elements comply with the rule defined by this instance. False otherwise.

        Parameters
        ----------
        elements : list(:class:`~compas_timber.elements.TimberElement`)

        Returns
        -------
        bool

        """
        raise NotImplementedError

    @staticmethod
    def get_direct_rules(rules):
        return [rule for rule in rules if rule.__class__.__name__ == "DirectRule"]

    @staticmethod
    def get_category_rules(rules):
        return [rule for rule in rules if rule.__class__.__name__ == "CategoryRule"]

    @staticmethod
    def get_topology_rules(rules, use_defaults=False):
        topo_rules = {}
        if use_defaults:
            topo_rules = {
                JointTopology.TOPO_L: TopologyRule(JointTopology.TOPO_L, LMiterJoint),
                JointTopology.TOPO_T: TopologyRule(JointTopology.TOPO_T, TButtJoint),
                JointTopology.TOPO_X: TopologyRule(JointTopology.TOPO_X, XHalfLapJoint),
            }
        for rule in rules:  # separate category and topo and direct joint rules
            if rule.__class__.__name__ == "TopologyRule":
                topo_rules[rule.topology_type] = TopologyRule(rule.topology_type, rule.joint_type, rule.max_distance, **rule.kwargs)  # overwrites, meaning last rule wins
        return [rule for rule in topo_rules.values() if rule is not None]

    @staticmethod
    def joints_from_beams_and_rules(elements, rules, max_distance=1e-6):
        """processes joint rules into joint definitions.

        Parameters
        ----------
        elements : list(:class:`~compas_timber.elements.TimberElement`)
            A list of elements to be joined.
        rules : list(:class:`~compas_timber.design.JointRule`)
            A list of joint rules to be applied.
        max_distance : float, optional
            The maximum distance to consider two elements as intersecting.

        Returns
        -------
        list(:class:`~compas_timber.design.JointDefinition`)
            A list of joint definitions that can be applied to the given elements.

        """
        print("elements", elements)
        elements = elements if isinstance(elements, list) else list(elements)
        print("elements list", elements)
        direct_rules = JointRule.get_direct_rules(rules)
        solver = ConnectionSolver()
        print("max_distance in", max_distance)
        max_distances = [rule.max_distance for rule in rules if rule.max_distance]
        max_rule_distance = max(max_distances) if max_distances else max_distance
        print("max_rule_distance", max_rule_distance)
        element_pairs = solver.find_intersecting_pairs(elements, rtree=True, max_distance=max_rule_distance)
        joint_defs = []
        unmatched_pairs = []
        print("element_pairs", element_pairs)
        for rule in direct_rules:
            print("direct rule", rule)
            if rule.comply(element_pairs, model_max_distance=max_distance):
                joint_defs.append(JointDefinition(rule.joint_type, rule.elements, **rule.kwargs))
        while element_pairs:
            pair = element_pairs.pop()
            print(pair)
            match_found = False
            for rule in direct_rules:  # see if pair is used in a direct rule
                print("direct rule", rule)
                if rule.contains(pair):
                    match_found = True
                    break

            if not match_found:
                for rule in JointRule.get_category_rules(rules):  # see if pair is used in a category rule
                    if rule.comply(pair, model_max_distance=max_distance):
                        match_found = True
                        joint_defs.append(JointDefinition(rule.joint_type, rule.reorder(pair), **rule.kwargs))
                        break

            if not match_found:
                for rule in JointRule.get_topology_rules(rules):  # see if pair is used in a topology rule
                    print("topo rule", rule, rule.max_distance)
                    print([beam.key for beam in pair])
                    comply, ordered_pair = rule.comply(pair, model_max_distance=max_distance)
                    if comply:
                        match_found = True
                        joint_defs.append(JointDefinition(rule.joint_type, ordered_pair, **rule.kwargs))
                        break
            if not match_found:
                unmatched_pairs.append(pair)
            print("jdefs", joint_defs)
        return joint_defs, unmatched_pairs


class DirectRule(JointRule):
    """Creates a Joint Rule that directly joins multiple elements."""

    def __init__(self, joint_type, elements, max_distance = None, **kwargs):
        self.elements = elements
        self.joint_type = joint_type
        self.max_distance = max_distance
        self.kwargs = kwargs

    def ToString(self):
        # GH doesn't know
        return repr(self)

    def __repr__(self):
        return "{}({}, {})".format(DirectRule, self.elements, self.joint_type)

    def contains(self, elements):
        """Returns True if the given elements are defined within this DirectRule."""
        try:
            return set(elements).issubset(set(self.elements))
        except TypeError:
            raise UserWarning("unable to comply direct joint element sets")

    def comply(self, elements, model_max_distance=1e-6):

        if self.max_distance:
            max_distance = self.max_distance
        else:
            max_distance = model_max_distance
        print("element count", len(elements))
        print("pairs", list(combinations(list(elements), 2)))
        try:
            for pair in combinations(list(elements), 2):
                print("pair", pair)
                if distance_line_line(pair[0].centerline, pair[1].centerline) > max_distance:
                    return False
        except TypeError:
            raise UserWarning("unable to comply direct joint element sets")


class CategoryRule(JointRule):
    """Based on the category attribute attached to the elements, this rule assigns"""

    def __init__(self, joint_type, category_a, category_b, topos=None, max_distance = None, **kwargs):
        self.joint_type = joint_type
        self.category_a = category_a
        self.category_b = category_b
        self.topos = topos or []
        self.max_distance = max_distance
        self.kwargs = kwargs

    def ToString(self):
        # GH doesn't know
        return repr(self)

    def __repr__(self):
        return "{}({}, {}, {}, {})".format(CategoryRule.__name__, self.joint_type.__name__, self.category_a, self.category_b, self.topos)

    def comply(self, elements, model_max_distance=1e-6):
        if self.max_distance:
            max_distance = self.max_distance
        else:
            max_distance = model_max_distance
        try:
            element_cats = set([e.attributes["category"] for e in elements])
            comply = False
            elements = list(elements)
            if element_cats == set([self.category_a, self.category_b]):
                solver = ConnectionSolver()
                found_topology = solver.find_topology(elements[0], elements[1], max_distance=max_distance)[0]
                supported_topo = self.joint_type.SUPPORTED_TOPOLOGY
                if not isinstance(supported_topo, list):
                    supported_topo = [supported_topo]
                if found_topology in supported_topo:
                    comply = True
            return comply
        except KeyError:
            return False

    def reorder(self, elements):
        """Returns the given elements in a sorted order.

        The elements are sorted according to their category attribute, first the elements with `catergory_a` and second the
        one with `category_b`.
        This allows using the category to determine the role of the elements.

        Parameters
        ----------
        elements : tuple(:class:`~compas_timber.elements.TimberElement`, :class:`~compas_timber.elements.TimberElement`)
            A tuple containing two elements to sort.

        Returns
        -------
        tuple(:class:`~compas_timber.elements.TimberElement`, :class:`~compas_timber.elements.TimberElement`)

        """
        element_a, element_b = elements
        if element_a.attributes["category"] == self.category_a:
            return element_a, element_b
        else:
            return element_b, element_a


class TopologyRule(JointRule):
    """for a given connection topology type (L,T,X,I,K...), this rule assigns a joint type.

    parameters
    ----------
    topology_type : constant(compas_timber.connections.JointTopology)
        The topology type to which the rule is applied.
    joint_type : cls(:class:`compas_timber.connections.Joint`)
        The joint type to be applied to this topology.
    kwargs : dict
        The keyword arguments to be passed to the joint.
    """

    def __init__(self, topology_type, joint_type, max_distance = None, **kwargs):
        self.topology_type = topology_type
        self.joint_type = joint_type
        self.max_distance = max_distance
        print("topo __init__ max_distance", self.max_distance)
        print(kwargs)
        self.kwargs = kwargs

    def ToString(self):
        # GH doesn't know
        return repr(self)

    def __repr__(self):
        return "{}({}, {})".format(TopologyRule, self.topology_type, self.joint_type, self.max_distance)

    def comply(self, elements, model_max_distance=1e-6):
        if self.max_distance:
            max_distance = self.max_distance
        else:
            max_distance = model_max_distance
        try:
            elements = list(elements)
            solver = ConnectionSolver()
            topo_results = solver.find_topology(elements[0], elements[1], max_distance=max_distance)
            return (
                self.topology_type == topo_results[0],
                [topo_results[1], topo_results[2]],
            )  # comply, if topologies match, reverse if the element order should be switched
        except KeyError:
            return False


class JointDefinition(object):
    """Container for a joint type and the elements that shall be joined.

    This allows delaying the actual joining of the elements to a downstream component.

    """

    def __init__(self, joint_type, elements, **kwargs):
        # if not issubclass(joint_type, Joint):
        #     raise UserWarning("{} is not a valid Joint type!".format(joint_type.__name__))

        if len(elements) < 2:
            raise UserWarning("Joint requires at least two Elements, got {}.".format(len(elements)))

        self.joint_type = joint_type
        self.elements = elements
        self.kwargs = kwargs

    def __repr__(self):
        return "{}({}, {}, {})".format(JointDefinition.__name__, self.joint_type.__name__, self.elements, self.kwargs)

    def ToString(self):
        return repr(self)

    def __hash__(self):
        return hash((self.joint_type, self.elements))

    def is_identical(self, other):
        return isinstance(other, JointDefinition) and self.joint_type == other.joint_type and set([e.key for e in self.elements]) == set([e.key for e in other.elements])

    def match(self, elements):
        """Returns True if elements are defined within this JointDefinition."""
        set_a = set([id(e) for e in elements])
        set_b = set([id(e) for e in self.elements])
        return set_a == set_b


class FeatureDefinition(object):
    """Container linking a feature to the elements on which it should be applied.

    This allows delaying the actual applying of features to a downstream component.

    TODO: this needs to be adapted to in order to create processings.
    TODO: There needs to be a way for this to call a named alternative constructor with the required arguments.
    TODO: There needs to be a possibility to transform the elements before converting this to a processing.

    """

    def __init__(self, feature, elements=None):
        self.feature = feature
        self.elements = elements

    def __repr__(self):
        return "{}({}, {})".format(FeatureDefinition.__name__, repr(self.feature), self.elements)

    def ToString(self):
        return repr(self)


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
        self.joint_errors.append(error)
