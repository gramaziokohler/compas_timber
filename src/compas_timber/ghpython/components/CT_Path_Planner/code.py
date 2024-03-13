from ghpythonlib.componentbase import executingcomponent as component
import Grasshopper, GhPython
import System
import Rhino
import rhinoscriptsyntax as rs
from compas_timber.planning import TimberAssemblyPlanner
from compas_timber.planning import AssemblyBeam
from compas.geometry import Frame
from compas.geometry import Point
from compas.geometry import Vector
from compas_ghpython import unload_modules

class TimberPlanner(component):

    trajectories = []

    def RunScript(self, robot, assembly, pickup, beams_to_plan, plan):
        pickup_frame = Frame(pickup.Origin, pickup.XAxis, pickup.YAxis)

        """here is where one could change the order of assembly, gripping position on beam, and target approach vector

        beam.attributes["approach_vector"] = Vector
            -this is the vector of movement to the final beam target position. Default is beam.frame.zaxis.

        beam.attributes["grab_frame"] = Frame
            -this is the position on the beam where the gripper should grab it. Default is beam.frame aligned Frame at beam.midpoint.

        the order of assembly is also manipulated here.
        """
        beams = assembly.beams
        beams.sort(key = lambda x: x.midpoint.z)
        for beam in beams:
            if beam.midpoint.z < 0.6:
                beam.attributes["approach_vector"] = -Vector.Zaxis()
                target = AssemblyBeam.get_face_most_ortho_to_vector(beam, -Vector.Zaxis())
                target = Frame(target.point, target.xaxis, -target.yaxis)
                beam.attributes["grab_frame"] = target


        """ Here is where the planning happens"""

        planner = TimberAssemblyPlanner(robot, assembly, pickup_frame)
        if plan:
            planner.plan_assembly(beams_to_plan)    # this is currently by assembly order, but could be changed to beam.key
            TimberPlanner.trajectories = planner.trajectory_list

        return TimberPlanner.trajectories
