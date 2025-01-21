import inspect

from ghpythonlib.componentbase import executingcomponent as component
from Grasshopper.Kernel.GH_RuntimeMessageLevel import Warning
import Rhino.Geometry as rg
from compas_rhino.conversions import plane_to_compas
from compas.geometry import Line

from compas_timber.fabrication import BTLxFeatureDefinition
from compas_timber.fabrication import BTLxProcessing
from compas_timber.ghpython.ghcomponent_helpers import get_leaf_subclasses
from compas_timber.ghpython.ghcomponent_helpers import manage_dynamic_params
from compas_timber.ghpython.ghcomponent_helpers import rename_gh_output


class BTLxFeature(component):
    def __init__(self):
        super(BTLxFeature, self).__init__()
        self.classes = {}
        self.geometry_count = 0
        for cls in get_leaf_subclasses(BTLxProcessing):
            functions = inspect.getmembers(cls, predicate=inspect.ismethod)
            if "from_shapes_and_element" in [func[0] for func in functions]:
                self.classes[cls.__name__] = cls

        if ghenv.Component.Params.Output[0].NickName == "Process":
            self.processing_type = None
        else:
            self.processing_type = self.classes.get(ghenv.Component.Params.Output[0].NickName, None)

    def RunScript(self, elements, *args):
        if not self.processing_type:
            ghenv.Component.Message = "Select Process type from context menu (right click)"
            self.AddRuntimeMessage(Warning, "Select Process type from context menu (right click)")
            return None
        else:
            ghenv.Component.Message = self.processing_type.__name__
            for geo, arg_name in zip(args, self.arg_names()):
                if not geo:
                    self.AddRuntimeMessage(Warning, "Input parameter {} failed to collect data".format(arg_name))
                    return
            geometries = []
            for geo, arg_name in zip(args, self.arg_names())[0:self.geometry_count]:
                if not geo:
                    self.AddRuntimeMessage(Warning, "Input parameter {} failed to collect data".format(arg_name))
                if isinstance(geo, rg.Curve):
                    geometries.append(Line(geo.PointAtStart, geo.PointAtEnd))
                if isinstance(geo, rg.Plane):
                    geometries.append(plane_to_compas(geo))
            if not geometries:
                self.AddRuntimeMessage(Warning, "no valid geometry collected")
                return
            kwargs = {"geometries": geometries}
            if elements:
                kwargs["elements"] = elements
            for key, val in zip(self.arg_names()[self.geometry_count:], args[self.geometry_count:]):
                if val is not None:
                    kwargs[key] = val
            process = self.processing_type()
            return BTLxFeatureDefinition(process, **kwargs)

    def arg_names(self):
        names = inspect.getargspec(self.processing_type.from_shapes_and_element)[0][1:]
        count = 0
        for name in names:
            if name == "element":
                break
            else:
                count +=1
        self.geometry_count = count
        return [name for name in names if name != "element"]

    def AppendAdditionalMenuItems(self, menu):
        for name in self.classes.keys():
            item = menu.Items.Add(name, None, self.on_item_click)
            if self.processing_type and name == self.processing_type.__name__:
                item.Checked = True

    def on_item_click(self, sender, event_info):
        self.processing_type = self.classes[str(sender)]
        rename_gh_output(self.processing_type.__name__, 0, ghenv)
        manage_dynamic_params(self.arg_names(), ghenv, rename_count=0, permanent_param_count=1)
        ghenv.Component.ExpireSolution(True)
