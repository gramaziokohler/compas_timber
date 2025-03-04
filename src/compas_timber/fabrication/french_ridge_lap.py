import math
from collections import OrderedDict

from compas.datastructures import Mesh
from compas.geometry import Brep
from compas.geometry import BrepTrimmingError
from compas.geometry import Cylinder
from compas.geometry import Frame
from compas.geometry import Line
from compas.geometry import Plane
from compas.geometry import Point
from compas.geometry import Vector
from compas.geometry import angle_vectors_signed
from compas.geometry import intersection_line_line
from compas.geometry import intersection_line_plane
from compas.geometry import is_point_behind_plane
from compas.tolerance import TOL

from compas_timber.errors import FeatureApplicationError

from .btlx import BTLxProcessing
from .btlx import BTLxProcessingParams
from .btlx import EdgePositionType
from .btlx import OrientationType


class FrenchRidgeLap(BTLxProcessing):
    """Represents a French Ridge Lap feature to be made on a beam.

    Parameters
    ----------
    orientation : int
        The orientation of the cut. Must be either OrientationType.START or OrientationType.END.
    start_x : float
        The start x-coordinate of the cut in parametric space of the reference side. -100000.0 < start_x < 100000.0.
    angle : float
        The horizontal angle of the cut. 0.1 < angle < 179.9.
    ref_position: int
        The reference position of the cut. Must be either EdgePositionType.REFEDGE or EdgePositionType.OPPEDGE.
    drillhole : bool
        Flag indicating if a drill hole should be made.
    drillhole_diam : float
        The diameter of the drill hole.

    """

    PROCESSING_NAME = "FrenchRidgeLap"  # type: ignore

    @property
    def __data__(self):
        data = super(FrenchRidgeLap, self).__data__
        data["orientation"] = self.orientation
        data["start_x"] = self.start_x
        data["angle"] = self.angle
        data["ref_position"] = self.ref_position
        data["drillhole"] = self.drillhole
        data["drillhole_diam"] = self.drillhole_diam
        return data

    def __init__(self, orientation=OrientationType.START, start_x=0.0, angle=90.0, ref_position=EdgePositionType.REFEDGE, drillhole=False, drillhole_diam=0.0, **kwargs):
        super(FrenchRidgeLap, self).__init__(**kwargs)
        self._orientation = None
        self._start_x = None
        self._angle = None
        self._ref_position = None
        self._drillhole = None
        self._drillhole_diam = None

        self.orientation = orientation
        self.start_x = start_x
        self.angle = angle
        self.ref_position = ref_position
        self.drillhole = drillhole
        self.drillhole_diam = drillhole_diam

    ########################################################################
    # Properties
    ########################################################################

    @property
    def params(self):
        return FrenchRidgeLapParams(self)

    @property
    def orientation(self):
        return self._orientation

    @orientation.setter
    def orientation(self, orientation):
        if orientation not in [OrientationType.START, OrientationType.END]:
            raise ValueError("Orientation must be either OrientationType.START or OrientationType.END.")
        self._orientation = orientation

    @property
    def start_x(self):
        return self._start_x

    @start_x.setter
    def start_x(self, start_x):
        if start_x > 100000.0 or start_x < -100000.0:
            raise ValueError("Start X must be between -100000.0 and 100000.")
        self._start_x = start_x

    @property
    def angle(self):
        return self._angle

    @angle.setter
    def angle(self, angle):
        if angle > 179.9 or angle < 0.1:
            raise ValueError("Angle must be between 0.1 and 179.9.")
        self._angle = angle

    @property
    def ref_position(self):
        return self._ref_position

    @ref_position.setter
    def ref_position(self, ref_position):
        if ref_position not in [EdgePositionType.REFEDGE, EdgePositionType.OPPEDGE]:
            raise ValueError("Ref position must be either EdgePositionType.REFEDGE or EdgePositionType.OPPEDGE.")
        self._ref_position = ref_position

    @property
    def drillhole(self):
        return self._drillhole

    @drillhole.setter
    def drillhole(self, drillhole):
        if not isinstance(drillhole, bool):
            raise ValueError("Drillhole must be a boolean.")
        self._drillhole = drillhole

    @property
    def drillhole_diam(self):
        return self._drillhole_diam

    @drillhole_diam.setter
    def drillhole_diam(self, drillhole_diam):
        if 1000.0 < drillhole_diam < 0.0:
            raise ValueError("Drillhole diameter must be between 0.0 and 1000.0.")
        self._drillhole_diam = drillhole_diam

    ########################################################################
    # Alternative constructors
    ########################################################################

    @classmethod
    def from_beam_beam_and_plane(cls, beam, other_beam, plane, drillhole_diam=0.0, ref_side_index=0):
        """Create a FrenchRidgeLap instance from two beams and a cutting plane. The instance is used to cut the principal beam with the other beam.
        The plane is the furthest reference side of the other beam that cuts the exceeding part of the principal beam.

        Parameters
        ----------
        beam : :class:`~compas_timber.elements.Beam`
            The beam that is cut by this instance.
        other_beam : :class:`~compas_timber.elements.Beam`
            The beam that is used to cut the beam.
        plane : :class:`~compas.geometry.Plane`
            The plane that cuts the principal beam.
        drillhole_diam : float
            The diameter of the drillhole.
        ref_side_index : int, optional
            The reference side index of the beam to be cut. Default is 0 (i.e. RS1).

        Returns
        -------
        :class:`~compas_timber.fabrication.FrenchRidgeLap`

        """
        # type: (Beam, Beam, float, int) -> FrenchRidgeLap
        if isinstance(plane, Frame):
            plane = Plane.from_frame(plane)
        # the reference side of the beam to be cut
        ref_side = beam.ref_sides[ref_side_index]
        ref_surface = beam.side_as_surface(ref_side_index)

        # calculate the orientation of the cut
        orientation = cls._calculate_orientation(ref_side, plane)

        # calculate the angle of the cut
        angle = cls._calculate_angle(beam, other_beam, ref_side, orientation)

        # determine the reference position of the edge
        ref_position = cls._calculate_ref_position(beam, other_beam, ref_side, plane, angle)

        # calculate the start_x of the cut
        start_x = cls._calculate_start_x(ref_surface, orientation, angle)

        # define the drillhole
        drillhole = True if drillhole_diam else False
        drillhole_diam = 0.0 if not drillhole else drillhole_diam

        return cls(
            orientation,
            start_x,
            angle,
            ref_position,
            drillhole,
            drillhole_diam,
            ref_side_index=ref_side_index,
        )

    @staticmethod
    def _calculate_orientation(ref_side, plane):
        # orientation is START if cutting plane normal points towards the start of the beam and END otherwise
        # essentially if the start is being cut or the end
        if is_point_behind_plane(ref_side.point, plane):
            return OrientationType.END
        else:
            return OrientationType.START

    @staticmethod
    def _calculate_start_x(ref_surface, orientation, angle):
        # calculate the start_x of the cut
        start_x = 0.0
        dx = abs(ref_surface.ysize / math.tan(math.radians(angle)))
        if orientation == OrientationType.END:
            start_x = ref_surface.xsize
            dx = -dx
        if angle > 90.0:
            start_x += dx
        return start_x

    @staticmethod
    def _calculate_ref_position(beam, other_beam, ref_side, plane, angle):
        # determine if the position of the ridge lap is on the reference edge or the opposite edge
        angle_vector = Vector.cross(ref_side.normal, plane.normal)
        # condition for orthogonal connection
        if angle == 90.0:
            intersection_pt = intersection_line_line(other_beam.centerline, beam.centerline)[0]
            angle_vector = other_beam.centerline.direction
            # make sure the direction of the other beam's centerline is facing outwards
            if other_beam.endpoint_closest_to_point(Point(*intersection_pt))[0] == "start":
                angle_vector = -angle_vector

        # calculate the angle between angle vector and the reference side's x-axis
        signed_angle = angle_vectors_signed(ref_side.xaxis, angle_vector, ref_side.normal, deg=True)
        if angle > 90.0:
            is_ref_edge = abs(signed_angle) < 90
        elif angle < 90.0:
            is_ref_edge = abs(signed_angle) > 90
        else:
            is_ref_edge = signed_angle < 0
        if is_ref_edge:
            return EdgePositionType.REFEDGE
        return EdgePositionType.OPPEDGE

    @staticmethod
    def _calculate_angle(beam, other_beam, ref_side, orientation):
        # angle between the two beams at the intersection point of their centerlines, projected onto the plane of the reference side.
        intersection_pt = intersection_line_line(other_beam.centerline, beam.centerline)[0]
        vector_angle = other_beam.centerline.direction
        # make sure the direction of the other beam's centerline is facing outwards
        if other_beam.endpoint_closest_to_point(Point(*intersection_pt))[0] == "start":
            vector_angle = -vector_angle
        angle = angle_vectors_signed(ref_side.xaxis, vector_angle, ref_side.normal, deg=True)
        if orientation == OrientationType.START:
            return 180 - abs(angle)
        else:
            return abs(angle)

    ########################################################################
    # Methods
    ########################################################################

    def apply(self, geometry, beam):
        """Apply the feature to the beam geometry.

        Parameters
        ----------
        geometry : :class:`~compas.geometry.Brep`
            The beam geometry to be cut.
        beam : :class:`compas_timber.elements.Beam`
            The beam that is cut by this instance.

        Raises
        ------
        :class:`~compas_timber.errors.FeatureApplicationError`
            If the cutting plane does not intersect with beam geometry.

        Returns
        -------
        :class:`~compas.geometry.Brep`
            The resulting geometry after processing

        """
        # type: (Brep, Beam) -> Brep
        # trim the beam geometry with the cutting frame
        trimming_frame = self.frame_from_params_and_beam(beam)
        if not TOL.is_zero(self.angle - 90):
            try:
                geometry.trim(trimming_frame)
            except BrepTrimmingError:
                raise FeatureApplicationError(
                    trimming_frame,
                    geometry,
                    "Could not trim the beam geometry with the cutting frame.",
                )
        # subtract the lap volume from the beam geometry
        subtracting_volume = self.lap_volume_from_params_and_beam(beam)
        try:
            return geometry - subtracting_volume
        except IndexError:
            raise FeatureApplicationError(
                subtracting_volume,
                geometry,
                "Could not subtract the cutting volume from the beam geometry.",
            )

    def frame_from_params_and_beam(self, beam):
        """Calculates the frame that cuts the exceeding part of the blank of the beam from the machining parameters and the given beam.

        Parameters
        ----------
        beam : :class:`compas_timber.elements.Beam`
            The beam that is cut by this instance.

        Returns
        -------
        :class:`compas.geometry.Frame`
            The cutting frame.

        """
        # type: (Beam) -> Frame
        assert self.orientation is not None
        assert self.start_x is not None
        assert self.angle is not None
        assert self.ref_position is not None

        ref_surface = beam.side_as_surface(self.ref_side_index)
        # get the origin of the cutting frame
        start_x = self.start_x
        start_y = ref_surface.ysize if self.ref_position == EdgePositionType.OPPEDGE else 0
        origin = ref_surface.point_at(start_x, start_y)

        # flip the rot_axis if the orientation is END
        rot_axis = -ref_surface.frame.normal
        if self.orientation == OrientationType.END:
            rot_axis = -rot_axis

        # get the opposite angle if the reference position is REFEDGE
        angle = self.angle
        if self.ref_position == EdgePositionType.REFEDGE:
            angle = 180 - self.angle

        ref_surface.rotate(math.radians(angle), rot_axis, origin)
        return Frame(origin, ref_surface.frame.xaxis, ref_surface.frame.normal)

    def lap_volume_from_params_and_beam(self, beam):
        """
        Calculates the trimming volume of the french ridge lap from the machining parameters and the given beam.

        Parameters
        ----------
        beam : :class:`compas_timber.elements.Beam`
            The beam that is cut by this instance.

        Returns
        -------
        :class:`compas.geometry.Brep`
            The trimming volume of the lap.
        """
        # type: (Beam) -> Brep
        assert self.orientation is not None
        assert self.angle is not None
        assert self.ref_position is not None
        assert self.drillhole is not None
        assert self.drillhole_diam is not None

        # get the reference side and the opposite side of the beam
        ref_side = beam.side_as_surface(self.ref_side_index)
        ref_edge = Line.from_point_and_vector(ref_side.point, ref_side.xaxis)
        opp_edge = ref_edge.translated(ref_side.yaxis * ref_side.ysize)

        # get the height of the beam and the edge length of the lap
        height = beam.get_dimensions_relative_to_side(self.ref_side_index)[1]
        edge_length = ref_side.ysize / math.sin(math.radians(self.angle))
        if self.orientation == OrientationType.END:
            edge_length = -edge_length

        # side cutting frames of the lap
        frame1 = self.frame_from_params_and_beam(beam)
        frame2 = frame1.translated(ref_side.xaxis * edge_length)
        frame2.xaxis = -frame2.xaxis

        # bottom vertices
        bottom_vertices = [
            Point(*intersection_line_plane(ref_edge, Plane.from_frame(frame1))),
            Point(*intersection_line_plane(ref_edge, Plane.from_frame(frame2))),
            Point(*intersection_line_plane(opp_edge, Plane.from_frame(frame2))),
            Point(*intersection_line_plane(opp_edge, Plane.from_frame(frame1))),
        ]
        # top vertices
        top_vertices = [v.translated(-ref_side.zaxis * (height / 2)) for v in bottom_vertices]
        # translate vertices to create the french ridge lap
        if self.ref_position == EdgePositionType.OPPEDGE:
            frl_indexes = [0, 2]
        else:
            frl_indexes = [3, 1]
        top_vertices[frl_indexes[0]].translate(ref_side.zaxis * (height / 6))
        top_vertices[frl_indexes[1]].translate(-ref_side.zaxis * (height / 6))

        # create the faces of the french ridge lap
        vertices = bottom_vertices + top_vertices
        faces = [
            [0, 1, 2, 3],  # Top face
            [4, 7, 6, 5],  # Bottom face
            [0, 4, 5, 1],  # Side face 1
            [1, 5, 6, 2],  # Side face 2
            [2, 6, 7, 3],  # Side face 3
            [3, 7, 4, 0],  # Side face 4
        ]

        # reverse face orientation if the orientation is END
        if self.orientation == OrientationType.END:
            faces = [face[::-1] for face in faces]

        # generate the subtraction volume and convert it to a Brep
        subtraction_volume_mesh = Mesh.from_vertices_and_faces(vertices, faces)
        subtraction_volume = Brep.from_mesh(subtraction_volume_mesh)

        # add drilling cylinder to the subtraction_volume
        if self.drillhole:
            diagonal = Line(bottom_vertices[0], bottom_vertices[2])
            drill_frame = Frame(diagonal.midpoint, -ref_side.xaxis, ref_side.yaxis)
            drill_cylinder = Cylinder(self.drillhole_diam / 2, height * 2, drill_frame)
            subtraction_volume += Brep.from_cylinder(drill_cylinder)
        return subtraction_volume


class FrenchRidgeLapParams(BTLxProcessingParams):
    """A class to store the parameters of a French Ridge Lap feature.

    Parameters
    ----------
    instance : :class:`~compas_timber.fabrication.FrenchRidgeLap`
        The instance of the French Ridge Lap feature.
    """

    def __init__(self, instance):
        # type: (FrenchRidgeLap) -> None
        super(FrenchRidgeLapParams, self).__init__(instance)

    def as_dict(self):
        """Returns the parameters of the French Ridge Lap feature as a dictionary.

        Returns
        -------
        dict
            The parameters of the French Ridge Lap feature as a dictionary.
        """
        # type: () -> OrderedDict
        result = OrderedDict()
        result["Orientation"] = self._instance.orientation
        result["StartX"] = "{:.{prec}f}".format(float(self._instance.start_x), prec=TOL.precision)
        result["Angle"] = "{:.{prec}f}".format(float(self._instance.angle), prec=TOL.precision)
        result["RefPosition"] = self._instance.ref_position
        result["Drillhole"] = "yes" if self._instance.drillhole else "no"
        result["DrillholeDiam"] = "{:.{prec}f}".format(float(self._instance.drillhole_diam), prec=TOL.precision)
        return result
