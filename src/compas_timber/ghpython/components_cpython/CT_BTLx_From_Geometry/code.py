# r: compas_timber>=0.15.3
# flake8: noqa
import inspect

import Grasshopper
import Rhino.Geometry as rg
import System
from compas.geometry import Line
from compas_rhino.conversions import plane_to_compas
from compas_rhino.conversions import polyline_to_compas

from compas_timber.fabrication import BTLxFromGeometryDefinition
from compas_timber.fabrication import BTLxProcessing
from compas_timber.ghpython import get_leaf_subclasses
from compas_timber.ghpython import manage_cpython_dynamic_params
from compas_timber.ghpython import rename_cpython_gh_output
from compas_timber.ghpython import warning
from compas_timber.ghpython import error
from compas_timber.ghpython import message

import rhinoscriptsyntax as rs


class BTLxFromGeometry(Grasshopper.Kernel.GH_ScriptInstance):
    def __init__(self):
        super(BTLxFromGeometry, self).__init__()
        self.classes = {}
        self.geometry_count = 0
        for cls in get_leaf_subclasses(BTLxProcessing):
            functions = inspect.getmembers(cls, predicate=inspect.ismethod)
            if "from_shapes_and_element" in [func[0] for func in functions]:
                self.classes[cls.__name__] = cls

        if ghenv.Component.Params.Output[0].NickName == "Features":
            self.processing_type = None
        else:
            self.processing_type = self.classes.get(ghenv.Component.Params.Output[0].NickName, None)

    @property
    def component(self):
        return ghenv.Component  # type: ignore

    def RunScript(self, elements: System.Collections.Generic.List[object], *args):
        if not self.processing_type:
            warning(self.component, "Select Process type from context menu (right click)")
            return None
        else:
            message(self.component, self.processing_type.__name__)
            for arg, arg_name in zip(args, self.arg_names()[0 : self.geometry_count]):
                if arg is None:
                    warning(self.component, f"Input parameter {arg_name} failed to collect data")

            geometries = []
            for geo, arg_name in zip(args, self.arg_names()[0 : self.geometry_count]):
                geo = rs.coercegeometry(geo)  # guid to geometry

                if isinstance(geo, rg.LineCurve):
                    geometries.append(Line(geo.PointAtStart, geo.PointAtEnd))
                elif isinstance(geo, rg.Plane):
                    geometries.append(plane_to_compas(geo))
                elif isinstance(geo, rg.PolylineCurve):
                    geometries.append(polyline_to_compas(geo.ToPolyline()))
                else:
                    error(self.component, f"Input parameter {arg_name} collect unusable data")

            if not geometries:
                warning(self.component, "no valid geometry collected")
                return

            kwargs = {"geometries": geometries}
            if elements:
                kwargs["elements"] = list(elements)
            for key, val in zip(self.arg_names()[self.geometry_count :], args[self.geometry_count :]):
                if val is not None:
                    kwargs[key] = val
            return BTLxFromGeometryDefinition(self.processing_type, **kwargs)

    def arg_names(self):
        names = inspect.getargspec(self.processing_type.from_shapes_and_element)[0][1:]
        count = 0
        for name in names:
            if name == "element":
                break
            else:
                count += 1
        self.geometry_count = count
        return [name for name in names if name != "element"]

    def AppendAdditionalMenuItems(self, menu):
        for name in self.classes.keys():
            item = menu.Items.Add(name, None, self.on_item_click)
            if self.processing_type and name == self.processing_type.__name__:
                item.Checked = True

    def on_item_click(self, sender, event_info):
        self.processing_type = self.classes[str(sender)]
        rename_cpython_gh_output(self.processing_type.__name__, 0, ghenv)
        manage_cpython_dynamic_params(self.arg_names(), ghenv, rename_count=0, permanent_param_count=1)
        ghenv.Component.ExpireSolution(True)
