from compas_timber.connections import LMiterJoint
from compas_timber.connections import TButtJoint
from compas_timber.utils.compas_extra import intersection_line_line_3D


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


class DirectRule(JointRule):
    """Creates a Joint Rule that directly joins two beams."""

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
            return set(self.beams) == set(beams)
        except TypeError:
            print("unable to comply direct joint beam sets")
            return False


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

    def comply(self, beams):
        try:
            beam_cats = set([b.attributes["category"] for b in beams])
            return beam_cats == set([self.category_a, self.category_b])
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


class JointDefinition(object):
    """Container for a joint type and the beam that shall be joined.

    This allows delaying the actual joining of the beams to a downstream component.

    """

    def __init__(self, joint_type, beams, **kwargs):
        # if not issubclass(joint_type, Joint):
        #     raise UserWarning("{} is not a valid Joint type!".format(joint_type.__name__))
        if len(beams) != 2:
            raise UserWarning("Expected to get two Beams, got {}.".format(len(beams)))

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
    """Container linking a feature for the beams on which it should be applied.

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

    [pa, ta], [pb, tb] = intersection_line_line_3D(beamA.centerline, beamB.centerline, max_distance, True, tol)

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


def set_defaul_joints(model, x_default="x-lap", t_default="t-butt", l_default="l-miter"):
    beams = model.beams
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
