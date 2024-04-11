from .joint import Joint
from .solver import JointTopology
from .joint import BeamJoinningError
from compas_timber.parts import CutFeature
from compas_timber.parts import MillVolume
from compas.geometry import Plane, Polyhedron, Vector, Frame, Point
from compas.geometry import Rotation
from compas.geometry import intersection_plane_plane
from compas.geometry import intersection_plane_plane_plane
from compas.geometry import intersection_line_plane
from compas.geometry import angle_vectors
from compas.geometry import distance_point_point
from compas.geometry import midpoint_line
from compas.geometry import project_point_plane
from compas.geometry import translate_points
from compas.geometry import cross_vectors
import math

class TStirnversatzJoint(Joint):
    
    SUPPORTED_TOPOLOGY = JointTopology.TOPO_T

    def __init__(self, cross_beam=None, main_beam=None, cut_depth=0.25): #TODO Why main & cross swapped???
        super(TStirnversatzJoint, self).__init__(main_beam, cross_beam, cut_depth)
        self.main_beam = main_beam
        self.cross_beam = cross_beam
        self.main_beam_key = None
        self.cross_beam_key = None
        self.cut_depth = cut_depth
        self.features = []
        self.cross_cutting_plane_1 = None
        self.cross_cutting_plane_2 = None
        self.planetogh = [] # TODO Remove
        self.linetogh = [] # TODO Remove
        self.pointtogh = [] # TODO Remove
        self.polyhedrontogh = [] # TODO Remove

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
        bisector = plane1.normal + plane2.normal * angle_factor
        intersection = intersection_plane_plane(plane1, plane2)
        rotation_axis = Vector.from_start_end(*intersection)
        origin = intersection[0]
        R = Rotation.from_axis_and_angle(rotation_axis, math.radians(90))
        bisector.transform(R)
        plane = Plane(origin, bisector)
        return plane
       
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
    def _sort_frames_according_normals(frames, checkvector):
        angles = []
        for i in frames:
            angles.append(angle_vectors(checkvector, i.normal))
        angles, frames = zip(*sorted(zip(angles, frames)))
        return frames
    
    @staticmethod
    def _flip_plane_according_vector(plane, vector):
        if angle_vectors(plane.normal, vector, True) > 90:
            plane = Plane(plane.point, plane.normal * -1)
        return plane
        
    def get_cross_cutting_planes(self):
        main_int_frame = self.get_main_intersection_frame()
        main_int_plane = Plane.from_frame(main_int_frame)
        cross_faces = self.cross_beam.faces[:4]
        cross_faces_sorted = self._sort_frames_according_normals(cross_faces, main_int_frame.zaxis)
        cross_face = Plane.from_frame(cross_faces_sorted[0])
        cutplane_1 = self._bisector_plane(main_int_plane, cross_face, 0.5)
        cut_depth_point = project_point_plane(self.main_beam.frame.point, main_int_plane)
        cut_depth = distance_point_point(self.main_beam.frame.point, cut_depth_point) * self.cut_depth * 2
        split_plane = Plane(main_int_frame.point, main_int_frame.yaxis)
        p1 = intersection_plane_plane_plane(main_int_plane, Plane.from_frame(cross_faces_sorted[3]), split_plane)
        origin = translate_points([p1], main_int_frame.zaxis * -cut_depth)[0]
        cut_depth_plane = Plane(origin, main_int_frame.zaxis)
        p2 = intersection_plane_plane_plane(cut_depth_plane, cutplane_1, split_plane)
        cutplane_2 = Plane.from_frame(Frame(p1, Vector.from_start_end(p1, p2), split_plane.normal))
        cutplane_2 = self._flip_plane_according_vector(cutplane_2, main_int_frame.zaxis * -1)

        self.cross_cutting_plane_1 = cutplane_1
        self.cross_cutting_plane_2 = cutplane_2
        return self.cross_cutting_plane_1, self.cross_cutting_plane_2
    
    def get_main_cutting_volume(self):
        main_int_frame = self.get_main_intersection_frame()
        main_int_plane = Plane.from_frame(main_int_frame)
        l1 = intersection_plane_plane(main_int_plane, self.cross_cutting_plane_1)
        l2 = intersection_plane_plane(main_int_plane, self.cross_cutting_plane_2)
        l3 = intersection_plane_plane(self.cross_cutting_plane_1, self.cross_cutting_plane_2)
        main_frames_sorted = self._sort_frames_according_normals(self.main_beam.faces[:4], main_int_frame.zaxis)
        plane_side = [Plane.from_frame(main_frames_sorted[1]), Plane.from_frame(main_frames_sorted[2])]
        
        crossvector = cross_vectors(self.cross_cutting_plane_2.normal, self.cross_cutting_plane_1.normal)
        plane_side = self._sort_frames_according_normals(plane_side, crossvector)

        lines = [l1, l2, l3]
        points = []
        for i in lines:
            points.append(intersection_line_plane(i, plane_side[0]))
            points.append(intersection_line_plane(i, plane_side[1]))

        #TODO fix with Chen: Polyhedron.from_planes not working because numpy missing ?????
        main_cutting_volume = Polyhedron(points, 
                   [
                [0, 2, 4],  # front
                [1, 5, 3],  # back
                [0, 1, 3, 2],  # first
                [2, 3, 5, 4],  # second
                [4, 5, 1, 0],  # third
            ],
            )

        return main_cutting_volume

    def add_features(self):

        assert self.main_beam and self.cross_beam  # should never happen

        cross_cutting_plane1, cross_cutting_plane2 = self.get_cross_cutting_planes()
        main_cutting_vol = self.get_main_cutting_volume()

        trim_feature = CutFeature(cross_cutting_plane1)
        self.cross_beam.add_features(trim_feature)
        trim_feature = CutFeature(cross_cutting_plane2)
        self.cross_beam.add_features(trim_feature)
        volume = MillVolume(main_cutting_vol)
        self.main_beam.add_features(volume)