from ghpythonlib.componentbase import executingcomponent as component
from Grasshopper.Kernel.GH_RuntimeMessageLevel import Warning

from compas.scene import Scene
from compas_timber.assembly import TimberAssembly
from compas_timber.consumers import BrepGeometryConsumer
from compas_timber.connections import ConnectionSolver
from compas_timber.connections import JointTopology
from compas_timber.ghpython import JointDefinition
from compas_timber.ghpython import CategoryRule
from compas_timber.ghpython import TopologyRule
from compas_timber.ghpython import DirectRule


class Assembly(component):
    def __init__(self):
        # maintains relationship of old_beam.id => new_beam_obj for referencing
        # lets us modify copies of the beams while referencing them using their old identities.
        self._beam_map = {}
        self.joints = []

    def _get_copied_beams(self, old_beams):
        """For the given old_beams returns their respective copies."""
        new_beams = []
        for beam in old_beams:
            new_beams.append(self._beam_map[id(beam)])
        return new_beams

    def process_joint_rules(self, beams, rules, max_distance=0):
        if not isinstance(rules, list):
            rules = [rules]
        rules = [r for r in rules if r is not None]

        solver = ConnectionSolver()
        found_pairs = solver.find_intersecting_pairs(beams, rtree=True, max_distance=max_distance)

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
            detected_topo, beam_a, beam_b = solver.find_topology(beam_a, beam_b, max_distance=max_distance)
            pair_joined = False

            if detected_topo == JointTopology.TOPO_UNKNOWN:
                continue

            for rule in direct_rules:  # apply direct rules first
                if rule.comply(pair):
                    self.joints.append(JointDefinition(rule.joint_type, [beam_a, beam_b], **rule.kwargs))
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
                    self.joints.append(JointDefinition(rule.joint_type, [beam_a, beam_b], **rule.kwargs))
                    break  # first matching rule

                else:  # no category rule applies, apply topology rules
                    if detected_topo not in topo_rules:
                        continue
                    else:
                        self.joints.append(
                            JointDefinition(
                                topo_rules[detected_topo].joint_type,
                                [beam_a, beam_b],
                                **topo_rules[detected_topo].kwargs
                            )
                        )

    def RunScript(self, Beams, JointRules, Features, MaxDistance, CreateGeometry):
        if not Beams:
            self.AddRuntimeMessage(Warning, "Input parameter Beams failed to collect data")
        if not JointRules:
            self.AddRuntimeMessage(Warning, "Input parameter JointRules failed to collect data")
        if not (Beams):  # shows beams even if no joints are found
            return

        self.process_joint_rules(Beams, JointRules, max_distance=MaxDistance)

        Assembly = TimberAssembly()
        self._beam_map = {}
        beams = [b for b in Beams if b is not None]
        for beam in beams:
            c_beam = beam.copy()
            Assembly.add_beam(c_beam)
            self._beam_map[id(beam)] = c_beam
        beams = Assembly.beams

        if self.joints:
            handled_beams = []
            joints = [j for j in self.joints if j is not None]
            # apply reversed. later joints in orginal list override ealier ones
            for joint in joints[::-1]:
                beams_to_pair = self._get_copied_beams(joint.beams)
                beam_pair_ids = set([id(beam) for beam in beams_to_pair])
                if beam_pair_ids in handled_beams:
                    continue
                joint.joint_type.create(Assembly, *beams_to_pair, **joint.kwargs)
                handled_beams.append(beam_pair_ids)

        if Features:
            features = [f for f in Features if f is not None]
            for f_def in features:
                beams_to_modify = self._get_copied_beams(f_def.beams)
                for beam in beams_to_modify:
                    beam.add_feature(f_def.feature)

        Geometry = None
        scene = Scene()
        if CreateGeometry:
            vis_consumer = BrepGeometryConsumer(Assembly)
            for result in vis_consumer.result:
                scene.add(result.geometry)

        Geometry = scene.redraw()

        return Assembly, Geometry
