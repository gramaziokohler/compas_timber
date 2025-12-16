# r: compas_timber>=1.0.3
# flake8: noqa
import Grasshopper
from compas.scene import Scene
from System.Windows.Forms import ToolStripSeparator

from compas_timber.ghpython.ghcomponent_helpers import rename_gh_output


class ShowElementsByCategory(Grasshopper.Kernel.GH_ScriptInstance):
    def __init__(self):
        super(ShowElementsByCategory, self).__init__()
        ghenv.Component.Params.Output[0].NickName == "elements"
        self.element_type =  None

    def RunScript(self, model):

        if model is None:
            self.names = set()
            ghenv.Component.Message = "Please connect Model"
            ghenv.Component.AddRuntimeMessage(Grasshopper.Kernel.GH_RuntimeMessageLevel.Warning, "Please connect Model")
            return None
        
        self.names = set(element.attributes.get("category") for element in model.elements())
        self.names.discard(None)

        if not self.element_type:
            ghenv.Component.Message = "Select element type from context menu (right click)"
            ghenv.Component.AddRuntimeMessage(Grasshopper.Kernel.GH_RuntimeMessageLevel.Warning, "Select element type from context menu (right click)")
            return None
        
        ghenv.Component.Message = f"Category: {self.element_type}"

        scene = Scene()
        for element in model.elements():
            if element.attributes.get("category") == self.element_type:
                scene.add(element.geometry)
        return scene.draw()

    def AppendAdditionalMenuItems(self, menu):
        menu.Items.Add(ToolStripSeparator())
        for name in self.names:
            item = menu.Items.Add(name, None, self.on_item_click)
            if self.element_type and name == self.element_type:
                item.Checked = True

    def on_item_click(self, sender, event_info):
        self.element_type = sender.Text
        ghenv.Component.ExpireSolution(True)
