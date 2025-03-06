from ghpythonlib.componentbase import executingcomponent as component

from compas_timber.planning import DeferredLabel


class LabelBeamsComponent(component):
    def RunScript(self, elements, base_string=None, char_to_replace=None, attributes=None, text_height=None, ref_side_index=0):
        f_defs = []
        if not elements:
            return
        if len(list(elements)) == len(base_string):
            for st, el in zip(base_string, elements):
                f_defs.append(DeferredLabel([el], text=st, text_height=text_height, ref_side_index=ref_side_index))
        else:
            if base_string:
                base_string = base_string[0]
            f_defs.append(
                DeferredLabel(elements, attributes=attributes, base_string=base_string, char_to_replace=char_to_replace, text_height=text_height, ref_side_index=ref_side_index)
            )
        return f_defs
