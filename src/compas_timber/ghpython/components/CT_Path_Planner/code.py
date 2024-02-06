from compas.scene import Scene
from ghpythonlib.componentbase import executingcomponent as component
from Grasshopper.Kernel.GH_RuntimeMessageLevel import Warning


from compas_timber.planning import TimberAssemblyPlanner
from compas.geometry import Frame
from compas.geometry import Point
from compas.geometry import Vector

class MyComponent(component):

    def RunScript(self, robot, assembly, pickup, group):
        pickup_frame = Frame(Point(8.0,4.0,1.0), Vector(1.0,0.0,0.0), Vector(0.0,1.0,0.0))
        planner = TimberAssemblyPlanner(robot, assembly, pickup_frame, group = group )

        trajectories = []
        planner.robot.configuration = planner.safe_configuation
        for i in [6,9]:
            trajectories.extend(planner.get_trajectories_beam(assembly.beams[i]))

        return trajectories
