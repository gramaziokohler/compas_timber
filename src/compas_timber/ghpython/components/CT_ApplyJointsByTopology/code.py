from ghpythonlib.componentbase import executingcomponent as component
from Grasshopper.Kernel.GH_RuntimeMessageLevel import Warning

from compas_timber.connections import ConnectionSolver
from compas_timber.connections import JointTopology
from compas_timber.ghpython import JointDefinition

from compas_timber.connections import LButtJoint
from compas_timber.connections import LMiterJoint
from compas_timber.connections import TButtJoint
from compas_timber.connections import XHalfLapJoint
from compas_timber.connections import FrenchRidgeLapJoint


class MyComponent(component):
    def RunScript(self, Beams, L, T, X, MaxDistance):
        MAP = {
            "T-Butt": TButtJoint,
            "L-Miter": LMiterJoint,
            "L-Butt": LButtJoint,
            "French Ridge Lap": FrenchRidgeLapJoint,
            "X-HalfLap": XHalfLapJoint,
        }

        max_dist = MaxDistance or 1
        solver = ConnectionSolver()
        found_pairs = solver.find_intersecting_pairs(Beams, rtree=True, max_distance=max_dist)
        Joints = []
        Info = []

        for pair in found_pairs:
            beam_a, beam_b = pair
            detected_topo, beam_a, beam_b = solver.find_topology(beam_a, beam_b, max_distance=max_dist)
            flip_beams = False
            if detected_topo == JointTopology.TOPO_UNKNOWN:
                continue
            elif detected_topo == JointTopology.TOPO_L:
                joint_type = MAP.get(str(L)) or LMiterJoint
                if joint_type == LButtJoint:
                    if beam_a.width * beam_a.height > beam_b.width * beam_b.height:
                        flip_beams = True
            elif detected_topo == JointTopology.TOPO_T:
                joint_type = MAP.get(str(T)) or TButtJoint
            elif detected_topo == JointTopology.TOPO_X:
                joint_type = MAP.get(str(X)) or XHalfLapJoint

            if flip_beams:
                Joints.append(JointDefinition(joint_type, [beam_b, beam_a]))
            else:
                Joints.append(JointDefinition(joint_type, [beam_a, beam_b]))
            msg = "Beams: {}, {} meet with topology: {} and use joint: {}"
            Info.append(msg.format(beam_a, beam_b, JointTopology.get_name(detected_topo), joint_type.__name__))
        return Joints, Info
