from math import e
from compas.geometry import Frame
from compas.geometry import Line
from compas.geometry import Point
from compas.geometry import Vector
from compas.geometry import intersection_line_line
from compas.geometry import angle_vectors
from compas.geometry import cross_vectors
from compas_timber.parts import CutFeature
from compas_timber.parts import MillVolume
from compas_timber.parts import DrillFeature

from .joint import BeamJoinningError
from .solver import JointTopology
from .lap_joint import LapJoint


class LHalfLapJoint(LapJoint):
    """Represents a L-Lap type joint which joins the ends of two beams,
    trimming the main beam.

    This joint type is compatible with beams in L topology.

    Please use `LHalfLapJoint.create()` to properly create an instance of this class and associate it with an assembly.

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
    main_beam : :class:`~compas_timber.parts.Beam`
        The main beam to be joined.
    cross_beam : :class:`~compas_timber.parts.Beam`
        The cross beam to be joined.
    main_beam_key : str
        The key of the main beam.
    cross_beam_key : str
        The key of the cross beam.
    features : list(:class:`~compas_timber.parts.Feature`)
        The features created by this joint.
    joint_type : str
        A string representation of this joint's type.

    """

    SUPPORTED_TOPOLOGY = JointTopology.TOPO_L

    def __init__(
        self, main_beam=None, cross_beam=None, flip_lap_side=False, cut_plane_bias=0.5, drill_diameter=0.0, **kwargs
    ):
        super(LHalfLapJoint, self).__init__(**kwargs)

        self.main_beam = main_beam
        self.cross_beam = cross_beam
        self.main_beam_key = main_beam.key if main_beam else None
        self.cross_beam_key = cross_beam.key if cross_beam else None
        self.flip_lap_side = flip_lap_side
        self.cut_plane_bias = cut_plane_bias
        self.drill_diameter = float(drill_diameter)
        self.btlx_params_main = {}
        self.btlx_params_cross = {}
        self.btlx_drilling_params_main = {}
        self.features = []
        self.test = []
        self.top_plane, self.bottom_plane = self.get_world_top_bottom_faces(self.cross_beam)

    @property
    def __data__(self):
        data_dict = {
            "main_beam_key": self.main_beam_key,
            "cross_beam_key": self.cross_beam_key,
        }
        data_dict.update(super(LHalfLapJoint, self).__data__)
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

    def add_extensions(self):
        """Adds the extensions to the main beam and cross beam.

        This method is automatically called when joint is created by the call to `Joint.create()`.

        """

        assert self.main_beam and self.cross_beam
        extension_tolerance = 0.01  # TODO: this should be proportional to the unit used

        extension_plane_main = self.get_face_most_towards_beam(self.main_beam, self.cross_beam, ignore_ends=True)[1]
        extension_plane_main = self.get_face_most_towards_beam(self.main_beam, self.cross_beam, ignore_ends=True)[1]
        start_main, end_main = self.main_beam.extension_to_plane(extension_plane_main)
        self.main_beam.add_blank_extension(start_main + extension_tolerance, end_main + extension_tolerance, self.key)

        extension_plane_cross = self.get_face_most_towards_beam(self.cross_beam, self.main_beam, ignore_ends=True)[1]
        start_cross, end_cross = self.cross_beam.extension_to_plane(extension_plane_cross)
        self.cross_beam.add_blank_extension(
            start_cross + extension_tolerance, end_cross + extension_tolerance, self.key
        )


    def add_features(self):
        assert self.main_beam and self.cross_beam

        try:
            if self.main_beam.length < self.cross_beam.length:
                main_cutting_frame = self.main_beam.faces[self.top_plane]
                cross_cutting_frame = self.cross_beam.faces[self.bottom_plane]

            else:
                main_cutting_frame = self.main_beam.faces[self.bottom_plane]
                cross_cutting_frame = self.cross_beam.faces[self.top_plane]

            negative_brep_main_beam, negative_brep_cross_beam = self._create_negative_volumes()
        except Exception as ex:
            raise BeamJoinningError(beams=self.beams, joint=self, debug_info=str(ex))

        # call functions to calculate the parameters
        self.calc_params_cross()
        self.calc_params_main()

        main_volume = MillVolume(negative_brep_main_beam)
        cross_volume = MillVolume(negative_brep_cross_beam)

        self.main_beam.add_features(main_volume)
        self.cross_beam.add_features(cross_volume)

        f_cross = CutFeature(cross_cutting_frame)
        self.cross_beam.add_features(f_cross)

        trim_frame = Frame(main_cutting_frame.point, main_cutting_frame.xaxis, -main_cutting_frame.yaxis)
        f_main = CutFeature(trim_frame)
        self.main_beam.add_features(f_main)

        if self.drill_diameter > 0:
            self.cross_beam.add_features(DrillFeature(*self.calc_params_drilling_main()))
            self.features.append(DrillFeature(*self.calc_params_drilling_main()))

        self.features = [main_volume, cross_volume, f_main, f_cross]

    def get_world_top_bottom_faces(self, beam):
        faces = beam.faces
        face_normals = [face.zaxis for face in faces]
        angles = [angle_vectors(face_normal, [0, 0, 1]) for face_normal in face_normals]

        top_face_index = angles.index(min(angles))
        bottom_face_index = angles.index(max(angles))
        return top_face_index, bottom_face_index

    def calc_params_main(self):
        if self.ends[str(self.main_beam.key)] == "start":
            start_x = 0.0
        else:
            start_x = self.main_beam.blank_length
        self.btlx_params_main["ReferencePlaneID"] = str(self.bottom_plane)
        self.btlx_params_main["orientation"] = self.ends[str(self.main_beam.key)]
        self.btlx_params_main["start_x"] = start_x
        self.btlx_params_main["start_y"] = 0.0
        self.btlx_params_main["length"] = 60.0
        self.btlx_params_main["width"] = 30.0
        self.btlx_params_main["depth"] = 60.0

        self.btlx_params_main["machining_limits"] = {
            "FaceLimitedFront": "no",
            "FaceLimitedBack": "no",
        }

    def calc_params_cross(self):
        if self.ends[str(self.cross_beam.key)] == "start":
            start_x = 0.0
        else:
            start_x = self.cross_beam.blank_length
        self.btlx_params_cross["ReferencePlaneID"] = str(self.top_plane)
        self.btlx_params_cross["orientation"] = self.ends[str(self.cross_beam.key)]
        self.btlx_params_cross["start_x"] = start_x
        self.btlx_params_cross["start_y"] = 0.0
        self.btlx_params_cross["length"] = 60.0
        self.btlx_params_cross["width"] = 30.0
        self.btlx_params_cross["depth"] = 60.0
        self.btlx_params_cross["machining_limits"] = {
            "FaceLimitedFront": "no",
            "FaceLimitedBack": "no",
        }

    def calc_params_drilling_main(self):
        """
        Calculate the parameters for a drilling joint.

        Parameters:
        ----------
            joint (object): The joint object.
            main_part (object): The main part object.

        Returns:
        ----------
            dict: A dictionary containing the calculated parameters for the drilling joint

        """
        if self.ends[str(self.main_beam.key)] == "start":
            start_x = 30.0
        else:
            start_x = self.main_beam.blank_length - 30.0

        self.btlx_drilling_params_main = {
            "ReferencePlaneID": str(self.bottom_plane+1),
            "StartX": start_x,
            "StartY": 30.0,
            "Angle": 0.0,
            "Inclination": 90.0,
            "Diameter": self.drill_diameter,
            "DepthLimited": "no",
            "Depth": 0.0,
        }

        # Rhino geometry visualization
        point_xyz = intersection_line_line(self.cross_beam.centerline, self.main_beam.centerline)[1]
        cross_product = cross_vectors(self.cross_beam.centerline.direction, self.main_beam.centerline.direction)
        cross_vect = Vector(*cross_product)*(self.main_beam.width)

        mid_point = Point(*point_xyz)
        start_point = mid_point.translated(cross_vect)
        end_point = mid_point.translated(-cross_vect)

        line = Line(start_point, end_point)
        return line, self.drill_diameter, line.length
