from compas.scene import Scene
from ghpythonlib.componentbase import executingcomponent as component

from compas_timber.fabrication import Text


class LabelBeamsComponent(component):
    def RunScript(self, model, base_string=None, char_to_replace=None, attributes=None, text_size=None):
        scene = Scene()
        self.clear_labels(model)
        if len(list(model.beams)) == len(base_string):
            for st, b in zip(base_string, model.beams):
                tp = Text.label_element(b, st, text_size)
                for crv in tp.draw_string_on_element(b):
                    scene.add(crv)
        else:
            if base_string:
                base_string = base_string[0]
            for beam in model.beams:
                attribute_names = [attr for attr in attributes]
                if base_string and char_to_replace and attributes:
                    string_out = ""
                    for char in base_string:
                        if char != char_to_replace:
                            string_out += char
                        else:
                            string_out += str(getattr(beam, attribute_names.pop()))
                    tp = Text.label_element(beam, string_out, text_size)
                else:
                    tp = Text.label_element(beam, base_string, text_size)
                tp.is_label = True
                for crv in tp.draw_string_on_element(beam):
                    scene.add(crv)
        return scene.draw()

    def clear_labels(self, model):
        for element in model.beams:
            for feature in element.features:
                if getattr(feature, "is_label", None):
                    element.remove_features(feature)
