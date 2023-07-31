from compas_timber.connections import Joint
from compas_timber.connections import JointTopology
from compas.geometry import Point, Line, Plane, Polyhedron, Brep
from compas.geometry import midpoint_point_point
from compas.geometry import intersection_plane_plane
from compas.geometry import intersection_line_plane
from compas.geometry import angle_vectors
from compas.artists import Artist
from compas_timber.parts import BeamBooleanSubtraction
from compas_timber.utils import intersection_line_line_3D

# BREP HACK CHEN
import rhinoscriptsyntax as rs
from Rhino.Geometry import Brep as RhinoBrep


class HalfLapJoint(Joint):
    SUPPORTED_TOPOLOGY = JointTopology.TOPO_X

    def __init__(self, assembly=None, beam_a=None, beam_b=None, cut_plane_choice=None):
        super(HalfLapJoint, self).__init__(assembly, [beam_a, beam_b])
        self.beam_a = beam_a
        self.beam_b = beam_b
        self.beam_a_key = None
        self.beam_b_key = None
        self.cut_plane_choice = cut_plane_choice  # Decide if Direction of beam_a or beam_b
        self.max_distance = (beam_a.height + beam_b.height) * 0.55  # A Bit more than the Average of both Thicknesses
        self.features = []

    @property
    def data(self):
        data_dict = {
            "beam_a": self.beam_a.key,
            "beam_b": self.beam_b.key,
        }
        data_dict.update(Joint.data.fget(self))
        return data_dict

    @data.setter
    def data(self, value):
        Joint.data.fset(self, value)
        self.beam_a_key = value["beam_a"]
        self.beam_b_key = value["beam_b"]

    @property
    def joint_type(self):
        return "Half-Lap"

    @property
    def beams(self):
        return [self.beam_a, self.beam_b]

    def _cutplane(self):
        # Sets the Plane where the Cut will be
        centerline_a = self.beam_a.centerline
        centerline_b = self.beam_b.centerline
        plane_a = Plane.from_frame(self.beam_a.faces[3])
        plane_b = Plane.from_frame(self.beam_b.faces[3])
        int_a, int_b = intersection_line_line_3D(centerline_a, centerline_b, self.max_distance)
        int_a, _ = int_a
        int_b, _ = int_b
        point_cut = Point(*midpoint_point_point(int_a, int_b))  # If Centerline don't intersect
        if self.cut_plane_choice == None or "A":
            plane = plane_a
        if self.cut_plane_choice == "B":
            plane = plane_b
        plane_cut = Plane(point_cut, plane[1])
        return plane_cut

    @staticmethod
    def _create_polyhedron(plane_top, plane_bottom, lines_vertical):
        # Step 1: Get 8 Intersection Points from 2 Planes and 4 Lines
        int_points = []
        for i in lines_vertical:
            point = intersection_line_plane(i, plane_top)
            point = Point(*point)
            int_points.append(point)
        for i in lines_vertical:
            point = intersection_line_plane(i, plane_bottom)
            point = Point(*point)
            int_points.append(point)
        # Step 2: Create a hexahedron with 6 Faces from the 8 Points
        return Polyhedron(
            int_points,
            [
                [0, 1, 2, 3],  # top
                [4, 5, 6, 7],  # bottom
                [0, 1, 5, 4],  # left
                [1, 5, 6, 2],  # back
                [2, 6, 7, 3],  # right
                [3, 7, 4, 0],  # front
            ],
        )

    @staticmethod
    def _mesh_to_brep(negative_polyhedron_beam_a, negative_polyhedron_beam_b):
        # Show Polyhedrons
        negative_polyhedron_beam_a = Artist(negative_polyhedron_beam_a).draw()
        negative_polyhedron_beam_b = Artist(negative_polyhedron_beam_b).draw()

        # Breps from Polyhedrons
        negative_brep_beam_a = RhinoBrep.CreateFromMesh(rs.coercemesh(negative_polyhedron_beam_a), True)
        negative_brep_beam_b = RhinoBrep.CreateFromMesh(rs.coercemesh(negative_polyhedron_beam_b), True)
        return negative_brep_beam_a, negative_brep_beam_b

    def _create_negative_volumes(self):
        # Get Planes from Beams
        plane_a = Plane.from_frame(self.beam_a.faces[3])
        plane_a_side1 = Plane.from_frame(self.beam_a.faces[0])
        plane_a_side2 = Plane.from_frame(self.beam_a.faces[2])
        plane_b1 = Plane.from_frame(self.beam_b.faces[1])
        plane_b3 = Plane.from_frame(self.beam_b.faces[3])
        plane_b_side1 = Plane.from_frame(self.beam_b.faces[0])
        plane_b_side2 = Plane.from_frame(self.beam_b.faces[2])

        # 4 Lines as Intersections between Beam Sides left/right, just like the Hashtag-Sign (#) that has 4 intersection points!
        lines = []
        x = intersection_plane_plane(plane_a_side1, plane_b_side1)
        lines.append(Line(x[0], x[1]))
        x = intersection_plane_plane(plane_a_side1, plane_b_side2)
        lines.append(Line(x[0], x[1]))
        x = intersection_plane_plane(plane_a_side2, plane_b_side2)
        lines.append(Line(x[0], x[1]))
        x = intersection_plane_plane(plane_a_side2, plane_b_side1)
        lines.append(Line(x[0], x[1]))

        # Calculate Cut Direction of beam_b
        vector_angle_a_b1 = angle_vectors(plane_a[1], plane_b1[1])
        vector_angle_a_b3 = angle_vectors(plane_a[1], plane_b3[1])
        if vector_angle_a_b1 > vector_angle_a_b3:
            plane_b = plane_b1
        else:
            plane_b = plane_b3

        # Get Cut Plane
        plane_cut = self._cutplane()

        # Create Polyhedrons
        negative_polyhedron_beam_a = self._create_polyhedron(plane_a, plane_cut, lines)
        negative_polyhedron_beam_b = self._create_polyhedron(plane_cut, plane_b, lines)

        # Create BREP
        return self._mesh_to_brep(negative_polyhedron_beam_a, negative_polyhedron_beam_b)

    def restore_beams_from_keys(self, assemly):
        """After de-serialization, resotres references to the main and cross beams saved in the assembly."""
        self.beam_a = assemly.find_by_key(self.beam_a_key)
        self.beam_b = assemly.find_by_key(self.beam_b_key)

    def add_features(self):
        negative_brep_beam_a, negative_brep_beam_b = self._mesh_to_brep()
        self.beam_a.add_feature(BeamBooleanSubtraction(negative_brep_beam_a))
        self.beam_b.add_feature(BeamBooleanSubtraction(negative_brep_beam_b))
