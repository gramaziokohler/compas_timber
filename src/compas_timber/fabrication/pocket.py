from __future__ import annotations

import math
from collections import OrderedDict
from typing import Optional
from typing import Union

from compas.datastructures import Mesh
from compas.geometry import Brep
from compas.geometry import Frame
from compas.geometry import Line
from compas.geometry import Plane
from compas.geometry import Point
from compas.geometry import Polyhedron
from compas.geometry import Vector
from compas.geometry import angle_vectors
from compas.geometry import angle_vectors_projected
from compas.geometry import angle_vectors_signed
from compas.geometry import dot_vectors
from compas.geometry import intersection_plane_plane_plane
from compas.geometry import intersection_segment_plane
from compas.geometry import is_point_behind_plane
from compas.tolerance import TOL

from compas_timber.errors import FeatureApplicationError
from compas_timber.timber import TimberElement
from compas_timber.utils import planar_surface_point_at

from .btlx import BTLxProcessing
from .btlx import BTLxProcessingParams
from .btlx import MachiningLimits


class Pocket(BTLxProcessing):
    """Represents a Pocket feature to be made on a beam.

    Parameters
    ----------
    start_x : float
        The start x-coordinate of the cut in parametric space of the reference side. -100000.0 < start_x < 100000.0.
    start_y : float
        The start y-coordinate of the cut in parametric space of the reference side. -50000.0 < start_y < 50000.0.
    start_depth : float
        The start depth of the cut. -50000.0 < start_depth < 50000.0.
    angle : float
        The horizontal angle of the cut. -179.9 < angle < 179.9.
    inclination : float
        The vertical angle of the cut. -179.9 < inclination < 179.9.
    slope : float
        The slope of the cut. -179.9 < slope < 179.9.
    length : float
        The length of the cut. 0.0 < length < 100000.0.
    width : float
        The width of the cut. 0.0 < width < 50000.0.
    internal_angle : float
        The internal angle of the cut. 0.1 < internal_angle < 179.9.
    tilt_ref_side : float
        The tilt angle of the reference side. 0.1 < tilt_ref_side < 179.9.
    tilt_end_side : float
        The tilt angle of the end side. 0.1 < tilt_end_side < 179.9.
    tilt_opp_side : float
        The tilt angle of the opposing side. 0.1 < tilt_opp_side < 179.9.
    tilt_start_side : float
        The tilt angle of the start side. 0.1 < tilt_start_side < 179.9.
    machining_limits : :class:`~compas_timber.fabrication.MachiningLimits` or dict, optional
        The machining limits for the cut. Default is None

    """

    PROCESSING_NAME = "Pocket"  # type: ignore

    @property
    def __data__(self):
        data = super(Pocket, self).__data__
        data["start_x"] = self.start_x
        data["start_y"] = self.start_y
        data["start_depth"] = self.start_depth
        data["angle"] = self.angle
        data["inclination"] = self.inclination
        data["slope"] = self.slope
        data["length"] = self.length
        data["width"] = self.width
        data["internal_angle"] = self.internal_angle
        data["tilt_ref_side"] = self.tilt_ref_side
        data["tilt_end_side"] = self.tilt_end_side
        data["tilt_opp_side"] = self.tilt_opp_side
        data["tilt_start_side"] = self.tilt_start_side
        data["machining_limits"] = self.machining_limits.limits
        return data

    # fmt: off
    def __init__(
        self,
        start_x: float =0.0,
        start_y: float =0.0,
        start_depth: float =0.0,
        angle: float = 0.0,
        inclination: float = 0.0,
        slope: float = 0.0,
        length: float = 200.0,
        width: float = 50.0,
        internal_angle: float = 90.0,
        tilt_ref_side: float = 90.0,
        tilt_end_side: float = 90.0,
        tilt_opp_side: float = 90.0,
        tilt_start_side: float = 90.0,
        machining_limits: Optional[MachiningLimits] = None,
        **kwargs
    ):
        super(Pocket, self).__init__(**kwargs)
        self._start_x = None
        self._start_y = None
        self._start_depth = None
        self._angle = None
        self._inclination = None
        self._slope = None
        self._length = None
        self._width = None
        self._internal_angle = None
        self._tilt_ref_side = None
        self._tilt_end_side = None
        self._tilt_opp_side = None
        self._tilt_start_side = None
        self._machining_limits = None

        self.start_x: float = start_x
        self.start_y: float = start_y
        self.start_depth: float = start_depth
        self.angle: float = angle
        self.inclination: float = inclination
        self.slope: float = slope
        self.length: float = length
        self.width: float = width
        self.internal_angle: float = internal_angle
        self.tilt_ref_side: float = tilt_ref_side
        self.tilt_end_side: float = tilt_end_side
        self.tilt_opp_side: float = tilt_opp_side
        self.tilt_start_side: float = tilt_start_side
        self.machining_limits: MachiningLimits = machining_limits

    ########################################################################
    # Properties
    ########################################################################

    @property
    def params(self) -> PocketParams:
        return PocketParams(self)

    @property
    def start_x(self) -> float:
        return self._start_x

    @start_x.setter
    def start_x(self, start_x):
        if start_x > 100000.0 or start_x < -100000.0:
            raise ValueError("Start X must be between -100000.0 and 100000.")
        self._start_x = start_x

    @property
    def start_y(self) -> float:
        return self._start_y

    @start_y.setter
    def start_y(self, start_y):
        if -50000.0 > start_y > 50000.0:
            raise ValueError("Start Y must be between -50000.0 and 50000.")
        self._start_y = start_y

    @property
    def start_depth(self) -> float:
        return self._start_depth

    @start_depth.setter
    def start_depth(self, start_depth):
        if start_depth > 50000.0 or start_depth < -50000.0:
            raise ValueError("Start depth must be between -50000 and 50000.")
        self._start_depth = start_depth

    @property
    def angle(self) -> float:
        return self._angle

    @angle.setter
    def angle(self, angle):
        if angle > 179.9 or angle < -179.9:
            raise ValueError("Angle must be between -179.9 and 179.9.")
        self._angle = angle

    @property
    def inclination(self) -> float:
        return self._inclination

    @inclination.setter
    def inclination(self, inclination):
        if inclination > 179.9 or inclination < -179.9:
            raise ValueError("Inclination must be between -179.9 and 179.9.")
        self._inclination = inclination

    @property
    def slope(self) -> float:
        return self._slope

    @slope.setter
    def slope(self, slope):
        if slope > 179.9 or slope < -179.9:
            raise ValueError("Slope must be between -179.9 and 179.9.")
        self._slope = slope

    @property
    def length(self) -> float:
        return self._length

    @length.setter
    def length(self, length):
        if not 0.0 < length < 100000.0:
            raise ValueError("Length must be between 0.0 and 100000.0")
        self._length = length

    @property
    def width(self) -> float:
        return self._width

    @width.setter
    def width(self, width):
        if width > 50000.0 or width < 0.0:
            raise ValueError("Width must be between 0.0 and 50000.")
        self._width = width

    @property
    def internal_angle(self) -> float:
        return self._internal_angle

    @internal_angle.setter
    def internal_angle(self, internal_angle):
        if internal_angle > 179.9 or internal_angle < 0.1:
            raise ValueError("Internal angle must be between 0.1 and 179.9.")
        self._internal_angle = internal_angle

    @property
    def tilt_ref_side(self) -> float:
        return self._tilt_ref_side

    @tilt_ref_side.setter
    def tilt_ref_side(self, tilt_ref_side):
        if tilt_ref_side > 179.9 or tilt_ref_side < 0.1:
            raise ValueError("Tilt reference side must be between 0.1 and 179.9.")
        self._tilt_ref_side = tilt_ref_side

    @property
    def tilt_end_side(self) -> float:
        return self._tilt_end_side

    @tilt_end_side.setter
    def tilt_end_side(self, tilt_end_side):
        if tilt_end_side > 179.9 or tilt_end_side < 0.1:
            raise ValueError("Tilt end side must be between 0.1 and 179.9.")
        self._tilt_end_side = tilt_end_side

    @property
    def tilt_opp_side(self) -> float:
        return self._tilt_opp_side

    @tilt_opp_side.setter
    def tilt_opp_side(self, tilt_opp_side):
        if tilt_opp_side > 179.9 or tilt_opp_side < 0.1:
            raise ValueError("Tilt opposite side must be between 0.1 and 179.9.")
        self._tilt_opp_side = tilt_opp_side

    @property
    def tilt_start_side(self) -> float:
        return self._tilt_start_side

    @tilt_start_side.setter
    def tilt_start_side(self, tilt_start_side):
        if tilt_start_side > 179.9 or tilt_start_side < 0.1:
            raise ValueError("Tilt start side must be between 0.1 and 179.9.")
        self._tilt_start_side = tilt_start_side

    @property
    def machining_limits(self) -> MachiningLimits:
        return self._machining_limits

    @machining_limits.setter
    def machining_limits(self, machining_limits):
        if isinstance(machining_limits, MachiningLimits):
            self._machining_limits = machining_limits
        elif isinstance(machining_limits, dict):
            self._machining_limits = MachiningLimits.from_dict(machining_limits)
        elif machining_limits is None:
            self._machining_limits = MachiningLimits()
        else:
            raise ValueError("Invalid machining limits.")

    ########################################################################
    # Alternative constructors
    ########################################################################

    @classmethod
    def from_volume_and_element(
        cls,
        volume: Union[Polyhedron, Brep, Mesh],
        element: TimberElement,
        machining_limits: Optional[dict] = None,
        ref_side_index: Optional[int]=None
    ) -> Pocket:
        """Construct a Pocket feature from a volume and a TimberElement.

        Parameters
        ----------
        volume : :class:`~compas.geometry.Polyhedron` or :class:`~compas.geometry.Brep` or :class:`~compas.geometry.Mesh`
            The volume of the pocket. Must have 6 faces.
        element : :class:`~compas_timber.timber.TimberElement`
            The element that is cut by this instance.
        machining_limits : :class:`~compas_timber.fabrication.btlx.MachiningLimits` or dict, optional
            The machining limits for the cut. Default is None.
        ref_side_index : int, optional
            The index of the reference side of the element. Default is 0.

        Returns
        -------
        :class:`~compas_timber.fabrication.Pocket`
            The Pocket feature.

        """
        # type: (Polyhedron | Brep | Mesh, Beam | Plate, dict, int) -> Pocket
        if isinstance(volume, Mesh):
            planes = [volume.face_plane(i) for i in range(volume.number_of_faces())]
        elif isinstance(volume, Polyhedron):
            volume = volume.to_mesh()
            planes = [volume.face_plane(i) for i in range(volume.number_of_faces())]
        elif isinstance(volume, Brep):
            volume_frames = [face.frame_at(0,0) for face in volume.faces]
            planes = [Plane.from_frame(frame) for frame in volume_frames]
        else:
            raise ValueError("Volume must be either a Mesh, Brep, or Polyhedron.")

        if len(planes) != 6:
            raise ValueError("Volume must have 6 faces.")

        # get ref_side of the element
        if ref_side_index is None:
            ref_side_index = cls._get_optimal_ref_side_index(element, volume)
        ref_side = element.ref_sides[ref_side_index]

        # sort the planes based on the reference side
        planes = cls._sort_planes(planes, ref_side)
        start_plane, end_plane, front_plane, back_plane, bottom_plane, _ = planes

        # get the intersection points
        try:
            start_point = Point(*intersection_plane_plane_plane(start_plane, front_plane, bottom_plane, tol=TOL.ABSOLUTE))
            back_point = Point (*intersection_plane_plane_plane(start_plane, back_plane, bottom_plane, tol=TOL.ABSOLUTE))
            end_point = Point(*intersection_plane_plane_plane(end_plane, front_plane, bottom_plane, tol=TOL.ABSOLUTE))
        except TypeError as te:
            raise ValueError("Failed to orient the volume to the element. Consider using a different ref_side_index " + str(te))

        ## params calculations
        # calculate start_x, start_y, start_depth
        start_x, start_y, start_depth = cls._calculate_start_x_y_depth(ref_side, start_point)

        # x"-axis and y"-axis (planar axis of the bottom face of the volume)
        xxaxis = Vector.from_start_end(start_point, end_point)
        yyaxis = Vector.from_start_end(start_point, back_point)

        # calculate the angle of the pocket
        angle = angle_vectors_projected(ref_side.xaxis, xxaxis, ref_side.normal, deg=True)
        # x'-axis and y'-axis (see BTLx Documentation p.46)
        xaxis = ref_side.xaxis.rotated(math.radians(angle), ref_side.normal)
        yaxis = ref_side.yaxis.rotated(math.radians(angle), ref_side.normal)

        # calculate the inclination of the pocket
        inclination = angle_vectors_projected(xaxis, xxaxis, yaxis, deg=True)

        # calculate the slope of the pocket
        slope = angle_vectors_projected(yaxis, yyaxis, xxaxis, deg=True)

        # calculate internal_angle
        internal_angle = angle_vectors_signed(xxaxis, yyaxis, ref_side.normal, deg=True)

        # calculate length and width
        length = xxaxis.length*math.sin(math.radians(internal_angle))
        width = yyaxis.length*math.sin(math.radians(internal_angle))

        # calculate tilt angles
        tilt_ref_side = cls._calculate_tilt_angle(bottom_plane, front_plane)
        tilt_end_side = cls._calculate_tilt_angle(bottom_plane, end_plane)
        tilt_opp_side = cls._calculate_tilt_angle(bottom_plane, back_plane)
        tilt_start_side = cls._calculate_tilt_angle(bottom_plane, start_plane)

        # define machining limits
        if not machining_limits:
            machining_limits = cls._define_machining_limits(planes, element, ref_side_index)

        return cls(
            start_x,
            start_y,
            start_depth,
            angle,
            inclination,
            slope,
            length,
            width,
            internal_angle,
            tilt_ref_side,
            tilt_end_side,
            tilt_opp_side,
            tilt_start_side,
            machining_limits,
            ref_side_index=ref_side_index)

    @classmethod
    def from_shapes_and_element(cls, volume, element, **kwargs) -> Pocket:
        """Construct a Pocket feature from a volume and a TimberElement.

        Parameters
        ----------
        volume : :class:`~compas.geometry.Polyhedron` or :class:`~compas.geometry.Brep` or :class:`~compas.geometry.Mesh`
            The volume of the pocket. Must have 6 faces.
        element : :class:`~compas_timber.elements.Beam` or :class:`~compas_timber.elements.Plate`
            The element that is cut by this instance.
        machining_limits : :class:`compas_timber.fabrication.MachiningLimits()` or dict, optional
            The machining limits for the cut. Default is None.
        ref_side_index : int, optional
            The index of the reference side of the element. Default is 0.

        Returns
        -------
        :class:`~compas_timber.fabrication.Pocket`
            The Pocket feature.

        """
        return cls.from_volume_and_element(volume, element, **kwargs)

    @staticmethod
    def _get_optimal_ref_side_index(element, volume) -> int:
        # get the optimal reference side index based on the volume. The optimal reference side is the one with the most intersections with the volume edges.
        # get the volume edges
        if isinstance(volume, Brep):
            volume_curve = [edge.curve for edge in volume.edges]
            volume_edges = [Line(*curve.points) for curve in volume_curve]
        else:
            volume_edges = [volume.edge_line(edge) for edge in volume.edges()]

        intersection_counts = []
        for i, side in enumerate(element.ref_sides):
            int_pts = []
            for edge in volume_edges:
                int_pt = intersection_segment_plane(edge, Plane.from_frame(side))
                if int_pt:
                    int_pts.append(int_pt)
            intersection_counts.append((i, len(int_pts)))
        # Find the index with the maximum intersections
        optimal_index = max(intersection_counts, key=lambda x: x[1])[0] if intersection_counts else None
        return optimal_index

    @staticmethod
    def _sort_planes(planes, ref_side) -> list[Plane]:
        # Sort planes based on the dot product of face normals with the x-axis
        planes.sort(key=lambda plane: plane.normal.dot(ref_side.xaxis))
        start_plane, end_plane = planes[0], planes[-1]

        # Sort planes based on the dot product of face normals with the y-axis
        planes.sort(key=lambda plane: plane.normal.dot(ref_side.yaxis))
        front_plane, back_plane = planes[0], planes[-1]

        # Sort planes based on the dot product of face normals with the z-axis
        planes.sort(key=lambda plane: plane.normal.dot(ref_side.zaxis))
        bottom_plane, top_plane = planes[0], planes[-1]

        return start_plane, end_plane, front_plane, back_plane, bottom_plane, top_plane

    @staticmethod
    def _calculate_start_x_y_depth(ref_side, start_point) -> tuple[float, float, float]:
        # calculate the start_x, start_y, and start_depth of the pocket based on the start_corner_point and the ref_side
        start_vector = Vector.from_start_end(ref_side.point, start_point)
        start_x = dot_vectors(start_vector, ref_side.xaxis)
        start_y = dot_vectors(start_vector, ref_side.yaxis)
        start_depth = dot_vectors(start_vector, -ref_side.zaxis)
        return start_x, start_y, start_depth

    @staticmethod
    def _calculate_tilt_angle(bottom_plane, plane) -> float:
        # calculate the tilt angle of the pocket based on the bottom_plane and the plane of the face to be tilted
        return angle_vectors(-bottom_plane.normal, plane.normal, deg=True)

    @staticmethod
    def _define_machining_limits(planes, element, ref_side_index) -> MachiningLimits:
        # define machining limits based on the planes
        ref_sides = [Plane.from_frame(frame) for frame in element.ref_sides]
        start_side, end_side = ref_sides[-2:]
        ref_sides = ref_sides[:-2]
        ref_side, front_side, opp_side, back_side = ref_sides[ref_side_index:] + ref_sides[:ref_side_index]
        start_plane, end_plane, front_plane, back_plane, bottom_plane, top_plane = planes

        machining_limits = MachiningLimits()
        machining_limits.face_limited_top = False # TODO: Should this always be False?
        machining_limits.face_limited_start = is_point_behind_plane(start_plane.point, start_side)
        machining_limits.face_limited_end = is_point_behind_plane(end_plane.point, end_side)
        machining_limits.face_limited_front = is_point_behind_plane(front_plane.point, front_side)
        machining_limits.face_limited_back = is_point_behind_plane(back_plane.point, back_side)
        machining_limits.face_limited_bottom = is_point_behind_plane(bottom_plane.point, opp_side)

        return machining_limits


    ########################################################################
    # Methods
    ########################################################################

    def apply(self, geometry: Brep, element: TimberElement):
        """Apply the feature to the element geometry.

        Parameters
        ----------
        geometry : :class:`~compas.geometry.Brep`
            The geometry of the elements to be processed.
        element : :class:`compas_timber.timber.TimberElement`
            The element that is processed by this instance.

        Raises
        ------
        :class:`~compas_timber.errors.FeatureApplicationError`
            If the cutting plane does not intersect with element geometry.

        Returns
        -------
        :class:`~compas.geometry.Brep`
            The resulting geometry after processing

        """
        # type: (Brep, Beam | Plate) -> Brep
        # get the pocket volume as a polyhedron
        polyhedron_volume = self.volume_from_params_and_element(element)
        polyhedron_volume.transform(element.transformation_to_local())

        # convert the polyhedron to a brep
        try:
            pocket_volume = Brep.from_mesh(polyhedron_volume.to_mesh())
        except Exception as e:
            raise FeatureApplicationError(
                polyhedron_volume,
                geometry,
                "The pocket volume could not be converted to a Brep." + str(e),
            )
        try:
            return geometry - pocket_volume
        except Exception as e:
            raise FeatureApplicationError(
                pocket_volume,
                geometry,
                "The pocket volume does not intersect with the element geometry." + str(e),
            )

    def _bottom_frame_from_params_and_element(self, element: TimberElement) -> Frame:
        """Calculates the bottom frame of the pocket from the machining parameters in this instance and the given element.

        Parameters
        ----------
        element : :class:`compas_timber.elements.Beam` or :class:`compas_timber.elements.Plate`
            The element that is cut by this instance.

        Returns
        -------
        :class:`compas.geometry.Frame`
            The bottom frame of the pocket.
        """
        assert self.start_x is not None
        assert self.start_y is not None
        assert self.start_depth is not None
        assert self.angle is not None
        assert self.inclination is not None
        assert self.slope is not None
        assert self.internal_angle is not None

        ref_side = element.ref_sides[self.ref_side_index]
        ref_surface = element.side_as_surface(self.ref_side_index) # TODO: make sure `Plate` element has side_as_surface method

        p_origin = planar_surface_point_at(ref_surface, self.start_x, self.start_y)
        p_origin.translate(-ref_side.normal * self.start_depth)
        bottom_frame = Frame(p_origin, ref_side.xaxis, ref_side.yaxis)

        # rotate the plane based on the angle
        bottom_frame.rotate(math.radians(self.angle), bottom_frame.normal, point=bottom_frame.point)
        # rotate the plane based on the inclination
        bottom_frame.rotate(math.radians(self.inclination), bottom_frame.yaxis, point=bottom_frame.point)
        # rotate the plane based on the slope
        bottom_frame.rotate(math.radians(self.slope), bottom_frame.xaxis, point=bottom_frame.point)

        # flip the normal
        bottom_frame.xaxis = -bottom_frame.xaxis

        # rotate the plane based on the internal angle
        bottom_frame.rotate(math.radians(180-self.internal_angle), bottom_frame.normal, point=bottom_frame.point)
        return bottom_frame

    def _planes_from_params_and_element(self, element: TimberElement) -> list[Plane]:
        """Calculates the planes that create the pocket from the machining parameters in this instance and the given element

        Parameters
        ----------
        element : :class:`compas_timber.elements.Beam` or :class:`compas_timber.elements.Plate`
            The element that is cut by this instance.

        Returns
        -------
        list of :class:`compas.geometry.Plane`
            The planes of the cut as a list.

        """
        assert self.length
        assert self.width
        assert self.tilt_ref_side
        assert self.tilt_end_side
        assert self.tilt_opp_side
        assert self.tilt_start_side
        assert self.machining_limits

        tol = 1e-3  # TODO: use TOL.absolute if possible, but do not manipulate the global tolerance value

        # get bottom frame
        bottom_frame = self._bottom_frame_from_params_and_element(element)
        # get top frame
        if self.machining_limits.face_limited_top:
            top_frame = bottom_frame.translated(-bottom_frame.zaxis * self.start_depth)
            top_frame.xaxis = -top_frame.xaxis
        else:
            top_frame = element.ref_sides[self.ref_side_index]
            top_frame.translate(top_frame.normal * tol)

        # tilt start frame
        if self.machining_limits.face_limited_start:
            start_frame = bottom_frame.rotated(math.radians(180-self.tilt_start_side), bottom_frame.xaxis, point=bottom_frame.point)
        else:
            start_frame = element.ref_sides[4]
            start_frame.translate(start_frame.normal * tol)

        # tilt end frame
        if self.machining_limits.face_limited_end:
            end_frame = bottom_frame.translated(bottom_frame.yaxis * self.length)
            end_frame.rotate(math.radians(180-self.tilt_end_side), -end_frame.xaxis, point=end_frame.point)
        else:
            end_frame = element.ref_sides[5]
            end_frame.translate(end_frame.normal * tol)

        # Rotate the bottom frame so its xaxis is aligned to the axis of rotation.
        bottom_frame.rotate(math.radians(180-self.internal_angle), -bottom_frame.normal, point=bottom_frame.point)

        # tilt front frame
        if self.machining_limits.face_limited_front:
            front_frame = bottom_frame.rotated(-math.radians(self.tilt_ref_side), bottom_frame.xaxis, point=bottom_frame.point)
        else:
            front_frame = element.front_side(self.ref_side_index)
            front_frame.translate(front_frame.normal * tol)

        # tilt back frame
        if self.machining_limits.face_limited_back:
            back_frame = bottom_frame.rotated(math.radians(180 - self.tilt_opp_side), -bottom_frame.xaxis, point=bottom_frame.point)
            # back_frame.translate(back_frame.normal * self.width)
            back_frame.translate(bottom_frame.yaxis * self.width)
        else:
            back_frame = element.back_side(self.ref_side_index)
            back_frame.translate(back_frame.normal * tol)

        frames = [start_frame, end_frame, top_frame, bottom_frame, front_frame, back_frame]
        return [Plane.from_frame(frame) for frame in frames]

    def volume_from_params_and_element(self, element: TimberElement) -> Polyhedron:
        """
        Calculates the subtracting volume from the machining parameters in this instance and the given element, ensuring correct face orientation.

        Parameters
        ----------
        element : :class:`compas_timber.elements.Beam` or :class:`compas_timber.elements.Plate`
            The element that is cut by this instance.

        Returns
        -------
        :class:`compas.geometry.Polyhedron`
            The correctly oriented subtracting volume of the pocket.
        """
        # type: (Beam | Plate) -> Polyhedron
        # Get cutting planes
        start_plane, end_plane, top_plane, bottom_plane, front_plane, back_plane = self._planes_from_params_and_element(element)

        # Calculate vertices using plane-plane-plane intersection
        vertices = [
            Point(*intersection_plane_plane_plane(start_plane, bottom_plane, front_plane)),     # v0
            Point(*intersection_plane_plane_plane(start_plane, bottom_plane, back_plane)),      # v1
            Point(*intersection_plane_plane_plane(end_plane, bottom_plane, back_plane)),        # v2
            Point(*intersection_plane_plane_plane(end_plane, bottom_plane, front_plane)),       # v3
            Point(*intersection_plane_plane_plane(start_plane, top_plane, front_plane)),        # v4
            Point(*intersection_plane_plane_plane(start_plane, top_plane, back_plane)),         # v5
            Point(*intersection_plane_plane_plane(end_plane, top_plane, back_plane)),           # v6
            Point(*intersection_plane_plane_plane(end_plane, top_plane, front_plane)),          # v7
        ]

        # define faces of the trimming volume
        # ensure vertices are defined in counter-clockwise order when viewed from the outside
        faces = [
            [0, 1, 2, 3],  # Bottom face
            [7, 6, 5, 4],  # Top face
            [4, 5, 1, 0],  # Start face
            [5, 6, 2, 1],  # Back face
            [6, 7, 3, 2],  # End face
            [7, 4, 0, 3],  # Front face
        ]

        return Polyhedron(vertices, faces)

    def scale(self, factor: float) -> None:
        """Scale the parameters of this processing by a given factor.

        Note
        ----
        Only distances are scaled, angles remain unchanged.

        Parameters
        ----------
        factor : float
            The scaling factor. A value of 1.0 means no scaling, while a value of 2.0 means doubling the size.

        """
        self.start_x *= factor
        self.start_y *= factor
        self.start_depth *= factor
        self.length *= factor
        self.width *= factor


class PocketParams(BTLxProcessingParams):
    """A class to store the parameters of a Pocket feature.

    Parameters
    ----------
    instance : :class:`~compas_timber.fabrication.Pocket`
        The instance of the Pocket feature.
    """

    def __init__(self, instance):
        # type: (Pocket) -> None
        super(PocketParams, self).__init__(instance)

    def as_dict(self):
        """Returns the parameters of the Pocket feature as a dictionary.

        Returns
        -------
        dict
            The parameters of the Pocket feature as a dictionary.
        """
        # type: () -> OrderedDict
        result = OrderedDict()
        result["StartX"] = "{:.{prec}f}".format(float(self._instance.start_x), prec=TOL.precision)
        result["StartY"] = "{:.{prec}f}".format(float(self._instance.start_y), prec=TOL.precision)
        result["StartDepth"] = "{:.{prec}f}".format(float(self._instance.start_depth), prec=TOL.precision)
        result["Angle"] = "{:.{prec}f}".format(float(self._instance.angle), prec=TOL.precision)
        result["Inclination"] = "{:.{prec}f}".format(float(self._instance.inclination), prec=TOL.precision)
        result["Slope"] = "{:.{prec}f}".format(float(self._instance.slope), prec=TOL.precision)
        result["Length"] = "{:.{prec}f}".format(float(self._instance.length), prec=TOL.precision)
        result["Width"] = "{:.{prec}f}".format(float(self._instance.width), prec=TOL.precision)
        result["InternalAngle"] = "{:.{prec}f}".format(float(self._instance.internal_angle), prec=TOL.precision)
        result["TiltRefSide"] = "{:.{prec}f}".format(float(self._instance.tilt_ref_side), prec=TOL.precision)
        result["TiltEndSide"] = "{:.{prec}f}".format(float(self._instance.tilt_end_side), prec=TOL.precision)
        result["TiltOppSide"] = "{:.{prec}f}".format(float(self._instance.tilt_opp_side), prec=TOL.precision)
        result["TiltStartSide"] = "{:.{prec}f}".format(float(self._instance.tilt_start_side), prec=TOL.precision)
        result["MachiningLimits"] = {key: "yes" if value else "no" for key, value in self._instance.machining_limits.limits.items()}
        return result


class PocketProxy(object):
    """This object behaves like a Pocket except it only calculates the machining parameters once unproxified.
    Can also be used to defer the creation of the processing instance until it is actually needed.

    Until then, it can be used to visualize the machining operation.
    This slightly improves performance.

    Parameters
        ----------
        volume : :class:`~compas.geometry.Polyhedron` or :class:`~compas.geometry.Brep` or :class:`~compas.geometry.Mesh`
            The volume of the pocket. Must have 6 faces.
        element : :class:`~compas_timber.elements.Beam` or :class:`~compas_timber.elements.Plate`
            The element that is cut by this instance.
        machining_limits : :class:`~compas_timber.fabrication.MachiningLimits` or dict, optional
            The machining limits for the cut. Default is None.
        ref_side_index : int, optional
            The index of the reference side of the element. Default is 0.

        Returns
        -------
        :class:`~compas_timber.fabrication.Pocket`
            The Pocket feature.

    """

    def __deepcopy__(self, *args, **kwargs):
        # not sure there's value in copying the proxy as it's more of a performance hack.
        # plus it references a beam so it would be a bit of a mess to copy it.
        # for now just return the unproxified version
        return self.unproxified()

    def __init__(self, volume, element, machining_limits=None, ref_side_index=None):
        self.volume = volume.transformed(element.transformation_to_local())
        self.element = element
        self.machining_limits = machining_limits
        self.ref_side_index = ref_side_index
        self._processing = None

    def unproxified(self):
        """Returns the unproxified processing instance.

        Returns
        -------
        :class:`~compas_timber.fabrication.Pocket`

        """
        if not self._processing:
            volume = self.volume.transformed(self.element.modeltransformation)
            self._processing = Pocket.from_volume_and_element(volume, self.element, self.machining_limits, self.ref_side_index)
        return self._processing

    @classmethod
    def from_volume_and_element(cls, volume, element, machining_limits=None, ref_side_index=None):
        """Construct a Pocket feature from a volume and a TimberElement.

        Parameters
        ----------
        volume : :class:`~compas.geometry.Polyhedron` or :class:`~compas.geometry.Brep` or :class:`~compas.geometry.Mesh`
            The volume of the pocket. Must have 6 faces.
        element : :class:`~compas_timber.elements.Beam` or :class:`~compas_timber.elements.Plate`
            The element that is cut by this instance.
        machining_limits : :class:`compas_timber.fabrication.MachiningLimits()` or dict, optional
            The machining limits for the cut. Default is None.
        ref_side_index : int, optional
            The index of the reference side of the element. Default is 0.

        Returns
        -------
        :class:`~compas_timber.fabrication.Pocket`
            The Pocket feature.

        """
        if isinstance(volume, Polyhedron):
            volume = Brep.from_mesh(volume.to_mesh())
        if TOL.is_negative(volume.volume):
            volume.flip()
        return cls(volume, element, machining_limits, ref_side_index)

    def apply(self, geometry, _):
        """Apply the feature to the beam geometry.

        Parameters
        ----------
        geometry : :class:`~compas.geometry.Brep`
            The beam geometry to apply the pocket to.
        element : :class:`~compas_timber.elements.Beam` or :class:`~compas_timber.elements.Plate`
            The element that is cut by this instance.

        Raises
        ------
        :class:`~compas_timber.errors.FeatureApplicationError`
            If the pocket volume does not intersect with element geometry.

        Returns
        -------
        :class:`~compas.geometry.Brep`
            The resulting geometry after processing

        """
        # type: (Brep, Element) -> Brep
        try:
            return geometry - self.volume
        except IndexError:
            raise FeatureApplicationError(
                self.volume,
                geometry,
                "The volume to subtract does not intersect with element geometry.",
            )

    def __getattr__(self, attr):
        # any unknown calls are passed through to the processing instance
        return getattr(self.unproxified(), attr)
