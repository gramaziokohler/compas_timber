import math
from collections import OrderedDict

from compas.datastructures import Mesh
from compas.geometry import Brep
from compas.geometry import Frame
from compas.geometry import Line
from compas.geometry import Plane
from compas.geometry import Point
from compas.geometry import Polyhedron
from compas.geometry import Vector
from compas.geometry import angle_vectors_signed
from compas.geometry import distance_point_plane
from compas.geometry import distance_point_point
from compas.geometry import dot_vectors
from compas.geometry import intersection_line_plane
from compas.geometry import intersection_plane_plane_plane
from compas.geometry import intersection_segment_plane
from compas.geometry import is_point_behind_plane
from compas.tolerance import TOL
from compas.tolerance import Tolerance

from compas_timber.errors import FeatureApplicationError
from compas_timber.utils import angle_vectors_projected

from .btlx import BTLxProcessing
from .btlx import BTLxProcessingParams
from .btlx import MachiningLimits
from .btlx import OrientationType


class Lap(BTLxProcessing):
    """Represents a Lap feature to be made on a beam.

    Parameters
    ----------
    orientation : int
        The orientation of the cut. Must be either OrientationType.START or OrientationType.END.
    start_x : float
        The start x-coordinate of the cut in parametric space of the reference side. -100000.0 < start_x < 100000.0.
    start_y : float
        The start y-coordinate of the cut in parametric space of the reference side. -50000.0 < start_y < 50000.0.
    angle : float
        The horizontal angle of the cut. 0.1 < angle < 179.9.
    inclination : float
        The vertical angle of the cut. 0.1 < inclination < 179.9.
    slope : float
        The slope of the cut. -89.9 < slope < 89.9.
    length : float
        The length of the cut. 0.0 < length < 100000.0.
    width : float
        The width of the cut. 0.0 < width < 50000.0.
    depth : float
        The depth of the cut. -50000.0 < depth < 50000.0.
    lead_angle_parallel : bool
        The lead angle is parallel to the beam axis.
    lead_angle : float
        The lead angle of the cut. 0.1 < lead_angle < 179.9.
    lead_inclination_parallel : bool
        The lead inclination is parallel to the beam axis.
    lead_inclination : float
        The lead inclination of the cut. 0.1 < lead_inclination < 179.9.
    machining_limits : dict, optional
        The machining limits for the cut. Default is None

    """

    PROCESSING_NAME = "Lap"  # type: ignore

    @property
    def __data__(self):
        data = super(Lap, self).__data__
        data["orientation"] = self.orientation
        data["start_x"] = self.start_x
        data["start_y"] = self.start_y
        data["angle"] = self.angle
        data["inclination"] = self.inclination
        data["slope"] = self.slope
        data["length"] = self.length
        data["width"] = self.width
        data["depth"] = self.depth
        data["lead_angle_parallel"] = self.lead_angle_parallel
        data["lead_angle"] = self.lead_angle
        data["lead_inclination_parallel"] = self.lead_inclination_parallel
        data["lead_inclination"] = self.lead_inclination
        data["machining_limits"] = self.machining_limits
        return data

    # fmt: off
    def __init__(
        self,
        orientation=OrientationType.START,
        start_x=0.0,
        start_y=0.0,
        angle=90.0,
        inclination=90.0,
        slope=0.0,
        length=200.0,
        width=50.0,
        depth=40.0,
        lead_angle_parallel=True,
        lead_angle=90.0,
        lead_inclination_parallel=True,
        lead_inclination=90.0,
        machining_limits=None,
        **kwargs
    ):
        super(Lap, self).__init__(**kwargs)
        self._orientation = None
        self._start_x = None
        self._start_y = None
        self._angle = None
        self._inclination = None
        self._slope = None
        self._length = None
        self._width = None
        self._depth = None
        self._lead_angle_parallel = None
        self._lead_angle = None
        self._lead_inclination_parallel = None
        self._lead_inclination = None
        self._machining_limits = None

        self.orientation = orientation
        self.start_x = start_x
        self.start_y = start_y
        self.angle = angle
        self.inclination = inclination
        self.slope = slope
        self.length = length
        self.width = width
        self.depth = depth
        self.lead_angle_parallel = lead_angle_parallel
        self.lead_angle = lead_angle
        self.lead_inclination_parallel = lead_inclination_parallel
        self.lead_inclination = lead_inclination
        self.machining_limits = machining_limits

    ########################################################################
    # Properties
    ########################################################################

    @property
    def params(self):
        return LapParams(self)

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
    def start_y(self):
        return self._start_y

    @start_y.setter
    def start_y(self, start_y):
        if -50000.0 > start_y > 50000.0:
            raise ValueError("Start Y must be between -50000.0 and 50000.")
        self._start_y = start_y

    @property
    def angle(self):
        return self._angle

    @angle.setter
    def angle(self, angle):
        if angle > 179.9 or angle < 0.1:
            raise ValueError("Angle must be between 0.1 and 179.9.")
        self._angle = angle

    @property
    def inclination(self):
        return self._inclination

    @inclination.setter
    def inclination(self, inclination):
        if inclination > 179.9 or inclination < 0.1:
            raise ValueError("Inclination must be between 0.1 and 179.9.")
        self._inclination = inclination

    @property
    def slope(self):
        return self._slope

    @slope.setter
    def slope(self, slope):
        if slope > 89.9 or slope < -89.9:
            raise ValueError("Slope must be between -89.9 and 89.9.")
        self._slope = slope

    @property
    def length(self):
        return self._length

    @length.setter
    def length(self, length):
        if not 0.0 < length < 100000.0:
            raise ValueError("Length must be between 0.0 and 100000.0")
        self._length = length

    @property
    def width(self):
        return self._width

    @width.setter
    def width(self, width):
        if width > 50000.0 or width < 0.0:
            raise ValueError("Width must be between 0.0 and 50000.")
        self._width = width

    @property
    def depth(self):
        return self._depth

    @depth.setter
    def depth(self, depth):
        if depth > 50000.0 or depth < -50000.0:
            raise ValueError("Depth must be between -50000 and 50000.")
        self._depth = depth

    @property
    def lead_angle_parallel(self):
        return self._lead_angle_parallel

    @lead_angle_parallel.setter
    def lead_angle_parallel(self, lead_angle_parallel):
        if not isinstance(lead_angle_parallel, bool):
            raise ValueError("Lead angle parallel must be a boolean.")
        self._lead_angle_parallel = lead_angle_parallel

    @property
    def lead_angle(self):
        return self._lead_angle

    @lead_angle.setter
    def lead_angle(self, lead_angle):
        if lead_angle > 179.9 or lead_angle < 0.1:
            raise ValueError("Lead angle must be between 0.1 and 179.9.")
        self._lead_angle = lead_angle

    @property
    def lead_inclination_parallel(self):
        return self._lead_inclination_parallel

    @lead_inclination_parallel.setter
    def lead_inclination_parallel(self, lead_inclination_parallel):
        if not isinstance(lead_inclination_parallel, bool):
            raise ValueError("Lead inclination parallel must be a boolean.")
        self._lead_inclination_parallel = lead_inclination_parallel

    @property
    def lead_inclination(self):
        return self._lead_inclination

    @lead_inclination.setter
    def lead_inclination(self, lead_inclination):
        if lead_inclination > 179.9 or lead_inclination < 0.1:
            raise ValueError("Lead inclination must be between 0.1 and 179.9.")
        self._lead_inclination = lead_inclination

    @property
    def machining_limits(self):
        return self._machining_limits

    @machining_limits.setter
    def machining_limits(self, machining_limits):
        if not isinstance(machining_limits, dict):
            raise ValueError("Machining limits must be a dictionary.")
        for key, value in machining_limits.items():
            if key not in MachiningLimits.EXPECTED_KEYS:
                raise ValueError("The key must be one of the following: ", {self.EXPECTED_KEYS})
            if not isinstance(value, bool):
                raise ValueError("The values must be a boolean.")
        self._machining_limits = machining_limits


    ########################################################################
    # Alternative constructors
    ########################################################################

    @classmethod
    def from_plane_and_beam(cls, plane, beam, length, depth, ref_side_index=0):
        """Create a Lap instance from a plane and a beam. The lap is defined by the plane given and a plane parallel to that at a distance defined by the length and a given depth.
        This method is used to create pocket cuts.

        Parameters
        ----------
        plane : :class:`~compas.geometry.Plane`
            The plane that defines the lap.
        beam : :class:`~compas_timber.elements.Beam`
            The beam that the Lap instance is applied to.
        length : float
            The length of the lap.
        depth : float
            The depth of the lap.
        ref_side_index : int, optional
            The reference side index of the main_beam to be cut. Default is 0 (i.e. RS1).

        Returns
        -------
        :class:`~compas_timber.fabrication.Lap`

        """
        # type: (Plane, Beam, float, float, int) -> Lap
        if isinstance(plane, Frame):
            plane = Plane.from_frame(plane)

        # create an offset plane at the depth of the lap
        offset_plane = Plane(plane.point - plane.normal * length, -plane.normal)
        planes = [plane, offset_plane]

        # get ref_side, and ref_edge from the beam
        ref_side = beam.ref_sides[ref_side_index]
        ref_side_surface = beam.side_as_surface(ref_side_index)
        ref_edge = Line.from_point_and_vector(ref_side.point, ref_side.xaxis)

        # sort the planes based on the angle between their normals and the reference side's normal
        planes.sort(key=lambda plane: abs(angle_vectors_signed(ref_side.normal, plane.normal, ref_side.yaxis, deg=True)))

        # calculate the orientation of the lap
        orientation = cls._calculate_orientation(ref_side, planes[0])

        # calculate the start_x of the lap
        start_x = cls._calculate_start_x(ref_side, ref_edge, planes, orientation, depth)

        # calculate the angle of the lap
        angle = cls._calculate_angle(ref_side, planes[0])

        # calculate the inclination of the lap
        inclination = 90.0

        # calculate the slope of the lap
        slope = 0.0

        # calculate length
        length = cls._calculate_length(planes, ref_side, ref_edge, depth, angle)

        # define the width of the lap
        width = ref_side_surface.ysize

        # define machining limits
        machining_limits = MachiningLimits()
        machining_limits.face_limited_top = False
        machining_limits.face_limited_back = False
        machining_limits.face_limited_front = False

        return cls(orientation=orientation,
                   start_x=start_x,
                   angle=angle,
                   inclination=inclination,
                   slope=slope,
                   length=length,
                   width=width,
                   depth=depth,
                   machining_limits=machining_limits.limits,
                   ref_side_index=ref_side_index)

    @classmethod
    def from_volume_and_beam(cls, volume, beam, machining_limits=None, ref_side_index=None):
        """Construct a Lap feature from a volume and a Beam.

        Parameters
        ----------
        volume : :class:`~compas.geometry.Polyhedron` or :class:`~compas.geometry.Brep` or :class:`~compas.geometry.Mesh`
            The volume of the lap. Must have 6 faces.
        beam : :class:`~compas_timber.elements.Beam`
            The beam that is cut by this instance.
        machining_limits : dict, optional
            The machining limits for the cut. Default is None.
        ref_side_index : int, optional
            The index of the reference side of the element. Default is 0.

        Returns
        -------
        :class:`~compas_timber.fabrication.Lap`
            The Lap feature.

        """
        # type: (Polyhedron | Brep | Mesh, Beam, dict, int) -> Lap
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

        # get ref_side of the
        if not ref_side_index:
            ref_side_index = cls._get_optimal_ref_side_index(beam, volume)
        ref_side = beam.ref_sides[ref_side_index]

        # sort the planes based on the reference side
        planes = cls._sort_planes(planes, ref_side)
        start_plane, end_plane, front_plane, back_plane, bottom_plane, _ = planes

        # get the intersection points
        try:
            start_point = Point(*intersection_plane_plane_plane(start_plane, front_plane, Plane.from_frame(ref_side), tol=TOL.ABSOLUTE))
            bottom_point = Point(*intersection_plane_plane_plane(start_plane, front_plane, bottom_plane, tol=TOL.ABSOLUTE))
            back_point = Point (*intersection_plane_plane_plane(start_plane, back_plane, Plane.from_frame(ref_side), tol=TOL.ABSOLUTE))
            end_point = Point(*intersection_plane_plane_plane(end_plane, front_plane, Plane.from_frame(ref_side), tol=TOL.ABSOLUTE))
        except TypeError as te:
            raise ValueError("Failed to orient the volume to the element. Consider using a different ref_side_index " + str(te))

        # for simplicity, orientation is always set to START
        orientation = OrientationType.START

        # calculate start_x, start_y
        start_x, start_y = cls._calculate_start_x_y(ref_side, start_point)

        # x"-axis and y"-axis (planar axis of the top face of the volume)
        xxaxis = Vector.from_start_end(start_point, end_point)
        yyaxis = Vector.from_start_end(start_point, back_point)
        zzaxis = Vector.from_start_end(start_point, bottom_point)

        # calculate the angle of the lap
        angle = angle_vectors_signed(-yyaxis, ref_side.xaxis, ref_side.normal, deg=True)

        # calculate the inclination of the lap
        inclination = angle_vectors_projected(zzaxis, front_plane.normal, yyaxis)
        inclination = 180 + inclination if inclination < 0 else inclination

        # calculate the slope of the lap
        slope = angle_vectors_projected(-ref_side.normal, bottom_plane.normal, start_plane.normal)

        # calculate length, width and depth
        length = distance_point_plane(start_plane.point, end_plane)
        width = abs(yyaxis.dot(ref_side.yaxis))
        depth = abs(zzaxis.dot(ref_side.zaxis))

        # define lead_angle and lead_inclination parallelity
        lead_angle_parallel = cls._check_lead_parallelity(beam, ref_side_index, front_plane, back_plane)
        lead_inclination_parallel = lead_angle_parallel

        if lead_angle_parallel:
            lead_angle = 90.0
        else:
            lead_angle = angle_vectors_signed(xxaxis, yyaxis, ref_side.normal, deg=True)

        if lead_inclination_parallel:
            lead_inclination = 90.0
        else:
            lead_inclination = angle_vectors_signed(front_plane.normal, bottom_plane.normal, ref_side.xaxis, deg=True)

        # define machining limits
        if machining_limits:
            if not isinstance(machining_limits, dict):
                raise ValueError("machining_limits must be a dictionary.")
        else:
            machining_limits = cls._define_machining_limits(planes, beam, ref_side_index)

        return cls(orientation,
                   start_x,
                   start_y,
                   angle,
                   inclination,
                   slope,
                   length,
                   width,
                   depth,
                   lead_angle_parallel,
                   lead_angle,
                   lead_inclination_parallel,
                   lead_inclination,
                   machining_limits=machining_limits,
                   ref_side_index=ref_side_index)

    @classmethod
    def from_shapes_and_element(cls, volume, element, **kwargs):
        """Construct a Lap feature from a volume and a TimberElement.

        Parameters
        ----------
        volume : :class:`~compas.geometry.Polyhedron` or :class:`~compas.geometry.Brep` or :class:`~compas.geometry.Mesh`
            The volume of the Lap. Must have 6 faces.
        element : :class:`~compas_timber.elements.Beam`
            The element that is cut by this instance.
        machining_limits : dict, optional
            The machining limits for the cut. Default is None.
        ref_side_index : int, optional
            The index of the reference side of the element. Default is 0.

        Returns
        -------
        :class:`~compas_timber.fabrication.Lap`
            The Lap feature.

        """
        return cls.from_volume_and_element(volume, element, **kwargs)

    @staticmethod
    def _calculate_orientation(ref_side, plane):
        # orientation is START if cutting plane normal points towards the start of the beam and END otherwise
        if is_point_behind_plane(ref_side.point, plane):
            return OrientationType.END
        else:
            return OrientationType.START

    @staticmethod
    def _calculate_start_x(ref_side, ref_edge, planes, orientation, depth):
        # calculate the start x distance based on intersections of planes with reference edges.
        # if the lap is meant for a pocket one must consider the offseted reference edge
        offseted_ref_edge = ref_edge.translated(-ref_side.normal * depth)
        ref_edges = [offseted_ref_edge, ref_edge]

        x_distances = []
        for edge, plane in zip(ref_edges, planes):
            if intersection_line_plane(edge, plane) is None:
                raise ValueError("One of the planes does not intersect with the beam.")
            intersection_point = Point(*intersection_line_plane(edge, plane))
            distance_vector = (Vector.from_start_end(edge.start, intersection_point))
            x_distances.append(dot_vectors(distance_vector, edge.direction))
        return max(x_distances) if orientation == OrientationType.END else min(x_distances)

    @staticmethod
    def _calculate_angle(ref_side, plane):
        # vector rotation direction of the plane's normal in the vertical direction
        angle_vector = Vector.cross(ref_side.normal, plane.normal)
        return abs(angle_vectors_signed(ref_side.xaxis, angle_vector, ref_side.normal, deg=True))

    @staticmethod
    def _calculate_length(planes, ref_side, ref_edge, depth, angle):
        # calculate the length of the lap based on the intersection points of the planes with the reference edge
        # the length is the perpendicular distance between the two planes
        vect = ref_side.yaxis.cross(planes[0].normal)
        intersection_pts = [Point(*intersection_line_plane(ref_edge, plane)) for plane in planes]
        dist = distance_point_point(*intersection_pts)
        # calculate the compansation distance based on the angle of intersection
        compensation_angle = angle_vectors_signed(vect, ref_side.xaxis, ref_side.normal)
        dist += depth / abs(math.tan(compensation_angle))
        # calculate the perpendicular distance between the two planes
        length = math.sin(math.radians(angle))*dist
        return length

    @staticmethod
    def _get_optimal_ref_side_index(element, volume):
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
    def _sort_planes(planes, ref_side):
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
    def _calculate_start_x_y(ref_side, start_point):
        # calculate the start_x, start_y of the lap based on the start_corner_point and the ref_side
        start_vector = Vector.from_start_end(ref_side.point, start_point)
        start_x = dot_vectors(start_vector, ref_side.xaxis)
        start_y = dot_vectors(start_vector, ref_side.yaxis)
        return start_x, start_y

    @staticmethod
    def _check_lead_parallelity(beam, ref_side_index, front_plane, back_plane):
        # define lead_angle and lead_inclination parallelity
        front_side = beam.front_side(ref_side_index)
        parallelity = True
        for plane in [front_plane, back_plane]:
            dot = dot_vectors(plane.normal, front_side.normal)
            if not TOL.is_close(abs(dot), 1.0):
                parallelity = False  # Change to False if any plane is not parallel
        return parallelity

    @staticmethod
    def _define_machining_limits(planes, element, ref_side_index):
        # define machining limits based on the planes
        ref_sides = [Plane.from_frame(frame) for frame in element.ref_sides]
        start_side, end_side = ref_sides[-2:]
        ref_sides = ref_sides[:-2]
        _, front_side, opp_side, back_side = ref_sides[ref_side_index:] + ref_sides[:ref_side_index]
        start_plane, end_plane, front_plane, back_plane, bottom_plane, _ = planes

        machining_limits = MachiningLimits()
        machining_limits.face_limited_top = False
        machining_limits.face_limited_start = is_point_behind_plane(start_plane.point, start_side)
        machining_limits.face_limited_end = is_point_behind_plane(end_plane.point, end_side)
        machining_limits.face_limited_front = is_point_behind_plane(front_plane.point, front_side)
        machining_limits.face_limited_back = is_point_behind_plane(back_plane.point, back_side)
        machining_limits.face_limited_bottom = is_point_behind_plane(bottom_plane.point, opp_side)
        return machining_limits.limits


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
        lap_volume = self.volume_from_params_and_beam(beam)

        # convert mesh to brep
        try:
            lap_volume = Brep.from_mesh(lap_volume)
        except Exception:
            raise FeatureApplicationError(
                lap_volume,
                geometry,
                "Could not convert the lap volume to a Brep.",
            )

        # subtract the lap volume from the beam geometry
        try:
            return geometry - lap_volume
        except IndexError:
            raise FeatureApplicationError(
                lap_volume,
                geometry,
                "The lap volume does not intersect with the beam geometry.",
            )

    def _start_frame_from_params_and_beam(self, beam):
        """Calculates the start frame of the lap from the machining parameters in this instance and the given beam.

        Parameters
        ----------
        beam : :class:`compas_timber.elements.Beam`
            The beam that is cut by this instance.

        Returns
        -------
        :class:`compas.geometry.Frame`
            The start frame of the lap.
        """
        assert self.start_x is not None
        assert self.start_y is not None
        assert self.depth is not None
        assert self.angle is not None
        assert self.inclination is not None
        assert self.slope is not None

        ref_surface = beam.side_as_surface(self.ref_side_index)
        p_origin = ref_surface.point_at(self.start_x, self.start_y)
        start_frame = Frame(p_origin, -ref_surface.frame.yaxis, ref_surface.frame.xaxis)

        # define angle rotation matrix
        angle_angle = self.angle if self.orientation == OrientationType.END else 180-self.angle
        start_frame.rotate(math.radians(angle_angle), start_frame.normal, point=p_origin)
        # define inclination rotation matrix
        inclination_axis = start_frame.yaxis if self.orientation == OrientationType.END else -start_frame.yaxis
        start_frame.rotate(math.radians(self.inclination), inclination_axis, point=start_frame.point)
        # define slope rotation matrix
        start_frame.rotate(math.radians(self.slope), start_frame.normal, point=start_frame.point)
        return start_frame

    def _planes_from_params_and_beam(self, beam):
        """Calculates the planes that create the lap from the machining parameters in this instance and the given beam

        Parameters
        ----------
        beam : :class:`compas_timber.elements.Beam`
            The beam that is cut by this instance.

        Returns
        -------
        list of :class:`compas.geometry.Plane`
            The planes of the cut as a list.
        """
        # type: (Beam) -> List[Plane]
        assert self.length is not None
        assert self.width is not None
        assert self.depth is not None
        assert self.machining_limits is not None

        tol = Tolerance()
        tol.absolute=1e-3

        if self.machining_limits["FaceLimitedStart"]:
            start_frame = self._start_frame_from_params_and_beam(beam)
        else:
            start_frame = beam.ref_sides[4]

        if self.machining_limits["FaceLimitedEnd"]:
            end_frame = start_frame.translated(-start_frame.normal * self.length)
            end_frame.yaxis = -end_frame.yaxis
        else:
            end_frame = beam.ref_sides[5]

        top_frame = beam.ref_sides[self.ref_side_index] # top should always be unlimited

        if self.machining_limits["FaceLimitedBottom"]:
            bottom_frame = Frame(start_frame.point, start_frame.zaxis, start_frame.yaxis)
            angle = angle_vectors_signed(top_frame.xaxis, -start_frame.xaxis, top_frame.yaxis)
            bottom_frame = bottom_frame.translated(bottom_frame.zaxis * (self.depth/math.sin(angle)))
        else:
            bottom_frame = beam.ref_sides[4]

        if self.machining_limits["FaceLimitedFront"]:
            front_frame = bottom_frame.rotated(math.radians(self.lead_angle), bottom_frame.xaxis, point=bottom_frame.point)
        else:
            front_frame = beam.front_side(self.ref_side_index)
            front_frame.translate(front_frame.normal * tol.absolute)

        if self.machining_limits["FaceLimitedBack"]:
            back_frame = front_frame.translated(-front_frame.zaxis * self.width)
            back_frame.xaxis = -back_frame.xaxis
        else:
            back_frame = beam.back_side(self.ref_side_index)
            back_frame.translate(back_frame.normal * tol.absolute)

        frames = [start_frame, end_frame, top_frame, bottom_frame, front_frame, back_frame]
        return [Plane.from_frame(frame) for frame in frames]

    def volume_from_params_and_beam(self, beam):
        """
        Calculates the subtracting volume from the machining parameters in this instance and the given beam, ensuring correct face orientation.

        Parameters
        ----------
        beam : :class:`compas_timber.elements.Beam`
            The beam that is cut by this instance.

        Returns
        -------
        :class:`compas.geometry.Polyhedron`
            The correctly oriented subtracting volume of the lap.
        """
        # type: Beam -> Polyhedron
        # Get cutting planes
        start_plane, end_plane, top_plane, bottom_plane, front_plane, back_plane = self._planes_from_params_and_beam(beam)

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

        # ensure proper vertex order based on orientation
        if self.orientation == OrientationType.END:
            faces = [face[::-1] for face in faces]
        return Polyhedron(vertices, faces)


class LapParams(BTLxProcessingParams):
    """A class to store the parameters of a Lap feature.

    Parameters
    ----------
    instance : :class:`~compas_timber.fabrication.Lap`
        The instance of the Lap feature.
    """

    def __init__(self, instance):
        # type: (Lap) -> None
        super(LapParams, self).__init__(instance)

    def as_dict(self):
        """Returns the parameters of the Lap feature as a dictionary.

        Returns
        -------
        dict
            The parameters of the Lap feature as a dictionary.
        """
        # type: () -> OrderedDict
        result = OrderedDict()
        result["Orientation"] = self._instance.orientation
        result["StartX"] = "{:.{prec}f}".format(float(self._instance.start_x), prec=TOL.precision)
        result["StartY"] = "{:.{prec}f}".format(float(self._instance.start_y), prec=TOL.precision)
        result["Angle"] = "{:.{prec}f}".format(float(self._instance.angle), prec=TOL.precision)
        result["Inclination"] = "{:.{prec}f}".format(float(self._instance.inclination), prec=TOL.precision)
        result["Slope"] = "{:.{prec}f}".format(float(self._instance.slope), prec=TOL.precision)
        result["Length"] = "{:.{prec}f}".format(float(self._instance.length), prec=TOL.precision)
        result["Width"] = "{:.{prec}f}".format(float(self._instance.width), prec=TOL.precision)
        result["Depth"] = "{:.{prec}f}".format(float(self._instance.depth), prec=TOL.precision)
        result["LeadAngleParallel"] = "yes" if self._instance.lead_angle_parallel else "no"
        result["LeadAngle"] = "{:.{prec}f}".format(float(self._instance.lead_angle), prec=TOL.precision)
        result["LeadInclinationParallel"] = "yes" if self._instance.lead_inclination_parallel else "no"
        result["LeadInclination"] = "{:.{prec}f}".format(float(self._instance.lead_inclination), prec=TOL.precision)
        result["MachiningLimits"] = {key: "yes" if value else "no" for key, value in self._instance.machining_limits.items()}
        return result


class LapProxy(object):
    """This object behaves like a Lap except it only calculates the machining parameters once unproxified.
    Can also be used to defer the creation of the processing instance until it is actually needed.

    Until then, it can be used to visualize the machining operation.
    This slightly improves performance.

    Parameters
    ----------
    volume : :class:`~compas.geometry.Polyhedron` or :class:`~compas.geometry.Brep`
        The negative volume that constitutes the lap.
    beam : :class:`~compas_timber.elements.Beam`
        The beam where lap should be applied.
    machining_limits : dict, optional
        The machining limits for the cut. Default is None.
    ref_side_index : int, optional
        The reference side index for the Lap.

    """

    def __deepcopy__(self, *args, **kwargs):
        # not sure there's value in copying the proxt as it's more of a performance hack.
        # plus it references a beam so it would be a bit of a mess to copy it.
        # for now just return the unproxified version
        return self.unproxified()

    def __init__(self, volume, beam, machining_limits=None, ref_side_index=None):
        self.volume = volume
        self.beam = beam
        self.machining_limits = machining_limits
        self.ref_side_index = ref_side_index
        self._processing = None

    def unproxified(self):
        """Returns the unproxified processing instance.

        Returns
        -------
        :class:`~compas_timber.fabrication.Lap`

        """
        if not self._processing:
            self._processing = Lap.from_volume_and_beam(self.volume, self.beam, self.machining_limits, self.ref_side_index)
        return self._processing

    @classmethod
    def from_volume_and_beam(cls, volume, beam, machining_limits=None, ref_side_index=None):
        """Construct a Lap feature from a volume and a Beam.

        Parameters
        ----------
        volume : :class:`~compas.geometry.Polyhedron` or :class:`~compas.geometry.Brep`
            The volume of the lap. Must have 6 faces.
        beam : :class:`~compas_timber.elements.Beam`
            The beam that is cut by this instance.
        machining_limits : dict, optional
            The machining limits for the cut. Default is None.
        ref_side_index : int, optional
            The index of the reference side of the element. Default is 0.

        Returns
        -------
        :class:`~compas_timber.fabrication.Lap`
            The Lap feature.

        """
        if isinstance(volume, Polyhedron):
            volume = Brep.from_mesh(volume.to_mesh())
        if volume.volume < 0:
            volume.flip()
        return cls(volume, beam, machining_limits, ref_side_index)

    def apply(self, geometry, _):
        """Apply the feature to the beam geometry.

        Parameters
        ----------
        geometry : :class:`~compas.geometry.Brep`
            The beam geometry to apply the lap to.
        beam : :class:`compas_timber.elements.Beam`
            The beam that is lapped by this instance.

        Raises
        ------
        :class:`~compas_timber.errors.FeatureApplicationError`
            If the lap volume does not intersect with beam geometry.

        Returns
        -------
        :class:`~compas.geometry.Brep`
            The resulting geometry after processing

        """
        # type: (Brep, Beam) -> Brep
        try:
            return geometry - self.volume
        except IndexError:
            raise FeatureApplicationError(
                self.volume,
                geometry,
                "The volume to subtract does not intersect with beam geometry.",
            )

    def __getattr__(self, attr):
        # any unknown calls are passed through to the processing instance
        return getattr(self.unproxified(), attr)
