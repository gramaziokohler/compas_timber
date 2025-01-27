from ghpythonlib.componentbase import executingcomponent as component
from compas_timber.fabrication import Text
from compas.scene import Scene

labels = []

class MyComponent(component):
    def RunScript(self, model, base_string, char_to_replace, attributes, text_size):
        model = model.copy()
        if labels:
            for element in model.beams:
                for label in labels:
                    if label in element.features:
                        print("removing text")
                        element.remove_features(label)
                        labels.remove(label)
        scene = Scene()
        for element in model.beams:
            if char_to_replace and attributes:
                text = base_string
                frags = text.split(char_to_replace)

                if text[0] == char_to_replace:
                    new_text = getattr(element, attributes[0])
                    for frag, attribute in zip(frags, attributes[1:]):
                        new_text += [frag, getattr(element, attribute)]
                else:
                    new_text = frags[0]
                    for attribute, frag in zip(attributes, frags[1:]):
                        new_text += str(getattr(element, attribute)) + frag

                tp = Text.label_element(element, new_text, text_size)

            else:
                tp = Text.label_element(element, base_string, text_size)
            labels.append(tp)

            for crv in tp.draw_string_on_element(element):
                scene.add(crv)
        return scene.draw()
