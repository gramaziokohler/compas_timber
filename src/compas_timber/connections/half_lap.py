from compas_timber.connections import Joint
from compas_timber.connections import JointTopology
from compas.geometry import Point, Line, Plane, Polyhedron, Brep
from compas.geometry import intersection_line_line
from compas.geometry import midpoint_point_point
from compas.geometry import intersection_plane_plane
from compas.geometry import intersection_line_plane
from compas.geometry import angle_vectors
from compas.artists import Artist, ShapeArtist
from compas_timber.parts import BeamBooleanSubtraction
from compas_timber.utils import intersection_line_line_3D

# BREP HACK CHEN
from compas.data import json_load
from compas.artists import Artist
from compas.geometry import Brep
import rhinoscriptsyntax as rs
from Rhino.Geometry import Brep as RhinoBrep

class HalfLapJoint(Joint):
    
    SUPPORTED_TOPOLOGY = JointTopology.TOPO_X
    
    def __init__(self, assembly=None, beam_a=None, beam_b=None):
        super(HalfLapJoint, self).__init__(assembly, [beam_a, beam_b])       
        self.beam_a = beam_a
        self.beam_b = beam_b
        self.beam_a_key = None
        self.beam_b_key = None
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


    # TODO one function create_negative_volumes > return breps

    def half_lap(beam_a, beam_b, cut):
    
        # Get Planes from Beams
        plane_a = Plane.from_frame(beam_a.faces[3])
        plane_a_side1 = Plane.from_frame(beam_a.faces[0])
        plane_a_side2 = Plane.from_frame(beam_a.faces[2])
        plane_b1 = Plane.from_frame(beam_b.faces[1])
        plane_b3 = Plane.from_frame(beam_b.faces[3])
        plane_b_side1 = Plane.from_frame(beam_b.faces[0])
        plane_b_side2 = Plane.from_frame(beam_b.faces[2])

        # Create Cut Plane
        def cutplane(centerline_a, centerline_b, plane_a, plane_b, max_distance):
            int_a, int_b = intersection_line_line_3D(centerline_a, centerline_b, max_distance)
            int_a, _ = int_a
            int_b, _ = int_b
            point_cut = Point(*midpoint_point_point(int_a, int_b))
            if cut == None or "A":
                plane = plane_a
            if cut == "B":
                plane = plane_b
            plane_cut = Plane(point_cut, plane[1])
            return plane_cut

        max_distance = 0.5
        plane_cut = cutplane(beam_a.centerline, beam_b.centerline, plane_a, plane_b3, max_distance)

        # Lines as Frame Intersections
        lines = []
        x = intersection_plane_plane(plane_a_side1, plane_b_side1)
        lines.append(Line(x[0], x[1]))
        x = intersection_plane_plane(plane_a_side1, plane_b_side2)
        lines.append(Line(x[0], x[1]))
        x = intersection_plane_plane(plane_a_side2, plane_b_side2)
        lines.append(Line(x[0], x[1]))
        x = intersection_plane_plane(plane_a_side2, plane_b_side1)
        lines.append(Line(x[0], x[1]))

        # Decide Cut Direction of beam_b
        vector_angle_a_b1 = angle_vectors(plane_a[1], plane_b1[1])
        vector_angle_a_b3 = angle_vectors(plane_a[1], plane_b3[1])
        if vector_angle_a_b1 > vector_angle_a_b3:
            plane_b = plane_b1
        else:
            plane_b = plane_b3

        # Function Polyhedrons
        def create_polyhedrons(plane1, plane2, lines):
            points = []
            for i in lines:
                point = intersection_line_plane(i, plane1)
                point = Point(*point)
                points.append(point)
            for i in lines:
                point = intersection_line_plane(i, plane2)
                point = Point(*point)
                points.append(point)
            return Polyhedron(points, [[0,1,2,3], [4,5,6,7], [0,1,5,4], [1,5,6,2], [2,6,7,3], [3,7,4,0]])
        
        # Create Polyhedrons
        negative_polyhedron_beam_a = create_polyhedrons(plane_a, plane_cut, lines)
        negative_polyhedron_beam_b = create_polyhedrons(plane_cut, plane_b, lines)
        
        # Show Polyhedrons
        negative_polyhedron_beam_a = Artist(negative_polyhedron_beam_a).draw()
        negative_polyhedron_beam_b = Artist(negative_polyhedron_beam_b).draw()
        
        # Breps from Polyhedrons
        negative_brep_beam_a = RhinoBrep.CreateFromMesh(rs.coercemesh(negative_polyhedron_beam_a), True)
        negative_brep_beam_b = RhinoBrep.CreateFromMesh(rs.coercemesh(negative_polyhedron_beam_b), True)
        return negative_brep_beam_a, negative_brep_beam_b

    #TODO ba.apply_features()
    negative_brep_beam_a, negative_brep_beam_b = half_lap(beam_a, beam_b, cut)
    beam_a.add_feature(BeamBooleanSubtraction(negative_brep_beam_a))
    beam_a.apply_features()
    beam_b.add_feature(BeamBooleanSubtraction(negative_brep_beam_b))
    beam_b.apply_features()



    def restore_beams_from_keys(self, assemly):
        """After de-serialization, resotres references to the main and cross beams saved in the assembly."""
        self.beam_a = assemly.find_by_key(self.beam_a_key)
        self.beam_b = assemly.find_by_key(self.beam_b_key)
    
    def add_features(self):
        # TODO: implement
        negative_brep_beam_a = None # TODO: figure out the negative for beam a
        negative_brep_beam_b = None # TODO: figure out the negative for beam b
        self.beam_a.add_feature(BeamBooleanSubtraction(negative_brep_beam_a))
        self.beam_b.add_feature(BeamBooleanSubtraction(negative_brep_beam_b))        
