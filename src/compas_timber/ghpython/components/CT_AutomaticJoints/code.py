from ghpythonlib.componentbase import executingcomponent as component
from Grasshopper.Kernel.GH_RuntimeMessageLevel import Warning

from compas_timber.connections import ConnectionSolver
from compas_timber.connections import JointTopology
from compas_timber.ghpython import JointDefinition


class AutotomaticJoints(component):
    def RunScript(self, beams, rules, max_distance):
        if not beams:
            self.AddRuntimeMessage(Warning, "Input parameter beams failed to collect data")
        if not rules:
            self.AddRuntimeMessage(Warning, "Input parameter rules failed to collect data")
        if not (beams and rules):
            return

        if not isinstance(rules, list):
            rules = [rules]
        rules = [r for r in rules if r is not None]

        solver = ConnectionSolver()
        found_pairs = solver.find_intersecting_pairs(beams, rtree=True)
        joint_defs = []
        info = []
        # rules have to be resolved into joint definitions
        for pair in found_pairs:
            beam_a, beam_b = pair
            detected_topo, beam_a, beam_b = solver.find_topology(beam_a, beam_b, max_distance=max_distance)

            if detected_topo == JointTopology.TOPO_UNKNOWN:
                continue

            for rule in rules:
                if not rule.comply(pair):
                    continue
                if rule.joint_type.SUPPORTED_TOPOLOGY != detected_topo:
                    msg = "Conflict detected! Beams: {}, {} meet with topology: {} but rule assigns: {}"
                    info.append(
                        msg.format(beam_a, beam_b, JointTopology.get_name(detected_topo), rule.joint_type.__name__)
                    )
                    continue
                # sort by category to allow beam role by order (main beam first, cross beam second)
                beam_a, beam_b = rule.reorder([beam_a, beam_b])
                joint_defs.append(JointDefinition(rule.joint_type, [beam_a, beam_b]))
                break  # first matching rule

        return joint_defs, info
