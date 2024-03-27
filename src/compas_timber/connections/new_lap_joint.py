from ast import main
from compas.geometry import Frame
from compas.geometry import Line
from compas.geometry import Plane
from compas.geometry import Point
from compas.geometry import Polyhedron
from compas.geometry import Vector
from compas.geometry import angle_vectors
from compas.geometry import cross_vectors
from compas.geometry import dot_vectors
from compas.geometry import intersection_line_plane
from compas.geometry import intersection_line_line
from compas.geometry import intersection_plane_plane_plane
from compas.geometry import closest_point_on_plane
from compas.geometry import Transformation
from compas.geometry import Brep
from compas.geometry import Box
from compas_timber.parts import BrepSubtraction
from compas_timber.parts.features import MillVolume
from .joint import Joint


class NewLapJoint(Joint):
    """Abstract Lap type joint with functions common to L-Lap, T-Lap, and X-Lap Joints.

    Do not instantiate directly. Please use `**LapJoint.create()` to properly create an instance of lap sub-class and associate it with an assembly.

    Parameters
    ----------
    main_beam : :class:`~compas_timber.parts.Beam`
        The main beam to be joined.
    cross_beam : :class:`~compas_timber.parts.Beam`
        The cross beam to be joined.
    flip_lap_side : bool
        If True, the lap is flipped to the other side of the beams.
    cut_plane_bias : float
        Allows lap to be shifted deeper into one beam or the other. Value should be between 0 and 1.0 without completely cutting through either beam. Default is 0.5.

    Attributes
    ----------
    beams : list(:class:`~compas_timber.parts.Beam`)
        The beams joined by this joint.
    beams : list(:class:`~compas_timber.parts.Beam`)
        The main beam to be joined.
    main_beam_key : str
        The key of the main beam.
    cross_beam_key : str
        The key of the cross beam.
    features : list(:class:`~compas_timber.parts.Feature`)
        The features created by this joint.
    joint_type : str
        A string representation of this joint's type.

    """

    def __init__(self, main_beam=None, cross_beam=None, flip_lap_side=False, cut_plane_bias=0.5, frame=None, key=None):
        super(NewLapJoint, self).__init__(frame=frame, key=key)
        self.main_beam = main_beam
        self.cross_beam = cross_beam
        self.flip_lap_side = flip_lap_side
        self.cut_plane_bias = cut_plane_bias
        self.main_beam_key = main_beam.key if main_beam else None
        self.cross_beam_key = cross_beam.key if cross_beam else None
        self.features = []

    @property
    def __data__(self):
        data_dict = {
            "main_beam": self.main_beam_key,
            "cross_beam": self.cross_beam_key,
            "flip_lap_side": self.flip_lap_side,
            "cut_plane_bias": self.cut_plane_bias,
        }
        data_dict.update(super(NewLapJoint, self).__data__)
        return data_dict

    @classmethod
    def __from_data__(cls, value):
        instance = cls(
            frame=Frame.__from_data__(value["frame"]),
            key=value["key"],
            cut_plane_bias=value["cut_plane_bias"],
            flip_lap_side=value["flip_lap_side"],
        )
        instance.main_beam_key = value["main_beam"]
        instance.cross_beam_key = value["cross_beam"]
        return instance

    @property
    def beams(self):
        return [self.main_beam, self.cross_beam]

    def restore_beams_from_keys(self, assemly):
        """After de-serialization, resotres references to the main and cross beams saved in the assembly."""
        self.main_beam = assemly.find_by_key(self.main_beam_key)
        self.cross_beam = assemly.find_by_key(self.cross_beam_key)

    @staticmethod
    def _sort_beam_planes(beam, cutplane_vector):
        # Sorts the Beam Face Planes according to the Cut Plane
        frames = beam.faces[:4]
        planes = [Plane.from_frame(frame) for frame in frames]
        planes.sort(key=lambda x: angle_vectors(cutplane_vector, x.normal))
        return planes

    @staticmethod
    def _create_polyhedron(plane_a, lines, bias):  # Hexahedron from 2 Planes and 4 Lines
        # Step 1: Get 8 Intersection Points from 2 Planes and 4 Lines
        int_points = []
        for i in lines:
            point_top = intersection_line_plane(i, plane_a)
            point_bottom = i.point_at(1 - bias)  # intersection_line_plane(i, plane_b
            point_top = Point(*point_top)
            point_bottom = Point(*point_bottom)
            int_points.append(point_top)
            int_points.append(point_bottom)

        # Step 2: Check if int_points Order results in an inward facing Polyhedron
        test_face_vector1 = Vector.from_start_end(int_points[0], int_points[2])
        test_face_vector2 = Vector.from_start_end(int_points[0], int_points[6])
        test_face_normal = Vector.cross(test_face_vector1, test_face_vector2)
        check_vector = Vector.from_start_end(int_points[0], int_points[1])
        # Flip int_points Order if needed
        if angle_vectors(test_face_normal, check_vector) < 1:
            a, b, c, d, e, f, g, h = int_points
            int_points = b, a, d, c, f, e, h, g

        # Step 3: Create a Hexahedron with 6 Faces from the 8 Points
        return Polyhedron(
            int_points,
            [
                [1, 7, 5, 3],  # top
                [0, 2, 4, 6],  # bottom
                [1, 3, 2, 0],  # left
                [3, 5, 4, 2],  # back
                [5, 7, 6, 4],  # right
                [7, 1, 0, 6],  # front
            ],
        )

    def get_main_cutting_frame(self):
        beam_a, beam_b = self.beams
        assert beam_a and beam_b

        _, cfr = self.get_face_most_towards_beam(beam_a, beam_b)
        cfr = Frame(cfr.point, cfr.yaxis, cfr.xaxis)  # flip normal towards the inside of main beam
        return cfr

    def get_cross_cutting_frame(self):
        beam_a, beam_b = self.beams
        assert beam_a and beam_b
        _, cfr = self.get_face_most_towards_beam(beam_b, beam_a)
        return cfr

    def generate_intersect_geometry(self):
        print("get_intersect_points")
        points = []
        self.main_intersecting_geometry = {
            "beam": self.main_beam ,
            "faces": [],
            "face_points": {},
            "edges": [],
        }
        self.cross_intersecting_geometry = {
            "beam": self.cross_beam,
            "faces": [],
            "face_points": {},
            "edges": [],
            }
        face_indices = []
        edge_indices = []
        for i, face in enumerate(self.main_beam.faces[0:4]):
            face_pts = []
            for j, edge in enumerate(self.cross_beam.long_edges):
                point = intersection_line_plane(edge, Plane.from_frame(face))
                if point:

                    pt_xy = Point(*point)
                    pt_xy.transform(Transformation.from_frame_to_frame(face, Frame.worldXY()))
                    if i % 2 == 0:
                        if (pt_xy.x > 0) and (pt_xy.x < self.main_beam.blank_length)  and (pt_xy.y> 0) and (pt_xy.y < self.main_beam.width):
                            points.append(Point(*point))
                            face_indices.append(i)
                            edge_indices.append(j)
                            face_pts.append(point)
                    else:
                        if (pt_xy.x > 0) and (pt_xy.x < self.main_beam.blank_length)  and (pt_xy.y> 0) and (pt_xy.y < self.main_beam.height):
                            points.append(Point(*point))
                            face_indices.append(i)
                            edge_indices.append(j)
                            face_pts.append(point)
            if face_pts:
                self.cross_intersecting_geometry["face_points"][i] = face_pts
        self.main_intersecting_geometry["faces"] = set([self.main_beam.faces[i] for i in face_indices])
        self.cross_intersecting_geometry["edges"] = set([self.cross_beam.long_edges[i] for i in edge_indices])


        for i, face in enumerate(self.cross_beam.faces[0:4]):
            for j, edge in enumerate(self.main_beam.long_edges):
                point = intersection_line_plane(edge, Plane.from_frame(face))
                if point:
                    pt_xy = Point(*point)
                    pt_xy.transform(Transformation.from_frame_to_frame(face, Frame.worldXY()))
                    if i%2 == 0:
                        if pt_xy.x > 0 and pt_xy.x < self.cross_beam.blank_length  and pt_xy.y> 0 and pt_xy.y < self.cross_beam.width:
                            points.append(Point(*point))
                            face_indices.append(i)
                            edge_indices.append(j)
                            self.main_intersecting_geometry["edge_points"].append(point)
                    else:
                        if pt_xy.x > 0 and pt_xy.x < self.cross_beam.blank_length  and pt_xy.y> 0 and pt_xy.y < self.cross_beam.height:
                            points.append(Point(*point))
                            face_indices.append(i)
                            edge_indices.append(j)
                            self.main_intersecting_geometry["edge_points"].append(point)
        self.cross_intersecting_geometry["faces"] = set([self.cross_beam.faces[i] for i in face_indices])
        self.main_intersecting_geometry["edges"] = set([self.main_beam.long_edges[i] for i in edge_indices])
        return points


    def intersecting_geometry
        self.cross_intersecting_geometry = {
            "beam": self.cross_beam,
            "faces": [],
            "face_points": {},
            "edges": [],
            }
        face_indices = []
        edge_indices = []
        for i, face in enumerate(self.main_beam.faces[0:4]):
            face_pts = []
            for j, edge in enumerate(self.cross_beam.long_edges):
                point = intersection_line_plane(edge, Plane.from_frame(face))
                if point:

                    pt_xy = Point(*point)
                    pt_xy.transform(Transformation.from_frame_to_frame(face, Frame.worldXY()))
                    if i % 2 == 0:
                        if (pt_xy.x > 0) and (pt_xy.x < self.main_beam.blank_length)  and (pt_xy.y> 0) and (pt_xy.y < self.main_beam.width):
                            points.append(Point(*point))
                            face_indices.append(i)
                            edge_indices.append(j)
                            face_pts.append(point)
                    else:
                        if (pt_xy.x > 0) and (pt_xy.x < self.main_beam.blank_length)  and (pt_xy.y> 0) and (pt_xy.y < self.main_beam.height):
                            points.append(Point(*point))
                            face_indices.append(i)
                            edge_indices.append(j)
                            face_pts.append(point)
            if face_pts:
                self.cross_intersecting_geometry["face_points"][i] = face_pts




    # def parse_intersections(self):
    #     self.main_vol = None
    #     self.cross_vol = None
    #     if len(self.intersecting_geometry["edges"]) == 1:
    #         if len(self.cross_intersecting_geometry["edges"]) == 1: # diagonal-diagonal  crazy
    #             print("diagonal-diagonal")



    #             self.generate_diagonal_diagonal_vols()

    #             return
    #         elif len(self.intersecting_geometry["edges"]) == 2: # flat-diagonal
    #             self.generate_flat_diagonal_vols()

    #         elif len(self.intersecting_geometry["edges"]) > 2: # diagonal-embedded
    #             print("diagonal-embedded")
    #             return

    #     elif len(self.intersecting_geometry["edges"]) == 2:
    #         if len(self.intersecting_geometry["edges"]) == 1: # flat-diagonal
    #             self.generate_flat_diagonal_vols()

    #         elif len(self.intersecting_geometry["edges"]) == 2: # flat-flat
    #             self.generate_flat_flat_vols()

    #         elif len(self.intersecting_geometry["edges"]) > 2: # flat-embedded
    #             self.generate_embedded_vols()
    #             return

    #     elif len(self.intersecting_geometry["edges"]) == 3:
    #         if len(self.intersecting_geometry["edges"]) == 1: # embedded-diagonal
    #             print("embedded-diagonal")
    #             return
    #         elif len(self.intersecting_geometry["edges"]) == 2: # embedded-flat
    #             self.generate_embedded_vols()
    #             return
    #         elif len(self.intersecting_geometry["edges"]) > 2: # embedded-embedded
    #             print("embedded-embedded")
    #             return

    #     elif len(self.intersecting_geometry["edges"]) == 4:
    #         if len(self.intersecting_geometry["faces"]) > 1: # embedded-embedded
    #             print("cfi len = ", len(self.intersecting_geometry["faces"]))
    #             if abs(self.intersecting_geometry["faces"][0] - self.intersecting_geometry["faces"][-1]) == 2 or len(self.intersecting_geometry["faces"]) == 3:
    #                 print("embedded-flat")
    #                 self.generate_through_vols()
    #             else:
    #                 print("THIS embedded-diagonal")
    #                 return
    #         if len(self.intersecting_geometry["edges"]) == 1: # embedded-diagonal
    #             print("embedded-diagonal")
    #             return
    #         elif len(self.intersecting_geometry["edges"]) == 2: # embedded-flat
    #             self.generate_embedded_vols()
    #             return
    #         elif len(self.intersecting_geometry["edges"]) > 2: # embedded-embedded
    #             print("embedded-embedded")
    #             return

    def get_diagonal_plane(self):
        pass

    def get_beam_cut_frame(self, intersect_info, other_beam):
        if len(intersect_info["edges"]) == 1:        #diagonal
            pt = intersect_info["edges"][0].start
            vector = cross_vectors(intersect_info["edges"][0].direction, other_beam.centerline.direciton)
            return Frame(pt, intersect_info["beam"].frame.xaxis, other_beam.frame.yaxis)
        else:
            intersection = intersection_line_line(intersect_info["beam"].centerline, other_beam.centerline)
            if intersection[0] != intersection[1]:
                vector = Vector.from_start_end(intersection[1], intersection[0])
            else:
                vector = cross_vectors(intersect_info["beam"].frame.xaxis, other_beam.frame.xais)
            angles_dict = Joint.beam_side_incidence_from_vector(intersect_info["beam"], vector)
            min_index = min(angles_dict, key=angles_dict.get)
            max_index = max(angles_dict, key=angles_dict.get)
            if len(intersect_info["edges"] < 4):
                return intersect_info["beam"].faces[max_index]
            else:
                return [intersect_info["beam"].faces[min_index], intersect_info["beam"].faces[max_index]]






    def generate_sub_vols_from_cut_plane(self):
        self.main_vol = Brep.from_box(self.main_beam.blank)
        try:
            self.main_vol.trim(self.cut_plane)
        except:
            print("main failed")
            pass
        cut_plane = Plane(self.cut_plane.point, -self.cut_plane.normal)
        self.cross_vol = Brep.from_box(self.cross_beam.blank)
        try:
            self.cross_vol.trim(cut_plane)
        except:
            print("cross failed")
            pass


    def get_diagonal_diagonal_plane(self):
        print("DID diagonal-diagonal")
        pts = intersection_line_line(self.main_beam.long_edges[self.intersecting_geometry["edges"][0]], self.cross_beam.long_edges[self.intersecting_geometry["edges"][0]])
        pt = Point(*pts[0])* self.cut_plane_bias + Point(*pts[1]) * (1-self.cut_plane_bias)
        return Plane(pt, Vector.from_start_end(pts[1], pts[0]))



    def get_flat_diagonal_plane(self):
        if len(self.intersecting_geometry["edge_points"]) == 4:
            pts = self.intersecting_geometry["edge_points"][0:3]
            pt = self.cross_beam.long_edges[self.intersecting_geometry["edges"][0]].start
            flip = False
        else:
            pts = self.intersecting_geometry["edge_points"][0:3]
            pt = self.main_beam.long_edges[self.intersecting_geometry["edges"][0]].start
            flip = True
        vector = cross_vectors(self.cross_beam.centerline.vector, self.main_beam.centerline.vector)
        diagonal_plane = Plane(pt, vector)
        pts_projected = []
        bias = self.cut_plane_bias if flip else 1 - self.cut_plane_bias
        for point in pts[0:3]:
            pt_proj = closest_point_on_plane(point, diagonal_plane)
            pts_projected.append(Point(*pt_proj) * self.cut_plane_bias + Point(*point) * (1-self.cut_plane_bias))
        print(pts_projected)
        self.cut_plane = Plane.from_three_points(*[Point(*cut_point) for cut_point in pts_projected])
        self.generate_sub_vols_from_cut_plane()



    def generate_flat_flat_vols(self):
        main_pts = self.intersecting_geometry["edge_points"][0:3]
        cross_pts = self.intersecting_geometry["edge_points"][0:3]
        cross_plane = Plane.from_three_points(*[Point(*cut_point) for cut_point in cross_pts])

        cut_pts = []
        for point in main_pts[0:3]:
            pt_proj = closest_point_on_plane(point, cross_plane)
            cut_pts.append(Point(*pt_proj) * self.cut_plane_bias + Point(*point) * (1-self.cut_plane_bias))
        print(cut_pts)
        self.cut_plane = Plane.from_three_points(*[Point(*cut_point) for cut_point in cut_pts])
        self.generate_sub_vols_from_cut_plane()


    @property
    def get_cut_plane(self):
        main_cut_frame = self.get_beam_cut_frame(self.main_intersecting_geometry, self.cross_beam)
        cross_cut_frame = self.get_beam_cut_frame(self.cross_intersecting_geometry, self.main_beam)
        rebase = Transformation.from_frame(main_cut_frame)
        pts = [[0,0,0], [100,0,0], [0,100,0]]
        main_pts = [pt.transform(rebase) for pt in pts]
        cross_pts = [closest_point_on_plane(pt, cross_cut_frame) for pt in main_pts]
        cut_pts = []
        for i in range(3):
            cut_pts.append(main_pts[i] * self.cut_plane_bias + cross_pts[i] * (1-self.cut_plane_bias))
        plane = Plane.from_three_points(*cut_pts)
        int_pts = intersection_line_line(self.cross_beam.centerline, self.main_beam.centerline)
        if dot_vectors(plane.normal, Vector.from_start_end(*int_pts)) < 0:
            plane = Plane(plane.point, -plane.normal)
        return plane




    def generate_vols(self):






    def generate_standard_vols(self):
        print("embedded")
        beam_a, beam_b = self.beams
        assert beam_a and beam_b

        # Get Cut Plane
        plane_cut_vector = beam_a.centerline.vector.cross(beam_b.centerline.vector)

        if self.flip_lap_side:
            plane_cut_vector = -plane_cut_vector

        # Get Beam Faces (Planes) in right order
        planes_main = self._sort_beam_planes(beam_a, plane_cut_vector)
        plane_a0, plane_a1, plane_a2, plane_a3 = planes_main

        planes_cross = self._sort_beam_planes(beam_b, -plane_cut_vector)
        plane_b0, plane_b1, plane_b2, plane_b3 = planes_cross

        # Lines as Frame Intersections
        lines = []

        pt_a = intersection_plane_plane_plane(plane_a1, plane_b1, plane_a0)
        pt_b = intersection_plane_plane_plane(plane_a1, plane_b1, plane_b0)
        lines.append(Line(pt_a, pt_b))

        pt_a = intersection_plane_plane_plane(plane_a1, plane_b2, plane_a0)
        pt_b = intersection_plane_plane_plane(plane_a1, plane_b2, plane_b0)
        lines.append(Line(pt_a, pt_b))

        pt_a = intersection_plane_plane_plane(plane_a2, plane_b2, plane_a0)
        pt_b = intersection_plane_plane_plane(plane_a2, plane_b2, plane_b0)
        lines.append(Line(pt_a, pt_b))

        pt_a = intersection_plane_plane_plane(plane_a2, plane_b1, plane_a0)
        pt_b = intersection_plane_plane_plane(plane_a2, plane_b1, plane_b0)
        lines.append(Line(pt_a, pt_b))

        # Create Polyhedrons
        self.cross_vol =  self._create_polyhedron(plane_a0, lines, self.cut_plane_bias)
        self.main_vol = self._create_polyhedron(plane_b0, lines, self.cut_plane_bias)

    def add_features(self):
        self.generate_intersect_geometry()
        self.parse_intersections()

        if self.main_vol:
            if isinstance(self.main_vol, Brep):
                self.cross_beam.add_features(BrepSubtraction(self.main_vol))
            if isinstance(self.main_vol, Polyhedron):
                    self.cross_beam.add_features(MillVolume(self.main_vol))
        if self.cross_vol:
            if isinstance(self.cross_vol, Brep):
                self.main_beam.add_features(BrepSubtraction(self.cross_vol))
            if isinstance(self.cross_vol, Polyhedron):
                self.main_beam.add_features(MillVolume(self.cross_vol))


