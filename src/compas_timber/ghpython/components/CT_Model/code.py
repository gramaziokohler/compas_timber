from compas.scene import Scene
from compas.tolerance import TOL
from ghpythonlib.componentbase import executingcomponent as component
from Grasshopper.Kernel.GH_RuntimeMessageLevel import Warning

from compas_timber.connections import JointTopology
from compas_timber.connections import LMiterJoint
from compas_timber.connections import TButtJoint
from compas_timber.connections import XLapJoint
from compas_timber.design import DebugInfomation
from compas_timber.design import JointRule
from compas_timber.design import WallPopulator
from compas_timber.elements import Beam
from compas_timber.elements import Plate
from compas_timber.errors import FeatureApplicationError
from compas_timber.model import TimberModel

JOINT_DEFAULTS = {
    JointTopology.TOPO_X: XLapJoint,
    JointTopology.TOPO_T: TButtJoint,
    JointTopology.TOPO_L: LMiterJoint,
}

# workaround for https://github.com/gramaziokohler/compas_timber/issues/280
TOL.absolute = 1e-6


class ModelComponent(component):
    def RunScript(self, Elements, Containers, JointRules, Features, MaxDistance, CreateGeometry):
        if not Elements:
            self.AddRuntimeMessage(Warning, "Input parameter Beams failed to collect data")
        if not JointRules:
            self.AddRuntimeMessage(Warning, "Input parameter JointRules failed to collect data")
        if not (Elements or Containers):  # shows beams even if no joints are found
            return
        if MaxDistance is None:
            MaxDistance = TOL.ABSOLUTE  # compared to calculted distance, so shouldn't be just 0.0

        # clear Nones
        Containers = [c for c in Containers if c is not None]

        Model = TimberModel()
        debug_info = DebugInfomation()

        ##### Adding elements #####
        for element in Elements:
            # prepare elements for downstream processing
            element.reset()
            Model.add_element(element)

        for index, c_def in enumerate(Containers):
            slab = c_def.slab
            Model.add_group_element(slab, name=slab.name + str(index))

        Model.connect_adjacent_walls()

        ##### Wall populating #####
        config_sets = [c_def.config_set for c_def in Containers]
        populators = []
        if any(config_sets):
            populators = WallPopulator.from_model(Model, config_sets)

        handled_pairs = []
        wall_joint_definitions = []
        for populator, slab in zip(populators, Model.slabs):
            elements = populator.create_elements()
            Model.add_elements(elements, parent=slab.name)
            joint_definitions = populator.create_joint_definitions(elements, MaxDistance)
            wall_joint_definitions.extend(joint_definitions)
            for j_def in joint_definitions:
                element_a, element_b = j_def.elements
                handled_pairs.append({element_a, element_b})

        ##### Handle joinery #####
        joint_defs, unmatched_pairs = JointRule.joints_from_beams_and_rules(Model.beams, JointRules, MaxDistance, handled_pairs=handled_pairs)
        if unmatched_pairs:
            for pair in unmatched_pairs:
                self.AddRuntimeMessage(Warning, "No joint rule found for beams {} and {}".format(list(pair)[0].key, list(pair)[1].key))  # TODO: add to debug_info

        if wall_joint_definitions:
            joint_defs += wall_joint_definitions

        # apply reversed. later joints in orginal list override ealier ones
        for joint_def in joint_defs[::-1]:
            joint_def.joint_type.create(Model, *joint_def.elements, **joint_def.kwargs)

        # checks elements compatibility and applies extensions and features resulting from joints
        bje = Model.process_joinery()
        if bje:
            debug_info.add_joint_error(bje)

        ##### Handle user features #####
        if Features:
            feature_errors = []
            features = [f for f in Features if f is not None]
            for f_def in features:
                if not f_def.elements:
                    self.AddRuntimeMessage(Warning, "Features defined in model must have elements defined. Features without elements will be ignored")
                    continue

                for element in f_def.elements:
                    try:
                        element.add_features(f_def.feature_from_element(element))
                    except FeatureApplicationError as ex:
                        feature_errors.append(ex)

            for error in feature_errors:
                debug_info.add_feature_error(error)

        ##### Visualization #####
        Geometry = None
        scene = Scene()
        for element in Model.elements():
            if CreateGeometry:
                scene.add(element.geometry)
                if getattr(element, "debug_info", False):
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
