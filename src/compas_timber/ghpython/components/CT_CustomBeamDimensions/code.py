from ghpythonlib.componentbase import executingcomponent as component

from compas_timber.design import SurfaceModel

beam_category_names = SurfaceModel.beam_category_names()


def on_item_click(sender, event_info):
    ghenv.Component.Params.Output[0].NickName = str(sender)
    ghenv.Component.Params.OnParametersChanged()
    ghenv.Component.ExpireSolution(True)


class CustomBeamDimensions(component):
    def RunScript(self, width, height):
        dims = {}

        if width is None or height is None:
            return

        if ghenv.Component.Params.Output[0].NickName != "Dimensions":
            dims[ghenv.Component.Params.Output[0].NickName] = (width or 0, height or 0)
        return (dims,)  # return a tuple to allow passing dict between components

    def AppendAdditionalMenuItems(self, menu):
        for name in beam_category_names:
            item = menu.Items.Add(name, None, on_item_click)
            if name == ghenv.Component.Params.Output[0].NickName:
                item.Checked = True
