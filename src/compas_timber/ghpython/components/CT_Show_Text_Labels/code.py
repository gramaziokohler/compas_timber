# flake8: noqa
from ghpythonlib.componentbase import executingcomponent as component
from Grasshopper.Kernel.Data import GH_Path

from compas_rhino.conversions import frame_to_rhino
from compas_timber.fabrication import Text

from Rhino.DocObjects import TextHorizontalAlignment, TextVerticalAlignment
from System.Drawing import Color


class ShowTextLabels(component):
    def RunScript(self, model):
        self.label_data = []
        for element in model.elements():
            for feature in element.features:
                if isinstance(feature, Text):
                    frame = element.ref_sides[feature.ref_side_index]
                    frame.point = element.side_as_surface(feature.ref_side_index).point_at(feature.start_x, feature.start_y)
                    text_data = {"frame": frame_to_rhino(frame)}
                    text_data["height"] = feature.text_height
                    text_data["text"] = feature.text
                    text_data["vertical_alignment"] = map_vert_alignment_to_rhino(feature.alignment_vertical)
                    text_data["horizontal_alignment"] = map_hori_alignment_to_rhino(feature.alignment_horizontal)
                    self.label_data.append(text_data)

    def DrawViewportWires(self, arg):
        if self.Locked:
            return
        col = Color.FromArgb(255, 0, 0, 0)
        for t in self.label_data:
            arg.Display.Draw3dText(t["text"], col, t["frame"], t["height"], "SLF-RHN Architect", False, False, t["horizontal_alignment"], t["vertical_alignment"])


def map_vert_alignment_to_rhino(ct_alignment):
    if ct_alignment == "top":
        return TextVerticalAlignment.Top
    elif ct_alignment == "center":
        return TextVerticalAlignment.Middle
    elif ct_alignment == "bottom":
        return TextVerticalAlignment.Bottom


def map_hori_alignment_to_rhino(ct_alignment):
    if ct_alignment == "left":
        return TextHorizontalAlignment.Left
    elif ct_alignment == "center":
        return TextHorizontalAlignment.Center
    elif ct_alignment == "right":
        return TextHorizontalAlignment.Right
