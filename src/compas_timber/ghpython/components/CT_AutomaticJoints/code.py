from ghpythonlib.componentbase import executingcomponent as component
from Grasshopper.Kernel.GH_RuntimeMessageLevel import Warning

from compas_timber.connections import ConnectionSolver
from compas_timber.ghpython import JointDefinition


class AutotomaticJoints(component):

    def RunScript(self, beams, rules, overrides, max_distance):
        if not beams:
            return

        solver = ConnectionSolver()
        found_pairs = solver.find_intersecting_pairs(beams)
        not_handled = []
        joint_defs= []

        # overrides are already joint definitions
        if overrides:
            for od in overrides:
                for pair in found_pairs:
                    if od.match(pair):
                        joint_defs.append(od)
                    else:
                        not_handled.append(pair)
            found_pairs = not_handled

        if not rules:
            return

        # rules have to be resolved into joint definitions
        for pair in found_pairs:
            beam_a, beam_b = pair
            detected_topo, beam_a, beam_b = solver.find_topology(beam_a, beam_b, max_distance=max_distance)
            for rule in rules:
                if not rule.comply(pair):
                    continue
                if rule.joint_type.SUPPORTED_TOPOLOGY != detected_topo:
                    self.AddRuntimeMessage(Warning, "Rule and found topology don't match")
                    continue
                # find_topology reorders beams if needed
                joint_defs.append(JointDefinition(rule.joint_type, [beam_a, beam_b]))
                break  # first matching rule

        return joint_defs, None
