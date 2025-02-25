import math
from collections import OrderedDict

from compas.geometry import Box
from compas.geometry import Brep
from compas.geometry import Frame
from compas.geometry import Line
from compas.geometry import PlanarSurface
from compas.geometry import Plane
from compas.geometry import Rotation
from compas.geometry import Vector
from compas.geometry import angle_vectors_signed
from compas.geometry import distance_point_point
from compas.geometry import intersection_line_plane
from compas.geometry import is_point_behind_plane
from compas.tolerance import TOL

from compas_timber.errors import FeatureApplicationError

from .btlx import BTLxProcessing
from .btlx import BTLxProcessingParams
from .btlx import OrientationType
from .btlx import TenonShapeType


class DovetailTenon(BTLxProcessing):
    """Represents a Dovetail Tenon feature to be made on a beam.

    Parameters
    ----------
    orientation : int
        The orientation of the cut. Must be either OrientationType.START or OrientationType.END.
    start_x : float
        The start x-coordinate of the cut in parametric space of the reference side. Distance from the beam start to the reference point. -100000.0 < start_x < 100000.0.
    start_y : float
        The start y-coordinate of the cut in parametric space of the reference side. Distance from the reference edge to the reference point. -5000.0 < start_y < 5000.0.
    start_depth : float
        The start depth of the cut in parametric space of the reference side. Margin on the reference side. -5000.0 < start_depth < 5000.0.
    angle : float
        The angle of the cut. Angle between edge and reference edge. 0.1 < angle < 179.9.
    inclination : float
        The inclination of the cut. Inclination between face and reference side. 0.1 < inclination < 179.9.
    rotation : float
        The rotation of the cut. Angle between axis of the tenon and rederence side. 0.1 < rotation < 179.9.
    length_limited_top : bool
        Whether the top length of the cut is limited. True or False.
    length_limited_bottom : bool
        Whether the bottom length of the cut is limited. True or False.
    length : float
        The length of the cut. 0.0 < length < 5000.0.
    width : float
        The width of the cut. 0.0 < width < 1000.0.
    height : float
        The height of the tenon. 0.0 < height < 1000.0.
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

    PROCESSING_NAME = "DovetailTenon"  # type: ignore

    # Class-level attribute
    _DOVETAIL_TOOL_PARAMS = {}

    @property
    def __data__(self):
        data = super(DovetailTenon, self).__data__
        data["orientation"] = self.orientation
        data["start_x"] = self.start_x
        data["start_y"] = self.start_y
        data["start_depth"] = self.start_depth
        data["angle"] = self.angle
        data["inclination"] = self.inclination
        data["rotation"] = self.rotation
        data["length_limited_top"] = self.length_limited_top
        data["length_limited_bottom"] = self.length_limited_bottom
        data["length"] = self.length
        data["width"] = self.width
        data["height"] = self.height
        data["cone_angle"] = self.cone_angle
        data["use_flank_angle"] = self.use_flank_angle
        data["flank_angle"] = self.flank_angle
        data["shape"] = self.shape
        data["shape_radius"] = self.shape_radius
        return data

    # fmt: off
    def __init__(
        self,
        orientation = OrientationType.START,
        start_x=0.0,
        start_y=50.0,
        start_depth=50.0,
        angle=90.0,
        inclination=90.0,
        rotation=90.0,
        length_limited_top=True,
        length_limited_bottom=True,
        length=80.0,
        width=40.0,
        height=28.0,
        cone_angle=15.0,
        use_flank_angle=False,
        flank_angle=15.0,
        shape=TenonShapeType.AUTOMATIC,
        shape_radius=20.0,
        **kwargs
    ):
        super(DovetailTenon, self).__init__(**kwargs)
        self._orientation = None
        self._start_x = None
        self._start_y = None
        self._start_depth = None
        self._angle = None
        self._inclination = None
        self._rotation = None
        self._length_limited_top = None
        self._length_limited_bottom = None
        self._length = None
        self._width = None
        self._height = None
        self._cone_angle = None
        self._use_flank_angle = None
        self._flank_angle = None
        self._shape = None
        self._shape_radius = None

        self.orientation = orientation
        self.start_x = start_x
        self.start_y = start_y
        self.start_depth = start_depth
        self.angle = angle
        self.inclination = inclination
        self.rotation = rotation
        self.length_limited_top = length_limited_top
        self.length_limited_bottom = length_limited_bottom
        self.length = length
        self.width = width
        self.height = height
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
        return DovetailTenonParams(self)

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
            raise ValueError("StartX must be between -100000.0 and 100000.0.")
        self._start_x = start_x

    @property
    def start_y(self):
        return self._start_y

    @start_y.setter
    def start_y(self, start_y):
        if start_y > 5000.0 or start_y < -5000.0:
            raise ValueError("StartY must be between -5000.0 and 5000.0.")
        self._start_y = start_y

    @property
    def start_depth(self):
        return self._start_depth

    @start_depth.setter
    def start_depth(self, start_depth):
        if start_depth > 5000.0 or start_depth < -5000.0:
            raise ValueError("StartDepth must be between -5000.0 and 5000.0.")
        self._start_depth = start_depth

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
    def rotation(self):
        return self._rotation

    @rotation.setter
    def rotation(self, rotation):
        if rotation > 179.9 or rotation < 0.1:
            raise ValueError("Rotation must be between 0.1 and 179.9.")
        self._rotation = rotation

    @property
    def length_limited_top(self):
        return self._length_limited_top

    @length_limited_top.setter
    def length_limited_top(self, length_limited_top):
        if not isinstance(length_limited_top, bool):
            raise ValueError("LengthLimitedTop must be either True or False.")
        self._length_limited_top = length_limited_top

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
            raise ValueError("Length must be between 0.0 and 5000.0.")
        self._length = length

    @property
    def width(self):
        return self._width

    @width.setter
    def width(self, width):
        if width > 1000.0 or width < 0.0:
            raise ValueError("Width must be between 0.0 and 1000.0.")
        self._width = width

    @property
    def height(self):
        return self._height

    @height.setter
    def height(self, height):
        if height > 1000.0 or height < 0.0:
            raise ValueError("Height must be between 0.0 and 1000.0.")
        self._height = height

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
            raise ValueError("ShapeRadius must be between 0.0 and 1000.")
        self._shape_radius = shape_radius

    ########################################################################
    # Alternative constructors
    ########################################################################

    @classmethod
    def from_plane_and_beam(
        cls,
        plane,
        beam,
        start_y=0.0,
        start_depth=50.0,
        rotation=0.0,
        length=80.0,
        width=40.0,
        height=28.0,
        cone_angle=10.0,
        flank_angle=15.0,
        shape=TenonShapeType.AUTOMATIC,
        shape_radius=20.0,
        ref_side_index=0,
    ):
        """Create a DovetailTenon instance from a cutting surface and the beam it should cut. This could be the ref_side of the cross beam of a Joint and the main beam.

        Parameters
        ----------
        plane : :class:`~compas.geometry.Plane` or :class:`~compas.geometry.Frame`
            The cutting plane.
        beam : :class:`~compas_timber.elements.Beam`
            The beam that is cut by this instance.
        start_y : float, optional
            The start y-coordinate of the cut in parametric space of the reference side. Default is 0.0.
        start_depth : float, optional
            The start depth of the tenon, which is an offset along the normal of the reference side. Default is 50.0.
        rotation : float, optional
            The angle of rotation of the tenon. Default is 0.0.
        length : float, optional
            The length of the tenon. Default is 80.0.
        width : float, optional
            The width of the bottom edge of the tenon. Default is 40.0.
        height : float, optional
            The height of the tenon. Related to the dovetail tool and can be defined using the `DovetailTenon.define_dovetail_tool()` method. Default is 28.0.
        cone_angle : float, optional
            The angle of the cone of the tenon. Default is 10.0.
        flank_angle : float, optional
            The angle of the flank of the tenon. Related to the dovetail tool and can be defined using the `DovetailTenon.define_dovetail_tool()` method. Default is 15.0.
        shape : str, optional
            The shape of the tenon. Default is 'automatic'.
        shape_radius : float, optional
            The radius of the shape of the tenon. Related to the dovetail tool and can be defined using the `DovetailTenon.define_dovetail_tool()` method. Default is 20.0.
        ref_side_index : int, optional
            The reference side index of the beam to be cut. Default is 0 (i.e. RS1).

        Returns
        -------
        :class:`~compas_timber.fabrication.DovetailTenon`

        """
        # type: (Plane|Frame, Beam, float, float, bool, int) -> DovetailTenon

        if cls._DOVETAIL_TOOL_PARAMS:
            # get the tool parameters
            tool_angle = cls._DOVETAIL_TOOL_PARAMS["tool_angle"]
            tool_diameter = cls._DOVETAIL_TOOL_PARAMS["tool_diameter"]
            tool_height = cls._DOVETAIL_TOOL_PARAMS["tool_height"]
            tool_top_radius = tool_diameter / 2 - tool_height * (math.tan(math.radians(tool_angle)))
            # update parameters related to the tool if a tool is defined
            height = min(height, tool_height)
            flank_angle = tool_angle
            shape_radius = tool_top_radius

        # find the difference of the bottom and top radius of the frustum cone
        frustum_difference = height * math.tan(math.radians(flank_angle))

        if isinstance(plane, Frame):
            plane = Plane.from_frame(plane)
        # define ref_side & ref_edge
        ref_side = beam.ref_sides[ref_side_index]
        ref_edge = Line.from_point_and_vector(ref_side.point, ref_side.xaxis)

        # calculate orientation
        orientation = cls._calculate_orientation(ref_side, plane)

        # calculate angle
        angle = cls._calculate_angle(ref_side, plane)

        # calculate inclination
        inclination = cls._calculate_inclination(ref_side, plane, orientation, angle)

        # calculate start_y & rotation
        if orientation == OrientationType.END:
            rotation = -rotation
            start_y = -start_y
        start_y += beam.width / 2  # TODO: Should this be bound as well?
        rotation += 90

        # bound start_depth, length and width
        start_depth = cls._bound_start_depth(start_depth, inclination, height)
        length = cls._bound_length(
            ref_side, plane, beam.height, start_depth, inclination, length, height, frustum_difference
        )
        width = cls._bound_width(beam.width, angle, length, width, cone_angle, shape_radius, frustum_difference)

        # calculate start_x
        start_x = cls._calculate_start_x(
            ref_side,
            ref_edge,
            plane,
            orientation,
            start_y,
            start_depth,
            angle,
        )

        # determine if the top and bottom length of the cut is limited
        length_limited_top, length_limited_bottom = cls._calculate_length_limits(
            beam, start_depth, length, inclination
        )  # TODO: Should this instead come first and override the start_depth and length?

        use_flank_angle = True if flank_angle != 15.0 else False  # TODO: does this change anything?

        return cls(
            orientation,
            start_x,
            start_y,
            start_depth,
            angle,
            inclination,
            rotation,
            length_limited_top,
            length_limited_bottom,
            length,
            width,
            height,
            cone_angle,
            use_flank_angle,
            flank_angle,
            shape,
            shape_radius,
            ref_side_index=ref_side_index,
        )

    @staticmethod
    def _calculate_orientation(ref_side, cutting_plane):
        # orientation is START if cutting plane normal points towards the start of the beam and END otherwise
        # essentially if the start is being cut or the end
        if is_point_behind_plane(ref_side.point, cutting_plane):
            return OrientationType.START
        else:
            return OrientationType.END

    @staticmethod
    def _calculate_start_x(ref_side, ref_edge, plane, orientation, start_y, start_depth, angle):
        # calculate the start_x of the cut based on the ref_side, ref_edge, plane, start_y and angle
        plane.translate(ref_side.normal * start_depth)
        point_start_x = intersection_line_plane(ref_edge, plane)
        if point_start_x is None:
            raise ValueError("Plane does not intersect with beam.")
        start_x = distance_point_point(ref_side.point, point_start_x)
        # count for start_depth and start_y in the start_x
        if orientation == OrientationType.END:
            start_x -= start_y / math.tan(math.radians(angle))
        else:
            start_x += start_y / math.tan(math.radians(angle))
        return start_x

    @staticmethod
    def _calculate_angle(ref_side, plane):
        # vector rotation direction of the plane's normal in the vertical direction
        angle_vector = Vector.cross(ref_side.zaxis, plane.normal)
        angle = angle_vectors_signed(ref_side.xaxis, angle_vector, ref_side.zaxis, deg=True)
        return abs(angle)

    @staticmethod
    def _calculate_inclination(ref_side, plane, orientation, angle):
        # calculate the inclination between the ref_side and the plane
        if orientation == OrientationType.END:
            angle = 180 - angle
        rotation = Rotation.from_axis_and_angle(ref_side.normal, math.radians(angle))
        rotated_axis = ref_side.xaxis.copy()
        rotated_axis.transform(rotation)

        cross_plane = Vector.cross(rotated_axis, plane.normal)
        cross_ref_side = Vector.cross(rotated_axis, ref_side.normal)

        inclination = angle_vectors_signed(cross_ref_side, cross_plane, rotated_axis, deg=True)
        return abs(inclination)

    @staticmethod
    def _calculate_length_limits(beam, start_depth, length, inclination):
        # determine if the top and bottom length of the cut is limited
        length_limited_top = start_depth > 0.0
        length_limited_bottom = length < ((beam.height) / math.sin(math.radians(inclination)) - start_depth)

        # necessary override, otherwise tenon would go out of the blank
        if inclination > 90.0:
            length_limited_bottom = True
        elif inclination < 90.0:
            length_limited_top = True
        return length_limited_top, length_limited_bottom

    @staticmethod
    def _bound_length(ref_side, plane, beam_height, start_depth, inclination, length, height, frustum_difference):
        # bound the inserted length value to the maximum possible length for the beam based on the inclination so that the tenon does not go out of the blank
        max_length = (beam_height) / (math.sin(math.radians(inclination))) - start_depth

        # define the inclination angle regardless of the orientation start or end
        inclination_vector = Vector.cross(ref_side.yaxis, plane.normal)
        origin_inclination = math.degrees(ref_side.xaxis.angle(inclination_vector))
        if origin_inclination < 90.0:
            max_length = max_length - (frustum_difference + height / abs(math.tan(math.radians(inclination))))
        return min(max_length, length)

    @staticmethod
    def _bound_width(beam_width, angle, length, width, cone_angle, shape_radius, frustum_difference):
        # bound the inserted width value to the minumum(based on the dovetail tool radius) and maximum(so that the tenon does not go out of the blank) possible width for the beam
        max_width = beam_width / math.sin(math.radians(angle)) - 2 * (
            frustum_difference + length * math.tan(math.radians(cone_angle))
        )
        min_width = 2 * shape_radius
        if width < min_width:
            width = min_width
        elif width > max_width:
            width = max_width
        return width

    @staticmethod
    def _bound_start_depth(start_depth, inclination, height):
        # bound the start_depth value to the minimum possible start_depth if the incliantion is larger than 90 so that the tenon does not go out of the blank
        min_start_depth = height / (math.tan(math.radians(180 - inclination)))
        return max(start_depth, min_start_depth)

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
            If the cutting frames do not create a volume that itersects with beam geometry or any step fails.

        Returns
        -------
        :class:`~compas.geometry.Brep`
            The resulting geometry after processing

        """
        # type: (Brep, Beam) -> Brep

        # get cutting plane from params and beam
        try:
            cutting_plane = Plane.from_frame(self.frame_from_params_and_beam(beam))
        except ValueError as e:
            raise FeatureApplicationError(
                None, geometry, "Failed to generate cutting frame from parameters and beam: {}".format(str(e))
            )

        # get dovetail volume from params and beam
        try:
            dovetail_volume = self.dovetail_volume_from_params_and_beam(beam)
        except ValueError as e:
            raise FeatureApplicationError(
                None, geometry, "Failed to generate dovetail tenon volume from parameters and beam: {}".format(str(e))
            )

        # fillet the edges of the dovetail volume based on the shape
        if (
            self.shape != TenonShapeType.SQUARE and not self.length_limited_bottom
        ):  # TODO: Change negation to affirmation once Brep.fillet is implemented
            edge_indices = [4, 7] if self.length_limited_top else [5, 8]
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

        # trim geometry with cutting planes
        try:
            geometry.trim(cutting_plane)
        except Exception as e:
            raise FeatureApplicationError(
                cutting_plane, geometry, "Failed to trim geometry with cutting plane: {}".format(str(e))
            )

        # add tenon volume to geometry
        try:
            geometry += dovetail_volume
        except Exception as e:
            raise FeatureApplicationError(
                dovetail_volume, geometry, "Failed to add tenon volume to geometry: {}".format(str(e))
            )

        return geometry

    def frame_from_params_and_beam(self, beam):
        """
        Calculates the cutting frame from the machining parameters in this instance and the given beam.

        Parameters
        ----------
        beam : :class:`compas_timber.elements.Beam`
            The beam that is cut by this instance.

        Returns
        -------
        :class:`compas.geometry.Frame`
            The cutting frame.
        """
        assert self.angle is not None
        assert self.inclination is not None
        assert self.start_depth is not None

        # get the reference side surface of the beam
        ref_side = beam.side_as_surface(self.ref_side_index)

        # move the reference side surface to the start depth
        ref_side.translate(-ref_side.frame.normal * self.start_depth)

        # convert angles to radians
        inclination_radians = math.radians(self.inclination)
        angle_radians = math.radians(self.angle + 90)

        # calculate the point of origin based on orientation
        p_origin = ref_side.point_at(self.start_x, self.start_y)
        if self.orientation == OrientationType.END:
            yaxis = ref_side.frame.yaxis
        else:
            yaxis = -ref_side.frame.yaxis
            inclination_radians += math.pi

        # create the initial cutting plane
        cutting_frame = Frame(p_origin, -ref_side.frame.xaxis, yaxis)

        # apply rotations to the cutting plane based on angle and inclination parameters
        rot_a = Rotation.from_axis_and_angle(cutting_frame.zaxis, angle_radians, point=p_origin)
        rot_b = Rotation.from_axis_and_angle(cutting_frame.yaxis, inclination_radians, point=p_origin)
        cutting_frame.transform(rot_a * rot_b)

        # for simplicity align normal towards x-axis
        cutting_frame = Frame(cutting_frame.point, -cutting_frame.yaxis, cutting_frame.xaxis)

        # apply rotation based on the rotation parameter
        rot_angle = math.radians(self.rotation - 90)
        if self.orientation == OrientationType.START:
            rot_angle = -rot_angle
        rotation = Rotation.from_axis_and_angle(cutting_frame.normal, rot_angle, cutting_frame.point)
        cutting_frame.transform(rotation)

        return cutting_frame

    def dovetail_cutting_frames_from_params_and_beam(self, beam):
        """Calculates the cutting frames for the dovetail tenon from the machining parameters in this instance and the given beam."""

        # get the cutting frame
        cutting_frame = self.frame_from_params_and_beam(beam)

        # offset the cutting frame to create the cutting surface based on the height of the tenon. It needs to face in the opposite direction.
        offseted_cutting_frame = Frame(cutting_frame.point, cutting_frame.xaxis, cutting_frame.yaxis)
        offseted_cutting_frame.point += cutting_frame.normal * self.height

        cutting_surface = PlanarSurface(
            xsize=beam.height / math.sin(math.radians(self.inclination)),
            ysize=beam.width / math.sin(math.radians(self.angle)),
            frame=cutting_frame,
        )
        # move the cutting surface to the center
        cutting_surface.translate(-cutting_frame.xaxis * self.start_y)

        dx_top = self.width / 2 + self.length * abs(math.tan(math.radians(self.cone_angle)))
        dx_bottom = self.width / 2
        dy = -self.length

        bottom_dovetail_points = [
            cutting_surface.point_at(self.start_y - dx_top, 0),
            cutting_surface.point_at(self.start_y + dx_top, 0),
            cutting_surface.point_at(self.start_y + dx_bottom, dy),
            cutting_surface.point_at(self.start_y - dx_bottom, dy),
        ]

        dovetail_edges = [
            Line(bottom_dovetail_points[0], bottom_dovetail_points[1]),  # Top line
            Line(bottom_dovetail_points[1], bottom_dovetail_points[2]),  # Right line
            Line(bottom_dovetail_points[2], bottom_dovetail_points[3]),  # Bottom line
            Line(bottom_dovetail_points[3], bottom_dovetail_points[0]),  # Left line
        ]

        trimming_frames = []
        for i, edge in enumerate(dovetail_edges):
            # create the initial frame using the line's direction and the cutting frame's normal
            frame = Frame(edge.midpoint, -edge.direction, cutting_frame.normal)

            if i != 0:
                # determine the rotation direction: right and bottom are positive, top and left are negative
                # apply the rotation based on the flank angle
                rotation = Rotation.from_axis_and_angle(-edge.direction, math.radians(self.flank_angle), frame.point)
                frame.transform(rotation)

            trimming_frames.append(frame)

        cutting_frame.xaxis = -cutting_frame.xaxis
        trimming_frames.extend([cutting_frame, offseted_cutting_frame])
        return trimming_frames

    def dovetail_volume_from_params_and_beam(self, beam):
        """Calculates the dovetail tenon volume from the machining parameters in this instance and the given beam.

        Parameters
        ----------
        beam : :class:`compas_timber.elements.Beam`
            The beam that is cut by this instance.

        Returns
        -------
        :class:`compas.geometry.Brep`
            The tenon volume.

        """
        # type: (Beam) -> Brep

        assert self.inclination is not None
        assert self.rotation is not None
        assert self.height is not None
        assert self.flank_angle is not None
        assert self.shape is not None
        assert self.shape_radius is not None
        assert self.length_limited_top is not None
        assert self.length_limited_bottom is not None

        cutting_frame = self.frame_from_params_and_beam(beam)

        # create the dovetail volume by trimming a box  # TODO: PluginNotInstalledError for Brep.from_loft
        # get the box as a brep
        dovetail_volume = Brep.from_box(
            Box(
                (beam.width + (beam.width * math.sin(math.radians(self.rotation)))) * 2,
                (beam.height / math.sin(math.radians(self.inclination))) * 2,
                self.height * 2,
                cutting_frame,
            )
        )

        # get the cutting frames for the dovetail tenon
        trimming_frames = self.dovetail_cutting_frames_from_params_and_beam(beam)

        # trim the box to create the dovetail volume
        for frame in trimming_frames:
            try:
                dovetail_volume.trim(frame)
            except Exception as e:
                raise FeatureApplicationError(
                    frame, dovetail_volume, "Failed to trim tenon volume with cutting frame: {}".format(str(e))
                )

        return dovetail_volume


class DovetailTenonParams(BTLxProcessingParams):
    """A class to store the parameters of a Dovetail Tenon feature.

    Parameters
    ----------
    instance : :class:`~compas_timber.fabrication.DovetailTenon`
        The instance of the Dovetail Tenon feature.
    """

    def __init__(self, instance):
        # type: (DovetailTenon) -> None
        super(DovetailTenonParams, self).__init__(instance)

    def as_dict(self):
        """Returns the parameters of the Dovetail Tenon feature as a dictionary.

        Returns
        -------
        dict
            The parameters of the Dovetail Tenon as a dictionary.
        """
        # type: () -> OrderedDict
        result = OrderedDict()
        result["Orientation"] = self._instance.orientation
        result["StartX"] = "{:.{prec}f}".format(float(self._instance.start_x), prec=TOL.precision)
        result["StartY"] = "{:.{prec}f}".format(float(self._instance.start_y), prec=TOL.precision)
        result["StartDepth"] = "{:.{prec}f}".format(float(self._instance.start_depth), prec=TOL.precision)
        result["Angle"] = "{:.{prec}f}".format(float(self._instance.angle), prec=TOL.precision)
        result["Inclination"] = "{:.{prec}f}".format(float(self._instance.inclination), prec=TOL.precision)
        result["Rotation"] = "{:.{prec}f}".format(float(self._instance.rotation), prec=TOL.precision)
        result["LengthLimitedTop"] = "yes" if self._instance.length_limited_top else "no"
        result["LengthLimitedBottom"] = "yes" if self._instance.length_limited_bottom else "no"
        result["Length"] = "{:.{prec}f}".format(float(self._instance.length), prec=TOL.precision)
        result["Width"] = "{:.{prec}f}".format(float(self._instance.width), prec=TOL.precision)
        result["Height"] = "{:.{prec}f}".format(float(self._instance.height), prec=TOL.precision)
        result["ConeAngle"] = "{:.{prec}f}".format(float(self._instance.cone_angle), prec=TOL.precision)
        result["UseFlankAngle"] = "yes" if self._instance.use_flank_angle else "no"
        result["FlankAngle"] = "{:.{prec}f}".format(float(self._instance.flank_angle), prec=TOL.precision)
        result["Shape"] = self._instance.shape
        result["ShapeRadius"] = "{:.{prec}f}".format(float(self._instance.shape_radius), prec=TOL.precision)
        return result
