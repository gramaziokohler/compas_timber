# r: compas_timber>=0.15.3
# flake8: noqa
import inspect

import Grasshopper
import System
from compas.scene import Scene

from compas_timber.fabrication import BTLxProcessing
from compas_timber.ghpython.ghcomponent_helpers import get_leaf_subclasses
from compas_timber.ghpython.ghcomponent_helpers import manage_cpython_dynamic_params
from compas_timber.ghpython.ghcomponent_helpers import rename_cpython_gh_output


class BTLxFromParams(Grasshopper.Kernel.GH_ScriptInstance):
    def __init__(self):
        super(BTLxFromParams, self).__init__()
        self.classes = {}
        for cls in get_leaf_subclasses(BTLxProcessing):
            self.classes[cls.__name__] = cls
        if ghenv.Component.Params.Output[0].NickName == "Processing":
            self.processing_type = None
        else:
            self.processing_type = self.classes.get(ghenv.Component.Params.Output[0].NickName, None)

    def RunScript(self, element: System.Collections.Generic.List[object], ref_side: System.Collections.Generic.List[int], *args):
        if not self.processing_type:
            ghenv.Component.Message = "Select Process type from context menu (right click)"
            ghenv.Component.AddRuntimeMessage(Grasshopper.Kernel.GH_RuntimeMessageLevel.Warning, "Select Process type from context menu (right click)")
            return None
        else:
            if not ref_side:
                ref_side = [0 for _ in range(len(element))]
            elif len(ref_side) == 1:
                ref_side = [ref_side[0] for _ in range(len(element))]
            else:
                if len(ref_side) != len(element):
                    ghenv.Component.AddRuntimeMessage(Grasshopper.Kernel.GH_RuntimeMessageLevel.Warning, "Ref side should be empty,a single index, or the same length as elements")
                    return
            ghenv.Component.Message = self.processing_type.__name__
            kwargs = {}
            kwargs["ref_side_index"] = ref_side
            for arg, val in zip(self.arg_names(), args):
                if val is not None:
                    kwargs[arg] = val

            processing = self.processing_type(**kwargs)

            scene = Scene()
            if processing and element:
                for e in element:
                    e_copy = e.copy()
                    e_copy.add_features(processing)
                    scene.add(e_copy.geometry)

            return DeferredBTLxProcessing(processing, element), scene.draw()

    def arg_names(self):
        return inspect.getargspec(self.processing_type.__init__)[0][1:]

    def AppendAdditionalMenuItems(self, menu):
        for name in self.classes.keys():
            item = menu.Items.Add(name, None, self.on_item_click)
            if self.processing_type and name == self.processing_type.__name__:
                item.Checked = True

    def on_item_click(self, sender, event_info):
        self.processing_type = self.classes[str(sender)]
        rename_cpython_gh_output(self.processing_type.__name__, 0, ghenv)
        manage_cpython_dynamic_params(self.arg_names(), ghenv, rename_count=0, permanent_param_count=2)
        ghenv.Component.ExpireSolution(True)


class DeferredBTLxProcessing(object):
    def __init__(self, processing, elements):
        self.processing = processing
        self.elements = elements if isinstance(elements, list) else [elements]

    def __str__(self):
        return "DeferredBTLxProcessing({})".format(self.processing.__class__.__name__)

    def __repr__(self):
        return "DeferredBTLxProcessing(processing={!r})".format(self.processing.__class__.__name__)

    def ToString(self):
        return self.__str__()

    def feature_from_element(self, element):
        return self.processing
