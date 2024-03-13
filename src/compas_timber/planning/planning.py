from collections import OrderedDict
import math
from compas.geometry import Frame
from compas.geometry import Vector
from compas.datastructures import Mesh
from compas.geometry import angle_vectors
from compas.geometry import angle_vectors_xy

from compas_fab.robots import JointConstraint
from compas_fab.robots import PlanningScene
from compas_fab.robots import CollisionMesh
from compas_fab.robots import AttachedCollisionMesh

from compas.geometry import Transformation
from compas.geometry import Rotation
from compas_robots import Configuration


class TimberAssemblyPlanner(object):

    TOLERANCE_POSITION = 0.001          # 1 mm tolerance on position
    TOLERANCE_AXES = [math.radians(1.0)]*3    # 1 degree tolerance per axis
    TOLERANCE_JOINT = math.radians(1.0)   # 1 degree tolerance per axis

    def __init__(self, robot, assembly,  pickup_base_frame, building_plan = None, scene_objects = None, group = "robot11_eaXYZ", planner_id = None):
        self.pickup_base_frame = pickup_base_frame
        self.safe_height = 3
        self.robot = robot
        self.assembly = assembly
        self.building_plan = building_plan
        self.group = group or self.robot.main_group_name
        self.planner_id = str(planner_id) if planner_id else "RRTConnect"
        self.attached_collision_meshes = []
        self.path_constraints = []
        self.frames = []
        self.beams = []
        self.robot_steps = {}
        self.scene_objects = [scene_objects]
        self.scene = PlanningScene(robot)
        for beam in self.assembly.beams:
            self.beams.append(AssemblyBeam(beam, self))
        if scene_objects:
            for mesh in scene_objects:
                self.scene.add_collision_meshes(CollisionMesh(mesh, "scene_mesh"))



    def plan_assembly(self, range = None):
        for beam in self.beams:
            if range:
                if beam.sequence_index not in range:
                    continue
                beam.plan_beam()
            else:
                beam.plan_beam()


    def plan_single_beam(self, index, intermediate_frames = None):
        beam = self.beams[index]
        beam.plan_beam(intermediate_frames = intermediate_frames)



    def get_trajectory(self, target, linear = False, check_collisions = True):
        self.scene.remove_collision_mesh("beam_meshes")
        self.frames.append(target)

        if check_collisions:
            for beam in self.beams_in_scene:
                added_beam_collision_mesh = CollisionMesh(Mesh.from_shape(beam.beam.blank), "beam_meshes")
                self.scene.append_collision_mesh(added_beam_collision_mesh)
        if self.robot.client and self.robot.client.is_connected:
            options = dict(
                    attached_collision_meshes = self.attached_collision_meshes,
                    path_constraints=self.path_constraints,
                    planner_id=self.planner_id
                    )
            if linear:
                this_trajectory = self.robot.plan_cartesian_motion([self.current_frame, target], start_configuration=self.current_configuration, group=self.group, options = options)
            else:
                if type(target) is Configuration:
                    target_config = self.robot.get_group_configuration(self.group, target)
                    constraints = self.robot.constraints_from_configuration(target_config, [TimberAssemblyPlanner.TOLERANCE_JOINT], [TimberAssemblyPlanner.TOLERANCE_JOINT], group = self.group)
                else:
                    constraints = self.robot.constraints_from_frame(target, TimberAssemblyPlanner.TOLERANCE_POSITION, TimberAssemblyPlanner.TOLERANCE_AXES, group = self.group)
                this_trajectory = self.robot.plan_motion(constraints, start_configuration=self.current_configuration, group=self.group, options = options)

            this_trajectory.attributes["beams_in_scene"] = self.beams_in_scene
        if this_trajectory.fraction < 1:
            print("Failed to plan trajectory")

        return this_trajectory


    def offset_frame(self, frame, offset):
        return Frame(frame.point - frame.zaxis * offset, frame.xaxis, frame.yaxis)


    @property
    def trajectory_frames(self):
        for beam in self.beams:
            for frame in beam.frames:
                yield frame

    @property
    def trajectory_list(self):
        traj_list = []
        for beam in self.beams:
            for traj in beam.trajectories.values():
                    traj_list.append(traj)
        return traj_list

    @property
    def beams_in_scene(self):
        return [beam for beam in self.beams if beam.is_in_scene]

    @property
    def current_configuration(self):
        if len(self.trajectory_list) == 0:
            return self.safe_configuation
        else:
            config = self.trajectory_list[-1].start_configuration
            return self.robot.merge_group_with_full_configuration(self.trajectory_list[-1].points[-1], config, self.group)

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
        configuration['robot11_joint_EA_Y'] = -4
        configuration['robot11_joint_EA_Z'] = -5
        configuration['robot11_joint_1'] = math.pi
        configuration['robot11_joint_2'] = 0
        configuration['robot11_joint_3'] = 0
        configuration['robot11_joint_5'] = -math.pi/(3)
        configuration['bridge1_joint_EA_X'] = 7

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
        constraints.append(JointConstraint('robot11_joint_6', -0, 6, 6, 1.0))
        constraints.append(JointConstraint('bridge1_joint_EA_X', 9, 3, 3, 1.0))
        constraints.append(JointConstraint('bridge1_joint_EA_Z', -5, 1, 1, 0.7))
        return constraints



class AssemblyBeam(TimberAssemblyPlanner):
    def __init__(self, beam, parent, approach_vector = None):
        self.parent = parent
        self.beam = beam
        self.blank = beam.blank
        self.safe_height = parent.safe_height
        self.robot = parent.robot
        self.scene = parent.scene
        self.pickup_base_frame = parent.pickup_base_frame
        self.approach_vector = approach_vector or beam.attributes.get("approach_vector", None)
        self.frames = []
        self.trajectories = OrderedDict()
        self.key = beam.key
        self.sequence_index = len(parent.beams)
        self.is_built = False
        self.is_planned = False
        self.is_in_scene = False

    def plan_beam(self, intermediate_frames = None):
        self.intermediate_frames = intermediate_frames
        self.scene.reset()
        try:
            self.pickup_beam()
        except:
            print("failed to pick up beam")
        try:
            self.place_beam()
        except:
            print("failed to place beam")
        try:
            self.go_home()
        except:
            print("failed to go home")
        return self.trajectories


    def pickup_beam(self):
        self.trajectories["pickup_approach"] = (self.parent.get_trajectory(self.offset_pickup_frame))
        self.trajectories["to_pickup"] = (self.parent.get_trajectory(self.pickup_frame, linear=True, check_collisions=False))
        self.grab_beam()
        self.trajectories["from_pickup"] = (self.parent.get_trajectory(self.offset_pickup_frame, linear=True, check_collisions=False))
        self.trajectories["to_safe_height"] = (self.parent.get_trajectory(self.safe_height_pickup_frame, linear=True))

    def place_beam(self):
        if self.intermediate_frames:
            print("intermediate frames")
            for i, frame in enumerate(self.intermediate_frames):
                self.trajectories["intermediate_"+ str(i)] = self.parent.get_trajectory(frame)
        else:
            self.trajectories["translate"] = (self.parent.get_trajectory(self.safe_height_offset_target_frame, linear=True))
        self.trajectories["target_approach"] = (self.parent.get_trajectory(self.approach_target_frame))
        self.trajectories["to_target"] = (self.parent.get_trajectory(self.target_frame, linear = True, check_collisions=False))
        self.release_beam()
        self.trajectories["from_target"] = (self.parent.get_trajectory(self.retract_target_frame, linear = True, check_collisions=False))

    def go_home(self):
        self.trajectories["go_home"] = (self.parent.get_trajectory(self.parent.safe_configuation))


    def grab_beam(self):
        beam_mesh = Mesh.from_shape(self.beam.blank)
        beam_mesh.transform(Transformation.from_frame_to_frame(self.target_frame, Frame.worldXY()))
        beam_collision_mesh = CollisionMesh(beam_mesh, "attached_beam")
        acm = AttachedCollisionMesh(beam_collision_mesh, 'robot11_tool0', touch_links = ['robot11_link_6'])
        self.parent.scene.add_attached_collision_mesh(acm)


    def release_beam(self):
        self.scene.remove_attached_collision_mesh("attached_beam")
        self.is_in_scene = True


    @property
    def pickup_frame(self):
        return Frame(self.pickup_base_frame.point + (self.pickup_base_frame.xaxis * (self.beam.length / 2.0)) + (self.pickup_base_frame.yaxis* (self.beam.width / 2.0)) - (self.pickup_base_frame.zaxis * (self.beam.height)), self.pickup_base_frame.xaxis, self.pickup_base_frame.yaxis)

    @property
    def offset_pickup_frame(self):
        return self.offset_frame(self.pickup_frame, 0.5)

    @property
    def safe_height_pickup_frame(self):
        frame = self.offset_pickup_frame
        frame.point.z = self.safe_height
        angle = angle_vectors(frame.zaxis, self.target_frame.zaxis)
        rot_X = Rotation.from_axis_and_angle(frame.xaxis, angle, point = frame.point)
        frame.transform(rot_X)
        return frame


    @property
    def target_frame(self):
        return self.beam.attributes.get("grab_frame", Frame(self.beam.midpoint - (self.beam.frame.zaxis * (self.beam.height/2.0)), self.beam.frame.xaxis, self.beam.frame.yaxis))

    @property
    def safe_height_offset_target_frame(self):
        frame = self.safe_height_pickup_frame
        frame.point.x = self.approach_target_frame.point.x
        frame.point.y = self.approach_target_frame.point.y
        angle = angle_vectors_xy(frame.xaxis, self.approach_target_frame.xaxis)
        rot_X = Rotation.from_axis_and_angle(Vector.Zaxis(), angle, point = frame.point)
        frame.transform(rot_X)
        return frame

    @property
    def approach_target_frame(self):
        if self.approach_vector:
            point = self.target_frame.point - self.approach_vector
            return Frame(point, self.target_frame.xaxis, self.target_frame.yaxis)
        else:
            return self.retract_target_frame

    @property
    def retract_target_frame(self):
        return self.offset_frame(self.target_frame, 0.5)


    @staticmethod
    def get_face_most_ortho_to_vector(beam, vector, ignore_ends=True):
        face_dict = AssemblyBeam._beam_side_incidence(beam, vector, ignore_ends)
        face_index = max(face_dict, key=face_dict.get)
        return beam.faces[face_index]

    @staticmethod
    def _beam_side_incidence(beam, vector, ignore_ends=True):
        if ignore_ends:
            beam_faces = beam.faces[:4]
        else:
            beam_faces = beam.faces

        face_angles = {}
        for face_index, face in enumerate(beam_faces):
            face_angles[face_index] = angle_vectors(face.normal, vector)

        return face_angles


