from ghpythonlib.componentbase import executingcomponent as component


class SurfaceModelOptions(component):
    def RunScript(self, sheeting_outside, sheeting_inside, lintel_posts, edge_stud_offset, custom_dimensions, joint_overrides):
        if sheeting_outside is not None and not isinstance(sheeting_outside, float):
            raise TypeError("sheeting_outside expected a float, got: {}".format(type(sheeting_outside)))
        if sheeting_inside is not None and not isinstance(sheeting_inside, float):
            raise TypeError("sheeting_inside expected a float, got: {}".format(type(sheeting_inside)))
        if lintel_posts is not None and not isinstance(lintel_posts, bool):
            raise TypeError("lintel_posts expected a bool, got: {}".format(type(lintel_posts)))

        dims = {}
        for item in custom_dimensions:
            for key, val in item.items():
                dims[key] = val

        dict = {
            "sheeting_outside": sheeting_outside,
            "sheeting_inside": sheeting_inside,
            "lintel_posts": lintel_posts,
            "edge_stud_offset": edge_stud_offset,
            "custom_dimensions": dims,
            "joint_overrides": joint_overrides,
        }

        return (dict,)
