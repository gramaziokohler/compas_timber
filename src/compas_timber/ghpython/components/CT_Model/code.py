from compas.scene import Scene
from compas.tolerance import TOL
from ghpythonlib.componentbase import executingcomponent as component
from Grasshopper.Kernel.GH_RuntimeMessageLevel import Warning

from compas_timber.design import DebugInfomation
from compas_timber.design import JointRule
from compas_timber.elements import Beam
from compas_timber.elements import Plate
from compas_timber.model import TimberModel

# workaround for https://github.com/gramaziokohler/compas_timber/issues/280
TOL.absolute = 1e-6


class ModelComponent(component):
    def RunScript(self, Elements, JointRules, Features, MaxDistance, CreateGeometry):
        if not Elements:
            self.AddRuntimeMessage(Warning, "Input parameter Beams failed to collect data")
        if not JointRules:
            self.AddRuntimeMessage(Warning, "Input parameter JointRules failed to collect data")
        if not (Elements):  # shows beams even if no joints are found
            return
        if MaxDistance is None:
            MaxDistance = TOL.ABSOLUTE  # compared to calculted distance, so shouldn't be just 0.0

        Model = TimberModel()
        debug_info = DebugInfomation()
        for element in Elements:
            # prepare elements for downstream processing
            element.reset(only_joinery_features=True)
            Model.add_element(element)

        joints, unmatched_pairs = JointRule.joints_from_beams_and_rules(
            Model.beams, JointRules, MaxDistance
        )  # TODO this is giving strange pairs that should not actually be joined. check.

        if unmatched_pairs:
            for pair in unmatched_pairs:
                self.AddRuntimeMessage(Warning, "No joint rule found for beams {} and {}".format(list(pair)[0].key, list(pair)[1].key))  # TODO: add to debug_info

        if joints:
            # apply reversed. later joints in orginal list override ealier ones
            for joint in joints[::-1]:
                joint.joint_type.create(Model, *joint.elements, **joint.kwargs)

        # checks elements compatibility and applies extensions and features resulting from joints
        bje = Model.process_joinery()
        if bje:
            debug_info.add_joint_error(bje)

        if Features:
            features = [f for f in Features if f is not None]
            for f_def in features:
                if not f_def.elements:
                    self.AddRuntimeMessage(Warning, "Features defined in model must have elements defined. Features without elements will be ignored")
                elif f_def.geometries:
                    for element in f_def.elements:
                        element.add_features(f_def.feature_from_element(element))

        scene = Scene()
        for element in Model.elements():
            direct_feats = element.attributes.get("BTLx", None)
            if direct_feats:
                element.add_features(direct_feats)
            if CreateGeometry:
                scene.add(element.geometry)
                if element.debug_info:
                    debug_info.add_feature_error(element.debug_info)
            else:
                if isinstance(element, Beam) or isinstance(element, Plate):
                    scene.add(element.blank)
                else:
                    scene.add(element.geometry)

        if debug_info.has_errors:
            self.AddRuntimeMessage(Warning, "Error found during joint creation. See DebugInfo output for details.")

        Geometry = scene.draw()
        return Model, Geometry, debug_info
