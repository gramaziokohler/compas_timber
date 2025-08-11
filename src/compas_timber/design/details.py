from compas_timber.connections import JointTopology
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

    def beam_from_category(self, segment, category, slab_populator, normal_offset=True, **kwargs):
        """Creates a beam from a segment and a category, using the dimensions from the configuration set.
        Parameters
        ----------
        segment : :class:`compas.geometry.Line`
            The segment to create the beam from.
        category : str
            The category of the beam, which determines its dimensions.
        slab_populator : :class:`compas_timber.populators.SlabPopulator`
            The populator instance that provides the beam dimensions.
        normal_offset : bool, optional
            Whether to offset the beam by 1/2 of the beam height in the parent.normal direction. Defaults to True.
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
        beam = Beam.from_centerline(segment, width=width, height=height, z_vector=slab_populator.normal)
        for key, value in kwargs.items():
            beam.attributes[key] = value
        beam.attributes["category"] = category

        if normal_offset:
            # beam centerlines are aligned to the slab frame, so we offset them by half the height
            beam.frame.translate(slab_populator.normal * height * 0.5)  # align the beam to the slab frame
        if beam is None:
            raise ValueError("Failed to create beam from segment: {}".format(segment))
        return beam

    def get_joint_from_elements(self, element_a, element_b, **kwargs):
        """Get the joint type for the given elements."""
        for rule in self.rules:
            if rule.category_a == element_a.attributes["category"] and rule.category_b == element_b.attributes["category"]:
                rule.kwargs.update(kwargs)
                return rule.joint_type(element_a, element_b, **rule.kwargs)
        raise ValueError("No joint definition found for {} and {}".format(element_a.attributes["category"], element_b.attributes["category"]))
