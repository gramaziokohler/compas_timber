from compas.geometry import Vector

from compas_timber.connections import JointTopology
from compas_timber.design import DirectRule
from compas_timber.elements import Beam


class DetailBase(object):
    """Base class for opening detail sets.

    Parameters
    ----------
    beam_width_overrides : dict, optional
        A dictionary of beam width overrides for specific beam categories.
        key = beam category name, value = beam width.
    joint_rule_overrides : list[:class:`compas_timber.design.CategoryRule`], optional
        A list of category rules to override the default ones.
    """

    BEAM_CATEGORY_NAMES = []

    def __init__(self, beam_width_overrides=None, joint_rule_overrides=None):
        self.beam_width_overrides = beam_width_overrides or {}  # actual dimensions need a SlabPopulator instance
        print("Beam width overrides:", self.beam_width_overrides)
        if not joint_rule_overrides:
            self.rules = self.RULES
        else:
            self.rules = self.update_rules(joint_rule_overrides)

    def update_rules(self, joint_rule_overrides):
        """Update the rules with any overrides provided."""
        rules = [r for r in self.RULES]

        for override in joint_rule_overrides:
            for rule in rules:
                # element order is important TODO: use rule.comply_topology when merged. TOPO_EDGE_EDGE should not occur, but adding for future-proofing.
                if rule.joint_type.supported_topology == JointTopology.TOPO_T or rule.joint_type.supported_topology == JointTopology.TOPO_EDGE_FACE:
                    if override.category_a == rule.category_a and override.category_b == rule.category_b:
                        rule = override
                        break
                else:  # order does not matter
                    if set([override.category_a, override.category_b]) == set([rule.category_a, rule.category_b]):
                        rule = override
                        break
            else:
                rules.append(override)
        return rules

    def get_beam_dimensions(self, slab_populator):
        """Get the beam dimensions for the detail set."""
        beam_dims = {}
        for category in self.BEAM_CATEGORY_NAMES:
            if category in self.beam_width_overrides:
                beam_dims[category] = (self.beam_width_overrides[category], slab_populator.frame_thickness)
            else:
                beam_dims[category] = (slab_populator.detail_set.beam_width, slab_populator.frame_thickness)
        return beam_dims

    def beam_from_category(self, segment, category, slab_populator, **kwargs):
        """Creates a beam from a segment and a category, using the dimensions from the configuration set.
        Parameters
        ----------
        segment : :class:`compas.geometry.Line`
            The segment to create the beam from.
        category : str
            The category of the beam, which determines its dimensions.
        slab_populator : :class:`compas_timber.populators.SlabPopulator`
            The populator instance that provides the beam dimensions.
        kwargs : dict, optional
            Additional attributes to set on the beam.

        Returns
        -------
        :class:`compas_timber.elements.Beam`
            The created beam with the specified category and attributes.
        """
        beam_dimensions = self.get_beam_dimensions(slab_populator)
        if category not in beam_dimensions:
            raise ValueError("Unknown beam category: {}".format(category))
        width = beam_dimensions[category][0]
        height = beam_dimensions[category][1]
        beam = Beam.from_centerline(segment, width=width, height=height, z_vector=Vector(0,0,1))
        for key, value in kwargs.items():
            beam.attributes[key] = value
        beam.attributes["category"] = category
        if beam is None:
            raise ValueError("Failed to create beam from segment: {}".format(segment))
        return beam

    def get_direct_rule_from_elements(self, element_a, element_b, **kwargs):
        """Get the joint type for the given elements."""
        for rule in self.rules:
            if rule.category_a == element_a.attributes["category"] and rule.category_b == element_b.attributes["category"]:
                rule.kwargs.update(kwargs)
                return DirectRule(rule.joint_type, [element_a, element_b], **rule.kwargs)
        raise ValueError("No joint definition found for {} and {}".format(element_a.attributes["category"], element_b.attributes["category"]))

    def _append_and_replace_joints(self, joints, slab_populator):
            to_remove = []
            for joint in joints:
                for sp_joint in slab_populator.joints:
                    if set(joint.elements) == set(sp_joint.elements):
                        to_remove.append(sp_joint)
                        break
            for joint in to_remove:
                slab_populator.joints.remove(joint)
            slab_populator.joints.extend(joints)
