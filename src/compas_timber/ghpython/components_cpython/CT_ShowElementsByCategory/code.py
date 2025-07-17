# r: compas_timber>=0.15.3
# flake8: noqa
import Grasshopper
from compas.scene import Scene
from System.Windows.Forms import ToolStripSeparator

from compas_timber.ghpython.ghcomponent_helpers import rename_gh_output


class ShowElementsByCategory(Grasshopper.Kernel.GH_ScriptInstance):
    def __init__(self):
        super(ShowElementsByCategory, self).__init__()
        self.element_type = None
        if ghenv.Component.Params.Output[0].NickName == "elements":
            self.joint_type = None
        else:
            self.element_type = ghenv.Component.Params.Output[0].NickName

    def RunScript(self, model):
        self.names = set(element.attributes.get("category") for element in model.elements())
        self.names.remove(None)
        if not self.element_type:
            ghenv.Component.Message = "Select element type from context menu (right click)"
            ghenv.Component.AddRuntimeMessage(Grasshopper.Kernel.GH_RuntimeMessageLevel.Warning, "Select element type from context menu (right click)")
            return None
        else:
            ghenv.Component.Message = self.element_type
            scene = Scene()
            for beam in model.beams:
                if beam.attributes["category"] == self.element_type:
                    scene.add(beam.geometry)
            return scene.draw()

    def AppendAdditionalMenuItems(self, menu):
        if not self.RuntimeMessages(Warning):
            menu.Items.Add(ToolStripSeparator())
        for name in self.names:
            item = menu.Items.Add(name, None, self.on_item_click)
            if self.element_type and name == self.element_type:
                item.Checked = True

    def on_item_click(self, sender, event_info):
        self.element_type = str(sender)
        rename_gh_output(self.element_type, 0, ghenv)
        ghenv.Component.ExpireSolution(True)
