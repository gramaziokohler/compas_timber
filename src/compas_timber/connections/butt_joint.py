from compas.geometry import Frame
from compas.geometry import intersection_plane_plane_plane
from compas.geometry import subtract_vectors
from compas.geometry import dot_vectors
from compas.geometry import closest_point_on_line
from compas.geometry import distance_line_line
from compas.geometry import intersection_plane_plane
from compas.geometry import intersection_line_plane
from compas.geometry import intersection_line_line
from compas.geometry import Plane
from compas.geometry import Line
from compas.geometry import Polyhedron
from compas.geometry import Point
from compas.geometry import Vector
from compas.geometry import Transformation
from compas.geometry import Polyline
from compas.geometry import Curve
from compas.geometry import angle_vectors_signed
from compas.geometry import angle_vectors
from compas.geometry import cross_vectors
from compas.geometry import Brep
from compas.geometry import Scale
from .joint import Joint
import math


class ButtJoint(Joint):
    """Abstract Lap type joint with functions common to L-Butt and T-Butt Joints.

    Do not instantiate directly. Please use `**LapJoint.create()` to properly create an instance of lap sub-class and associate it with an assembly.

    Parameters
    ----------
    assembly : :class:`~compas_timber.assembly.TimberAssembly`
        The assembly associated with the beams to be joined.
    main_beam : :class:`~compas_timber.parts.Beam`
        The main beam to be joined.
    cross_beam : :class:`~compas_timber.parts.Beam`
        The cross beam to be joined.
    small_beam_butts : bool, default False
        If True, the beam with the smaller cross-section will be trimmed. Otherwise, the main beam will be trimmed.
    modify_cross : bool, default True
        If True, the cross beam will be extended to the opposite face of the main beam and cut with the same plane.
    reject_i : bool, default False
        If True, the joint will be rejected if the beams are not in I topology (i.e. main butts at crosses end).

    Attributes
    ----------
    beams : list(:class:`~compas_timber.parts.Beam`)
        The beams joined by this joint.
    joint_type : str
        A string representation of this joint's type.

    """

    def __init__(self, main_beam=None, cross_beam=None, mill_depth=0, drill_diameter=0.0, birdsmouth=False, stepjoint=False, **kwargs):
        super(ButtJoint, self).__init__(**kwargs)
        self.main_beam = main_beam
        self.cross_beam = cross_beam
        self.main_beam_key = main_beam.key if main_beam else None
        self.cross_beam_key = cross_beam.key if cross_beam else None
        self.mill_depth = mill_depth
        self.drill_diameter = float(drill_diameter)
        self.birdsmouth = birdsmouth
        self.stepjoint = stepjoint
        self.btlx_params_main = {}
        self.btlx_params_cross = {}
        self.btlx_drilling_params_cross = {}
        self.btlx_stepjoint_params_main = {}
        self.btlx_params_stepjoint_cross = {}
        self.features = []
        self.test = []

    @property
    def __data__(self):
        data_dict = {
            "main_beam_key": self.main_beam_key,
            "cross_beam_key": self.cross_beam_key,
            "mill_depth": self.mill_depth,
        }
        data_dict.update(super(ButtJoint, self).__data__)
        return data_dict

    @classmethod
    def __from_data__(cls, value):
        instance = cls(**value)
        instance.main_beam_key = value["main_beam_key"]
        instance.cross_beam_key = value["cross_beam_key"]
        return instance

    @property
    def beams(self):
        return [self.main_beam, self.cross_beam]

    def restore_beams_from_keys(self, assemly):
        """After de-serialization, resotres references to the main and cross beams saved in the assembly."""
        self.main_beam = assemly.find_by_key(self.main_beam_key)
        self.cross_beam = assemly.find_by_key(self.cross_beam_key)

    def side_surfaces_cross(self):
        assert self.main_beam and self.cross_beam

        face_dict = Joint._beam_side_incidence(self.main_beam, self.cross_beam, ignore_ends=True)
        face_indices = face_dict.keys()
        angles = face_dict.values()
        angles, face_indices = zip(*sorted(zip(angles, face_indices)))

        return [self.cross_beam.faces[(face_indices[0] + 1) % 4], self.cross_beam.faces[(face_indices[0] + 3) % 4]]

    def front_back_surface_main(self):
        assert self.main_beam and self.cross_beam

        face_dict = Joint._beam_side_incidence(self.cross_beam, self.main_beam, ignore_ends=True)
        face_indices = face_dict.keys()
        angles = face_dict.values()
        angles, face_indices = zip(*sorted(zip(angles, face_indices)))
        return self.main_beam.faces[face_indices[0]], self.main_beam.faces[face_indices[3]]

    def back_surface_main(self):
        face_dict = Joint._beam_side_incidence(self.main_beam, self.cross_beam, ignore_ends=True)
        face_dict.sort(lambda x: x.values())
        return face_dict.values()[3]

    def get_main_cutting_plane(self):
        assert self.main_beam and self.cross_beam
        self.reference_side_index_cross, cfr = self.get_face_most_ortho_to_beam(
            self.main_beam, self.cross_beam, ignore_ends=True
        )

        cross_mating_frame = cfr.copy()
        cfr = Frame(cfr.point, cfr.xaxis, cfr.yaxis * -1.0)  # flip normal
        cfr.point = cfr.point + cfr.zaxis * self.mill_depth

        return cfr, cross_mating_frame

    def subtraction_volume(self):
        """Returns the volume to be subtracted from the cross beam."""
        vertices = []
        front_frame, back_frame = self.front_back_surface_main() #main_beam
        top_frame, bottom_frame = self.get_main_cutting_plane() #cross_beam -- cutting/offsetted_cutting plane
        sides = self.side_surfaces_cross() #cross_beam -- side faces
        for i, side in enumerate(sides):
            points = []
            for frame in [bottom_frame, top_frame]:
                for fr in [front_frame, back_frame]:
                    points.append(
                        intersection_plane_plane_plane(
                            Plane.from_frame(side), Plane.from_frame(frame), Plane.from_frame(fr)
                        )
                    )
            pv = [subtract_vectors(pt, self.cross_beam.blank_frame.point) for pt in points]
            dots = [dot_vectors(v, self.cross_beam.centerline.direction) for v in pv]
            dots, points = zip(*sorted(zip(dots, points)))
            min_pt, max_pt = points[0], points[-1]
            if i == 1:
                self.btlx_params_cross["start_x"] = abs(dots[0])
            top_line = Line(*intersection_plane_plane(Plane.from_frame(side), Plane.from_frame(top_frame)))
            top_min = Point(*closest_point_on_line(min_pt, top_line))
            top_max = Point(*closest_point_on_line(max_pt, top_line))

            bottom_line = Line(*intersection_plane_plane(Plane.from_frame(side), Plane.from_frame(bottom_frame)))

            bottom_min = Point(*closest_point_on_line(min_pt, bottom_line))
            bottom_max = Point(*closest_point_on_line(max_pt, bottom_line))

            vertices.extend([Point(*top_min), Point(*top_max), Point(*bottom_max), Point(*bottom_min)])

        top_front = Line(vertices[0], vertices[4])
        top_back = Line(vertices[1], vertices[5])
        _len = distance_line_line(top_front, top_back)

        front_line = Line(*intersection_plane_plane(Plane.from_frame(front_frame), Plane.from_frame(top_frame)))

        self.btlx_params_cross["depth"] = self.mill_depth

        self.btlx_params_cross["width"] = (
            self.cross_beam.height if self.reference_side_index_cross % 2 == 0 else self.cross_beam.width
        )

        self.btlx_params_cross["length"] = _len
        if dot_vectors(top_frame.yaxis, front_line.direction) < 0:
            front_line = Line(front_line.end, front_line.start)
        self.btlx_params_cross["angle"] = abs(
            angle_vectors_signed(top_frame.xaxis, front_line.direction, top_frame.zaxis, deg=True)
        )

        center = (vertices[0] + vertices[1] + vertices[2] + vertices[3]) * 0.25
        angle = angle_vectors_signed(
            subtract_vectors(vertices[0], center), subtract_vectors(vertices[1], center), sides[0].zaxis
        )
        if angle > 0:
            ph = Polyhedron(
                vertices, [[0, 1, 2, 3], [1, 0, 4, 5], [2, 1, 5, 6], [3, 2, 6, 7], [0, 3, 7, 4], [7, 6, 5, 4]]
            )
        else:
            ph = Polyhedron(
                vertices, [[3, 2, 1, 0], [5, 4, 0, 1], [6, 5, 1, 2], [7, 6, 2, 3], [4, 7, 3, 0], [4, 5, 6, 7]]
            )

        return ph

    def calc_params_birdsmouth(self):
        """
        Calculate the parameters for a birdsmouth joint.

        Parameters:
        ----------
            joint (object): The joint object.
            main_part (object): The main part object.
            cross_part (object): The cross part object.

        Returns:
        ----------
            bool: True if the joint creation is successful, False otherwise.

        """
        face_dict = self._beam_side_incidence(self.main_beam, self.cross_beam, ignore_ends=True)
        face_keys = sorted([key for key in face_dict.keys()], key=face_dict.get)

        frame1, og_frame = self.get_main_cutting_plane()  # offset pocket mill plane
        frame2 = self.cross_beam.faces[face_keys[1]]

        self.test.append(og_frame)

        plane1, plane2 = Plane(frame1.point, -frame1.zaxis), Plane.from_frame(frame2)
        intersect_vec = Vector.from_start_end(*intersection_plane_plane(plane2, plane1))

        angles_dict = {}
        for i, face in enumerate(self.main_beam.faces[0:4]):
            angles_dict[i] = face.normal.angle(intersect_vec)
        self.main_face_index = min(angles_dict.keys(), key=angles_dict.get)
        ref_frame = self.main_beam.faces[self.main_face_index]

        if angle_vectors(og_frame.zaxis, self.main_beam.centerline.direction, deg = True) < 1:
            self.birdsmouth = False
            return False

        ref_frame.point = self.main_beam.blank_frame.point
        if self.main_face_index % 2 == 0:
            ref_frame.point = ref_frame.point - ref_frame.yaxis * self.main_beam.height * 0.5
            ref_frame.point = ref_frame.point + ref_frame.zaxis * self.main_beam.width * 0.5
        else:
            ref_frame.point = ref_frame.point - ref_frame.yaxis * self.main_beam.width * 0.5
            ref_frame.point = ref_frame.point + ref_frame.zaxis * self.main_beam.height * 0.5


        cross_ref_main = cross_vectors(og_frame.zaxis, self.main_beam.centerline.direction)
        cross_centerlines = cross_vectors(self.main_beam.centerline.direction, self.cross_beam.centerline.direction)
        self.test.append(Line(og_frame.point, og_frame.point + cross_ref_main * 100))
        angle = angle_vectors(cross_ref_main, og_frame.yaxis, deg=True)
        angle2 = angle_vectors(cross_centerlines, self.main_beam.frame.zaxis, deg=True)
        angle2 = round(angle2, 1) - 180
        print("angle2", angle2+180)
        threshold_angle = 3.0
        # if angle < 1.0 or angle > 179.0:
        #     self.birdsmouth = False
        #     return False

        if abs(angle2)%90 <= threshold_angle or abs((abs(angle2)-90)%90) <= threshold_angle:
            print("smaller than threshold", abs(angle2%90))
            self.birdsmouth = False
            return False

        start_point = Point(*intersection_plane_plane_plane(plane1, plane2, Plane.from_frame(ref_frame)))
        coord_point = start_point.transformed(Transformation.from_frame_to_frame(ref_frame, Frame.worldXY()))
        StartX, StartY = coord_point[0], coord_point[1]

        self.bm_sub_volume = Brep.from_box(self.cross_beam.blank)
        self.bm_sub_volume.translate(Vector.from_start_end(og_frame.point, frame1.point))
        s = Scale.from_factors([10.0, 10.0, 10.0], Frame(start_point, ref_frame.xaxis, ref_frame.yaxis))
        self.bm_sub_volume.transform(s)


        dot_frame1 = plane1.normal.dot(ref_frame.yaxis)
        if dot_frame1 > 0:
            plane1, plane2 = plane2, plane1

        intersect_vec1 = Vector.from_start_end(*intersection_plane_plane(plane1, Plane.from_frame(ref_frame)))
        intersect_vec2 = Vector.from_start_end(*intersection_plane_plane(plane2, Plane.from_frame(ref_frame)))

        if self.ends[str(self.main_beam.key)] == "start":
            reference_vector = ref_frame.xaxis
        else:
            reference_vector = -ref_frame.xaxis

        if intersect_vec1.dot(ref_frame.yaxis) < 0:
            intersect_vec1 = -intersect_vec1
        if intersect_vec2.dot(ref_frame.yaxis) < 0:
            intersect_vec2 = -intersect_vec2

        Angle1 = angle_vectors(intersect_vec1, reference_vector, deg=True)
        Angle2 = angle_vectors(intersect_vec2, reference_vector, deg=True)

        Inclination1 = angle_vectors(ref_frame.zaxis, plane1.normal, deg=True)
        Inclination2 = angle_vectors(ref_frame.zaxis, plane2.normal, deg=True)

        self.btlx_params_main = {
            "Orientation": self.ends[str(self.main_beam.key)],
            "StartX": StartX,
            "StartY": StartY,
            "Angle1": Angle1,
            "Inclination1": Inclination1,
            "Angle2": Angle2,
            "Inclination2": Inclination2,
            "ReferencePlaneID": self.main_face_index,
        }

        return True


    def calc_params_drilling(self):
        """
        Calculate the parameters for a drilling joint.

        Parameters:
        ----------
            joint (object): The joint object.
            main_part (object): The main part object.
            cross_part (object): The cross part object.

        Returns:
        ----------
            dict: A dictionary containing the calculated parameters for the drilling joint

        """

        _cut_plane, cutting_frame = self.get_main_cutting_plane()
        ref_plane = Plane.from_frame(cutting_frame)

        angles_dict = {}
        for i, face in enumerate(self.cross_beam.faces[0:4]):
            angles_dict[i] = face.normal.angle(cutting_frame.normal)
        cross_face_index = min(angles_dict.keys(), key=angles_dict.get)
        ref_frame = self.cross_beam.faces[cross_face_index]

        ref_frame.point = self.cross_beam.blank_frame.point
        if cross_face_index % 2 == 0:
            ref_frame.point = ref_frame.point - ref_frame.yaxis * self.cross_beam.height * 0.5
            ref_frame.point = ref_frame.point + ref_frame.zaxis * self.cross_beam.width * 0.5
        else:
            ref_frame.point = ref_frame.point - ref_frame.yaxis * self.cross_beam.width * 0.5
            ref_frame.point = ref_frame.point + ref_frame.zaxis * self.cross_beam.height * 0.5

        point_xyz = (intersection_line_plane(self.main_beam.centerline, ref_plane))
        start_point = Point(*point_xyz)
        ref_point = start_point.transformed(Transformation.from_frame_to_frame(ref_frame, Frame.worldXY()))
        StartX, StartY = ref_point[0], ref_point[1]

        param_point_on_line = self.main_beam.centerline.closest_point(start_point, True)[1]
        if param_point_on_line > 0.5:
            line_point = self.main_beam.centerline.end
        else:
            line_point = self.main_beam.centerline.start
        projected_point = ref_plane.projected_point(line_point)

        center_line_vec = Vector.from_start_end(start_point, line_point)
        projected_vec = Vector.from_start_end(start_point, projected_point)
        Angle = 180 - math.degrees(ref_frame.xaxis.angle_signed(projected_vec, ref_frame.zaxis))
        inclination = projected_vec.angle(center_line_vec, True)
        if inclination == 0:
            Inclination = 90.0
        else:
            Inclination = inclination

        self.btlx_drilling_params_cross = {
            "ReferencePlaneID": cross_face_index,
            "StartX": StartX,
            "StartY": StartY,
            "Angle": Angle,
            "Inclination": float(Inclination),
            "Diameter": self.drill_diameter,
            "DepthLimited": "no",
            "Depth": 0.0

        }

        # Rhino geometry visualization
        line = Line(start_point, line_point)
        line.start.translate(-line.vector)
        normal_centerline_angle = 180-math.degrees(ref_frame.zaxis.angle(self.main_beam.centerline.direction))
        length = abs(self.cross_beam.width/(math.cos(math.radians(normal_centerline_angle))))
        return line, self.drill_diameter, length*3

    def calc_params_stepjoint(self):
        """
        Calculate the parameters for a step joint based on a Double Cut BTLx process.

        Parameters:
        ----------
            joint (object): The joint object.
            main_part (object): The main part object.
            cross_part (object): The cross part object.
            StepDepth (float): The depth of the step joint.

        Returns:
        ----------
            dict: A dictionary containing the calculated parameters for the step joint (double cut process)

        """
        #check if beams are coplanar
        cross_product_centerlines = self.main_beam.centerline.direction.cross(self.cross_beam.centerline.direction).unitized()
        dot_product_cp_crossbnormal = float(abs(cross_product_centerlines.dot(self.cross_beam.frame.normal)))
        dot_product_centerline = float(abs(self.main_beam.centerline.direction.dot(self.cross_beam.centerline.direction)))
        if 0.999 < dot_product_cp_crossbnormal or dot_product_cp_crossbnormal < 0.001:
            self.mill_depth = 0.0
        else:
            self.stepjoint = False
            return False

        # if 0.999 < dot_product_centerline or dot_product_centerline < 0.001:
        #     self.stepjoint = False
        #     return False
        # else:
        #     self.mill_depth = 0.0


        face_dict = self._beam_side_incidence(self.cross_beam, self.main_beam, ignore_ends=True)
        face_keys = sorted([key for key in face_dict.keys()], key=face_dict.get)

        # dot = self.main_beam.centerline.direction.dot(self.cross_beam.centerline.direction)

        if self.main_beam.centerline.end.on_line(self.cross_beam.centerline):
            centerline_vec = self.main_beam.centerline.direction
        else:
            centerline_vec = -self.main_beam.centerline.direction

        # finding the inclination of the strut based on the two centerlines
        StrutInclination = math.degrees(self.cross_beam.centerline.direction.angle(centerline_vec))

        inter_centerlines = intersection_line_line(self.cross_beam.centerline, self.main_beam.centerline)
        inter_param = self.cross_beam.centerline.closest_point(Point(*inter_centerlines[0]), True)[1]

        angles_dict = {}
        for i, face in enumerate(self.main_beam.faces[0:4]):
            angles_dict[i] = face.normal.angle_signed(self.main_beam.faces[face_keys[0]].normal, centerline_vec)
        faces_ordered = sorted(angles_dict.keys(), key=angles_dict.get)
        if (inter_param > 0.5 and StrutInclination < 90) or (inter_param < 0.5 and StrutInclination > 90):
            self.ref_face_id = faces_ordered[2]
        else:
            self.ref_face_id = faces_ordered[0]

        ref_face = self.main_beam.faces[self.ref_face_id]

        ref_face.point = self.main_beam.blank_frame.point
        if self.ref_face_id % 2 == 0:
            ref_face.point = ref_face.point - ref_face.yaxis * self.main_beam.height * 0.5
            ref_face.point = ref_face.point + ref_face.zaxis * self.main_beam.width * 0.5
        else:
            ref_face.point = ref_face.point - ref_face.yaxis * self.main_beam.width * 0.5
            ref_face.point = ref_face.point + ref_face.zaxis * self.main_beam.height * 0.5
        # print("StrutInclination", StrutInclination)
        if StrutInclination < 90:
            angle1 = (180 - StrutInclination)/2
            strut_inclination = StrutInclination
        else:
            angle1 = StrutInclination/2
            strut_inclination = 180 - StrutInclination
        # print("angle1", angle1)
        # print("strut_inclination", strut_inclination)

        buried_depth = math.sin(math.radians(90-strut_inclination))*self.main_beam.width/2
        blank_vert_depth = self.cross_beam.width/2 - buried_depth
        blank_edge_depth = abs(blank_vert_depth)/math.sin(math.radians(strut_inclination))
        startx = blank_edge_depth/2
        starty = self.main_beam.width/4

        outside_length = self.main_beam.width/math.tan(math.radians(strut_inclination))
        x_main_cutting_face = outside_length + blank_edge_depth

        vec_angle2 = Vector.from_start_end(Point(startx, self.cross_beam.width - starty), Point(x_main_cutting_face, 0))
        vec_xaxis = Vector.from_start_end(Point(startx, self.cross_beam.width - starty), Point(0, self.cross_beam.width - starty))
        angle2 = vec_xaxis.angle(vec_angle2, True)

        if self.ends[str(self.main_beam.key)] == "start":
            StartX = startx
            StartY = starty
            Angle1 = 180-angle1
            Angle2 = 180-angle2
        else:
            StartX = self.main_beam.blank_length - startx
            StartY = self.main_beam.width - starty
            Angle1 = angle2
            Angle2 = angle1

        # print("Angle1", Angle1)
        # print("Angle2", Angle2)


        Inclination1 = 90.0
        Inclination2 = 90.0
        self.btlx_params_stepjoint_main = {
            "Orientation": self.ends[str(self.main_beam.key)],
            "StartX": float(StartX),
            "StartY": float(StartY),
            "Angle1": float(Angle1),
            "Inclination1": float(Inclination1),
            "Angle2": Angle2,
            "Inclination2": Inclination2,
            "ReferencePlaneID": self.ref_face_id,
        }

        #find params lap cross beam
        angles_dict_cross = {}
        for i, face in enumerate(self.cross_beam.faces[0:4]):
            angles_dict_cross[i] = face.normal.dot(ref_face.normal)
        # print(angles_dict)
        self.cross_face_id = max(angles_dict_cross.keys(), key=angles_dict_cross.get)
        cross_face = self.cross_beam.faces[self.cross_face_id]

        cross_face.point = self.cross_beam.blank_frame.point
        if self.cross_face_id % 2 == 0:
            cross_face.point = cross_face.point - cross_face.yaxis * self.cross_beam.height * 0.5
            cross_face.point = cross_face.point + cross_face.zaxis * self.cross_beam.width * 0.5
        else:
            cross_face.point = cross_face.point - cross_face.yaxis * self.cross_beam.width * 0.5
            cross_face.point = cross_face.point + cross_face.zaxis * self.cross_beam.height * 0.5

        main_xypoint = Point(StartX, StartY, 0)
        # print("main_xypoint", main_xypoint)
        worldxy_xypoint = main_xypoint.transformed(Transformation.from_frame_to_frame(Frame.worldXY(), ref_face))
        # print("worldxy_xypoint", worldxy_xypoint)
        cross_xy_point = worldxy_xypoint.transformed(Transformation.from_frame_to_frame(cross_face, Frame.worldXY()))
        # print("cross_xy_point", cross_xy_point)

        StartX_cross = cross_xy_point[0]
        StartY_cross = cross_xy_point[1]

        if (inter_param > 0.5 and StrutInclination < 90) or (inter_param < 0.5 and StrutInclination > 90):
            orientation = self.ends[str(self.cross_beam.key)]
            if self.ends[str(self.cross_beam.key)] == "start":
                self.cross_face_id = min(angles_dict_cross.keys(), key=angles_dict_cross.get)
                cross_face = self.cross_beam.faces[self.cross_face_id]
                StartY_cross = self.cross_beam.width - StartY_cross
                if self.ends[str(self.main_beam.key)] == "start":
                    Angle_cross = 180 - Angle1
                    LeadAngle = 180 - (Angle1 - Angle2)
                else:
                    Angle_cross = Angle2
                    LeadAngle = 180 - (Angle1 - Angle2)

            else:
                if self.ends[str(self.main_beam.key)] == "start":
                    Angle_cross = 180 - Angle1
                    LeadAngle = 180 - (Angle1 - Angle2)
                else:
                    Angle_cross = Angle2
                    LeadAngle = 180 - (Angle1 - Angle2)
        else:
            if self.ends[str(self.cross_beam.key)] == "start":
                if self.ends[str(self.main_beam.key)] == "start":
                    orientation = "end"
                    Angle_cross = 180 - Angle1
                    LeadAngle = 180 - (Angle1 - Angle2)
                else:
                    orientation = "end"
                    Angle_cross = Angle2
                    LeadAngle = 180 - (Angle1 - Angle2)
            else:
                self.cross_face_id = min(angles_dict_cross.keys(), key=angles_dict_cross.get)
                cross_face = self.cross_beam.faces[self.cross_face_id]
                StartY_cross = self.cross_beam.width - StartY_cross
                if self.ends[str(self.main_beam.key)] == "start":
                    orientation = "start"
                    Angle_cross = 180 - Angle1
                    LeadAngle = 180 - (Angle1 - Angle2)
                else:
                    orientation = "start"
                    Angle_cross = Angle2
                    LeadAngle = (180 - Angle1) + Angle2


        main_most_towards = self.get_face_most_towards_beam(self.cross_beam, self.main_beam, ignore_ends=True)[1]
        cross_most_ortho = self.get_face_most_ortho_to_beam(self.main_beam, self.cross_beam, ignore_ends=True)[1]

        main_most_ortho = self.get_face_most_ortho_to_beam(self.cross_beam, self.main_beam, ignore_ends=True)[1]

        intersection_pt = Point(*intersection_plane_plane_plane(Plane.from_frame(main_most_towards), Plane.from_frame(cross_most_ortho), Plane.from_frame(ref_face)))
        intersection_pt2 = Point(*intersection_plane_plane_plane(Plane.from_frame(main_most_ortho), Plane.from_frame(cross_most_ortho), Plane.from_frame(ref_face)))
        # print("intersection_pt", intersection_pt)
        # print("intersection_pt2", intersection_pt2)

        self.btlx_params_stepjoint_cross = {
            "orientation": orientation,
            "start_x": StartX_cross,
            "start_y": StartY_cross,
            "angle": Angle_cross,
            "depth": 60.0,
            "lead_angle_parallel": "no",
            "lead_angle": LeadAngle,
            "ReferencePlaneID": self.cross_face_id,
        }


        #brep for main beam sub volume
        if (inter_param > 0.5 and StrutInclination < 90) or (inter_param < 0.5 and StrutInclination > 90):
            self.sj_main_sub_volume0 = Brep.from_box(self.cross_beam.blank)
            self.sj_main_sub_volume0.rotate(math.radians(180+Angle_cross+LeadAngle), ref_face.normal, intersection_pt2)
            self.sj_main_sub_volume1 = Brep.from_box(self.cross_beam.blank)
            self.sj_main_sub_volume1.rotate(math.radians(Angle_cross), ref_face.normal, intersection_pt)
        else:
            self.sj_main_sub_volume0 = Brep.from_box(self.cross_beam.blank)
            self.sj_main_sub_volume0.rotate(math.radians(Angle_cross), ref_face.normal, intersection_pt2)
            self.sj_main_sub_volume1 = Brep.from_box(self.cross_beam.blank)
            self.sj_main_sub_volume1.rotate(math.radians(180+Angle_cross+LeadAngle), ref_face.normal, intersection_pt)


        #brep for cross beam sub volume
        pts_ph = [worldxy_xypoint, intersection_pt, intersection_pt2]
        vertices_ph_sj_cross = pts_ph
        vertices_ph_sj_cross.extend([pt.translated(-ref_face.normal*60) for pt in pts_ph])
        # print(vertices_ph_sj_cross)
        if (inter_param > 0.5 and StrutInclination < 90) or (inter_param < 0.5 and StrutInclination > 90):
            # print("yes")
            self.ph_sj_cross = Polyhedron(vertices_ph_sj_cross, [[0, 1, 2], [3, 5, 4], [0, 3, 4, 1], [1, 4, 5, 2], [0, 2, 5, 3]])
        else:
            # print("no")
            self.ph_sj_cross = Polyhedron(vertices_ph_sj_cross, [[0, 2, 1], [3, 4, 5], [0, 1, 4, 3], [1, 2, 5, 4], [0, 3, 5, 2]])
        self.brep_sj_cross = Brep.from_mesh(self.ph_sj_cross)
        # print(self.brep_sj_cross)


        return True
