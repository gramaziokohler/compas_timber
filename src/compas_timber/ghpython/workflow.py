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


class CategoryRule(JointRule):
    """Based on the category attribute attached to the beams, this rule assigns"""

    def __init__(self, joint_type, category_a, category_b):
        self.joint_type = joint_type
        self.category_a = category_a
        self.category_b = category_b

    def ToString(self):
        # GH doesn't know
        return repr(self)

    def __repr__(self):
        return "{}({}, {}, {})".format(
            CategoryRule.__name__, self.joint_type.__name__, self.category_a, self.category_b
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


class JointDefinition(object):
    """Container for a joint type and the beam that shall be joined.

    This allows delaying the actual joining of the beams to a downstream component.

    """

    def __init__(self, joint_type, beams):
        # if not issubclass(joint_type, Joint):
        #     raise UserWarning("{} is not a valid Joint type!".format(joint_type.__name__))
        if len(beams) != 2:
            raise UserWarning("Expected to get two Beams, got {}.".format(len(beams)))

        self.joint_type = joint_type
        self.beams = beams

    def __repr__(self):
        return "{}({}, {})".format(JointDefinition.__name__, self.joint_type.__name__, self.beams)

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

    def __init__(self, feature, beams):
        self.feature = feature
        self.beams = beams

    def __repr__(self):
        return "{}({}, {})".format(FeatureDefinition.__name__, repr(self.feature), self.beams)

    def ToString(self):
        return repr(self)


class Attribute:
    def __init__(self, attr_name, attr_value):
        self.name = attr_name
        self.value = attr_value

    def __str__(self):
        return "Attribute %s: %s" % (self.name, self.value)


def guess_joint_topology_2beams(beamA, beamB, tol=1e-6, max_distance=1e-6):
    #TODO: replace default max_distance ~ zero with global project precision

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
