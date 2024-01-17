from ghpythonlib.componentbase import executingcomponent as component
from Grasshopper.Kernel.GH_RuntimeMessageLevel import Warning

from compas_timber.connections import ConnectionSolver
from compas_timber.connections import JointTopology
from compas_timber.ghpython import JointDefinition
from compas_timber.ghpython import CategoryRule
from compas_timber.ghpython import TopologyRule
from compas_timber.ghpython import DirectRule


class AutotomaticJoints(component):
    def RunScript(self, Beams, Rules, MaxDistance):
        if not Beams:
            self.AddRuntimeMessage(Warning, "Input parameter Beams failed to collect data")
        if not Rules:
            self.AddRuntimeMessage(Warning, "Input parameter Rules failed to collect data")
        if not (Beams and Rules):
            return

        if not isinstance(Rules, list):
            Rules = [Rules]
        rules = [r for r in Rules if r is not None]

        solver = ConnectionSolver()
        found_pairs = solver.find_intersecting_pairs(Beams, rtree=True, max_distance=MaxDistance)
        Joints = []
        Info = []
        # rules have to be resolved into joint definitions
        topo_rules = {}
        cat_rules = []
        direct_rules = []

        for r in rules:  # separate category and topo and direct joint rules
            if isinstance(r, TopologyRule):
                topo_rules[r.topology_type] = r
            elif isinstance(r, CategoryRule):
                cat_rules.append(r)
            if isinstance(r, DirectRule):
                direct_rules.append(r)

        for pair in found_pairs:
            beam_a, beam_b = pair
            detected_topo, beam_a, beam_b = solver.find_topology(beam_a, beam_b, max_distance=MaxDistance)
            pair_joined = False

            if detected_topo == JointTopology.TOPO_UNKNOWN:
                continue

            for rule in direct_rules:  # apply direct rules first
                if rule.comply(pair):
                    Joints.append(JointDefinition(rule.joint_type, [beam_a, beam_b], **rule.kwargs))
                    pair_joined = True
                    break

            if not pair_joined:  # if no direct rule applies, apply category rules next
                for rule in cat_rules:
                    if not rule.comply(pair):
                        continue
                    if rule.joint_type.SUPPORTED_TOPOLOGY != detected_topo:
                        msg = "Conflict detected! Beams: {}, {} meet with topology: {} but rule assigns: {}"
                        Info.append(
                            msg.format(beam_a, beam_b, JointTopology.get_name(detected_topo), rule.joint_type.__name__)
                        )
                        continue
                    # sort by category to allow beam role by order (main beam first, cross beam second)
                    beam_a, beam_b = rule.reorder([beam_a, beam_b])
                    Joints.append(JointDefinition(rule.joint_type, [beam_a, beam_b], **rule.kwargs))
                    break  # first matching rule

                else:  # no category rule applies, apply topology rules
                    Joints.append(
                        JointDefinition(
                            topo_rules[detected_topo].joint_type, [beam_a, beam_b], **topo_rules[detected_topo].kwargs
                        )
                    )

        return Joints, Info
