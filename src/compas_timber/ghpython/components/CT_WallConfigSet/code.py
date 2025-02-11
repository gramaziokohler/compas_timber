from ghpythonlib.componentbase import executingcomponent as component

from compas_timber.design import WallPopulatorConfigurationSet


class WallPopulatorConfigSetComponent(component):
    def RunScript(self, stud_spacing, beam_width, sheeting_outside, sheeting_inside, lintel_posts, edge_stud_offset, custom_dimensions, joint_overrides):
        # if sheeting_outside is not None and not isinstance(sheeting_outside, float):
        #     raise TypeError("sheeting_outside expected a float, got: {}".format(type(sheeting_outside)))
        # if sheeting_inside is not None and not isinstance(sheeting_inside, float):
        #     raise TypeError("sheeting_inside expected a float, got: {}".format(type(sheeting_inside)))
        # if lintel_posts is not None and not isinstance(lintel_posts, bool):
        #     raise TypeError("lintel_posts expected a bool, got: {}".format(type(lintel_posts)))

        dims = {}
        for item in custom_dimensions:
            for key, val in item.items():
                dims[key] = val

        return WallPopulatorConfigurationSet(stud_spacing, beam_width, custom_dimensions=dims)
