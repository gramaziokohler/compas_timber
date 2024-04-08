from .joint import Joint
from .solver import JointTopology
from .joint import BeamJoinningError
from compas_timber.parts import CutFeature
from compas_timber.parts import MillVolume
from compas.geometry import Plane, Polyhedron, Brep, Polyline, Vector, Box, Frame, Point
from compas.geometry import Rotation
from compas.geometry import intersection_plane_plane
from compas.geometry import intersection_plane_plane_plane
from compas.geometry import intersection_line_plane
from compas.geometry import intersection_polyline_plane
from compas.geometry import angle_vectors
from compas.geometry import angle_planes
from compas.geometry import distance_point_point
from compas.geometry import midpoint_line
from compas.geometry import project_point_plane
from compas.geometry import length_vector
from compas.geometry import translate_points
import math

# BREP HACK CHEN
# from compas.artists import Artist
# import rhinoscriptsyntax as rs
# from Rhino.Geometry import Brep as RhinoBrep
# from Rhino.Geometry import Plane as RhinoPlane


class TStirnversatzJoint(Joint):
    SUPPORTED_TOPOLOGY = JointTopology.TOPO_T

    def __init__(self, assembly=None, main_beam=None, cross_beam=None):
        super(TStirnversatzJoint, self).__init__(assembly, [main_beam, cross_beam])
        self.main_beam = main_beam
        self.cross_beam = cross_beam
        self.main_beam_key = None
        self.cross_beam_key = None
        self.cut_depth = 0.25  # TODO How to make this changable by user?
        self.features = []

    @property
    def data(self):
        data_dict = {
            "main_beam": self.main_beam_key,
            "cross_beam": self.cross_beam_key,
        }
        data_dict.update(Joint.data.fget(self))
        return data_dict

    # @data.setter
    # def data(self, value):
    #     Joint.data.fset(self, value)
    #     self.main_beam_key = value["main_beam"]
    #     self.cross_beam_key = value["cross_beam"]

    @property
    def joint_type(self):
        return "Stirnversatz"

    @property
    def beams(self):
        return [self.main_beam, self.cross_beam]

    @staticmethod
    def _get_planes(list):
        # Get Planes from Beams
        output = []
        for i in list:
            result = Plane.from_frame(i)
            output.append(result)
        return output

    @staticmethod
    def _get_plane_normals(list):
        output = []
        for i in list:
            output.append(i[1])
        return output

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

    @staticmethod
    def _plane_between(plane1, plane2, shift_factor):
        # Sets a Plane between plane1 and plane2 with a Shift Factor
        vector = Vector.from_start_end(plane1[0], plane2[0])
        vector = vector * shift_factor
        origin = plane1[0] + vector
        return Plane(origin, plane1[1])

    @staticmethod
    def _plane_dir_correction(targetplane, operationplane):
        # Flips targetplane if its normal points into the opposite direction of operationplane
        a = angle_vectors(targetplane[1], operationplane[1])
        b = angle_vectors(targetplane[1] * -1, operationplane[1])
        if a > b:
            return targetplane
        else:
            return Plane(targetplane[0], targetplane[1] * -1)

    @staticmethod
    def _mesh_to_brep(negative_polyhedron):
        # Show Polyhedrons
        negative_polyhedron = Artist(negative_polyhedron).draw()

        # Breps from Polyhedrons
        negative_brep = RhinoBrep.CreateFromMesh(rs.coercemesh(negative_polyhedron), True)
        return negative_brep

    def _create_features(self):
        # Get Planes and Normals for the Beam Faces
        planes_a = self._get_planes(self.main_beam.faces[:4])
        planes_b = self._get_planes(self.cross_beam.faces[:4])
        normals_b = self._get_plane_normals(planes_b)

        # Find plane_a0 where cross_beam meets main_beam and shift it to position 0 in planes_a
        b_centerline = self.cross_beam.centerline[0], self.cross_beam.centerline[1]
        b_centerline = Polyline(b_centerline)
        for idx, i in enumerate(planes_a):
            intersect = intersection_polyline_plane(b_centerline, i)
            if intersect != []:
                plane_a0 = i
                index = idx
        planes_a = planes_a[index:] + planes_a[:index]

        # Sort planes_b by their angle in relation to plane_a0
        angles = []
        for i in normals_b:
            angle = angle_vectors(i, plane_a0[1])
            angles.append(angle)
        angles, planes_b = zip(*sorted(zip(angles, planes_b)))

        # Plane b1 as Feature for cross_beam
        plane_cross_beam1 = self._bisector_plane(plane_a0, planes_b[0], 1)[0]

        # Plane b2 as Feature for cross_beam
        planebetween = self._plane_between(planes_a[0], planes_a[2], self.cut_depth)
        point1 = intersection_plane_plane_plane(plane_cross_beam1, planebetween, planes_b[1])
        point2 = intersection_plane_plane_plane(planes_a[0], planes_b[3], planes_b[1])
        point3 = intersection_plane_plane_plane(planes_a[0], planes_b[3], planes_b[2])
        plane_cross_beam2 = Plane.from_three_points(point1, point2, point3)
        plane_cross_beam2 = self._plane_dir_correction(plane_cross_beam2, planes_b[0])

        # Triangular Prism as Negative Volume for main_beam: Find 3 Prism Edges Lines
        edge_1 = intersection_plane_plane(plane_a0, plane_cross_beam1)
        edge_2 = intersection_plane_plane(plane_a0, plane_cross_beam2)
        edge_3 = intersection_plane_plane(plane_cross_beam1, plane_cross_beam2)

        # Find 6 intersection Points for constructing the Prism
        points = []
        points.append(intersection_line_plane(edge_1, planes_a[1]))
        points.append(intersection_line_plane(edge_2, planes_a[1]))
        points.append(intersection_line_plane(edge_3, planes_a[1]))
        points.append(intersection_line_plane(edge_1, planes_a[3]))
        points.append(intersection_line_plane(edge_2, planes_a[3]))
        points.append(intersection_line_plane(edge_3, planes_a[3]))

        # Create the Prism from Points 0-5
        polyhedron = Polyhedron(points, [[0, 1, 2], [3, 4, 5], [0, 3, 4, 1], [1, 4, 5, 2], [2, 5, 3, 0]])

        # Mesh to Brep
        negative_brep_main_beam = self._mesh_to_brep(polyhedron)

        return plane_cross_beam1, plane_cross_beam2, negative_brep_main_beam
    
    def get_main_cutting_frame(self):
        assert self.beams
        main_beam, cross_beam = self.beams

        _, cfr = self.get_face_most_ortho_to_beam(main_beam, cross_beam, True)
        cfr = Frame(cfr.point, cfr.yaxis, cfr.xaxis)  # flip normal towards the inside of main beam
        return cfr
    
    def get_cross_cutting_frame(self):
        assert self.beams
        main_beam, cross_beam = self.beams
        _, cfr = self.get_face_most_towards_beam(cross_beam, main_beam)
        return cfr

    def get_main_intersection_frame(self):
        #find the Face on main_beam where cross_beam intersects
        #TODO simplify with Chen!
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
    
    @staticmethod
    def _rotation_plane(plane1, plane2):
        line = intersection_plane_plane(plane1, plane2)
        vector = Vector.from_start_end(line[0], line[1])
        plane = Plane(line[0], vector)
        return plane
    
    @staticmethod
    def _angle_plane_normals(plane1, plane2):
        return angle_vectors(plane1.normal, plane2.normal)


    def add_features(self):
        # Cross Cutting Plane 1
        main_intersection_frame = self.get_main_intersection_frame()
        main_intersection_plane = Plane.from_frame(main_intersection_frame)
        cross_frames = self.cross_beam.faces
        cross_frames_sorted = self._sort_frames_according_normals(main_intersection_frame, cross_frames[:4])
        cross_frame = cross_frames_sorted[0]
        bisector_plane = self._bisector_plane(main_intersection_plane, Plane.from_frame(cross_frame), 0.5)
        cross_cutting_plane1 = bisector_plane[0]

        # Cut Depth
        cut_depth_point = project_point_plane(self.main_beam.frame.point, main_intersection_plane)
        cut_depth = distance_point_point(self.main_beam.frame.point, cut_depth_point) / 2 #TODO implement cut depth factor

        # SplitPlane
        split_plane =  Plane(main_intersection_frame.point, main_intersection_frame.yaxis)

        # Cross Cutting Plane 2
        p1 = intersection_plane_plane_plane(Plane.from_frame(main_intersection_frame), Plane.from_frame(cross_frames_sorted[3]), split_plane)
        origin = translate_points([p1], main_intersection_frame.zaxis * -cut_depth)[0]
        cut_depth_plane = Plane(origin, main_intersection_frame.zaxis)
        p2 = intersection_plane_plane_plane(cut_depth_plane, bisector_plane[0], split_plane)
        cross_cutting_plane2 = Plane.from_frame(Frame(p1, Vector.from_start_end(p1, p2), split_plane.normal))

        # Main Cutting Volume
        l1 = intersection_plane_plane(cross_cutting_plane1, main_intersection_plane)
        l2 = intersection_plane_plane(cross_cutting_plane1, cross_cutting_plane2)
        l3 = intersection_plane_plane(cross_cutting_plane2, main_intersection_plane)
        main_frames_sorted = self._sort_frames_according_normals(main_intersection_frame, self.main_beam.faces[:4])
        p4 = Plane.from_frame(main_frames_sorted[1])
        p5 = Plane.from_frame(main_frames_sorted[3])
        #TODO Polyhedron!!!

        self.cross_beam.add_features(cross_cutting_plane1)
        self.cross_beam.add_features(cross_cutting_plane2)

        return cross_cutting_plane1, cross_cutting_plane2