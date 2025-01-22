import inspect

from ghpythonlib.componentbase import executingcomponent as component
from Grasshopper.Kernel.GH_RuntimeMessageLevel import Warning

from compas_timber.fabrication import BTLxProcessing
from compas_timber.ghpython.ghcomponent_helpers import get_leaf_subclasses
from compas_timber.ghpython.ghcomponent_helpers import manage_dynamic_params
from compas_timber.ghpython.ghcomponent_helpers import rename_gh_output


class BTLxFromParams(component):
    def __init__(self):
        super(BTLxFromParams, self).__init__()
        self.classes = {}
        for cls in get_leaf_subclasses(BTLxProcessing):
            self.classes[cls.__name__] = cls

        if ghenv.Component.Params.Output[0].NickName == "Processing":
            self.processing_type = None
        else:
            self.processing_type = self.classes.get(ghenv.Component.Params.Output[0].NickName, None)

    def RunScript(self, ref_side, *args):
        if not ref_side:
            ref_side = 0

        if not self.processing_type:
            ghenv.Component.Message = "Select Processing type from context menu (right click)"
            self.AddRuntimeMessage(Warning, "Select Processing type from context menu (right click)")
            return
        else:
            ghenv.Component.Message = self.processing_type.__name__
            kwargs = {"ref_side_index": ref_side}
            for arg, val in zip(self.arg_names(), args):
                if val is not None:
                    kwargs[arg] = val

            processing = self.processing_type(**kwargs)
            processing.is_joinery_feature = False
            return processing

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
        manage_dynamic_params(self.arg_names(), ghenv, rename_count=0, permanent_param_count=1)
        ghenv.Component.ExpireSolution(True)
