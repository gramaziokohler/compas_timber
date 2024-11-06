import math

from compas.geometry import Box
from compas.geometry import Brep
from compas.geometry import BrepTrimmingError
from compas.geometry import Frame
from compas.geometry import Line
from compas.geometry import Plane
from compas.geometry import Point
from compas.geometry import Vector
from compas.geometry import angle_vectors_signed
from compas.geometry import angle_vectors
from compas.geometry import distance_point_line
from compas.geometry import distance_point_point
from compas.geometry import intersection_line_plane
from compas.geometry import intersection_plane_plane_plane
from compas.geometry import is_point_behind_plane
from compas.tolerance import TOL

from compas_timber.elements import FeatureApplicationError

from .btlx_process import BTLxProcess
from .btlx_process import BTLxProcessParams
from .btlx_process import OrientationType


class Lap(BTLxProcess):
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

    PROCESS_NAME = "Lap"  # type: ignore

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
        orientation,
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
    def params_dict(self):
        return LapParams(self).as_dict()

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
        if machining_limits is not None and not isinstance(machining_limits, dict):
            raise ValueError("Machining limits must be a dictionary.")
        self._machining_limits = machining_limits


    ########################################################################
    # Alternative constructors
    ########################################################################

    @classmethod
    def from_two_planes_and_beam(cls, planes, beam, depth, ref_side_index=0):
        """Create a Lap instance from two planes and a beam. The planes should be parallel to each other and their normals should be facing in the opposite direction.

        Parameters
        ----------
        planes : list of :class:`~compas.geometry.Plane`
            The planes that define the lap.
        beam : :class:`~compas_timber.elements.Beam`
            The beam that the Lap instance is applied to.
        depth : float
            The depth of the lap.
        ref_side_index : int, optional
            The reference side index of the main_beam to be cut. Default is 0 (i.e. RS1).

        Returns
        -------
        :class:`~compas_timber.fabrication.Lap`

        """
        # type: (list[Plane], Beam, float, int) -> Lap
        if len(planes) != 2:
            raise ValueError("Exactly two planes are required to define the lap.")

        planes = [Plane.from_frame(plane) for plane in planes if isinstance(plane, Frame)]

        # get ref_side and ref_edge of the main beam
        ref_side = beam.ref_sides[ref_side_index]
        ref_edge = Line.from_point_and_vector(ref_side.point, ref_side.xaxis)

        # calculate the orientation of the lap
        orientation = cls._calculate_orientation(ref_side, planes[0])

        # find the intersection points of the planes with the reference edge and calculate the distances from the start of the beam
        x_distances = []
        for plane in planes:
            if intersection_line_plane(ref_edge, plane) is None:
                raise ValueError("One of the planes does not intersect with the beam.")
            intersection_point = Point(*intersection_line_plane(ref_edge, plane))
            x_distance = distance_point_point(ref_side.point, intersection_point)
            x_distances.append(x_distance)

        # Sort planes and distances together based on the distances
        reverse = False if orientation == OrientationType.END else True
        x_distances, planes = zip(*sorted(zip(x_distances, planes), reverse=reverse))

        # calculate the start_x of the lap from the closest intersection point
        start_x = x_distances[0]

        # calculate the width of the lap
        width = beam.width if ref_side_index%2 == 0 else beam.height

        # calculate the angle of the lap
        angle = cls._calculate_angle(ref_side, planes[0], orientation)
        print(angle)

        # calculate length
        length = cls._calculate_length(planes, ref_side, ref_edge, depth)

        # define machining limits
        machining_limits = {
            "FaceLimitedFront": "no",
            "FaceLimitedBack": "no"
        }

        return cls(orientation=orientation, start_x=start_x, angle=angle, length=length, width=width, depth=depth, machining_limits=machining_limits, ref_side_index=ref_side_index)

    @staticmethod
    def _calculate_orientation(ref_side, cutting_plane):
        # orientation is START if the angle of
        cross_vect = Vector.cross(ref_side.yaxis, cutting_plane.normal)
        dot = cross_vect.dot(ref_side.normal)
        if dot > 0:
            cross_vect = -cross_vect
        if angle_vectors(ref_side.xaxis, cross_vect, deg=True) > 90:
            return OrientationType.START
        else:
            return OrientationType.END

    @staticmethod
    def _calculate_angle(ref_side, plane, orientation):
        # vector rotation direction of the plane's normal in the vertical direction
        angle_vector = Vector.cross(ref_side.normal, plane.normal)
        return abs(angle_vectors_signed(ref_side.xaxis, angle_vector, ref_side.normal, deg=True))

    # @staticmethod
    # def _calculate_inclination(ref_side, plane, orientation):
    #     # vector rotation direction of the plane's normal in the horizontal direction
    #     inclination_vector = Vector.cross(ref_side.yaxis, plane.normal)
    #     inclination = angle_vectors_signed(ref_side.xaxis, inclination_vector, ref_side.yaxis, deg=True)
    #     if orientation == OrientationType.START:
    #         return 180 - abs(inclination)  # get the other side of the angle
    #     else:
    #         return abs(inclination)

    @staticmethod
    def _calculate_length(planes, ref_side, ref_edge, depth):
        # calculate the length of the lap from the intersection points of the planes with the reference edge
        offseted_ref_edge = ref_edge.translated(-ref_side.normal*depth)
        ref_edges = ref_edge, offseted_ref_edge

        intersection_pts = [Point(*intersection_line_plane(ref_edge, plane)) for ref_edge, plane in zip(ref_edges, planes)]
        vector = Vector.from_start_end(*intersection_pts)
        return abs(vector.dot(ref_side.xaxis))

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
        lap_volume = self.volume_from_params_and_beam(beam)
        try:
            return geometry - lap_volume
        except BrepTrimmingError:
            raise FeatureApplicationError(
                lap_volume,
                geometry,
                "The lap volume does not intersect with the beam geometry.",
            )

    def volume_from_params_and_beam(self, beam):
        """Calculates the volume of the cut from the machining parameters in this instance and the given beam

        Parameters
        ----------
        beam : :class:`compas_timber.elements.Beam`
            The beam that is cut by this instance.

        Returns
        -------
        :class:`compas.geometry.Brep`
            The volume of the cut.

        """
        # type: (Beam) -> Brep

        ref_side = beam.side_as_surface(self.ref_side_index)
        p_origin = ref_side.point_at(self.start_x, self.start_y)

        box_frame = Frame(p_origin, ref_side.frame.xaxis, -ref_side.frame.yaxis)
        box_frame.rotate(math.radians(self.angle%90), box_frame.normal, point=box_frame.point)

        box = Box(xsize=self.length, ysize=self.width, zsize=self.depth, frame=box_frame)
        box.translate(box_frame.xaxis * (self.length / 2) + box_frame.yaxis * (-self.width / 2) + box_frame.zaxis * (self.depth / 2))

        if self.orientation == OrientationType.START:
            box.translate(box_frame.xaxis * -self.length)

        if self.machining_limits["FaceLimitedFront"] == "no" or self.machining_limits["FaceLimitedBack"] == "no":
            box.ysize = box.ysize*2

        return Brep.from_box(box)

class LapParams(BTLxProcessParams):
    """A class to store the parameters of a Lap feature.

    Parameters
    ----------
    instance : :class:`~compas_timber._fabrication.Lap`
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
        result = super(LapParams, self).as_dict()
        result["Orientation"] = self._instance.orientation
        result["StartX"] = "{:.{prec}f}".format(self._instance.start_x, prec=TOL.precision)
        result["StartY"] = "{:.{prec}f}".format(self._instance.start_y, prec=TOL.precision)
        result["Angle"] = "{:.{prec}f}".format(self._instance.angle, prec=TOL.precision)
        result["Inclination"] = "{:.{prec}f}".format(self._instance.inclination, prec=TOL.precision)
        result["Slope"] = "{:.{prec}f}".format(self._instance.slope, prec=TOL.precision)
        result["Length"] = "{:.{prec}f}".format(self._instance.length, prec=TOL.precision)
        result["Width"] = "{:.{prec}f}".format(self._instance.width, prec=TOL.precision)
        result["Depth"] = "{:.{prec}f}".format(self._instance.depth, prec=TOL.precision)
        result["LeadAngleParallel"] = "yes" if self._instance.lead_angle_parallel else "no"
        result["LeadAngle"] = "{:.{prec}f}".format(self._instance.lead_angle, prec=TOL.precision)
        result["LeadInclinationParallel"] = "yes" if self._instance.lead_inclination_parallel else "no"
        result["LeadInclination"] = "{:.{prec}f}".format(self._instance.lead_inclination, prec=TOL.precision)
        result["MachiningLimits"] = self._instance.machining_limits
        return result
