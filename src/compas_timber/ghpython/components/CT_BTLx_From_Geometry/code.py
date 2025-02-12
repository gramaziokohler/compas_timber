import inspect

import Rhino.Geometry as rg
from compas.geometry import Line
from compas_rhino.conversions import plane_to_compas
from ghpythonlib.componentbase import executingcomponent as component
from Grasshopper.Kernel.GH_RuntimeMessageLevel import Error
from Grasshopper.Kernel.GH_RuntimeMessageLevel import Warning

from compas_timber.fabrication import BTLxFromGeometryDefinition
from compas_timber.fabrication import DeferredBTLxProcessing
from compas_timber.ghpython.ghcomponent_helpers import get_leaf_subclasses
from compas_timber.ghpython.ghcomponent_helpers import manage_dynamic_params
from compas_timber.ghpython.ghcomponent_helpers import rename_gh_output


class BTLxFromGeometry(component):
    def __init__(self):
        super(BTLxFromGeometry, self).__init__()
        self.classes = {}
        self.required_input_count = 0
        for cls in get_leaf_subclasses(DeferredBTLxProcessing):
            self.classes[cls.TYPE_NAME] = cls

        if ghenv.Component.Params.Output[0].NickName == "Features":
            self.processing_type = None
        else:
            self.processing_type = self.classes.get(ghenv.Component.Params.Output[0].NickName, None)

    def RunScript(self, *args):
        print(self.arg_names())
        if not self.processing_type:
            ghenv.Component.Message = "Select Process type from context menu (right click)"
            self.AddRuntimeMessage(Warning, "Select Process type from context menu (right click)")
            return None
        else:
            ghenv.Component.Message = self.processing_type.TYPE_NAME
            for arg, arg_name in zip(args[0:self.required_input_count], self.arg_names()[0:self.required_input_count]):
                print(arg_name, arg)
                if not arg:
                    self.AddRuntimeMessage(Warning, "Input parameter {} failed to collect data".format(arg_name))
                    return
            kwargs = {}
            for geo, arg_name in zip(args[0:self.processing_type.GEOMETRY_COUNT], self.arg_names())[0:self.processing_type.GEOMETRY_COUNT]:
                if isinstance(geo, rg.Curve):
                    kwargs[arg_name] = Line(geo.PointAtStart, geo.PointAtEnd)
                elif isinstance(geo, rg.Plane):
                    plane = plane_to_compas(geo)
                    print("plane is the following: ", plane)
                    kwargs[arg_name] = plane
                    print(kwargs)
                else:
                    self.AddRuntimeMessage(Error, "Input parameter {} collected unusable data".format(arg_name))

            for key, val in zip(self.arg_names()[self.processing_type.GEOMETRY_COUNT:], args[self.processing_type.GEOMETRY_COUNT:]):
                if val is not None:
                    kwargs[key] = val
            return self.processing_type.from_shapes(**kwargs)

    def arg_names(self):
        args = inspect.getargspec(self.processing_type.from_shapes)
        arg_names, defaults = args.args[1:], args.defaults if args.defaults else 0
        self.required_input_count = len(arg_names) - len(defaults)
        return arg_names

    def AppendAdditionalMenuItems(self, menu):
        for name in self.classes.keys():
            item = menu.Items.Add(name, None, self.on_item_click)
            if self.processing_type and name == self.processing_type.TYPE_NAME:
                item.Checked = True

    def on_item_click(self, sender, event_info):
        self.processing_type = self.classes[str(sender)]
        rename_gh_output(self.processing_type.TYPE_NAME, 0, ghenv)
        manage_dynamic_params(self.arg_names(), ghenv, rename_count=0, permanent_param_count=0)
        ghenv.Component.ExpireSolution(True)
