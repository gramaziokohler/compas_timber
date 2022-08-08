"""
TODO: Add description

COMPAS Timber v0.1.0
"""
from compas_rhino.conversions import RhinoPlane
from ghpythonlib.componentbase import executingcomponent as component


class TestComponent(component):
    def RunScript(self, x, y):
        a = "Hello Grasshopper"
        return (a,)
