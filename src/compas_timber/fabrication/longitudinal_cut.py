import math
from collections import OrderedDict

from compas.geometry import BrepTrimmingError
from compas.geometry import Frame
from compas.geometry import Line
from compas.geometry import Plane
from compas.geometry import Rotation
from compas.geometry import Vector
from compas.geometry import angle_vectors_signed
from compas.geometry import distance_point_point
from compas.geometry import intersection_line_plane
from compas.tolerance import TOL

from compas_timber.errors import FeatureApplicationError

from .btlx import BTLxProcessing
from .btlx import BTLxProcessingParams
from .btlx import OrientationType
from .btlx import ToolPositionType


class LongitudinalCut(BTLxProcessing):
    """Represents a Longitudinal Cut feature to be made on a beam.

    Parameters
    ----------
    start_x : float
        The start x-coordinate of the cut in parametric space of the reference side. -100000.0 < start_x < 100000.0.
    start_y : float
        The start y-coordinate of the cut in parametric space of the reference side. 0.0 < start_y < 50000.0.
    inclination : float
        The vertical angle of the cut. -90.0 < inclination < 90.0.
    start_limited : bool
        Whether the cut is limited at the start. If True, the cut starts at the start_x coordinate.
    end_limited : bool
        Whether the cut is limited at the end. If True, the cut ends at the start_x + length coordinate.
    length : float
        The length of the cut in parametric space of the reference side. 0.0 < length < 100000.0.
    depth_limited : bool
        Whether the cut is limited in depth. If True, the cut goes to a certain depth.
    depth : float
        The depth of the cut in parametric space of the reference side. 0.0 < depth < 50000.0.
    angle_start : float
        The angle at the start of the cut in degrees. 0.1 < angle_start < 179.9.
    angle_end : float
        The angle at the end of the cut in degrees. 0.1 < angle_end < 179.9.
    tool_position : :class:`~compas_timber.fabrication.ToolPositionType`
        The position of the tool relative to the beam. Can be 'left', 'center', or 'right'.

    """

    PROCESSING_NAME = "LongitudinalCut"  # type: ignore

    @property
    def __data__(self):
        data = super(LongitudinalCut, self).__data__
        data["start_x"] = self.start_x
        data["start_y"] = self.start_y
        data["inclination"] = self.inclination
        data["start_limited"] = self.start_limited
        data["end_limited"] = self.end_limited
        data["length"] = self.length
        data["depth_limited"] = self.depth_limited
        data["depth"] = self.depth
        data["angle_start"] = self.angle_start
        data["angle_end"] = self.angle_end
        data["tool_position"] = self.tool_position
        return data

    def __init__(
        self,
        start_x=0.0,
        start_y=0.0,
        inclination=40.0,
        start_limited=False,
        end_limited=False,
        length=0.0,
        depth_limited=False,
        depth=0.0,
        angle_start=90.0,
        angle_end=90.0,
        tool_position=ToolPositionType.LEFT,
        **kwargs,
    ):
        super(LongitudinalCut, self).__init__(**kwargs)
        self._start_x = None
        self._start_y = None
        self._inclination = None
        self._start_limited = None
        self._end_limited = None
        self._length = None
        self._depth_limited = None
        self._depth = None
        self._angle_start = None
        self._angle_end = None
        self._tool_position = None

        self.start_x = start_x
        self.start_y = start_y
        self.inclination = inclination
        self.start_limited = start_limited
        self.end_limited = end_limited
        self.length = length
        self.depth_limited = depth_limited
        self.depth = depth
        self.angle_start = angle_start
        self.angle_end = angle_end
        self.tool_position = tool_position

    ########################################################################
    # Properties
    ########################################################################

    @property
    def params(self):
        return LongitudinalCutParams(self)

    @property
    def start_x(self):
        return self._start_x

    @start_x.setter
    def start_x(self, start_x):
        if start_x > 100000.0 or start_x < -100000.0:
            raise ValueError("start_x must be between -100000.0 and 100000.")
        self._start_x = start_x

    @property
    def start_y(self):
        return self._start_y

    @start_y.setter
    def start_y(self, start_y):
        if start_y > 50000.0:
            raise ValueError("start_y must be less than 50000.0.")
        self._start_y = start_y

    @property
    def inclination(self):
        return self._inclination

    @inclination.setter
    def inclination(self, inclination):
        if inclination > 90.0 or inclination < -90.0:
            raise ValueError("inclination must be between -90.0 and 90.0.")
        self._inclination = inclination

    @property
    def start_limited(self):
        return self._start_limited

    @start_limited.setter
    def start_limited(self, start_limited):
        if not isinstance(start_limited, bool):
            raise ValueError("start_limited must be a boolean value.")
        self._start_limited = start_limited

    @property
    def end_limited(self):
        return self._end_limited

    @end_limited.setter
    def end_limited(self, end_limited):
        if not isinstance(end_limited, bool):
            raise ValueError("end_limited must be a boolean value.")
        self._end_limited = end_limited

    @property
    def length(self):
        return self._length

    @length.setter
    def length(self, length):
        if length > 100000.0 or length < 0.0:
            raise ValueError("length must be between 0.0 and 100000.0.")
        self._length = length

    @property
    def depth_limited(self):
        return self._depth_limited

    @depth_limited.setter
    def depth_limited(self, depth_limited):
        if not isinstance(depth_limited, bool):
            raise ValueError("depth_limited must be a boolean value.")
        self._depth_limited = depth_limited

    @property
    def depth(self):
        return self._depth

    @depth.setter
    def depth(self, depth):
        if depth > 50000.0 or depth < 0.0:
            raise ValueError("depth must be between 0.0 and 50000.0.")
        self._depth = depth

    @property
    def angle_start(self):
        return self._angle_start

    @angle_start.setter
    def angle_start(self, angle_start):
        if angle_start > 179.9 or angle_start < 0.1:
            raise ValueError("angle_start must be between 0.1 and 179.9 degrees.")
        self._angle_start = angle_start

    @property
    def angle_end(self):
        return self._angle_end

    @angle_end.setter
    def angle_end(self, angle_end):
        if angle_end > 179.9 or angle_end < 0.1:
            raise ValueError("angle_end must be between 0.1 and 179.9 degrees.")
        self._angle_end = angle_end

    @property
    def tool_position(self):
        return self._tool_position

    @tool_position.setter
    def tool_position(self, tool_position):
        if tool_position not in [ToolPositionType.LEFT, ToolPositionType.CENTER, ToolPositionType.RIGHT]:
            raise ValueError("tool_position must be one of 'left', 'center', or 'right'.")
        self._tool_position = tool_position

    ########################################################################
    # Alternative constructors
    ########################################################################

    @classmethod
    def from_plane_and_beam(cls, plane, beam, start_x=None, length=None, ref_side_index=0, **kwargs):
        """Create a LongitudinalCut instance from a cutting plane and the beam it should cut.

        Parameters
        ----------
        plane : :class:`~compas.geometry.Plane` or :class:`~compas.geometry.Frame`
            The cutting plane.
        beam : :class:`~compas_timber.elements.Beam`
            The beam that is cut by this instance.
        ref_side_index : int, optional
            The reference side index of the beam to be cut. Default is 0 (i.e. RS1).

        Returns
        -------
        :class:`~compas_timber.fabrication.Longitudinal`

        """
        # type: (Plane | Frame, Beam, int) -> Longitudinal
        if isinstance(plane, Frame):
            plane = Plane.from_frame(plane)

        ref_side = beam.ref_sides[ref_side_index]  # TODO: is this arbitrary?
        start_edge = Line.from_point_and_vector(ref_side.point, ref_side.yaxis)
        front_edge = Line.from_point_and_vector(ref_side.point, -ref_side.zaxis)

        # calculate start_x
        start_x = 0.0 if start_x is None else start_x

        # calculate start_y
        point_start_y = intersection_line_plane(start_edge, plane)
        if point_start_y is None:
            raise ValueError("Plane does not intersect with beam.")  # TODO: update error message
        start_y = distance_point_point(start_edge.point, point_start_y)

        # calculate inclination
        inclination = angle_vectors_signed(ref_side.zaxis, plane.normal, ref_side.xaxis, deg=True)

        # calculate length
        length = beam.length - start_x if length is None else length

        # calculate start_limited
        start_limited = False if start_x == 0.0 else True

        # calculate end_limited
        end_limited = False if length + start_x >= beam.length else True

        # calculate depth
        point_depth = intersection_line_plane(front_edge, plane)
        if point_depth is None:
            raise ValueError("Plane does not intersect with beam.")  # TODO: update error message
        depth = distance_point_point(ref_side.point, point_depth)

        return cls(
            start_x=start_x,
            start_y=start_y,
            inclination=inclination,
            start_limited=start_limited,
            end_limited=end_limited,
            length=length,
            depth=depth,
            ref_side_index=ref_side_index,
            **kwargs,
        )

    @classmethod
    def from_shapes_and_element(cls, plane, element, **kwargs):
        """Construct a drilling process from a shape and a beam.

        Parameters
        ----------
        plane : :class:`compas.geometry.Plane` or :class:`compas.geometry.Frame`
            The cutting plane.
        element : :class:`compas_timber.elements.Element`
            The element to be cut.

        Returns
        -------
        :class:`compas_timber.fabrication.JackRafterCut`
            The constructed Jack Rafter Cut process.

        """
        if isinstance(plane, list):
            plane = plane[0]
        return cls.from_plane_and_beam(plane, element, **kwargs)

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
        cutting_plane = self.plane_from_params_and_beam(beam)
        try:
            return geometry.trimmed(cutting_plane)
        except BrepTrimmingError:
            raise FeatureApplicationError(
                cutting_plane,
                geometry,
                "The cutting plane does not intersect with beam geometry.",
            )

    def plane_from_params_and_beam(self, beam):
        """Calculates the cutting plane from the machining parameters in this instance and the given beam

        Parameters
        ----------
        beam : :class:`compas_timber.elements.Beam`
            The beam that is cut by this instance.

        Returns
        -------
        :class:`compas.geometry.Plane`
            The cutting plane.

        """
        # type: (Beam) -> Plane
        assert self.angle is not None
        assert self.inclination is not None

        # start with a plane aligned with the ref side but shifted to the start_x of the cut
        ref_side = beam.side_as_surface(self.ref_side_index)
        p_origin = ref_side.point_at(self.start_x, 0.0)
        cutting_plane = Frame(p_origin, ref_side.frame.xaxis, ref_side.frame.yaxis)

        # normal pointing towards xaxis so just need the delta
        if self.orientation == OrientationType.END:
            horizontal_angle = math.radians(90 - self.angle)
            vertical_angle = math.radians(90 - self.inclination)
        else:
            horizontal_angle = math.radians(self.angle - 90)
            vertical_angle = math.radians(self.inclination - 90)

        rot_a = Rotation.from_axis_and_angle(cutting_plane.zaxis, horizontal_angle, point=p_origin)
        rot_b = Rotation.from_axis_and_angle(cutting_plane.yaxis, vertical_angle, point=p_origin)

        cutting_plane.transform(rot_a * rot_b)
        # for simplicity, we always start with normal pointing towards xaxis.
        # if start is cut, we need to flip the normal
        if self.orientation == OrientationType.END:
            plane_normal = cutting_plane.xaxis
        else:
            plane_normal = -cutting_plane.xaxis
        return Plane(cutting_plane.point, plane_normal)


class LongitudinalCutParams(BTLxProcessingParams):
    """A class to store the parameters of a Longitudinal Cut feature.

    Parameters
    ----------
    instance : :class:`~compas_timber.fabrication.LongitudinalCut`
        The instance of the Longitudinal Cut feature.
    """

    def __init__(self, instance):
        # type: (LongitudinalCut) -> None
        super(LongitudinalCutParams, self).__init__(instance)

    def as_dict(self):
        """Returns the parameters of the Longitudinal Cut feature as a dictionary.

        Returns
        -------
        dict
            The parameters of the Longitudinal Cut feature as a dictionary.
        """
        # type: () -> OrderedDict
        result = OrderedDict()
        result["StartX"] = "{:.{prec}f}".format(float(self._instance.start_x), prec=TOL.precision)
        result["StartY"] = "{:.{prec}f}".format(float(self._instance.start_y), prec=TOL.precision)
        result["Inclination"] = "{:.{prec}f}".format(float(self._instance.inclination), prec=TOL.precision)
        result["StartLimited"] = "yes" if self._instance.start_limited else "no"
        result["EndLimited"] = "yes" if self._instance.end_limited else "no"
        result["Length"] = "{:.{prec}f}".format(float(self._instance.length), prec=TOL.precision)
        result["DepthLimited"] = "yes" if self._instance.depth_limited else "no"
        result["Depth"] = "{:.{prec}f}".format(float(self._instance.depth), prec=TOL.precision)
        result["AngleStart"] = "{:.{prec}f}".format(float(self._instance.angle_start), prec=TOL.precision)
        result["AngleEnd"] = "{:.{prec}f}".format(float(self._instance.angle_end), prec=TOL.precision)
        result["ToolPosition"] = self._instance.tool_position.value
        return result


class JackRafterCutProxy(object):
    """This object behaves like a JackRafterCut except it only calculates the machining parameters once unproxified.
    Can also be used to defer the creation of the processing instance until it is actually needed.

    Until then, it can be used to visualize the machining operation.
    This slightly improves performance.

    Parameters
    ----------
    plane : :class:`~compas.geometry.Plane` or :class:`~compas.geometry.Frame`
        The cutting plane.
    beam : :class:`~compas_timber.elements.Beam`
        The beam that is cut by this instance.
    ref_side_index : int, optional
        The reference side index of the beam to be cut. Default is 0 (i.e. RS1).

    """

    def __deepcopy__(self, *args, **kwargs):
        # not sure there's value in copying the proxt as it's more of a performance hack.
        # plus it references a beam so it would be a bit of a mess to copy it.
        # for now just return the unproxified version
        return self.unproxified()

    def __init__(self, plane, beam, ref_side_index=0):
        self.plane = plane
        self.beam = beam
        self.ref_side_index = ref_side_index
        self._processing = None

    def unproxified(self):
        """Returns the unproxified processing instance.

        Returns
        -------
        :class:`~compas_timber.fabrication.JackRafterCut`

        """
        if not self._processing:
            self._processing = JackRafterCut.from_plane_and_beam(self.plane, self.beam, self.ref_side_index)
        return self._processing

    @classmethod
    def from_plane_and_beam(cls, plane, beam, ref_side_index=0):
        """Create a JackRafterCutProxy instance from a cutting plane and the beam it should cut.

        Parameters
        ----------
        plane : :class:`~compas.geometry.Plane` or :class:`~compas.geometry.Frame`
            The cutting plane.
        beam : :class:`~compas_timber.elements.Beam`
            The beam that is cut by this instance.
        ref_side_index : int, optional
            The reference side index of the beam to be cut. Default is 0 (i.e. RS1).

        Returns
        -------
        :class:`~compas_timber.fabrication.JackRafterCutProxy`

        """
        return cls(plane, beam, ref_side_index)

    def apply(self, geometry, _):
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
        cutting_plane = self.plane
        try:
            return geometry.trimmed(cutting_plane)
        except BrepTrimmingError:
            raise FeatureApplicationError(
                cutting_plane,
                geometry,
                "The cutting plane does not intersect with beam geometry.",
            )

    def __getattr__(self, attr):
        # any unknown calls are passed through to the processing instance
        return getattr(self.unproxified(), attr)
