from compas.scene import Scene
from compas.tolerance import TOL
from ghpythonlib.componentbase import executingcomponent as component
from Grasshopper.Kernel.GH_RuntimeMessageLevel import Warning

from compas_timber.connections import BeamJoinningError
from compas_timber.connections import ConnectionSolver
from compas_timber.connections import JointTopology
from compas_timber.connections import LMiterJoint
from compas_timber.connections import TButtJoint
from compas_timber.connections import XHalfLapJoint
from compas_timber.design import CategoryRule
from compas_timber.design import DebugInfomation
from compas_timber.design import DirectRule
from compas_timber.design import JointDefinition
from compas_timber.design import TopologyRule
from compas_timber.model import TimberModel

JOINT_DEFAULTS = {
    JointTopology.TOPO_X: XHalfLapJoint,
    JointTopology.TOPO_T: TButtJoint,
    JointTopology.TOPO_L: LMiterJoint,
}


class ModelComponent(component):
    def get_joints_from_rules(self, beams, rules, topologies):
        if not isinstance(rules, list):
            rules = [rules]
        rules = [r for r in rules if r is not None]

        joints = []
        # rules have to be resolved into joint definitions
        topo_rules = {}
        cat_rules = []
        direct_rules = []

        # TODO: refactor this into some kind of a rule reloving class/function
        for r in rules:  # separate category and topo and direct joint rules
            if isinstance(r, TopologyRule):
                if topo_rules.get(r.topology_type, None):  # if rule for this Topo exists
                    if (r.joint_type != JOINT_DEFAULTS[r.topology_type]) or (
                        len(r.kwargs) != 0
                    ):  # if this rule is NOT default
                        topo_rules[r.topology_type] = r
                else:
                    topo_rules[r.topology_type] = r
            elif isinstance(r, CategoryRule):
                cat_rules.append(r)
            if isinstance(r, DirectRule):
                direct_rules.append(r)

        for topo in topologies:
            beam_a = topo["beam_a"]
            beam_b = topo["beam_b"]
            detected_topo = topo["detected_topo"]
            pair = beam_a, beam_b
            pair_joined = False

            if detected_topo == JointTopology.TOPO_UNKNOWN:
                continue

            for rule in direct_rules:  # apply direct rules first
                if rule.comply(pair):
                    joints.append(JointDefinition(rule.joint_type, rule.beams, **rule.kwargs))
                    pair_joined = True
                    break

            if not pair_joined:  # if no direct rule applies, apply category rules next
                for rule in cat_rules:
                    if not rule.comply(pair):
                        continue
                    if rule.joint_type.SUPPORTED_TOPOLOGY != detected_topo:
                        msg = "Conflict detected! Beams: {}, {} meet with topology: {} but rule assigns: {}"
                        self.AddRuntimeMessage(
                            Warning,
                            msg.format(
                                beam_a.guid,
                                beam_b.guid,
                                JointTopology.get_name(detected_topo),
                                rule.joint_type.__name__,
                            ),
                        )
                        continue
                    if rule.topos and detected_topo not in rule.topos:
                        msg = "Conflict detected! Beams: {}, {} meet with topology: {} but rule allows: {}"
                        self.AddRuntimeMessage(
                            Warning,
                            msg.format(
                                beam_a.guid,
                                beam_b.guid,
                                JointTopology.get_name(detected_topo),
                                [JointTopology.get_name(topo) for topo in rule.topos],
                            ),
                        )
                        continue
                    # sort by category to allow beam role by order (main beam first, cross beam second)
                    beam_a, beam_b = rule.reorder([beam_a, beam_b])
                    joints.append(JointDefinition(rule.joint_type, [beam_a, beam_b], **rule.kwargs))
                    break  # first matching rule

                else:  # no category rule applies, apply topology rules
                    if detected_topo not in topo_rules:
                        continue
                    else:
                        joints.append(
                            JointDefinition(
                                topo_rules[detected_topo].joint_type,
                                [beam_a, beam_b],
                                **topo_rules[detected_topo].kwargs
                            )
                        )
        return joints

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
            if element is None:
                continue
            element.remove_features()
            if hasattr(element, "remove_blank_extension"):
                element.remove_blank_extension()
            element.debug_info = []
            Model.add_element(element)

        topologies = []
        solver = ConnectionSolver()
        found_pairs = solver.find_intersecting_pairs(Model.beams, rtree=True, max_distance=MaxDistance)
        for pair in found_pairs:
            beam_a, beam_b = pair
            detected_topo, beam_a, beam_b = solver.find_topology(beam_a, beam_b, max_distance=MaxDistance)
            if not detected_topo == JointTopology.TOPO_UNKNOWN:
                topologies.append({"detected_topo": detected_topo, "beam_a": beam_a, "beam_b": beam_b})
        Model.set_topologies(topologies)

        joints = self.get_joints_from_rules(Model.beams, JointRules, topologies)

        if joints:
            handled_beams = []
            joints = [j for j in joints if j is not None]
            # apply reversed. later joints in orginal list override ealier ones
            for joint in joints[::-1]:
                beams_to_pair = joint.beams
                beam_pair_ids = set([id(beam) for beam in beams_to_pair])
                if beam_pair_ids in handled_beams:
                    continue
                try:
                    joint.joint_type.create(Model, *beams_to_pair, **joint.kwargs)
                except BeamJoinningError as bje:
                    debug_info.add_joint_error(bje)
                else:
                    handled_beams.append(beam_pair_ids)

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
