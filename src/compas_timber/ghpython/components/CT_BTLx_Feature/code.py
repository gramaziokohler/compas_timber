import inspect

from compas.geometry import Line
from compas.scene import Scene
from ghpythonlib.componentbase import executingcomponent as component
from Grasshopper.Kernel.GH_RuntimeMessageLevel import Warning

from compas_timber._fabrication import BTLxProcess
from compas_timber.design import FeatureDefinition
from compas_timber.ghpython.ghcomponent_helpers import get_leaf_subclasses
from compas_timber.ghpython.ghcomponent_helpers import manage_dynamic_params
from compas_timber.ghpython.ghcomponent_helpers import rename_gh_output


class BTLxFeature(component):
    def __init__(self):
        super(BTLxFeature, self).__init__()
        self.classes = {}
        for cls in get_leaf_subclasses(BTLxProcess):
            self.classes[cls.__name__] = cls

        if ghenv.Component.Params.Output[0].NickName == "Process":
            self.processing_type = None
        else:
            self.processing_type = self.classes.get(ghenv.Component.Params.Output[0].NickName, None)

    def RunScript(self, beam, ref_side, *args):
        if not self.processing_type:
            ghenv.Component.Message = "Select Process type from context menu (right click)"
            self.AddRuntimeMessage(Warning, "Select Process type from context menu (right click)")
            return None
        else:
            ghenv.Component.Message = self.processing_type.__name__
            kwargs = {}
            kwargs["ref_side_index"] = ref_side
            for arg, val in zip(self.arg_names(), args):
                if val is not None:
                    kwargs[arg] = val

            process = self.processing_type(**kwargs)
            face = beam.ref_sides[ref_side]

            line_scene = Scene()
            line_scene.add(Line.from_point_direction_length(face.point, face.xaxis, beam.length))
            line_scene.add(
                Line.from_point_direction_length(
                    face.point, face.yaxis, beam.width if ref_side % 2 == 0 else beam.height
                )
            )

            return FeatureDefinition(process, [beam]), line_scene.draw()

    def arg_names(self):
        return inspect.getargspec(self.processing_type.__init__)[0][1:]

    def AppendAdditionalMenuItems(self, menu):
        for name in self.classes.keys():
            item = menu.Items.Add(name, None, self.on_item_click)
            if self.processing_type and name == self.processing_type.__name__:
                item.Checked = True

    def on_item_click(self, sender, event_info):
        self.processing_type = self.classes[str(sender)]
        rename_gh_output(self.processing_type.__name__, 0, ghenv)
        manage_dynamic_params(self.arg_names(), ghenv, rename_count=0, permanent_param_count=2)
        ghenv.Component.ExpireSolution(True)
