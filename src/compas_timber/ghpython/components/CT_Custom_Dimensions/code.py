import clr
from ghpythonlib.componentbase import executingcomponent as component
import System
from compas_timber.assembly import SurfaceAssembly

beam_category_names = SurfaceAssembly.beam_category_names()


def on_item_click(sender, event_info):
    item = clr.Convert(sender, System.Windows.Forms.ToolStripItem)
    item.Checked = not item.Checked
    ghenv.Component.ExpireSolution(True)


class CustomBeamDimensions(component):
    def __init__(self):
        super(CustomBeamDimensions, self).__init__()
        self.items = []

    def RunScript(self, width, height):
        self.dims = {}
        if self.items:
            for i, item in enumerate(self.items):
                if item.Checked and (width or height):
                    self.dims[beam_category_names[i]] = (width or 0, height or 0)
        return (self.dims,)  # return a tuple to allow passing dict between components

    def AppendAdditionalMenuItems(self, menu):
        if self.items:
            for item in self.items:
                menu.Items.Add(item)
        else:
            for name in beam_category_names:
                item = menu.Items.Add(name, None, on_item_click)
                self.items.append(item)
