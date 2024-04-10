from .joint import Joint
from .solver import JointTopology
from .joint import BeamJoinningError
from compas_timber.parts import CutFeature
from compas_timber.parts import MillVolume
from compas.geometry import Plane, Polyhedron, Vector, Frame
from compas.geometry import Rotation
from compas.geometry import intersection_plane_plane
from compas.geometry import intersection_plane_plane_plane
from compas.geometry import intersection_line_plane
from compas.geometry import angle_vectors
from compas.geometry import distance_point_point
from compas.geometry import midpoint_line
from compas.geometry import project_point_plane
from compas.geometry import translate_points
import math


class TStirnversatzJoint(Joint):
    
    SUPPORTED_TOPOLOGY = JointTopology.TOPO_T

    def __init__(self, cross_beam=None, main_beam=None): #TODO Why main & cross swapped???
        super(TStirnversatzJoint, self).__init__(main_beam, cross_beam)
        self.main_beam = main_beam
        self.cross_beam = cross_beam
        self.main_beam_key = None
        self.cross_beam_key = None
        self.cut_depth = 0.25  # TODO How to make this changable by user?
        self.features = []

    @property
    def data(self):
        data_dict = {
            "cross_beam": self.cross_beam_key,
            "main_beam": self.main_beam_key,
        }
        data_dict.update(Joint.data.fget(self))
        return data_dict

    # @data.setter
    # def data(self, value):
    #     Joint.data.fset(self, value)
    #     self.cross_beam_key = value["cross_beam"]
    #     self.main_beam_key = value["main_beam"]

    @property
    def joint_type(self):
        return "Stirnversatz"

    @property
    def beams(self):
        return [self.main_beam, self.cross_beam]

    @staticmethod
    def _bisector_plane(plane1, plane2, angle_factor):
        bisector = plane1[1] + plane2[1] * angle_factor
        intersection = intersection_plane_plane(plane1, plane2)
        rotation_axis = Vector.from_start_end(*intersection)
        origin = intersection[0]
        R = Rotation.from_axis_and_angle(rotation_axis, math.radians(90))
        bisector.transform(R)
        plane = Plane(origin, bisector)
        return plane, plane1[1], plane2[1]
    
    #TODO Remove if not used
    def get_main_cutting_frame(self):
        assert self.beams
        cross_beam, main_beam = self.beams

        _, cfr = self.get_face_most_ortho_to_beam(main_beam, cross_beam, True)
        cfr = Frame(cfr.point, cfr.yaxis, cfr.xaxis)  # flip normal towards the inside of main beam
        return cfr
    
    # TODO Remove if not used
    def get_cross_cutting_frame(self):
        assert self.beams
        cross_beam, main_beam = self.beams
        _, cfr = self.get_face_most_towards_beam(main_beam, cross_beam)
        return cfr

    #find the Face on cross_beam where main_beam intersects
    #TODO simplify with Chen!
    def get_main_intersection_frame(self):
        diagonal = math.sqrt(self.main_beam.width ** 2 + self.main_beam.height ** 2)
        main_frames = self.main_beam.faces[:4]
        cross_centerline = self.cross_beam.centerline
        cross_centerpoint = midpoint_line(self.cross_beam.centerline)
        projectionplane = self.main_beam.faces[5]
        frames, distances = [], []
        for i in main_frames:
            int_centerline_frame = intersection_line_plane(cross_centerline, Plane.from_frame(i))
            if int_centerline_frame == None:
                pass
            else:
                projected_int = project_point_plane(int_centerline_frame, Plane.from_frame(projectionplane))
                distance = distance_point_point(projected_int, projectionplane.point)
                if distance > diagonal / 2:
                    pass
                else:
                    distance = distance_point_point(cross_centerpoint, int_centerline_frame)
                    distances.append(distance)
                    frames.append(i)
        distances, frames = zip(*sorted(zip(distances, frames)))
        return frames[0]

    @staticmethod
    def _sort_frames_according_normals(frame, frames):
        angles = []
        for i in frames:
            angles.append(angle_vectors(frame.normal, i.normal))
        angles, frames = zip(*sorted(zip(angles, frames)))
        return frames
    
    #TODO Delete if not needed
    @staticmethod
    def _rotation_plane(plane1, plane2):
        line = intersection_plane_plane(plane1, plane2)
        vector = Vector.from_start_end(line[0], line[1])
        plane = Plane(line[0], vector)
        return plane
    
    #TODO Delete if not needed
    @staticmethod
    def _angle_plane_normals(plane1, plane2):
        return angle_vectors(plane1.normal, plane2.normal)
    
    def get_cross_cutting_planes(self):
        main_int_frame = self.get_main_intersection_frame()
        main_int_plane = Plane.from_frame(main_int_frame)
        cross_faces = self.cross_beam.faces[:4]
        cross_faces_sorted = self._sort_frames_according_normals(main_int_frame, cross_faces)
        cross_face = Plane.from_frame(cross_faces_sorted[0])
        cutplane_1 = self._bisector_plane(main_int_plane, cross_face, 0.5)

        cut_depth_point = project_point_plane(self.main_beam.frame.point, main_int_plane)
        cut_depth = distance_point_point(self.main_beam.frame.point, cut_depth_point) / 2 #TODO implement cut depth factor
        split_plane = Plane(main_int_frame.point, main_int_frame.yaxis)
        p1 = intersection_plane_plane_plane(main_int_plane, Plane.from_frame(cross_faces_sorted[3]), split_plane)
        origin = translate_points([p1], main_int_frame.zaxis * -cut_depth)[0]
        cut_depth_plane = Plane(origin, main_int_frame.zaxis)
        p2 = intersection_plane_plane_plane(cut_depth_plane, cutplane_1[0], split_plane)
        cutplane_2 = Plane.from_frame(Frame(p1, Vector.from_start_end(p1, p2), split_plane.normal))
        print(cutplane_1[0], cutplane_2[0])
        return cutplane_1[0], cutplane_2

    def add_features(self):

        assert self.main_beam and self.cross_beam  # should never happen

        cross_cutting_plane1, cross_cutting_plane2 = self.get_cross_cutting_planes()

        # Main Cutting Volume
        main_int_frame = self.get_main_intersection_frame()
        main_int_plane = Plane.from_frame(main_int_frame)
        l1 = intersection_plane_plane(main_int_plane, cross_cutting_plane1)
        l2 = intersection_plane_plane(main_int_plane, cross_cutting_plane2)
        l3 = intersection_plane_plane(cross_cutting_plane1, cross_cutting_plane2)
        main_frames_sorted = self._sort_frames_according_normals(main_int_frame, self.main_beam.faces[:4])
        pl1 = Plane.from_frame(main_frames_sorted[1])
        pl2 = Plane.from_frame(main_frames_sorted[2])
        lines = [l1, l2, l3]
        points = []
        for i in lines:
            points.append(intersection_line_plane(i, pl1))
            points.append(intersection_line_plane(i, pl2))
        
        main_cutting_volume = Polyhedron(points, 
                   [
                [0, 2, 4],  # front
                [1, 5, 3],  # back
                [0, 1, 3, 2],  # first
                [2, 3, 5, 4],  # second
                [4, 5, 1, 0],  # third
            ],
            )
        
        print(main_cutting_volume) #TODO just for debugging, remove...
        print("polyhedron is closed: " + str(main_cutting_volume.is_closed())) #TODO just for debugging, remove...

        trim_feature = CutFeature(cross_cutting_plane1)
        self.cross_beam.add_features(trim_feature)
        trim_feature = CutFeature(cross_cutting_plane2)
        self.cross_beam.add_features(trim_feature)

        volume = MillVolume(main_cutting_volume)
        self.main_beam.add_features(volume)