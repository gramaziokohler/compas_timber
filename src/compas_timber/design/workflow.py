from email import errors
from itertools import combinations

from compas.tolerance import TOL

from compas_timber.connections import ConnectionSolver
from compas_timber.connections import JointTopology
from compas_timber.connections import LMiterJoint
from compas_timber.connections import PlateConnectionSolver
from compas_timber.connections import PlateJoint
from compas_timber.connections import TButtJoint
from compas_timber.connections import XLapJoint
from compas_timber.connections.plate_butt_joint import PlateButtJoint
from compas_timber.connections.plate_butt_joint import PlateTButtJoint
from compas_timber.connections.plate_miter_joint import PlateMiterJoint
from compas_timber.errors import BeamJoiningError
from compas_timber.elements.beam import Beam
from compas_timber.elements.plate import Plate
from compas_timber.utils import distance_segment_segment
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


class JointRule(object):
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
                JointTopology.TOPO_X: TopologyRule(JointTopology.TOPO_X, XLapJoint),
                JointTopology.TOPO_EDGE_EDGE: TopologyRule(JointTopology.TOPO_EDGE_EDGE, PlateMiterJoint),
                JointTopology.TOPO_EDGE_FACE: TopologyRule(JointTopology.TOPO_EDGE_FACE, PlateTButtJoint),
            }
        for rule in rules:  # separate category and topo and direct joint rules
            if rule.__class__.__name__ == "TopologyRule":
                topo_rules[rule.topology_type] = TopologyRule(rule.topology_type, rule.joint_type, rule.max_distance, **rule.kwargs)  # overwrites, meaning last rule wins
        return [rule for rule in topo_rules.values() if rule is not None]

    @staticmethod
    def joints_from_rules_and_elements(rules, elements, max_distance=TOL.absolute, handled_pairs=None):
        handled_pairs = handled_pairs or []
        elements = elements if isinstance(elements, list) else list(elements)
        direct_rules = JointRule.get_direct_rules(rules)
        solver = ConnectionSolver()

        max_rule_distance = max([rule.max_distance for rule in rules if rule.max_distance] + [max_distance])

        element_pairs = solver.find_intersecting_pairs(elements, rtree=True, max_distance=max_rule_distance)

        # these pairs were already handled by some external logic and shouldn't be processed again
        # e.g. the beams within a wall are joined by wall specific logic
        # however, other beams in the model should be allowed to be joined with them, thus they cannot be altogether excluded
        for pair in handled_pairs:
            if pair in element_pairs:
                element_pairs.remove(pair)

        direct_joints = []
        joints = []
        joining_errors = []
        for rule in direct_rules:
            try:
                joint = rule.get_joint(model_max_distance=max_distance)  # try to get the joint from the rule
                direct_joints.append(joint)
            except BeamJoiningError as e:
                joining_errors.append(e)

        while element_pairs:
            pair = element_pairs.pop()
            joint_found = False
            # ignore pairs that are joined by direct rules
            for joint in direct_joints:
                if set(pair).issubset(set(joint.elements)):
                    joint_found = True
                    break
            if joint_found:
                continue
            for rule in JointRule.get_category_rules(rules):  # see if pair is used in a category rule
                joint = rule.try_get_joint(pair, model_max_distance=max_distance)
                if joint:
                    joint_found = True
                    joints.append(joint)
                    break
            if joint_found:
                continue
            for rule in JointRule.get_topology_rules(rules):  # see if pair is used in a topology rule
                joint = rule.try_get_joint(pair, model_max_distance=max_distance)
                if joint:
                    joints.append(joint)
                    break

        return direct_joints + joints, joining_errors


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

    def get_joint(self, model_max_distance=TOL.absolute):
        """Returns True if the given elements comply with this DirectRule.
        Checks if the distance between the centerlines of the elements is less than the max_distance.
        Does not check for JointTopology compliance.

        Parameters
        ----------
        elements : tuple(:class:`~compas_timber.elements.TimberElement`, :class:`~compas_timber.elements.TimberElement`)
            A tuple containing two elements to check.
        model_max_distance : float, optional
            The maximum distance to consider two elements as intersecting. Defaults to TOL.absolute.
            This is only used if the rule does not already have a max_distance set.

        Returns
        -------
        bool
            True if the elements comply with the rule, False otherwise.

        """

        max_distance = self.max_distance or model_max_distance

        if all([isinstance(e, Beam) for e in self.elements]) and not issubclass(self.joint_type, PlateJoint):
            try:
                for pair in combinations(list(self.elements), 2):
                    if distance_segment_segment(pair[0].centerline, pair[1].centerline) > max_distance:
                        raise BeamJoiningError(pair,
                                               self.joint_type,
                                               "Joint type {} does not support elements with distance greater than {}".format(self.joint_type.__name__, max_distance),
                                               [e.shape for e in pair])
                return self.joint_type(*self.elements, **self.kwargs)
            except TypeError:
                raise UserWarning("unable to comply direct joint element sets")
        elif all([isinstance(e, Plate) for e in self.elements]) and issubclass(self.joint_type, PlateJoint):
            if len(self.elements) != 2:
                raise BeamJoiningError(self.elements, self.joint_type, "DirectRule for Plates requires exactly two elements.", [e.shape for e in self.elements])

            topo, plate_a, plate_b = PlateConnectionSolver().find_topology(self.elements[0], self.elements[1], max_distance=max_distance)
            if topo is not None:
                if topo != self.joint_type.SUPPORTED_TOPOLOGY:
                    raise BeamJoiningError(self.elements,
                                           self.joint_type,
                                           "Joint type {} does not support topology {}".format(self.joint_type.__name__, JointTopology.get_name(topo)),
                                           [e.shape for e in self.elements])
                    # TODO: implement error handling a la FeatureApplicationError.
                if topo == JointTopology.TOPO_EDGE_EDGE:
                    return self.joint_type(plate_a[0], plate_b[0], topo, plate_a[1], plate_b[1], **self.kwargs)
                else:
                    return self.joint_type(plate_a[0], plate_b[0], topo, plate_a[1], **self.kwargs)

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
    max_distance : float, optional
        The maximum distance to consider two elements as intersecting.
    kwargs : dict
        The keyword arguments to be passed to the joint.
    """

    def __init__(self, joint_type, category_a, category_b, topos=None, max_distance=None, **kwargs):
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

    def try_get_joint(self, elements, model_max_distance=TOL.absolute):
        """Checks if the given elements comply with this CategoryRule.
        It checks:
        that the elements have the expected category attribute,
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
        bool
            True if the elements comply with the rule, False otherwise.

        """
        if not set([e.attributes["category"] for e in elements]) == set([self.category_a, self.category_b]):
            return None

        elements = list(self.reorder(elements))  # reorder the elements to match the expected order of the joint type
        max_distance = self.max_distance or model_max_distance

        if all([isinstance(e, Beam) for e in elements]) and not issubclass(self.joint_type, PlateJoint):
            solver = ConnectionSolver()
            if (self.joint_type.SUPPORTED_TOPOLOGY, elements[0], elements[1]) != solver.find_topology(elements[0], elements[1], max_distance=max_distance):
                return None
            return self.joint_type(*elements, **self.kwargs)
        elif all([isinstance(e, Plate) for e in elements]) and issubclass(self.joint_type, PlateJoint):
            solver = PlateConnectionSolver()
            topo, plate_a, plate_b = solver.find_topology(elements[0], elements[1], max_distance=max_distance)
            if topo is not None:
                if topo != self.joint_type.SUPPORTED_TOPOLOGY:
                    return None
                if plate_a[0] != elements[0]:  # check that the plate roles are correct
                    return None
                if topo == JointTopology.TOPO_EDGE_EDGE:
                    return self.joint_type(plate_a[0], plate_b[0], topo, plate_a[1], plate_b[1], **self.kwargs)
                else:
                    return self.joint_type(plate_a[0], plate_b[0], topo, plate_a[1], **self.kwargs)
        return None

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
    max_distance : float, optional
        The maximum distance to consider two elements as intersecting.
        This will override a global max_distance if set.
    kwargs : dict
        The keyword arguments to be passed to the joint.
    """

    def __init__(self, topology_type, joint_type, max_distance=None, **kwargs):
        self.topology_type = topology_type
        self.joint_type = joint_type
        self.max_distance = max_distance
        self.kwargs = kwargs

    def ToString(self):
        # GH doesn't know
        return repr(self)

    def __repr__(self):
        return "{}({}, {})".format(
            TopologyRule,
            self.topology_type,
            self.joint_type,
        )

    def try_get_joint(self, elements, model_max_distance=TOL.absolute):
        """Checks if the given elements comply with this CategoryRule.
        It checks:
        that the elements have the expected category attribute,
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
        bool
            True if the elements comply with the rule, False otherwise.

        """

        max_distance = self.max_distance or model_max_distance
        elements = list(elements)
        if all([isinstance(e, Beam) for e in elements]) and not issubclass(self.joint_type, PlateJoint):
            solver = ConnectionSolver()
            found_topology, beam_a, beam_b = solver.find_topology(elements[0], elements[1], max_distance=max_distance)
            if found_topology == self.joint_type.SUPPORTED_TOPOLOGY:
                return self.joint_type(beam_a, beam_b, **self.kwargs)
        elif all([isinstance(e, Plate) for e in elements]) and issubclass(self.joint_type, PlateJoint):
            solver = PlateConnectionSolver()
            topo, plate_a, plate_b = solver.find_topology(elements[0], elements[1], max_distance=max_distance)
            if topo is not None:
                if topo != self.joint_type.SUPPORTED_TOPOLOGY:
                    return None
                if topo == JointTopology.TOPO_EDGE_EDGE:
                    return self.joint_type(plate_a[0], plate_b[0], topo, plate_a[1], plate_b[1], **self.kwargs)
                else:
                    return self.joint_type(plate_a[0], plate_b[0], topo, plate_a[1], **self.kwargs)
        return None


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
        if isinstance(error, list):
            self.joint_errors.extend(error)
        else:
            self.joint_errors.append(error)
