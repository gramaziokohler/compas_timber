import math
from collections import OrderedDict

from compas.geometry import Box
from compas.geometry import Brep
from compas.geometry import Frame
from compas.geometry import Line
from compas.geometry import PlanarSurface
from compas.geometry import Plane
from compas.geometry import Rotation
from compas.geometry import angle_vectors_signed
from compas.geometry import distance_point_point
from compas.geometry import intersection_line_plane
from compas.geometry import is_point_behind_plane
from compas.tolerance import TOL

from compas_timber.errors import FeatureApplicationError

from .btlx import BTLxProcessing
from .btlx import BTLxProcessingParams
from .btlx import LimitationTopType
from .btlx import OrientationType
from .btlx import TenonShapeType


class DovetailMortise(BTLxProcessing):
    """Represents a Dovetail Mortise feature to be made on a beam.

    Parameters
    ----------
    start_x : float
        The start x-coordinate of the cut in parametric space of the reference side. Distance from the beam start to the reference point. -100000.0 < start_x < 100000.0.
    start_y : float
        The start y-coordinate of the cut in parametric space of the reference side. Distance from the reference edge to the reference point. -5000.0 < start_y < 5000.0.
    start_depth : float
        The start depth of the cut in parametric space of the reference side. Margin on the reference side. 0.0 < start_depth < 5000.0.
    angle : float
        The angle of the cut. Angle between edge and reference edge. -180.0 < angle < 180.0.
    slope : float
        The slope of the cut. Angle between axis along the length of the mortise and rederence side. 0.1 < slope < 179.9.
    inclination : float
        The inclination of the cut. Angle between axis along the width of the mortise and rederence side. 0.1 < inclination < 179.9.
    limitation_top : str
        The limitation type of the top length of the cut. Should be either 'limited', 'unlimited', or 'pocket'.
    length_limited_bottom : bool
        Whether the bottom length of the cut is limited. True or False.
    length : float
        The length of the cut. 0.0 < length < 5000.0.
    width : float
        The width of the cut. 0.0 < width < 1000.0.
    depth : float
        The depth of the mortise. 0.0 < depth < 1000.0.
    cone_angle : float
        The cone angle of the cut. 0.0 < cone_angle < 30.0.
    use_flank_angle : bool
        Whether the flank angle is used. True or False.
    flank_angle : float
        The flank angle of the cut. Angle of the tool. 5.0 < flank_angle < 35.0.
    shape : str
        The shape of the cut. Must be either 'automatic', 'square', 'round', 'rounded', or 'radius'.
    shape_radius : float
        The radius of the shape of the cut. 0.0 < shape_radius < 1000.0.

    """

    PROCESSING_NAME = "DovetailMortise"  # type: ignore

    # Class-level attribute
    _DOVETAIL_TOOL_PARAMS = {}

    @property
    def __data__(self):
        data = super(DovetailMortise, self).__data__
        data["start_x"] = self.start_x
        data["start_y"] = self.start_y
        data["start_depth"] = self.start_depth
        data["angle"] = self.angle
        data["slope"] = self.slope
        data["inclination"] = self.inclination
        data["limitation_top"] = self.limitation_top
        data["length_limited_bottom"] = self.length_limited_bottom
        data["length"] = self.length
        data["width"] = self.width
        data["depth"] = self.depth
        data["cone_angle"] = self.cone_angle
        data["use_flank_angle"] = self.use_flank_angle
        data["flank_angle"] = self.flank_angle
        data["shape"] = self.shape
        data["shape_radius"] = self.shape_radius
        return data

    # fmt: off
    def __init__(
        self,
        start_x=0.0,
        start_y=50.0,
        start_depth=0.0,
        angle=0.0,
        slope=90.0,
        inclination=90.0,
        limitation_top=LimitationTopType.LIMITED,
        length_limited_bottom=True,
        length=80.0,
        width=40.0,
        depth=28.0,
        cone_angle=15.0,
        use_flank_angle=False,
        flank_angle=15.0,
        shape=TenonShapeType.AUTOMATIC,
        shape_radius=20.0,
        **kwargs
    ):
        super(DovetailMortise, self).__init__(**kwargs)
        self._start_x = None
        self._start_y = None
        self._start_depth = None
        self._angle = None
        self._slope = None
        self._inclination = None
        self._limitation_top = None
        self._length_limited_bottom = None
        self._length = None
        self._width = None
        self._depth = None
        self._cone_angle = None
        self._use_flank_angle = None
        self._flank_angle = None
        self._shape = None
        self._shape_radius = None

        self.start_x = start_x
        self.start_y = start_y
        self.start_depth = start_depth
        self.angle = angle
        self.slope = slope
        self.inclination = inclination
        self.limitation_top = limitation_top
        self.length_limited_bottom = length_limited_bottom
        self.length = length
        self.width = width
        self.depth = depth
        self.cone_angle = cone_angle
        self.use_flank_angle = use_flank_angle
        self.flank_angle = flank_angle
        self.shape = shape
        self.shape_radius = shape_radius

    ########################################################################
    # Properties
    ########################################################################

    @property
    def params(self):
        return DovetailMortiseParams(self)

    @property
    def start_x(self):
        return self._start_x

    @start_x.setter
    def start_x(self, start_x):
        if start_x > 100000.0 or start_x < -100000.0:
            raise ValueError("StartX must be between -100000.0 and 100000.0")
        self._start_x = start_x

    @property
    def start_y(self):
        return self._start_y

    @start_y.setter
    def start_y(self, start_y):
        if start_y > 5000.0 or start_y < -5000.0:
            raise ValueError("StartY must be between -5000.0 and 5000.0")
        self._start_y = start_y

    @property
    def start_depth(self):
        return self._start_depth

    @start_depth.setter
    def start_depth(self, start_depth):
        if start_depth > 5000.0 or start_depth < 0.0:
            raise ValueError("StartDepth must be between 0.0 and 5000.0")
        self._start_depth = start_depth

    @property
    def angle(self):
        return self._angle

    @angle.setter
    def angle(self, angle):
        if angle > 180.0 or angle < -180.0:
            raise ValueError("Angle must be between -180.0 and 180.0.")
        self._angle = angle

    @property
    def slope(self):
        return self._slope

    @slope.setter
    def slope(self, slope):
        if slope > 179.9 or slope < 0.1:
            raise ValueError("Slope must be between 0.1 and 179.9.")
        self._slope = slope

    @property
    def inclination(self):
        return self._inclination

    @inclination.setter
    def inclination(self, inclination):
        if inclination > 179.9 or inclination < 0.1:
            raise ValueError("Inclination must be between 0.1 and 179.9.")
        self._inclination = inclination

    @property
    def limitation_top(self):
        return self._limitation_top

    @limitation_top.setter
    def limitation_top(self, limitation_top):
        if limitation_top not in [LimitationTopType.LIMITED, LimitationTopType.UNLIMITED, LimitationTopType.POCKET]:
            raise ValueError("LimitationTop must be either limited, unlimited or pocket.")
        self._limitation_top = limitation_top

    @property
    def length_limited_bottom(self):
        return self._length_limited_bottom

    @length_limited_bottom.setter
    def length_limited_bottom(self, length_limited_bottom):
        if not isinstance(length_limited_bottom, bool):
            raise ValueError("LengthLimitedBottom must be either True or False.")
        self._length_limited_bottom = length_limited_bottom

    @property
    def length(self):
        return self._length

    @length.setter
    def length(self, length):
        if length > 5000.0 or length < 0.0:
            raise ValueError("Length must be between 0.0 and 5000.0")
        self._length = length

    @property
    def width(self):
        return self._width

    @width.setter
    def width(self, width):
        if width > 1000.0 or width < 0.0:
            raise ValueError("Width must be between 0.0 and 1000.0")
        self._width = width

    @property
    def depth(self):
        return self._height

    @depth.setter
    def depth(self, depth):
        if depth > 1000.0 or depth < 0.0:
            raise ValueError("depth must be between 0.0 and 1000.0")
        self._height = depth

    @property
    def cone_angle(self):
        return self._cone_angle

    @cone_angle.setter
    def cone_angle(self, cone_angle):
        if cone_angle > 30.0 or cone_angle < 0.0:
            raise ValueError("ConeAngle must be between 0.0 and 30.0.")
        self._cone_angle = cone_angle

    @property
    def use_flank_angle(self):
        return self._use_flank_angle

    @use_flank_angle.setter
    def use_flank_angle(self, use_flank_angle):
        if not isinstance(use_flank_angle, bool):
            raise ValueError("UseFlankAngle must be either True or False.")
        self._use_flank_angle = use_flank_angle

    @property
    def flank_angle(self):
        return self._flank_angle

    @flank_angle.setter
    def flank_angle(self, flank_angle):
        if flank_angle > 35.0 or flank_angle < 5.0:
            raise ValueError("FlankAngle must be between 5.0 and 35.0.")
        self._flank_angle = flank_angle

    @property
    def shape(self):
        return self._shape

    @shape.setter
    def shape(self, shape):
        if shape not in [
            TenonShapeType.AUTOMATIC,
            TenonShapeType.SQUARE,
            TenonShapeType.ROUND,
            TenonShapeType.ROUNDED,
            TenonShapeType.RADIUS,
        ]:
            raise ValueError("Shape must be either 'automatic', 'square', 'round', 'rounded', or 'radius'.")
        self._shape = shape

    @property
    def shape_radius(self):
        return self._shape_radius

    @shape_radius.setter
    def shape_radius(self, shape_radius):
        if shape_radius > 1000.0 or shape_radius < 0.0:
            raise ValueError("ShapeRadius must be between 0.0 and 1000.0")
        self._shape_radius = shape_radius

    ########################################################################
    # Alternative constructors
    ########################################################################

    @classmethod
    def from_frame_and_beam(
        cls,
        frame,
        beam,
        start_depth=0.0,
        angle=0.0,
        length=80.0,
        width=40.0,
        depth=28.0,
        cone_angle=10.0,
        flank_angle=15.0,
        shape=TenonShapeType.AUTOMATIC,
        shape_radius=20.0,
        ref_side_index=0,
    ):
        """Create a DovetailMortise instance from a cutting surface and the beam it should cut. This could be the ref_side of the cross beam of a Joint and the cross beam.

        Parameters
        ----------
        frame : :class:`~compas.geometry.Frame` or :class:`~compas.geometry.Plane`
            The cutting frame.
        beam : :class:`~compas_timber.elements.Beam`
            The beam that is cut by this instance.
        start_depth : float, optional
            The start depth of the cut along the y-axis of the beam. This offset is to be used in case of housing. Default is 0.0.
        angle : float, optional
            The angle of the cut.
        length : float, optional
            The length of the mortise.
        width : float, optional
            The width of the mortise.
        depth : float, optional
            The depth of the mortise. The equivalent value of the DovetailTenon BTLxProcessing is the height.
        cone_angle : float, optional
            The cone angle of the dovetail mortise.
        flank_angle : float, optional
            The flank angle of the dovetail mortise.
        shape : str, optional
            The shape of the dovetail mortise in regards to it's edges. Default is 'automatic'.
        shape_radius : float, optional
            The radius of the shape of the dovetail mortise. Default is 20.0.
        ref_side_index : int, optional
            The reference side index of the beam to be cut. Default is 0 (i.e. RS1).

        Returns
        -------
        :class:`~compas_timber.fabrication.DovetailMortise`

        """
        # type: (Frame|Plane, Beam, float, float, float, float, float, float, float, float, float, float, int) -> DovetailMortise

        if isinstance(frame, Plane):
            frame = Frame.from_plane(frame)

        # define ref_side & ref_edge
        ref_side = beam.ref_sides[ref_side_index]
        ref_edge = Line.from_point_and_vector(ref_side.point, ref_side.xaxis)

        # calculate orientation
        orientation = cls._calculate_orientation(ref_side, frame)

        # calclulate start_x and start_y
        start_x = cls._calculate_start_x(ref_side, ref_edge, frame)
        start_y = cls._calculate_start_y(ref_side, frame)

        # define angle
        angle = cls._calculate_angle(ref_side, frame, orientation)

        # define slope and inclination
        # TODO: In which cases do you want indiferent slope and inclination?
        slope = 90.0
        inclination = 90.0

        # determine if the top and bottom length of the cut is limited
        limitation_top = LimitationTopType.UNLIMITED
        length_limited_bottom = True

        use_flank_angle = True if flank_angle != 15.0 else False  # TODO: does this change anything?

        return cls(
            start_x,
            start_y,
            start_depth,
            angle,
            slope,
            inclination,
            limitation_top,
            length_limited_bottom,
            length,
            width,
            depth,
            cone_angle,
            use_flank_angle,
            flank_angle,
            shape,
            shape_radius,
            ref_side_index=ref_side_index,
        )

    @staticmethod
    def _calculate_orientation(ref_side, cutting_frame):
        # calculate the orientation of the beam by comparing the xaxis's direction of the ref_side and the plane.
        # Orientation is not set as a param for the BTLxDovetailMortise processing but its essential for the definition of the rest of the params.
        perp_plane = Plane(cutting_frame.point, cutting_frame.xaxis)
        if is_point_behind_plane(ref_side.point, perp_plane):
            return OrientationType.END
        else:
            return OrientationType.START

    @staticmethod
    def _calculate_start_x(ref_side, ref_edge, cutting_frame):
        # calculate the start_x of the cut based on the ref_side, ref_edge and cutting_frame
        perp_plane = Plane(cutting_frame.point, ref_side.xaxis)
        point_start_x = intersection_line_plane(ref_edge, perp_plane)
        if point_start_x is None:
            raise ValueError("Plane does not intersect with beam.")

        start_x = distance_point_point(ref_side.point, point_start_x)
        return start_x

    @staticmethod
    def _calculate_start_y(ref_side, cutting_frame):
        # calculate the start_y from the distance between the ref_side and the cutting frame in the y-axis direction of the ref_side
        direction = ref_side.yaxis.unitized()
        vector = cutting_frame.point - ref_side.point
        return abs(vector.dot(direction))

    @staticmethod
    def _calculate_angle(ref_side, cutting_frame, orientation):
        # calculate the angle of the cut based on the ref_side and cutting_frame
        if orientation == OrientationType.START:
            angle = angle_vectors_signed(ref_side.xaxis, -cutting_frame.xaxis, ref_side.normal, deg=True)
            return angle - 90.0
        else:
            angle = angle_vectors_signed(ref_side.xaxis, cutting_frame.xaxis, ref_side.normal, deg=True)
            return angle + 90.0

    ########################################################################
    # Class Methods
    ########################################################################

    @classmethod
    def define_dovetail_tool(cls, tool_angle, tool_diameter, tool_height):
        """Define the parameters for the dovetail feature based on a defined dovetail cutting tool.

        Parameters
        ----------
        tool_angle : float
            The angle of the dovetail cutter tool.
        tool_diameter : float
            The diameter of the dovetail cutter tool.
        tool_height : float
            The height of the dovetail cutter tool.

        """
        # type: (float, float, float) -> None
        cls._DOVETAIL_TOOL_PARAMS = {
            "tool_angle": tool_angle,
            "tool_diameter": tool_diameter,
            "tool_height": tool_height,
        }

    ########################################################################
    # Methods
    ########################################################################

    def apply(self, geometry, beam):
        """Apply the feature to the beam geometry.

        Parameters
        ----------
        geometry : :class:`compas.geometry.Brep`
            The geometry to be processed.

        beam : :class:`compas_timber.elements.Beam`
            The beam that is milled by this instance.

        Raises
        ------
        :class:`~compas_timber.errors.FeatureApplicationError`
            If the cutting planes do not create a volume that itersects with beam geometry or any step fails.

        Returns
        -------
        :class:`~compas.geometry.Brep`
            The resulting geometry after processing

        """
        # type: (Brep, Beam) -> Brep

        # get dovetail volume from params and beam
        try:
            dovetail_volume = self.dovetail_volume_from_params_and_beam(beam)
        except ValueError as e:
            raise FeatureApplicationError(
                None, geometry, "Failed to generate dovetail mortise volume from parameters and beam: {}".format(str(e))
            )

        # fillet the edges of the dovetail volume based on the shape
        if (
            self.shape != TenonShapeType.SQUARE and not self.length_limited_bottom
        ):  # TODO: Change negation to affirmation once Brep.fillet is implemented
            edge_indices = [4, 7] if self.length_limited_bottom else [5, 8]
            try:
                dovetail_volume.fillet(
                    self.shape_radius, [dovetail_volume.edges[edge_indices[0]], dovetail_volume.edges[edge_indices[1]]]
                )  # TODO: NotImplementedError
            except Exception as e:
                raise FeatureApplicationError(
                    dovetail_volume,
                    geometry,
                    "Failed to fillet the edges of the dovetail volume based on the shape: {}".format(str(e)),
                )

        # remove tenon volume to geometry
        try:
            geometry -= dovetail_volume
        except Exception as e:
            raise FeatureApplicationError(
                dovetail_volume, geometry, "Failed to add tenon volume to geometry: {}".format(str(e))
            )

        return geometry

    def frame_from_params_and_beam(self, beam):
        """Calculates the cutting frame from the machining parameters in this instance and the given beam

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
        assert self.angle is not None
        assert self.inclination is not None

        # start with a plane aligned with the ref side but shifted to the start_x of the cut
        ref_side = beam.side_as_surface(self.ref_side_index)
        p_origin = ref_side.point_at(self.start_x, self.start_y)
        cutting_frame = Frame(p_origin, ref_side.frame.xaxis, ref_side.frame.yaxis)

        # rotate the cutting frame based on the angle
        rotation = Rotation.from_axis_and_angle(
            cutting_frame.normal, math.radians(self.angle + 90), cutting_frame.point
        )
        cutting_frame.transform(rotation)

        return cutting_frame

    def dovetail_cutting_frames_from_params_and_beam(self, beam):
        """Calculates the cutting frames for the dovetail mortise from the machining parameters in this instance and the given beam.

        Parameters
        ----------
        beam : :class:`compas_timber.elements.Beam`
            The beam that is cut by this instance.

        Returns
        -------
        list of :class:`compas.geometry.Frame`
            The cutting frames for the dovetail mortise.
        """
        assert self.angle is not None
        assert self.depth is not None
        assert self.start_depth is not None

        # start with a plane aligned with the ref side but shifted to the start_x of the cut
        cutting_frame = self.frame_from_params_and_beam(beam)

        offseted_cutting_frame = Frame(cutting_frame.point, -cutting_frame.xaxis, cutting_frame.yaxis)
        offseted_cutting_frame.point += cutting_frame.normal * self.depth

        cutting_surface = PlanarSurface(
            xsize=beam.height,
            ysize=beam.width,
            frame=cutting_frame,
        )

        # offset the cutting surface in case of housing
        cutting_surface.translate(-cutting_frame.zaxis * self.start_depth)

        # calculate the displacement of the edge points of the dovetail from the top-center
        dx_top = self.width / 2 + self.length * abs(math.tan(math.radians(self.cone_angle)))
        dx_bottom = self.width / 2
        dy = self.length

        dovetail_profile_points = [
            cutting_surface.point_at(-dx_top, 0),
            cutting_surface.point_at(dx_top, 0),
            cutting_surface.point_at(dx_bottom, -dy),
            cutting_surface.point_at(-dx_bottom, -dy),
        ]

        dovetail_edges = [
            Line(dovetail_profile_points[0], dovetail_profile_points[1]),  # Top line
            Line(dovetail_profile_points[1], dovetail_profile_points[2]),  # Right line
            Line(dovetail_profile_points[2], dovetail_profile_points[3]),  # Bottom line
            Line(dovetail_profile_points[3], dovetail_profile_points[0]),  # Left line
        ]

        trimming_frames = []
        for i, edge in enumerate(dovetail_edges):
            # create the initial frame using the line's direction and the cutting frame's normal
            frame = Frame(edge.midpoint, edge.direction, cutting_frame.normal)

            if i != 0:
                # determine the rotation direction: right and bottom are positive, top and left are negative
                # apply the rotation based on the flank angle
                rotation = Rotation.from_axis_and_angle(edge.direction, math.radians(self.flank_angle), frame.point)
                frame.transform(rotation)

            trimming_frames.append(frame)

        # translate the top trimming frame to the top of the beam if the top is unlimited
        if self.limitation_top == LimitationTopType.UNLIMITED:
            trimming_frames[0].translate(cutting_frame.yaxis * (beam.height - TOL.relative))

        cutting_frame.xaxis = -cutting_frame.xaxis
        trimming_frames.append(cutting_frame)
        return trimming_frames

    def dovetail_volume_from_params_and_beam(self, beam):
        """Calculates the dovetail mortise volume from the machining parameters in this instance and the given beam.

        Parameters
        ----------
        beam : :class:`compas_timber.elements.Beam`
            The beam that is cut by this instance.

        Returns
        -------
        :class:`compas.geometry.Brep`
            The mortise volume.

        """
        # type: (Beam) -> Brep

        assert self.inclination is not None
        assert self.slope is not None
        assert self.depth is not None

        cutting_frame = self.frame_from_params_and_beam(beam)

        # create the dovetail volume by trimming a box  # TODO: PluginNotInstalledError for Brep.from_loft
        # get the box as a brep
        dovetail_volume = Brep.from_box(
            Box(
                (beam.width + (beam.width * math.sin(math.radians(self.inclination)))) * 2,
                (beam.height / math.sin(math.radians(self.slope))) * 2,
                self.depth * 2,
                cutting_frame,
            )
        )

        # get the cutting frames for the dovetail tenon
        trimming_frames = self.dovetail_cutting_frames_from_params_and_beam(beam)

        # trim the box to create the dovetail volume
        for frame in trimming_frames:
            try:
                frame.xaxis = -frame.xaxis
                dovetail_volume.trim(frame)
            except Exception as e:
                raise FeatureApplicationError(
                    frame, dovetail_volume, "Failed to trim tenon volume with cutting plane: {}".format(str(e))
                )

        return dovetail_volume


class DovetailMortiseParams(BTLxProcessingParams):
    """A class to store the parameters of a Dovetail Mortise feature.

    Parameters
    ----------
    instance : :class:`~compas_timber.fabrication.DovetailMortise`
        The instance of the Dovetail Mortise feature.
    """

    def __init__(self, instance):
        # type: (DovetailMortise) -> None
        super(DovetailMortiseParams, self).__init__(instance)

    def as_dict(self):
        """Returns the parameters of the Dovetail Mortise feature as a dictionary.

        Returns
        -------
        dict
            The parameters of the Dovetail Mortise as a dictionary.
        """
        # type: () -> OrderedDict

        result = OrderedDict()
        result["StartX"] = "{:.{prec}f}".format(float(self._instance.start_x), prec=TOL.precision)
        result["StartY"] = "{:.{prec}f}".format(float(self._instance.start_y), prec=TOL.precision)
        result["StartDepth"] = "{:.{prec}f}".format(float(self._instance.start_depth), prec=TOL.precision)
        result["Angle"] = "{:.{prec}f}".format(float(self._instance.angle), prec=TOL.precision)
        result["Slope"] = "{:.{prec}f}".format(float(self._instance.slope), prec=TOL.precision)
        # result["Inclination"] = "{:.{prec}f}".format(float(self._instance.inclination), prec=TOL.precision)
        #! Inclination is a parameter according to the documentation but gives an error in BTL Viewer.
        result["LimitationTop"] = self._instance.limitation_top
        result["LengthLimitedBottom"] = "yes" if self._instance.length_limited_bottom else "no"
        result["Length"] = "{:.{prec}f}".format(float(self._instance.length), prec=TOL.precision)
        result["Width"] = "{:.{prec}f}".format(float(self._instance.width), prec=TOL.precision)
        result["Depth"] = "{:.{prec}f}".format(float(self._instance.depth), prec=TOL.precision)
        result["ConeAngle"] = "{:.{prec}f}".format(float(self._instance.cone_angle), prec=TOL.precision)
        result["UseFlankAngle"] = "yes" if self._instance.use_flank_angle else "no"
        result["FlankAngle"] = "{:.{prec}f}".format(float(self._instance.flank_angle), prec=TOL.precision)
        result["Shape"] = self._instance.shape
        result["ShapeRadius"] = "{:.{prec}f}".format(float(self._instance.shape_radius), prec=TOL.precision)
        return result
