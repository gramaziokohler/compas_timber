from compas.scene import Scene
from ghpythonlib.componentbase import executingcomponent as component
from Grasshopper.Kernel.GH_RuntimeMessageLevel import Warning
from System.Windows.Forms import ToolStripSeparator

from compas_timber.ghpython.ghcomponent_helpers import rename_gh_output


class ShowBeamsByCategory(component):
    def __init__(self):
        super(ShowBeamsByCategory, self).__init__()
        self.beam_type = None
        if ghenv.Component.Params.Output[0].NickName == "type":
            self.joint_type = None
        else:
            self.beam_type = ghenv.Component.Params.Output[0].NickName

    def RunScript(self, model):
        self.names = set(element.attributes.get("category") for element in model.elements())
        self.names.remove(None)
        if not self.beam_type:
            ghenv.Component.Message = "Select beam type from context menu (right click)"
            self.AddRuntimeMessage(Warning, "Select beam type from context menu (right click)")
            return None
        else:
            ghenv.Component.Message = self.beam_type
            scene = Scene()
            for beam in model.beams:
                if beam.attributes["category"] == self.beam_type:
                    scene.add(beam.geometry)
            return scene.draw()

    def AppendAdditionalMenuItems(self, menu):
        if not self.RuntimeMessages(Warning):
            menu.Items.Add(ToolStripSeparator())
        for name in self.names:
            item = menu.Items.Add(name, None, self.on_item_click)
            if self.beam_type and name == self.beam_type:
                item.Checked = True

    def on_item_click(self, sender, event_info):
        self.beam_type = str(sender)
        rename_gh_output(self.beam_type, 0, ghenv)
        ghenv.Component.ExpireSolution(True)
