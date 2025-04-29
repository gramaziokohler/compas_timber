# r: compas_timber>=0.15.3
# flake8: noqa
import Grasshopper

from compas_timber.design import SurfaceModel
from compas_timber.ghpython.ghcomponent_helpers import item_input_valid_cpython

beam_category_names = SurfaceModel.beam_category_names()


def on_item_click(sender, event_info):
    ghenv.Component.Params.Output[0].NickName = str(sender)
    ghenv.Component.Params.OnParametersChanged()
    ghenv.Component.ExpireSolution(True)


class CustomBeamDimensions(Grasshopper.Kernel.GH_ScriptInstance):
    def RunScript(self, width: float, height: float):
        dims = {}

        if not (item_input_valid_cpython(ghenv, width, "Width") and item_input_valid_cpython(ghenv, height, "Height")):
            return

        if ghenv.Component.Params.Output[0].NickName != "Dimensions":
            dims[ghenv.Component.Params.Output[0].NickName] = (width or 0, height or 0)
        return (dims,)  # return a tuple to allow passing dict between components

    def AppendAdditionalMenuItems(self, menu):
        for name in beam_category_names:
            item = menu.Items.Add(name, None, on_item_click)
            if name == ghenv.Component.Params.Output[0].NickName:
                item.Checked = True
