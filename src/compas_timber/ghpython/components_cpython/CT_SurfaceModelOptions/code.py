# r: compas_timber>=0.15.3
# flake8: noqa
import Grasshopper
import System


class SurfaceModelOptions(Grasshopper.Kernel.GH_ScriptInstance):
    def RunScript(
        self,
        sheeting_outside: float,
        sheeting_inside: float,
        lintel_posts: bool,
        edge_stud_offset: float,
        custom_dimensions: System.Collections.Generic.List[object],
        joint_overrides: System.Collections.Generic.List[object],
    ):
        if sheeting_outside is not None and not isinstance(sheeting_outside, float):
            ghenv.Component.AddRuntimeMessage(Grasshopper.Kernel.GH_RuntimeMessageLevel.Error, "sheeting_outside expected a float, got: {}".format(type(sheeting_outside)))
        if sheeting_inside is not None and not isinstance(sheeting_inside, float):
            ghenv.Component.AddRuntimeMessage(Grasshopper.Kernel.GH_RuntimeMessageLevel.Error, "sheeting_inside expected a float, got: {}".format(type(sheeting_inside)))
        if lintel_posts is not None and not isinstance(lintel_posts, bool):
            ghenv.Component.AddRuntimeMessage(Grasshopper.Kernel.GH_RuntimeMessageLevel.Error, "lintel_posts expected a bool, got: {}".format(type(lintel_posts)))

        dims = {}
        if custom_dimensions is not None:
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
