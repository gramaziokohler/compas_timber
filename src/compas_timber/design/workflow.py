from compas_timber.connections import ConnectionSolver
from compas_timber.connections import JointTopology
from compas_timber.connections import LMiterJoint
from compas_timber.connections import TButtJoint
from compas_timber.connections import XHalfLapJoint
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
    def comply(self, beams):
        """Returns True if the provided beams comply with the rule defined by this instance. False otherwise.

        Parameters
        ----------
        beams : list(:class:`~compas_timber.parts.Beam`)

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
                topo_rules[rule.topology_type] = TopologyRule(
                    rule.topology_type, rule.joint_type, **rule.kwargs
                )  # overwrites, meaning last rule wins
        return [rule for rule in topo_rules.values() if rule is not None]

    @staticmethod
    def joints_from_beams_and_rules(beams, rules, max_distance=1e-6):
        """Culls direct rules that are not applicable to the given beams.

        Parameters
        ----------
        beams : list(:class:`~compas_timber.parts.Beam`)
            A list of beams to be joined.
        rules : list(:class:`~compas_timber.design.JointRule`)
            A list of joint rules to be applied.
        max_distance : float, optional
            The maximum distance to consider two beams as intersecting.

        Returns
        -------
        list(:class:`~compas_timber.design.JointDefinition`)
            A list of joint definitions that can be applied to the given beams.

        """
        beams = beams if isinstance(beams, list) else list(beams)
        direct_rules = JointRule.get_direct_rules(rules)
        solver = ConnectionSolver()

        beam_pairs = solver.find_intersecting_pairs(beams, rtree=True, max_distance=max_distance)
        joint_defs = []
        unmatched_pairs = []
        for rule in direct_rules:
            joint_defs.append(JointDefinition(rule.joint_type, rule.beams, **rule.kwargs))

        while beam_pairs:
            pair = beam_pairs.pop()
            match_found = False
            for rule in direct_rules:  # see if pair is used in a direct rule
                if rule.comply(pair):
                    match_found = True
                    break

            if not match_found:
                for rule in JointRule.get_category_rules(rules):  # see if pair is used in a category rule
                    if rule.comply(pair):
                        match_found = True
                        joint_defs.append(JointDefinition(rule.joint_type, rule.reorder(pair), **rule.kwargs))
                        break

            if not match_found:
                for rule in JointRule.get_topology_rules(rules):  # see if pair is used in a topology rule
                    comply, pair = rule.comply(pair)
                    if comply:
                        match_found = True
                        joint_defs.append(JointDefinition(rule.joint_type, pair, **rule.kwargs))
                        break
            if not match_found:
                unmatched_pairs.append(pair)
        return joint_defs, unmatched_pairs


class DirectRule(JointRule):
    """Creates a Joint Rule that directly joins multiple elements."""

    def __init__(self, joint_type, beams, **kwargs):
        self.beams = beams
        self.joint_type = joint_type
        self.kwargs = kwargs

    def ToString(self):
        # GH doesn't know
        return repr(self)

    def __repr__(self):
        return "{}({}, {})".format(DirectRule, self.beams, self.joint_type)

    def comply(self, beams):
        try:
            return set(beams).issubset(set(self.beams))
        except TypeError:
            raise UserWarning("unable to comply direct joint beam sets")


class CategoryRule(JointRule):
    """Based on the category attribute attached to the beams, this rule assigns"""

    def __init__(self, joint_type, category_a, category_b, topos=None, **kwargs):
        self.joint_type = joint_type
        self.category_a = category_a
        self.category_b = category_b
        self.topos = topos or []
        self.kwargs = kwargs

    def ToString(self):
        # GH doesn't know
        return repr(self)

    def __repr__(self):
        return "{}({}, {}, {}, {})".format(
            CategoryRule.__name__, self.joint_type.__name__, self.category_a, self.category_b, self.topos
        )

    def comply(self, beams, max_distance=1e-6):
        try:
            beam_cats = set([b.attributes["category"] for b in beams])
            comply = False
            beams = list(beams)
            if beam_cats == set([self.category_a, self.category_b]):
                solver = ConnectionSolver()
                if (
                    self.joint_type.SUPPORTED_TOPOLOGY
                    == solver.find_topology(beams[0], beams[1], max_distance=max_distance)[0]
                ):
                    comply = True
            return comply
        except KeyError:
            return False

    def reorder(self, beams):
        """Returns the given beams in a sorted order.

        The beams are sorted according to their category attribute, first the beams with `catergory_a` and second the
        one with `category_b`.
        This allows using the category to determine the role of the beams.

        Parameters
        ----------
        beams : tuple(:class:`~compas_timber.parts.Beam`, :class:`~compas_timber.parts.Beam`)
            A tuple containing two beams to sort.

        Returns
        -------
        tuple(:class:`~compas_timber.parts.Beam`, :class:`~compas_timber.parts.Beam`)

        """
        beam_a, beam_b = beams
        if beam_a.attributes["category"] == self.category_a:
            return beam_a, beam_b
        else:
            return beam_b, beam_a


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

    def __init__(self, topology_type, joint_type, **kwargs):
        self.topology_type = topology_type
        self.joint_type = joint_type
        self.kwargs = kwargs

    def ToString(self):
        # GH doesn't know
        return repr(self)

    def __repr__(self):
        return "{}({}, {})".format(TopologyRule, self.topology_type, self.joint_type)

    def comply(self, beams, max_distance=1e-3):
        try:
            beams = list(beams)
            solver = ConnectionSolver()
            topo_results = solver.find_topology(beams[0], beams[1], max_distance=max_distance)
            return (
                self.topology_type == topo_results[0],
                [topo_results[1], topo_results[2]],
            )  # comply, if topologies match, reverse if the beam order should be switched
        except KeyError:
            return False


class JointDefinition(object):
    """Container for a joint type and the elements that shall be joined.

    This allows delaying the actual joining of the beams to a downstream component.

    """

    def __init__(self, joint_type, beams, **kwargs):
        # if not issubclass(joint_type, Joint):
        #     raise UserWarning("{} is not a valid Joint type!".format(joint_type.__name__))
        if len(beams) < 2:
            raise UserWarning("Joint requires at least two Beams, got {}.".format(len(beams)))

        self.joint_type = joint_type
        self.beams = beams
        self.kwargs = kwargs

    def __repr__(self):
        return "{}({}, {}, {})".format(JointDefinition.__name__, self.joint_type.__name__, self.beams, self.kwargs)

    def ToString(self):
        return repr(self)

    def __hash__(self):
        return hash((self.joint_type, self.beams))

    def is_identical(self, other):
        return (
            isinstance(other, JointDefinition)
            and self.joint_type == other.joint_type
            and set([b.key for b in self.beams]) == set([b.key for b in other.beams])
        )

    def match(self, beams):
        """Returns True if beams are defined within this JointDefinition."""
        set_a = set([id(b) for b in beams])
        set_b = set([id(b) for b in self.beams])
        return set_a == set_b


class FeatureDefinition(object):
    """Container linking a feature to the elements on which it should be applied.

    This allows delaying the actual applying of features to a downstream component.

    """

    def __init__(self, feature, elements):
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
        self.feature_errors = []
        self.joint_errors = []

    def __repr__(self):
        return "{}({} feature errors, {} joining errors)".format(
            DebugInfomation.__name__, len(self.feature_errors), len(self.joint_errors)
        )

    def ToString(self):
        return repr(self)

    @property
    def has_errors(self):
        return self.feature_errors or self.joint_errors

    def add_feature_error(self, error):
        if isinstance(error, list):
            self.feature_errors.extend(error)
        else:
            self.feature_errors.append(error)

    def add_joint_error(self, error):
        self.joint_errors.append(error)
