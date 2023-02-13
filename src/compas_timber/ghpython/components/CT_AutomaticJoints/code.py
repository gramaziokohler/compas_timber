from ghpythonlib.componentbase import executingcomponent as component
from Grasshopper.Kernel.GH_RuntimeMessageLevel import Warning

from compas_timber.connections import ConnectionSolver
from compas_timber.ghpython import JointDefinition


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
        found_pairs = solver.find_intersecting_pairs(Beams, rtree=True)
        JointDefs = []
        Info = []
        # rules have to be resolved into joint definitions
        for pair in found_pairs:
            beam_a, beam_b = pair
            detected_topo, beam_a, beam_b = solver.find_topology(beam_a, beam_b, max_distance=MaxDistance)
            for rule in rules:
                if not rule.comply(pair):
                    continue
                if rule.joint_type.SUPPORTED_TOPOLOGY != detected_topo:
                    msg = "Conflict detected! Beams: {}, {} meet with topology: {} but rule assigns: {}"
                    Info.append(msg.format(beam_a.key, beam_b.key, detected_topo, rule.joint_type.__name__))
                    continue
                # sort by category to allow beam role by order (main beam first, cross beam second)
                beam_a, beam_b = rule.reorder([beam_a, beam_b])
                JointDefs.append(JointDefinition(rule.joint_type, [beam_a, beam_b]))
                break  # first matching rule

        return JointDefs, Info
