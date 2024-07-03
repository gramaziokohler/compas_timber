from compas.geometry import Frame
from compas.geometry import intersection_plane_plane_plane
from compas.geometry import intersection_line_plane
from compas.geometry import intersection_line_line
from compas.geometry import Plane
from compas.geometry import Line
from compas.geometry import Polyhedron
from compas.geometry import Point
from compas.geometry import Vector
from compas.geometry import Transformation
from compas.geometry import Brep
from compas.geometry import Scale
from .joint import Joint
import math

from compas_timber.parts import CutFeature
from compas_timber.parts import BrepSubtraction
from compas_timber.parts import DrillFeature

from .joint import BeamJoinningError
from .solver import JointTopology

class TStepJoint(Joint):
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

    SUPPORTED_TOPOLOGY = JointTopology.TOPO_T

    def __init__(self, main_beam=None, cross_beam=None, drill_diameter=0.0, **kwargs):
        super(TStepJoint, self).__init__(**kwargs)
        self.main_beam = main_beam
        self.cross_beam = cross_beam
        self.main_beam_key = main_beam.key if main_beam else None
        self.cross_beam_key = cross_beam.key if cross_beam else None
        self.drill_diameter = float(drill_diameter)
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
            "drill_diameter": self.drill_diameter,
        }
        data_dict.update(super(TStepJoint, self).__data__)
        return data_dict

    @property
    def joint_type(self):
        return "StepJoint"

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
        cfr.point = cfr.point + cfr.zaxis# * self.mill_depth

        return cfr, cross_mating_frame

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
        # offset_from_edge = self.drill_diameter*4
        offset_from_edge = 30.0
        #####condition for doing vertical drilling
        if inclination == 0 or 39.9999<inclination<40.00001 or 129.9999<inclination<130.00001:
            Inclination = 90.0
        # elif inclination < 45:
        #     start_displacement = (self.cross_beam.width/2) / math.sin(math.radians(inclination)) - offset_from_edge
        #     if dot_vectors(self.main_beam.centerline.direction, self.cross_beam.centerline.direction)>0:
        #         start_displacement = start_displacement
        #     else:
        #         start_displacement = -start_displacement
        #     vector = -cutting_frame.xaxis
        #     Inclination = 90.0
        #     StartX = StartX - start_displacement
        #     start_point.translate(vector*start_displacement)
        #     line_point = start_point.translated(cutting_frame.normal*100)
        else:
            Inclination = inclination
        # print("Inclination", Inclination)

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

    def check_stepjoint_boolean(self):
        cross_product_centerlines = self.main_beam.centerline.direction.cross(self.cross_beam.centerline.direction).unitized()
        dot_product_cp_crossbnormal = float(abs(cross_product_centerlines.dot(self.main_beam.frame.normal)))
        if 0.999 < dot_product_cp_crossbnormal or dot_product_cp_crossbnormal < 0.001:
            return True
        else:
            return False

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
        if self.main_beam.centerline.end.on_line(self.cross_beam.centerline):
            centerline_vec = self.main_beam.centerline.direction
        else:
            centerline_vec = -self.main_beam.centerline.direction


        ref_vec = centerline_vec.cross(self.cross_beam.centerline.direction).unitized()
        dot_dict = {}
        for i, face in enumerate(self.main_beam.faces[:4]):
            dot_dict[i] = face.normal.dot(ref_vec)
        faces_dot_sorted = sorted(dot_dict.keys(), key=dot_dict.get)

        # finding the inclination of the strut based on the two centerlines
        StrutInclination = math.degrees(self.cross_beam.centerline.direction.angle(centerline_vec))

        inter_centerlines = intersection_line_line(self.cross_beam.centerline, self.main_beam.centerline)
        inter_param = self.cross_beam.centerline.closest_point(Point(*inter_centerlines[0]), True)[1]
        if 89.9 <= StrutInclination <= 90.1:
            self.ref_face_id = faces_dot_sorted[3]
        elif StrutInclination < 89.9:
            self.ref_face_id = faces_dot_sorted[3]
        else:
            self.ref_face_id = faces_dot_sorted[0]

        ref_face = self.main_beam.faces[self.ref_face_id]

        ref_face.point = self.main_beam.blank_frame.point
        if self.ref_face_id % 2 == 0:
            ref_face.point = ref_face.point - ref_face.yaxis * self.main_beam.height * 0.5
            ref_face.point = ref_face.point + ref_face.zaxis * self.main_beam.width * 0.5
        else:
            ref_face.point = ref_face.point - ref_face.yaxis * self.main_beam.width * 0.5
            ref_face.point = ref_face.point + ref_face.zaxis * self.main_beam.height * 0.5

        strut_inclination = StrutInclination
        if StrutInclination <= 89.9:
            angle1 = (180 - StrutInclination)/2
            strut_inclination = StrutInclination
        elif StrutInclination >= 90.1:
            angle1 = StrutInclination/2
            strut_inclination = 180 - StrutInclination

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

        if 89.9 <= StrutInclination <= 90.1:
            startx_90deg = self.main_beam.width/4
            starty_90deg = self.main_beam.width/2
            angle_90deg = math.degrees(math.atan(startx_90deg/starty_90deg))
            if self.ends[str(self.main_beam.key)] == "start":
                StartX = startx_90deg
                StartY = starty_90deg
                Angle1 = 90+angle_90deg
                Angle2 = 90-angle_90deg
            else:
                StartX = self.main_beam.blank_length - startx_90deg
                StartY = starty_90deg
                Angle1 = 90+angle_90deg
                Angle2 = 90-angle_90deg
        else:
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
        worldxy_xypoint = main_xypoint.transformed(Transformation.from_frame_to_frame(Frame.worldXY(), ref_face))
        cross_xy_point = worldxy_xypoint.transformed(Transformation.from_frame_to_frame(cross_face, Frame.worldXY()))

        SI_angle = math.degrees(self.cross_beam.centerline.direction.angle(self.main_beam.centerline.direction))

        StartX_cross = cross_xy_point[0]
        StartY_cross = cross_xy_point[1]
        orientation = self.ends[str(self.cross_beam.key)]
        if 89.9 <= SI_angle <= 90.1:
            Angle_cross = angle_90deg
            LeadAngle = 180-angle_90deg*2
            if inter_param == 0.5:
                orientation = "start"
        elif SI_angle < 89.9:
            if self.ends[str(self.cross_beam.key)] == "start":
                if self.ends[str(self.main_beam.key)] == "start":
                    self.cross_face_id = min(angles_dict_cross.keys(), key=angles_dict_cross.get)
                    cross_face = self.cross_beam.faces[self.cross_face_id]
                    StartY_cross = self.cross_beam.width - StartY_cross
                    Angle_cross = 180 - Angle1
                    LeadAngle = 180 - (Angle1 - Angle2)
                else:
                    orientation = "end"
                    Angle_cross = Angle2
                    LeadAngle = 180 - (Angle1 - Angle2)
            else:
                if self.ends[str(self.main_beam.key)] == "start":
                    self.cross_face_id = min(angles_dict_cross.keys(), key=angles_dict_cross.get)
                    cross_face = self.cross_beam.faces[self.cross_face_id]
                    StartY_cross = self.cross_beam.width - StartY_cross
                    orientation = "start"
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
                    self.cross_face_id = min(angles_dict_cross.keys(), key=angles_dict_cross.get)
                    cross_face = self.cross_beam.faces[self.cross_face_id]
                    StartY_cross = self.cross_beam.width - StartY_cross
                    Angle_cross = Angle2
                    LeadAngle = 180 - (Angle1 - Angle2)
            else:
                if self.ends[str(self.main_beam.key)] == "start":
                    Angle_cross = 180 - Angle1
                    LeadAngle = 180 - (Angle1 - Angle2)
                else:
                    orientation = "start"
                    self.cross_face_id = min(angles_dict_cross.keys(), key=angles_dict_cross.get)
                    cross_face = self.cross_beam.faces[self.cross_face_id]
                    StartY_cross = self.cross_beam.width - StartY_cross
                    Angle_cross = Angle2
                    LeadAngle = (180 - Angle1) + Angle2


        main_most_towards = self.get_face_most_towards_beam(self.cross_beam, self.main_beam, ignore_ends=True)[1]
        cross_most_ortho = self.get_face_most_ortho_to_beam(self.main_beam, self.cross_beam, ignore_ends=True)[1]

        main_most_ortho = self.get_face_most_ortho_to_beam(self.cross_beam, self.main_beam, ignore_ends=True)[1]

        intersection_pt = Point(*intersection_plane_plane_plane(Plane.from_frame(main_most_towards), Plane.from_frame(cross_most_ortho), Plane.from_frame(ref_face)))
        intersection_pt2 = Point(*intersection_plane_plane_plane(Plane.from_frame(main_most_ortho), Plane.from_frame(cross_most_ortho), Plane.from_frame(ref_face)))

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

        #brep for cross beam sub volume
        pts_ph = [worldxy_xypoint, intersection_pt, intersection_pt2]
        vertices_ph_sj_cross = pts_ph
        vertices_ph_sj_cross.extend([pt.translated(-ref_face.normal*60) for pt in pts_ph])
        ph_sj_cross_0 = Polyhedron(vertices_ph_sj_cross, [[0, 2, 1], [3, 4, 5], [0, 1, 4, 3], [1, 2, 5, 4], [0, 3, 5, 2]])
        brep_sj_cross_0 = Brep.from_mesh(ph_sj_cross_0)
        if brep_sj_cross_0.volume > 0:
            self.brep_sj_cross = brep_sj_cross_0
        else:
            self.brep_sj_cross = Brep.from_mesh(Polyhedron(vertices_ph_sj_cross, [[0, 1, 2], [3, 5, 4], [0, 3, 4, 1], [1, 4, 5, 2], [0, 2, 5, 3]]))
        scale_points = [pt.translated(-ref_face.normal*30) for pt in pts_ph]
        scale_origin = scale_points[0]
        scale_xaxis = Vector.from_start_end(scale_origin, worldxy_xypoint)
        scale_yaxis = Vector.from_start_end(scale_origin, scale_points[1])

        # print(worldxy_xypoint/2)
        # scale_origin = (worldxy_xypoint+vertices_ph_sj_cross[3])/2
        # scale_xaxis = Vector.from_start_end(scale_origin, worldxy_xypoint)
        # scale_yaxis = Vector.from_start_end(scale_origin, Point((vertices_ph_sj_cross[1]+vertices_ph_sj_cross[4])/2))
        s0 = Scale.from_factors([2, 2, 2], Frame(scale_origin, scale_xaxis, scale_yaxis))
        self.brep_sj_cross.transform(s0)
        # print(self.brep_sj_cross.volume)

        vec_inter_pt = Vector.from_start_end(worldxy_xypoint, intersection_pt)
        vec_inter_pt2 = Vector.from_start_end(worldxy_xypoint, intersection_pt2)
        vec_edge = Vector.from_start_end(worldxy_xypoint, vertices_ph_sj_cross[3])

        main_cutting_face = self.get_main_cutting_plane()


        self.cutting_frame0 = Frame(worldxy_xypoint, vec_inter_pt, vec_edge)
        # print(self.cutting_frame0.normal.dot(main_cutting_face[0].normal))
        if self.cutting_frame0.normal.dot(main_cutting_face[0].normal) < 0:
            self.cutting_frame0 = Frame(worldxy_xypoint, vec_edge, vec_inter_pt)
        self.cutting_frame1 = Frame(worldxy_xypoint, vec_edge, vec_inter_pt2)
        # print(self.cutting_frame1.normal.dot(main_cutting_face[0].normal))
        if self.cutting_frame1.normal.dot(main_cutting_face[0].normal) < 0:
            self.cutting_frame1 = Frame(worldxy_xypoint, vec_inter_pt2, vec_edge)



        # print(SI_angle)
        # if 89.9 <= SI_angle <= 90.1:
        #     print("90=")
        #     self.cutting_frame0 = Frame(worldxy_xypoint, vec_inter_pt, vec_edge)
        #     self.cutting_frame1 = Frame(worldxy_xypoint, vec_edge, vec_inter_pt2)
        # elif SI_angle < 89.9:
        #     print("90-")
        #     self.cutting_frame0 = Frame(worldxy_xypoint, vec_inter_pt, vec_edge)
        #     self.cutting_frame1 = Frame(worldxy_xypoint, vec_edge, vec_inter_pt2)
        # else:
        #     print("90+")
        #     self.cutting_frame0 = Frame(worldxy_xypoint, vec_edge, vec_inter_pt)
        #     self.cutting_frame1 = Frame(worldxy_xypoint, vec_inter_pt2, vec_edge)

        # print("cutting_frame0", self.cutting_frame0)
        # print("cutting_frame1", self.cutting_frame1)


        #brep for main beam sub volume
        s0 = Scale.from_factors([2, 2, 2], Frame(intersection_pt2, ref_face.xaxis, ref_face.yaxis))
        s1 = Scale.from_factors([2, 2, 2], Frame(intersection_pt, ref_face.xaxis, ref_face.yaxis))
        # if 89.9 <= StrutInclination <= 90.1:
        #     print("90=")
        #     self.sj_main_sub_volume0 = Brep.from_box(self.main_beam.blank)
        #     self.sj_main_sub_volume0.transform(s0)
        #     self.sj_main_sub_volume0.translate(ref_face.normal*(self.main_beam.width/2))
        #     self.sj_main_sub_volume0.rotate(math.radians((90+angle_90deg)), ref_face.normal, intersection_pt2)
        #     self.sj_main_sub_volume1 = Brep.from_box(self.main_beam.blank)
        #     self.sj_main_sub_volume1.transform(s1)
        #     self.sj_main_sub_volume1.translate(ref_face.normal*(self.main_beam.width/2))
        #     self.sj_main_sub_volume1.rotate(math.radians(-(90+angle_90deg)), ref_face.normal, intersection_pt)
        # elif SI_angle < 89.9:
        #     print("90-")
        #     self.sj_main_sub_volume0 = Brep.from_box(self.main_beam.blank)
        #     self.sj_main_sub_volume0.transform(s0)
        #     self.sj_main_sub_volume0.translate(ref_face.normal*(self.main_beam.width/2))
        #     self.sj_main_sub_volume0.rotate(-math.radians(SI_angle+LeadAngle), ref_face.normal, intersection_pt2)
        #     self.sj_main_sub_volume1 = Brep.from_box(self.main_beam.blank)
        #     self.sj_main_sub_volume1.transform(s1)
        #     self.sj_main_sub_volume1.translate(ref_face.normal*(self.main_beam.width/2))
        #     self.sj_main_sub_volume1.rotate(-math.radians(180+Angle_cross), ref_face.normal, intersection_pt)
        # else:
        #     print("90+")
        #     self.sj_main_sub_volume0 = Brep.from_box(self.cross_beam.blank)
        #     self.sj_main_sub_volume0.transform(s0)
        #     self.sj_main_sub_volume0.translate(ref_face.normal*(self.main_beam.width/2))
        #     self.sj_main_sub_volume0.rotate(math.radians(180+Angle_cross+LeadAngle), ref_face.normal, intersection_pt2)
        #     self.sj_main_sub_volume1 = Brep.from_box(self.cross_beam.blank)
        #     self.sj_main_sub_volume1.transform(s1)
        #     self.sj_main_sub_volume1.translate(ref_face.normal*(self.main_beam.width/2))
        #     self.sj_main_sub_volume1.rotate(math.radians(Angle_cross), ref_face.normal, intersection_pt)


        return True


    def add_extensions(self):
        """Adds the extensions to the main beam and cross beam.

        This method is automatically called when joint is created by the call to `Joint.create()`.

        """

        pass

    def add_features(self):
        """Adds the trimming plane to the main beam (no features for the cross beam).

        This method is automatically called when joint is created by the call to `Joint.create()`.

        """
        assert self.main_beam and self.cross_beam  # should never happen
        if self.features:
            self.main_beam.remove_features(self.features)
        cutting_plane = None
        cutting_plane = self.get_main_cutting_plane()[0]
        try:
            cutting_plane = self.get_main_cutting_plane()[0]
        except AttributeError as ae:
            raise BeamJoinningError(beams=self.beams, joint=self, debug_info=str(ae), debug_geometries=[cutting_plane])
        except Exception as ex:
            raise BeamJoinningError(beams=self.beams, joint=self, debug_info=str(ex))
        if self.check_stepjoint_boolean():
            if self.calc_params_stepjoint():
                pass
                # self.main_beam.add_features(BrepSubtraction(self.sj_main_sub_volume0))
                # self.features.append(BrepSubtraction(self.sj_main_sub_volume0))
                # self.main_beam.add_features(BrepSubtraction(self.sj_main_sub_volume1))
                # self.features.append(BrepSubtraction(self.sj_main_sub_volume1))
                self.main_beam.add_features(CutFeature(self.cutting_frame0))
                self.features.append(self.cutting_frame0)
                self.main_beam.add_features(CutFeature(self.cutting_frame1))
                self.features.append(self.cutting_frame1)
                self.cross_beam.add_features(BrepSubtraction(self.brep_sj_cross))
                self.features.append(BrepSubtraction(self.brep_sj_cross))
        else:
            self.main_beam.add_features(CutFeature(cutting_plane))
            self.features.append(cutting_plane)
        if self.drill_diameter > 0:
            self.cross_beam.add_features(DrillFeature(*self.calc_params_drilling()))
            self.features.append(DrillFeature(*self.calc_params_drilling()))