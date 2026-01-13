# r: compas_timber>=1.0.1
"""Creates an Model"""

import Grasshopper
import Rhino
import System
from compas.scene import Scene
from compas.tolerance import TOL
from compas.tolerance import Tolerance

from compas_timber.design import DebugInfomation
from compas_timber.design import JointRuleSolver
from compas_timber.elements import Beam
from compas_timber.elements import Plate
from compas_timber.errors import FeatureApplicationError
from compas_timber.ghpython import error
from compas_timber.ghpython import warning
from compas_timber.model import TimberModel

# workaround for https://github.com/gramaziokohler/compas_timber/issues/280
TOL.absolute = 1e-6


class ModelComponent(Grasshopper.Kernel.GH_ScriptInstance):
    @property
    def component(self):
        return ghenv.Component  # type: ignore

    def RunScript(
        self,
        Elements: System.Collections.Generic.List[object],
        Containers: System.Collections.Generic.List[object],
        JointRules: System.Collections.Generic.List[object],
        Features: System.Collections.Generic.List[object],
        MaxDistance: float,
        CreateGeometry: bool,
    ):
        # this used to be default behavior in Rhino7.. I think..
        Elements = Elements or []
        Containers = Containers or []
        JointRules = JointRules or []
        Features = Features or []

        if not Elements:
            warning(self.component, "Input parameter Beams failed to collect data")
        if not JointRules:
            warning(self.component, "Input parameter JointRules failed to collect data")
        if not (Elements or Containers):  # shows beams even if no joints are found
            return
        if MaxDistance is None:
            MaxDistance = TOL.ABSOLUTE  # compared to calculted distance, so shouldn't be just 0.0

        tol = self.get_tol()
        Model = TimberModel(tolerance=tol)
        debug_info = DebugInfomation()

        ##### Adding elements #####
        self.add_elements_to_model(Model, Elements)

        ##### Handle joinery #####
        # checks elements compatibility and generates Joints
        JointRules = [j for j in JointRules if j is not None]

        solver = JointRuleSolver(JointRules, max_distance=MaxDistance)
        joint_errors, _ = solver.apply_rules_to_model(Model)  # TODO: figure out best way to pass out unjoined_clusters

        for je in joint_errors:
            debug_info.add_joint_error(je)

        # applies extensions and features resulting from joints
        bje = Model.process_joinery()
        if bje:
            debug_info.add_joint_error(bje)

        ##### Handle user features #####
        if Features:
            feature_errors = self.handle_features(Features)
            debug_info.add_feature_error(feature_errors)

        ##### Visualization #####
        Geometry, errors = self.handle_geometry(Model, CreateGeometry)
        for geo_error in errors:
            debug_info.add_feature_error(geo_error)

        ##### Error Handling #####
        if debug_info.has_errors:
            warning(self.component, "Error found during joint creation. See DebugInfo output for details.")

        return Model, Geometry, debug_info

    def get_tol(self):
        units = Rhino.RhinoDoc.ActiveDoc.GetUnitSystemName(True, True, True, True)
        if units == "m":
            return Tolerance(unit="M", absolute=1e-6, relative=1e-6)
        elif units == "mm":
            return Tolerance(unit="MM", absolute=1e-3, relative=1e-3)
        else:
            error(self.component, f"Unsupported unit: {units}")
            return

    def add_elements_to_model(self, model, elements, containers):
        """Adds elements to the model and groups them by panel."""
        elements = [e for e in elements if e is not None]
        for element in elements:
            element.reset()
            model.add_element(element)

        containers = [c for c in containers if c is not None]

        for c_def in containers:
            panel = c_def.panel
            model.add_element(panel)

    def handle_features(self, features):
        feature_errors = []
        features = [f for f in features if f is not None]
        for f_def in features:
            if not f_def.elements:
                warning(self.component, "Features defined in model must have elements defined. Features without elements will be ignored")
                continue

            for element in f_def.elements:
                try:
                    element.add_features(f_def.feature_from_element(element))
                except FeatureApplicationError as ex:
                    feature_errors.append(ex)
        return feature_errors

    def handle_geometry(self, Model, CreateGeometry):
        scene = Scene()
        errors = []
        for element in Model.elements():
            if CreateGeometry:
                scene.add(element.geometry)
                if getattr(element, "debug_info", False):
                    errors.append(element.debug_info)
            else:
                if isinstance(element, Beam):
                    scene.add(element.blank)
                elif isinstance(element, Plate):
                    scene.add(element.shape)
                else:
                    scene.add(element.geometry)
        return scene.draw(), errors
