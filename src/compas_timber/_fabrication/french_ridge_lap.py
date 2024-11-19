import math

from compas.geometry import Brep
from compas.geometry import BrepTrimmingError
from compas.geometry import Frame
from compas.geometry import Line
from compas.geometry import Plane
from compas.geometry import Point
from compas.geometry import Polyhedron
from compas.geometry import Vector
from compas.datastructures import Mesh
from compas.geometry import angle_vectors_signed
from compas.geometry import distance_point_point
from compas.geometry import intersection_line_plane
from compas.geometry import is_point_behind_plane
from compas.geometry import project_points_plane
from compas.geometry import Rotation
from compas.tolerance import TOL

from compas_timber.elements import FeatureApplicationError

from .btlx_process import BTLxProcess
from .btlx_process import BTLxProcessParams
from .btlx_process import OrientationType
from .btlx_process import EdgePositionType


class FrenchRidgeLap(BTLxProcess):
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

    PROCESS_NAME = "FrenchRidgeLap"  # type: ignore

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

    def __init__(
        self,
        orientation,
        start_x=0.0,
        angle=90.0,
        ref_position=EdgePositionType.REFEDGE,
        drillhole=False,
        drillhole_diam=0.0,
        **kwargs
    ):
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
    def params_dict(self):
        return FrenchRidgeLapParams(self).as_dict()

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
    def from_plane_and_beam(cls, plane, beam, drillhole_diam=0.0, ref_side_index=0):
        """Create a FrenchRidgeLap instance from a cutting plane and the beam it should cut.

        Parameters
        ----------
        plane : :class:`~compas.geometry.Plane` or :class:`~compas.geometry.Frame`
            The cutting plane.
        beam : :class:`~compas_timber.elements.Beam`
            The beam that is cut by this instance.
        ref_position : int
            The reference position of the cut. Must be either EdgePositionType.REFEDGE or EdgePositionType.OPPEDGE.
        drillhole_diam : float
            The diameter of the drillhole.
        ref_side_index : int, optional
            The reference side index of the beam to be cut. Default is 0 (i.e. RS1).

        Returns
        -------
        :class:`~compas_timber.fabrication.JackRafterCut`

        """
        # type: (Plane | Frame, Beam, int) -> JackRafterCut
        if isinstance(plane, Frame):
            plane = Plane.from_frame(plane)
        ref_side = beam.ref_sides[ref_side_index]
        ref_surface = beam.side_as_surface(ref_side_index)

        # calculate the orientation of the cut
        orientation = cls._calculate_orientation(ref_side, plane)
        print(orientation)

        # calculate the angle of the cut
        angle = cls._calculate_angle(ref_side, plane)
        print(angle)

        # determine the reference position of the edge
        ref_position = EdgePositionType.REFEDGE if angle > 90 else EdgePositionType.OPPEDGE

        # calculate the start_x of the cut
        start_x = cls._calculate_start_x(ref_surface, plane, ref_position)
        print(start_x)

        drillhole = True if drillhole_diam else False
        drillhole_diam = 0.0 if not drillhole else drillhole_diam

        return cls(orientation, start_x, angle, ref_position, drillhole, drillhole_diam, ref_side_index=ref_side_index)

    @staticmethod
    def _calculate_orientation(ref_side, cutting_plane):
        # orientation is START if cutting plane normal points towards the start of the beam and END otherwise
        # essentially if the start is being cut or the end
        if is_point_behind_plane(ref_side.point, cutting_plane):
            return OrientationType.END
        else:
            return OrientationType.START

    @staticmethod
    def _calculate_start_x(ref_surface, cutting_plane, ref_position):
        # distance between the start of the beam and the intersection of the cutting plane with the reference edge
        if ref_position == EdgePositionType.REFEDGE:
            y_pos = 0
        else:
            y_pos = ref_surface.ysize

        ref_point = ref_surface.point_at(0, y_pos)
        ref_edge = Line.from_point_and_vector(ref_point, ref_surface.frame.xaxis)
        point_start_x = intersection_line_plane(ref_edge, cutting_plane)
        if point_start_x is None:
            raise ValueError("Plane does not intersect with beam.")
        return distance_point_point(ref_point, point_start_x)

    @staticmethod
    def _calculate_angle(ref_side, plane):
        # angle between the normal of the reference side and the normal of the cutting plane
        angle_vector = Vector.cross(ref_side.normal, plane.normal)
        angle = angle_vectors_signed(ref_side.xaxis, angle_vector, ref_side.normal, deg=True)
        return 180 - abs(angle)

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
        :class:`~compas_timber.elements.FeatureApplicationError`
            If the cutting plane does not intersect with beam geometry.

        Returns
        -------
        :class:`~compas.geometry.Brep`
            The resulting geometry after processing

        """
        # type: (Brep, Beam) -> Brep
        trimming_plane = self.plane_from_params_and_beam(beam)
        try:
            geometry.trim(trimming_plane)
        except BrepTrimmingError:
            raise FeatureApplicationError(
                trimming_plane,
                geometry,
                "Could not trim the beam geometry with the cutting plane.",
            )

        subtracting_volume = self.volume_from_params_and_beam(beam)
        try:
            brep_subtracting_volume = Brep.from_mesh(subtracting_volume)
        except ValueError:  # TODO: check if this is the right exception
            raise FeatureApplicationError(
                subtracting_volume,
                geometry,
                "Could not convert the cutting volume to a Brep.",
            )
        try:
            return geometry - brep_subtracting_volume
        except IndexError:
            raise FeatureApplicationError(
                subtracting_volume,
                geometry,
                "Could not subtract the cutting volume from the beam geometry.",
            )

    def plane_from_params_and_beam(self, beam):
        """Calculates the plane that cuts the exceeding part of the blank of the beam from the machining parameters in this instance and the given beam.

        Parameters
        ----------
        beam : :class:`compas_timber.elements.Beam`
            The beam that is cut by this instance.

        Returns
        -------
        :class:`compas.geometry.Plane`
            The cutting plane.

        """
        assert self.angle is not None
        ref_surface = beam.side_as_surface(self.ref_side_index)
        origin = ref_surface.point_at(self.start_x, 0)
        cutting_frame = Frame(origin, ref_surface.frame.xaxis, ref_surface.frame.yaxis)

        angle = self.angle
        if self.orientation == OrientationType.START:
            angle = -angle
        cutting_frame.rotate(math.radians(180 - angle), cutting_frame.yaxis, cutting_frame.point)

        return cutting_frame

    def equilateral_quadrilateral_vertices_from_params_and_beam(self, beam):
        """Calculates the vertices of the quadrilateral that represents the French Ridge Lap feature. The quadrilateral is a rhombus with the given angle.

        Parameters:
        ----------
        beam : :class:`compas_timber.elements.Beam`
            The beam that is cut by this instance.

        Returns:
        ----------
        list of :class:`compas.geometry.Point`
            The vertices of the quadrilateral.

        """
        assert self.angle is not None

        # Get the reference side of the beam (planar surface)
        ref_side = beam.side_as_surface(self.ref_side_index)

        # Translate the reference side to the middle of the beam
        height = beam.height if self.ref_side_index % 2 == 0 else beam.width
        ref_side.translate(-ref_side.frame.normal * (height / 2))

        # Calculate the edge length from the height
        edge_length = ref_side.ysize / math.sin(math.radians(180 - self.angle))

        # Determine origin point based on ref_position
        x_pos = self.start_x
        y_pos1, y_pos2 = [0, ref_side.ysize] if self.ref_position == EdgePositionType.REFEDGE else [ref_side.ysize, 0]

        # First vertex (origin)
        v0 = ref_side.point_at(x_pos, y_pos1)

        # Second vertex
        v1 = ref_side.point_at(x_pos + edge_length, y_pos1)

        # Third vertex
        v2 = ref_side.point_at(x_pos + edge_length, y_pos2)

        # Fourth vertex
        v3 = ref_side.point_at(x_pos, y_pos2)

        return [v0, v1, v2, v3]

    def volume_from_params_and_beam(self, beam):
        """Calculates the lap volume from the machining parameters in this instance and the given beam

        Parameters
        ----------
        beam : :class:`compas_timber.elements.Beam`
            The beam that is cut by this instance.

        Returns
        -------
        :class:`compas.geometry.Mesh`
            The lap volume.

        """
        # type: (Beam) -> Mesh
        ref_side = beam.ref_sides[self.ref_side_index]

        quad_vertices = self.equilateral_quadrilateral_vertices_from_params_and_beam(beam)
        projected_vertices = project_points_plane(quad_vertices, Plane.from_frame(ref_side))

        vertices = quad_vertices + projected_vertices
        faces = [[0, 1, 2, 3], [4, 7, 6, 5], [0, 4, 5, 1], [1, 5, 6, 2], [2, 6, 7, 3], [3, 7, 4, 0]]

        if self.ref_position == EdgePositionType.OPPEDGE:
            faces = [face[::-1] for face in faces]

        return Mesh.from_vertices_and_faces(vertices, faces)


class FrenchRidgeLapParams(BTLxProcessParams):
    """A class to store the parameters of a French Ridge Lap feature.

    Parameters
    ----------
    instance : :class:`~compas_timber._fabrication.FrenchRidgeLap`
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
        result = super(FrenchRidgeLapParams, self).as_dict()
        result["Orientation"] = self._instance.orientation
        result["StartX"] = "{:.{prec}f}".format(self._instance.start_x, prec=TOL.precision)
        result["Angle"] = "{:.{prec}f}".format(self._instance.angle, prec=TOL.precision)
        result["RefPosition"] = self._instance.ref_position
        result["Drillhole"] = "yes" if self._instance.drillhole else "no"
        result["DrillholeDiam"] = "{:.{prec}f}".format(self._instance.drillhole_diam, prec=TOL.precision)
        return result
