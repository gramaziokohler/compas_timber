from compas.scene import Scene
from compas.tolerance import TOL
from ghpythonlib.componentbase import executingcomponent as component
from Grasshopper.Kernel.GH_RuntimeMessageLevel import Warning

from compas_timber.connections import BeamJoinningError
from compas_timber.connections import JointTopology
from compas_timber.connections import LMiterJoint
from compas_timber.connections import TButtJoint
from compas_timber.connections import XHalfLapJoint
from compas_timber.design import DebugInfomation
from compas_timber.design import JointRule
from compas_timber.model import TimberModel

JOINT_DEFAULTS = {
    JointTopology.TOPO_X: XHalfLapJoint,
    JointTopology.TOPO_T: TButtJoint,
    JointTopology.TOPO_L: LMiterJoint,
}

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
            element.reset()
            Model.add_element(element)

        joints, unmatched_pairs = JointRule.joints_from_beams_and_rules(Model.beams, JointRules)

        if unmatched_pairs:
            for pair in unmatched_pairs:
                self.AddRuntimeMessage(
                    Warning, "No joint rule found for beams {} and {}".format(list(pair)[0].key, list(pair)[1].key)
                )  # TODO: add to debug_info

        if joints:
            # apply reversed. later joints in orginal list override ealier ones
            for joint in joints[::-1]:
                try:
                    joint.joint_type.create(Model, *joint.beams, **joint.kwargs)
                except BeamJoinningError as bje:
                    debug_info.add_joint_error(bje)

        # applies extensions and features resulting from joints
        Model.process_joinery()

        if Features:
            features = [f for f in Features if f is not None]
            for f_def in features:
                for element in f_def.elements:
                    element.add_features(f_def.feature)

        Geometry = None
        scene = Scene()
        for element in Model.elements():
            if CreateGeometry:
                scene.add(element.geometry)
                if element.debug_info:
                    debug_info.add_feature_error(element.debug_info)
            else:
                scene.add(element.blank)

        if debug_info.has_errors:
            self.AddRuntimeMessage(Warning, "Error found during joint creation. See DebugInfo output for details.")

        Geometry = scene.draw()
        return Model, Geometry, debug_info
