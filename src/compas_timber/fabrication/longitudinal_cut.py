import math

from compas.geometry import Brep
from compas.geometry import BrepTrimmingError
from compas.geometry import Frame
from compas.geometry import Line
from compas.geometry import Plane
from compas.geometry import Polyline
from compas.geometry import angle_vectors
from compas.geometry import angle_vectors_signed
from compas.geometry import distance_point_point
from compas.geometry import dot_vectors
from compas.geometry import intersection_line_plane
from compas.geometry import intersection_segment_plane
from compas.tolerance import TOL

from compas_timber.errors import FeatureApplicationError
from compas_timber.utils import planar_surface_point_at

from .btlx import AlignmentType
from .btlx import BTLxProcessing


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
    tool_position : :class:`~compas_timber.fabrication.AlignmentType`
        The position of the tool relative to the beam. Can be 'left', 'center', or 'right'.

    """

    PROCESSING_NAME = "LongitudinalCut"  # type: ignore
    ATTRIBUTE_MAP = {
        "StartX": "start_x",
        "StartY": "start_y",
        "Inclination": "inclination",
        "StartLimited": "start_limited",
        "EndLimited": "end_limited",
        "Length": "length",
        "DepthLimited": "depth_limited",
        "Depth": "depth",
        "AngleStart": "angle_start",
        "AngleEnd": "angle_end",
    }

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

    # fmt: off
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
        tool_position=AlignmentType.LEFT,
        **kwargs
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
        if tool_position not in [AlignmentType.LEFT, AlignmentType.CENTER, AlignmentType.RIGHT]:
            raise ValueError("tool_position must be one of 'left', 'center', or 'right'.")
        self._tool_position = tool_position

    ########################################################################
    # Alternative constructors
    ########################################################################

    @classmethod
    def from_plane_and_beam(
        cls, plane, beam, start_x=None, length=None, depth=None, angle_start=90.0, angle_end=90.0, tool_position=AlignmentType.LEFT, ref_side_index=None, **kwargs
    ):
        """Create a LongitudinalCut instance from a cutting plane and the beam it should cut.

        Parameters
        ----------
        plane : :class:`~compas.geometry.Plane` or :class:`~compas.geometry.Frame`
            The cutting plane. The normal of the plane must be perpendicular to the beam's x-axis.
        beam : :class:`~compas_timber.elements.Beam`
            The beam that is cut by this instance.
        start_x : float, optional
            The start x-coordinate of the cut in parametric space of the reference side. Default is 0.0.
        length : float, optional
            The length of the cut in parametric space of the reference side. Default is the minimum length so that the cut goes through the entire beam..
        depth : float, optional
            The depth of the cut in parametric space of the reference side. Default is the minimum depth so that the cut goes through the entire beam.
        angle_start : float, optional
            The chamfered angle at the start of the cut in degrees. Default is 90.0.
        angle_end : float, optional
            The chanfered angle at the end of the cut in degrees. Default is 90.0.
        tool_position : :class:`~compas_timber.fabrication.AlignmentType`, optional
            The position of the tool relative to the beam. Can be 'left', 'center', or 'right'. Default is 'left'.
        ref_side_index : int, optional
            The reference side index of the beam to be cut. The default ref_side_index is calculated based on the angle between the plane's normal and each ref_side's normal.

        """
        # type: (Plane | Frame, Beam, float, float, float, float, float, str, int)  -> LongitudinalCut
        if isinstance(plane, Frame):
            plane = Plane.from_frame(plane)

        # get the reference side index if not provided
        if ref_side_index is None:
            ref_side_index = cls._get_default_ref_side_index(plane, beam)
        ref_side = beam.ref_sides[ref_side_index]

        # check if the cutting plane's normal is perpendicular to the beam's x-axis
        if not TOL.is_zero(plane.normal.dot(ref_side.xaxis)):
            raise ValueError("The cutting plane's normal must be perpendicular to the beam's x-axis.")

        # calculate start_x
        start_x = 0.0 if start_x is None else start_x

        # calculate start_y
        start_edge = Line.from_point_and_vector(ref_side.point, ref_side.yaxis)
        point_start_y = intersection_line_plane(start_edge, plane)
        if point_start_y is None:
            raise ValueError("Plane is parallel to the ref_side. Consider trying a different ref_side_index")
        start_y = distance_point_point(ref_side.point, point_start_y)

        # calculate inclination
        inclination = angle_vectors_signed(ref_side.zaxis, plane.normal, ref_side.xaxis, deg=True)

        # calculate length
        length = beam.length - start_x if length is None else length

        # calculate start_limited and end_limited
        start_limited = not TOL.is_zero(start_x)
        end_limited = length + start_x < beam.length

        # calculate depth
        width, height = beam.get_dimensions_relative_to_side(ref_side_index)
        if abs(inclination) == 90.0:
            max_depth = height
        elif TOL.is_positive(inclination):
            max_depth = start_y * math.tan(math.radians(inclination))
        else:
            max_depth = abs((width - start_y) * math.tan(math.radians(inclination)))


        depth_limited = depth <= max_depth if depth is not None else False
        depth = 0.0 if depth is None else depth

        # calculate tool_position
        if TOL.is_negative(plane.normal.dot(ref_side.yaxis)):
            tool_position = AlignmentType.RIGHT
        else:
            tool_position = AlignmentType.LEFT

        return cls(
            start_x,
            start_y,
            inclination,
            start_limited,
            end_limited,
            length,
            depth_limited,
            depth,
            angle_start,
            angle_end,
            tool_position,
            ref_side_index=ref_side_index,
            **kwargs,
        )

    @classmethod
    def from_shapes_and_element(cls, plane, element, **kwargs):
        """Construct a Longitudinal Cut process from a shape and a beam.

        Parameters
        ----------
        plane : :class:`compas.geometry.Plane` or :class:`compas.geometry.Frame`
            The cutting plane.
        element : :class:`compas_timber.elements.Element`
            The element to be cut.

        Returns
        -------
        :class:`compas_timber.fabrication.LongitudinalCut`
            The constructed Logitudinal Cut process.

        """
        if isinstance(plane, list):
            plane = plane[0]
        return cls.from_plane_and_beam(plane, element, **kwargs)

    @staticmethod
    def _get_default_ref_side_index(plane, beam):
        """Get the default reference side index for the given cutting plane and beam.
        This method checks if the cutting plane intersects with the reference sides of the beam
        and returns the index of the reference side with the smallest angle to the plane's normal.

        # NOTE: Consider moving all connection-agnostic utilities (including this one) to a shared location for reuse in fabrication and other modules.

        Parameters
        ----------
        plane : :class:`~compas.geometry.Plane` or :class:`~compas.geometry.Frame`
            The cutting plane.
        beam : :class:`~compas_timber.elements.Beam`
            The beam that is cut by this instance.

        Returns
        -------
        int
            The default ref_side_index for the given cutting plane and beam.

        """
        # type: (Plane | Frame, Beam) -> int
        angles = {}
        for i, ref_side in enumerate(beam.ref_sides[:4]):
            width, _ = beam.get_dimensions_relative_to_side(i)
            y_seg = Line.from_point_and_vector(ref_side.point, ref_side.yaxis * width)
            # check if the plane intersects with the reference side and the angle between their normals is positive
            if intersection_segment_plane(y_seg, plane,tol=TOL.absolute) and dot_vectors(ref_side.normal, plane.normal) > 0:
                angle = angle_vectors(plane.normal, ref_side.normal)
                angles[i] = angle
        return min(angles, key=angles.get)

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
        if not any([self.start_limited, self.end_limited, self.depth_limited]):
            # if the cut is not limited, trim the geometry with the cutting plane
            cutting_plane = self.plane_from_params_and_beam(beam)
            cutting_plane.transform(beam.transformation_to_local())
            try:
                return geometry.trimmed(cutting_plane)
            except BrepTrimmingError:
                raise FeatureApplicationError(cutting_plane, geometry, "The trimming operation failed. The cutting plane does not intersect with beam geometry.")
        else:
            # if the cut is limited, calculate the negative volume representing the cut and subtract it from the geometry
            neg_vol = self.volume_from_params_and_beam(beam)
            neg_vol.transform(beam.transformation_to_local())
            try:
                return geometry - neg_vol
            except IndexError:
                raise FeatureApplicationError(neg_vol, geometry, "The boolean difference between the cutting volume and the beam geometry failed.")

    def plane_from_params_and_beam(self, beam):
        """Calculates the cutting plane from the machining parameters in this instance and the given beam

        Parameters
        ----------
        beam : :class:`compas_timber.elements.Beam`
            The beam that is cut by this instance.

        Returns
        -------
        :class:`compas.geometry.Plane`
            The cutting plane plane.

        """
        # type: (Beam) -> Frame
        assert self.start_x is not None
        assert self.start_y is not None
        assert self.inclination is not None

        ref_side = beam.side_as_surface(self.ref_side_index)
        p_origin = planar_surface_point_at(ref_side, self.start_x, self.start_y)

        frame = Frame(p_origin, ref_side.xaxis, ref_side.yaxis)
        frame.rotate(math.radians(self.inclination), ref_side.xaxis, p_origin)

        return Plane.from_frame(frame)

    def volume_from_params_and_beam(self, beam):
        """Calculates the negative volume representing the cut from the machining parameters in this instance and the given beam.

        Parameters
        ----------
        beam : :class:`compas_timber.elements.Beam`
            The beam that is cut by this instance.

        Returns
        -------
        :class:`~compas.geometry.Brep`
            The negative volume representing the cut.

        """
        # type: (Beam) -> Brep
        assert self.start_y is not None
        assert self.length is not None
        assert self.inclination is not None
        assert self.depth is not None
        assert self.angle_start is not None
        assert self.angle_end is not None

        # get the cutting plane from the parameters and the beam
        plane = self.plane_from_params_and_beam(beam)

        # calculate the start and end points of the top edge of the cut
        xaxis = beam.frame.xaxis
        p_start = plane.point
        p_end = p_start + xaxis * self.length

        # calculate the start_y position relative to the reference side
        width, height = beam.get_dimensions_relative_to_side(self.ref_side_index)
        start_y = self.start_y
        if TOL.is_negative(self.inclination):
            start_y -= width + TOL.approximation  # adjust start_y for negative inclination

        # calculate the start and end points of the bottom edge of the cut
        extr_length = start_y / math.cos(math.radians(self.inclination))
        if TOL.is_close(abs(self.inclination), 90.0):
            extr_length = height  # avoid infinite extrusion length
        start_vector = xaxis.rotated(math.radians(self.angle_start), plane.normal, p_start)
        p_angle_start = p_start - start_vector * extr_length

        end_vector = xaxis.rotated(math.radians(180 - self.angle_end), plane.normal, p_end)
        p_angle_end = p_end - end_vector * extr_length

        # create a polyline that represents the cut
        polyline = Polyline([p_start, p_angle_start, p_angle_end, p_end, p_start])
        polyline.scale(1 + TOL.relative)  # tolerance issue

        # create the negative volume by extruding the polyline along the frame's normal
        extr_vect = plane.normal * math.sin(math.radians(self.inclination)) * start_y
        neg_vol = Brep.from_extrusion(polyline, extr_vect)
        if TOL.is_negative(neg_vol.volume):
            neg_vol.flip()
        return neg_vol

    def scale(self, factor):
        """Scale the machining parameters of the Longitudinal Cut feature.

        Parameters
        ----------
        factor : float
            The scale factor.

        """
        self.start_x *= factor
        self.start_y *= factor
        self.length *= factor
        self.depth *= factor


class LongitudinalCutProxy(object):
    """This object behaves like a LongitudinalCut except it only calculates the machining parameters once unproxified.
    Can also be used to defer the creation of the processing instance until it is actually needed.

    Until then, it can be used to visualize the machining operation.
    This slightly improves performance.

    Parameters
    ----------
    plane : :class:`~compas.geometry.Plane` or :class:`~compas.geometry.Frame`
        The cutting plane.
    beam : :class:`~compas_timber.elements.Beam`
        The beam that is cut by this instance.
    start_x : float, optional
        The start x-coordinate of the cut in parametric space of the reference side. Default is 0.0.
    length : float, optional
        The length of the cut in parametric space of the reference side. Default is the minimum length so that the cut goes through the entire beam.
    depth : float, optional
        The depth of the cut in parametric space of the reference side. Default is the minimum depth so that the cut goes through the entire beam.
    angle_start : float, optional
        The chamfered angle at the start of the cut in degrees. Default is 90.0.
    angle_end : float, optional
        The chamfered angle at the end of the cut in degrees. Default is 90.0.
    tool_position : :class:`~compas_timber.fabrication.AlignmentType`, optional
        The position of the tool relative to the beam. Can be 'left', 'center', or 'right'. Default is 'left'.
    ref_side_index : int, optional
        The reference side index of the beam to be cut. The default ref_side_index is calculated based on the angle between the plane's normal and each ref_side's normal.

    """

    def __deepcopy__(self, *args, **kwargs):
        # not sure there's value in copying the proxy as it's more of a performance hack.
        # plus it references a beam so it would be a bit of a mess to copy it.
        # for now just return the unproxified version
        return self.unproxified()

    def __init__(self, plane, beam, start_x=None, length=None, depth=None, angle_start=90.0, angle_end=90.0, tool_position=AlignmentType.LEFT, ref_side_index=None, **kwargs):
        self.plane = plane.transformed(beam.transformation_to_local())
        self.beam = beam
        self.start_x = start_x
        self.length = length
        self.depth = depth
        self.angle_start = angle_start
        self.angle_end = angle_end
        self.tool_position = tool_position
        self.ref_side_index = ref_side_index
        self._processing = None
        self.kwargs = kwargs

    def unproxified(self):
        """Returns the unproxified processing instance.

        Returns
        -------
        :class:`~compas_timber.fabrication.LongitudinalCut`
            The unproxified LongitudinalCut instance.

        """
        if not self._processing:
            plane = self.plane.transformed(self.beam.modeltransformation)
            self._processing = LongitudinalCut.from_plane_and_beam(
                plane,
                self.beam,
                self.start_x,
                self.length,
                self.depth,
                self.angle_start,
                self.angle_end,
                self.tool_position,
                self.ref_side_index,
                **self.kwargs,
            )
        return self._processing

    @classmethod
    def from_plane_and_beam(
        cls, plane, beam, start_x=None, length=None, depth=None, angle_start=90.0, angle_end=90.0, tool_position=AlignmentType.LEFT, ref_side_index=None, **kwargs
    ):
        """Create a LongitudinalCutProxy instance from a cutting plane and the beam it should cut.

        Parameters
        ----------
        plane : :class:`~compas.geometry.Plane` or :class:`~compas.geometry.Frame`
            The cutting plane.
        beam : :class:`~compas_timber.elements.Beam`
            The beam that is cut by this instance.
        start_x : float, optional
            The start x-coordinate of the cut in parametric space of the reference side. Default is 0.0.
        length : float, optional
            The length of the cut in parametric space of the reference side. Default is the minimum length so that the cut goes through the entire beam.
        depth : float, optional
            The depth of the cut in parametric space of the reference side. Default is the minimum depth so that the cut goes through the entire beam.
        angle_start : float, optional
            The chamfered angle at the start of the cut in degrees. Default is 90.0.
        angle_end : float, optional
            The chamfered angle at the end of the cut in degrees. Default is 90.0.
        tool_position : :class:`~compas_timber.fabrication.AlignmentType`, optional
            The position of the tool relative to the beam. Can be 'left', 'center', or 'right'. Default is 'left'.
        ref_side_index : int, optional
            The reference side index of the beam to be cut. The default ref_side_index is calculated based on the angle between the plane's normal and each ref_side's normal.

        Returns
        -------
        :class:`~compas_timber.fabrication.LongitudinalCutProxy`

        """
        if isinstance(plane, Frame):
            plane = Plane.from_frame(plane)
        return cls(plane, beam, start_x, length, depth, angle_start, angle_end, tool_position, ref_side_index, **kwargs)

    def apply(self, geometry, _):
        """Apply the feature to the beam geometry.
        The resulting geometry might differ from the unproxified version, based on the parameters set in this instance.

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
            The resulting geometry after processing.

        """
        try:
            # TODO: add geometry implementation for cuts that don't go full length of beam
            return geometry.trimmed(self.plane)
        except BrepTrimmingError:
            raise FeatureApplicationError(self.plane, geometry, "The trimming operation failed. The cutting plane does not intersect with beam geometry.")

    def __getattr__(self, attr):
        # any unknown calls are passed through to the processing instance
        return getattr(self.unproxified(), attr)
