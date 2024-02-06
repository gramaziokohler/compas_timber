import math
from compas.geometry import Frame
from compas.geometry import Vector
from compas.datastructures import Mesh

# import compas_fab
# from compas_fab.robots import AttachedCollisionMesh
# from compas_fab import Robot
from compas_fab.robots import JointConstraint
from compas_fab.robots import PlanningScene
from compas_fab.robots import CollisionMesh
from compas_fab.robots import AttachedCollisionMesh





from compas.geometry import Transformation
from compas.geometry import Translation
from compas_timber.assembly import TimberAssembly
from compas_timber.parts import beam

class TimberAssemblyPlanner(object):

    TOLERANCE_POSITION = 0.001          # 1 mm tolerance on position
    TOLERANCE_AXES = [math.radians(1.0)]*3    # 1 degree tolerance per axis


    def __init__(self, robot, assembly,  pickup_base_frame, building_plan = None, scene_objects = None, group = None, planner_id = None):
        self.pickup_base_frame = pickup_base_frame
        self.robot = robot
        self.assembly = assembly
        self.building_plan = building_plan
        self.group = group or self.robot.main_group_name
        self.planner_id = str(planner_id) if planner_id else "RRTConnect"
        self.attached_collision_meshes = []
        self.path_constraints = []
        self.trajectories = []
        # self.current_configuration = self.safe_configuation
        self.robot_steps = {}
        self.scene_objects = [scene_objects]
        self.scene = PlanningScene(robot)
        for beam in self.assembly.beams:
            beam.attributes["is_built"] = False
            beam.attributes["is_planned"] = False
            beam.attributes["is_in_scene"] = False
        if scene_objects:
            for mesh in scene_objects:
                self.scene.add_collision_meshes(CollisionMesh(mesh, "scene_mesh"))


    def plan_robot_assembly(self, replan_index = 0):
        for index in range(replan_index, len(self.building_plan.steps)):
            step = self.building_plan.steps[index]
            if step["actor"] == "ROBOT":
                self.robot_steps[index] = self.plan_robot_step(step)


    def get_configurations(self, trajectories):
        configurations = []
        for trajectory in trajectories:
            for point in trajectory.points:
                config = self.robot.merge_group_with_full_configuration(point, self.safe_configuration, self.group)
                configurations.append(config)


    def plan_robot_step(self, step, path_constraints = None, group = None):
        self.path_constraints = list(path_constraints) if path_constraints else []
        self.path_constraints.extend(self.global_constraints)

        beam = self.assembly.beams[step["element_ids"][0]]
        return self.get_step_trajectories(beam)


    def get_step_trajectories(self, beam):
        """
        Plans the robot assembly process.

        Returns:
            dict: Dictionary of trajectories seaprated into `pickup`, `move`, and `retract` steps, each with a list of trajectories as value.
        """
        offset_vector = (self.pickup_base_frame.xaxis * (beam.length / 2.0)) + (self.pickup_base_frame.yaxis* (beam.width / 2.0)) + (self.pickup_base_frame.zaxis * beam.height)
        print(self.robot.forward_kinematics(self.current_configuration))
        pickup_frame = Frame(self.pickup_base_frame.point + offset_vector, self.pickup_base_frame.xaxis, self.pickup_base_frame.yaxis)
        target_frame = Frame(beam.midpoint, Vector.Xaxis(), -Vector.Yaxis())
        print("pickup_frame", pickup_frame)
        step_trajectories = {}
        step_trajectories["pickup"] = self.pickup_trajectories(pickup_frame)
        print("grab")

        self.grab_beam(beam, pickup_frame, target_frame)
        print("move")
        return step_trajectories
        step_trajectories["move"] = self.move_trajectories(target_frame)
        print("release")
        self.release_beam()
        print("retract")
        step_trajectories["retract"] = self.retract_trajectories()
        return step_trajectories


    def pickup_trajectories(self, pickup_frame):
        trajectories = []
        pickup_frame_offset = self.offset_frame(pickup_frame, 0.2)
        trajectories.append(self.get_trajectory(pickup_frame_offset))
        trajectories.append(self.get_trajectory(pickup_frame, linear=True))
        return trajectories


    def move_trajectories(self, target_frame, approach_vector = None):
        trajectories = []
        pickup_frame_offset = self.offset_frame(self.current_frame,  0.2)
        if approach_vector:
            approach_frame = Frame(target_frame.point - approach_vector, target_frame.xaxis, target_frame.yaxis)
        else:
            approach_frame = self.offset_frame(target_frame, 0.5)
        trajectories.append(self.get_trajectory(pickup_frame_offset, linear=True))
        trajectories.append(self.get_trajectory(approach_frame))
        trajectories.append(self.get_trajectory(target_frame, linear=True))
        return trajectories


    def retract_trajectories(self):
        trajectories = []
        offset_frame = Frame(self.current_frame.point - self.current_frame.zaxis * 0.5, self.current_frame.xaxis, self.current_frame.yaxis)
        trajectories.append(self.get_trajectory(offset_frame, linear=True))
        trajectories.append(self.get_trajectory(self.robot.forward_kinematics(self.safe_position, self.group)))
        return trajectories


    def grab_beam(self, beam, pickup_frame, target_frame):
        beam_mesh = Mesh.from_shape(beam.blank)
        beam_mesh.transform(Transformation.from_frame_to_frame(target_frame, Frame.worldXY()))
        beam_mesh.transform(Translation.from_vector([0,0,beam.height/2.0]))
        beam_collision_mesh = CollisionMesh(beam_mesh, "attached_beam")
        acm = AttachedCollisionMesh(beam_collision_mesh, 'robot11_tool0', touch_links = ['robot11_link_6'])
        self.scene.add_attached_collision_mesh(acm)


    def release_beam(self, beam):
        self.scene.remove_attached_collision_mesh("attached_beam")
        beam.attributes["is_in_scene"] = True


    def offset_frame(self, frame, offset):
        return Frame(frame.point - frame.zaxis * offset, frame.xaxis, frame.yaxis)


    def get_trajectory(self, target_frame, linear = False):
        self.scene.remove_collision_mesh("beam_meshes")
        beams_in_scene = [beam for beam in self.assembly.beams if beam.attributes["is_in_scene"]]
        for beam in beams_in_scene:

            added_beam_collision_mesh = CollisionMesh(Mesh.from_shape(beam.blank), "beam_meshes")
            self.scene.append_collision_mesh(added_beam_collision_mesh)

        if (self.robot.client and self.robot.client.is_connected):
            options = dict(
                    attached_collision_meshes = self.attached_collision_meshes,
                    path_constraints=self.path_constraints,
                    planner_id=self.planner_id
                    )
            if linear:
                this_trajectory = self.robot.plan_cartesian_motion([self.current_frame, target_frame], start_configuration=self.current_configuration, group=self.group, options = options)
            else:
                print("group is  {}", self.group)
                constraints = self.robot.constraints_from_frame(target_frame, TimberAssemblyPlanner.TOLERANCE_POSITION, TimberAssemblyPlanner.TOLERANCE_AXES, group = self.group)
                this_trajectory = self.robot.plan_motion(constraints, start_configuration=self.current_configuration, group=self.group, options = options)

            this_trajectory.attributes["beams_in_scene"] = beams_in_scene

        if this_trajectory.fraction < 1:
            raise Exception("Failed to plan trajectory")
        return this_trajectory

    # def get_trajectories_simple(self, beams, start = 0, end = None):
    #     trajectories = []
    #     for beam in beams[start:end]:
    #         print("to pick up")
    #         trajectories.append(self.get_trajectory(self.beam_pickup(beam)))
    #         target_frame = Frame(beam.midpoint, Vector.Xaxis(), Vector.Yaxis())
    #         print("to target")

    #         trajectories.append(self.get_trajectory(target_frame))
    #         print("to safe spot")

    #         trajectories.append(self.get_trajectory(self.safe_configuation))

    #     return trajectories



    def get_trajectories_beam(self, beam):
        self.scene.reset()

        self.trajectories = []

        print("to pick up")
        try:
            self.trajectories.append(self.get_trajectory(self.beam_pickup(beam)))
            print(self.trajectories[-1])
        except:
            print("failed to pick up")
            raise


        target_frame = Frame(beam.midpoint, beam.frame.xaxis, beam.frame.yaxis)
        self.grab_beam(beam, self.beam_pickup(beam), target_frame)

        print("to target")
        try:
            self.trajectories.append(self.get_trajectory(target_frame))
            print(self.trajectories[-1])

        except:
            print("failed to get target frame")
            raise

        self.release_beam(beam)

        print("to safe spot")
        try:
            self.trajectories.append(self.get_trajectory(self.safe_frame))
            print(self.trajectories[-1])

        except:
            print("failed to get safe frame")
            raise

        print("trajectories len = {}".format( len(self.trajectories)))
        return self.trajectories



    def beam_pickup(self, beam):
        # return self.pickup_base_frame
        return Frame(self.pickup_base_frame.point + (self.pickup_base_frame.xaxis * (beam.length / 2.0)) + (self.pickup_base_frame.yaxis* (beam.width / 2.0)) + (self.pickup_base_frame.zaxis * (beam.height/2.0)), self.pickup_base_frame.xaxis, self.pickup_base_frame.yaxis)



    @property
    def current_configuration(self):
        if len(self.trajectories) == 0:
            return self.safe_configuation
        else:
            config = self.trajectories[-1].start_configuration
            return self.robot.merge_group_with_full_configuration(self.trajectories[-1].points[-1], config, self.group)


    @property
    def current_frame(self):
        return self.robot.forward_kinematics(self.current_configuration, self.group)

    @property
    def safe_frame(self):
        return self.robot.forward_kinematics(self.safe_configuation, self.group)

    @property
    def safe_configuation(self):
        configuration = self.robot.zero_configuration()

        configuration['bridge2_joint_EA_X'] = 30

        configuration['robot11_joint_EA_Z'] = -4.5
        configuration['robot11_joint_2'] = 0
        configuration['robot11_joint_3'] = -math.pi/2
        configuration['bridge1_joint_EA_X'] = 9

        """ get robot_12 out of the way """
        configuration['robot12_joint_EA_Y'] = -12
        configuration['robot12_joint_EA_Z'] = -4.5
        configuration['robot12_joint_2'] = math.pi/2
        return configuration


    @property
    def global_constraints(self):
        constraints = []
        constraints.append(JointConstraint('robot11_joint_2', 0, -0.1, 0.1, 0.5))
        constraints.append(JointConstraint('robot11_joint_3', -math.pi/2, -0.1, 0.1, 0.5))
        constraints.append(JointConstraint('bridge1_joint_EA_X', 9, 3, 3, 1.0))
        return constraints
