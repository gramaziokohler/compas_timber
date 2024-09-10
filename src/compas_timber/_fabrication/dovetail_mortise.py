import math

from compas.geometry import Box
from compas.geometry import Brep
from compas.geometry import Frame
from compas.geometry import Line
from compas.geometry import Point
from compas.geometry import Plane
from compas.geometry import PlanarSurface
from compas.geometry import Rotation
from compas.geometry import Vector
from compas.geometry import angle_vectors_signed
from compas.geometry import distance_point_point
from compas.geometry import intersection_line_plane
from compas.geometry import is_point_behind_plane
from compas.geometry import offset_polyline
from compas.tolerance import TOL

from compas_timber.elements import FeatureApplicationError

from .btlx_process import BTLxProcess
from .btlx_process import BTLxProcessParams
from .btlx_process import TenonShapeType
from .btlx_process import OrientationType
from .btlx_process import LimitationTopType


class DovetailMortise(BTLxProcess):
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

    PROCESS_NAME = "DovetailMortise"  # type: ignore

    # Class-level attribute
    _dovetail_tool_params = {}

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
    def params_dict(self):
        return DovetailMortiseParams(self).as_dict()

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
        if angle > 90.0 or angle < -90.0:
            raise ValueError("Angle must be between -90.0 and 90.0.")
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
    def height(self):
        return self._height

    @height.setter
    def height(self, height):
        if height > 1000.0 or height < 0.0:
            raise ValueError("Height must be between 0.0 and 1000.0")
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
            raise ValueError("ShapeRadius must be between 0.0 and 1000.0")
        self._shape_radius = shape_radius

    ########################################################################
    # Alternative constructors
    ########################################################################

    @classmethod
    def from_plane_tenon_and_beam(
        cls,
        plane,
        dovetail_tenon,
        beam,
        ref_side_index=0,
    ):
        """Create a DovetailMortise instance from a cutting surface and the beam it should cut. This could be the ref_side of the cross beam of a Joint and the main beam.

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
        :class:`~compas_timber.fabrication.DovetailMortise`

        """
        # type: (Plane|Frame, Beam, float, float, bool, int) -> DovetailMortise

        if isinstance(plane, Frame):
            plane = Plane.from_frame(plane)
        # define ref_side & ref_edge
        ref_side = beam.ref_sides[ref_side_index]
        ref_edge = Line.from_point_and_vector(ref_side.point, ref_side.xaxis)

        plane = Plane(plane.point, ref_side.xaxis)

        # define orientation
        orientation = cls._calculate_orientation(ref_side, plane)

        # calclulate start_x
        start_x = cls._calculate_start_x(ref_side, ref_edge, plane)

        # calculate start_y and angle
        if orientation == OrientationType.END:
            start_y = beam.width
            angle = -90.0
        else:
            start_y = 0.0
            angle = 0.0

        # calculate start_depth
        # TODO: This is not 0 when you have housing. StartDepth -> House height
        start_depth = 0.0

        # define slope and inclination
        # TODO: In which cases do you want indiferent slope and inclination?
        slope = 90.0
        inclination = 90.0

        # define mortise parameters from tenon
        length, width, depth, cone_angle, use_flank_angle, flank_angle, shape, shape_radius = (
            dovetail_tenon.tenon_parameters
        )

        # determine if the top and bottom length of the cut is limited
        # TODO: this should instead come first and override the start_depth and length
        # length_limited_bottom = length < ((beam.height) / math.sin(math.radians(inclination)) - start_depth)
        # override because otherwise tenon would go out of the blank
        limitation_top = LimitationTopType.LIMITED
        length_limited_bottom = True

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
    def _calculate_orientation(ref_side, cutting_plane):
        # orientation is START if cutting plane normal points towards the start of the beam and END otherwise
        # essentially if the start is being cut or the end
        if is_point_behind_plane(ref_side.point, cutting_plane):
            return OrientationType.END
        else:
            return OrientationType.START

    @staticmethod
    def _calculate_start_x(ref_side, ref_edge, plane):
        # calculate the start_x of the cut based on the ref_side, ref_edge, plane, start_y and angle
        point_start_x = intersection_line_plane(ref_edge, plane)
        if point_start_x is None:
            raise ValueError("Plane does not intersect with beam.")
        start_x = distance_point_point(ref_side.point, point_start_x)
        return start_x

    # @staticmethod
    # def _calculate_angle(ref_side, plane):
    #     # vector rotation direction of the plane's normal in the vertical direction
    #     angle_vector = Vector.cross(ref_side.zaxis, plane.normal)
    #     angle = angle_vectors_signed(ref_side.xaxis, angle_vector, ref_side.zaxis, deg=True)
    #     return angle

    # @staticmethod
    # def _calculate_inclination(ref_side, plane):
    #     # vector rotation direction of the plane's normal in the horizontal direction
    #     inclination_vector = Vector.cross(ref_side.yaxis, plane.normal)
    #     inclination = angle_vectors_signed(ref_side.xaxis, inclination_vector, ref_side.yaxis, deg=True)
    #     return abs(inclination)

    # @staticmethod
    # def _calculate_rotation(ref_side, plane):
    #     # calculate the rotation of the cut based on the ref_side
    #     #! TODO: I should find a better way to get the normal of the cross_beam
    #     plane = Frame.from_plane(plane)

    #     def project_vector_on_plane(v, plane_normal):
    #         # Projects a vector onto a plane defined by a normal vector.
    #         plane_normal.unitize()
    #         dot_product = v.dot(plane_normal)
    #         projection = [i - dot_product * j for i, j in zip(v, plane_normal)]
    #         return Vector(*projection)

    #     projection_normal = ref_side.xaxis
    #     proj_ref_side_normal = project_vector_on_plane(ref_side.normal, projection_normal)
    #     proj_z_axis = project_vector_on_plane(plane.yaxis, projection_normal)
    #     rotation = 90 - angle_vectors_signed(proj_ref_side_normal, proj_z_axis, normal=projection_normal, deg=True)
    #     return rotation

    # @staticmethod
    # # bound the start_depth value to the minimum possible start_depth if the incliantion is larger than 90
    # def _bound_start_depth(start_depth, inclination, height):
    #     min_start_depth = height / (math.tan(math.radians(inclination)))
    #     return max(start_depth, min_start_depth)

    # @staticmethod
    # def _bound_length(ref_side, plane, beam_height, start_depth, inclination, length, height, frustum_difference):
    #     # bound the inserted lenhgth value to the maximum possible length for the beam based on the inclination
    #     max_length = (beam_height) / (math.sin(math.radians(inclination))) - start_depth

    #     # define the inclination angle regardless of the orientation start or end
    #     inclination_vector = Vector.cross(ref_side.yaxis, plane.normal)
    #     origin_inclination = math.degrees(ref_side.xaxis.angle(inclination_vector))
    #     if origin_inclination < 90.0:
    #         max_length = max_length - (frustum_difference + height / abs(math.tan(math.radians(inclination))))

    #     return min(max_length, length)

    # @staticmethod
    # def _bound_width(beam_width, angle, length, width, cone_angle, shape_radius, frustum_difference):
    #     # bound the inserted width value to the minumum and maximum possible width for the beam
    #     max_width = beam_width / math.sin(math.radians(angle)) - 2 * (
    #         frustum_difference + length * math.tan(math.radians(cone_angle))
    #     )
    #     min_width = 2 * shape_radius
    #     return min(max(width, min_width), max_width)

    @staticmethod
    def _create_trimming_planes_for_box(bottom_points, top_points, length_limited_top, length_limited_bottom):
        # Create the trimming planes to trim a box into a frustum trapezoid.
        if len(bottom_points) != len(top_points):
            raise ValueError("The number of bottom points must match the number of top points.")

        planes = []
        num_points = len(bottom_points)
        for i in range(num_points):
            # Get the bottom and top points for the current edge
            bottom1 = bottom_points[i]
            top1 = top_points[i]
            bottom2 = bottom_points[(i + 1) % num_points]
            # Define vectors for the plane
            x_axis = top1 - bottom1
            y_axis = bottom2 - bottom1
            # Compute the normal vector to the plane using the cross product
            normal = x_axis.cross(y_axis)
            # Create the plane
            plane = Plane(bottom1, -normal)
            planes.append(plane)

        return planes

    ########################################################################
    # Class Methods
    ########################################################################

    @classmethod
    def define_dovetail_tool(self, tool_angle, tool_diameter, tool_height):
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
        self._dovetail_tool_params = {
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
        :class:`~compas_timber.elements.FeatureApplicationError`
            If the cutting planes do not create a volume that itersects with beam geometry or any step fails.

        Returns
        -------
        :class:`~compas.geometry.Brep`
            The resulting geometry after processing

        """
        # type: (Brep, Beam) -> Brep

        # # get cutting plane from params and beam
        # try:
        #     cutting_plane = Plane.from_frame(self.frame_from_params_and_beam(beam))
        # except ValueError as e:
        #     raise FeatureApplicationError(
        #         None, geometry, "Failed to generate cutting plane from parameters and beam: {}".format(str(e))
        #     )

        # # get dovetail volume from params and beam
        # try:
        #     dovetail_volume = self.dovetail_volume_from_params_and_beam(beam)
        # except ValueError as e:
        #     raise FeatureApplicationError(
        #         None, geometry, "Failed to generate dovetail tenon volume from parameters and beam: {}".format(str(e))
        #     )

        # # fillet the edges of the dovetail volume based on the shape
        # if (
        #     self.shape not in [TenonShapeType.SQUARE, TenonShapeType.AUTOMATIC] and not self.length_limited_bottom
        # ):  # TODO: Remove AUTOMATIC once Brep Fillet is implemented
        #     edge_ideces = [4, 7] if self.length_limited_top else [5, 8]
        #     try:
        #         dovetail_volume.fillet(
        #             self.shape_radius, [dovetail_volume.edges[edge_ideces[0]], dovetail_volume.edges[edge_ideces[1]]]
        #         )  # TODO: NotImplementedError
        #     except Exception as e:
        #         raise FeatureApplicationError(
        #             dovetail_volume,
        #             geometry,
        #             "Failed to fillet the edges of the dovetail volume based on the shape: {}".format(str(e)),
        #         )

        # # trim geometry with cutting planes
        # try:
        #     geometry.trim(cutting_plane)
        # except Exception as e:
        #     raise FeatureApplicationError(
        #         cutting_plane, geometry, "Failed to trim geometry with cutting plane: {}".format(str(e))
        #     )

        # # add tenon volume to geometry
        # try:
        #     geometry += dovetail_volume
        # except Exception as e:
        #     raise FeatureApplicationError(
        #         dovetail_volume, geometry, "Failed to add tenon volume to geometry: {}".format(str(e))
        #     )

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
        cutting_plane = Frame(p_origin, ref_side.frame.xaxis, ref_side.frame.yaxis)

        # normal pointing towards xaxis so just need the delta
        horizontal_angle = math.radians(self.angle - 90)
        rot_a = Rotation.from_axis_and_angle(cutting_plane.zaxis, horizontal_angle, point=p_origin)

        # normal pointing towards xaxis so just need the delta
        vertical_angle = math.radians(self.inclination - 90)
        rot_b = Rotation.from_axis_and_angle(cutting_plane.yaxis, vertical_angle, point=p_origin)

        cutting_plane.transform(rot_a * rot_b)

        return cutting_plane

    def dovetail_cutting_planes_from_params_and_beam(self, beam):
        """Calculates the cutting planes for the dovetail tenon from the machining parameters in this instance and the given beam."""

        cutting_frame = beam.ref_side_frame(self.ref_side_index)
        offseted_cutting_frame = Frame(cutting_frame.point, -cutting_frame.xaxis, cutting_frame.yaxis)
        offseted_cutting_frame.point += cutting_frame.normal * self.height

        cutting_surface = PlanarSurface(
            xsize=beam.height / math.sin(math.radians(self.inclination)),
            ysize=beam.width / math.sin(math.radians(self.angle)),
            frame=cutting_frame,
        )
        # move the cutting surface to the center
        cutting_surface.translate(-cutting_frame.xaxis * self.start_y)

        start_depth = self.start_depth / math.sin(math.radians(self.inclination))
        # start_y = self.start_y / abs(math.cos(math.radians(self.angle)))
        start_y = self.start_y

        dx_top = self.width / 2 + self.length * abs(math.tan(math.radians(self.cone_angle)))
        dx_bottom = (beam.width / math.sin(math.radians(self.angle)) - self.width) / 2

        bottom_dovetail_points = [
            cutting_surface.point_at(start_y - dx_top, -start_depth),
            cutting_surface.point_at(start_y + dx_top, -start_depth),
            cutting_surface.point_at(start_y + dx_bottom / 2, -start_depth - self.length),
            cutting_surface.point_at(start_y - dx_bottom / 2, -start_depth - self.length),
        ]

        dovetail_edges = [
            Line(bottom_dovetail_points[0], bottom_dovetail_points[1]),  # Top line
            Line(bottom_dovetail_points[1], bottom_dovetail_points[2]),  # Right line
            Line(bottom_dovetail_points[2], bottom_dovetail_points[3]),  # Bottom line
            Line(bottom_dovetail_points[3], bottom_dovetail_points[0]),  # Left line
        ]

        trimming_frames = []
        for i, edge in enumerate(dovetail_edges):
            # Create the initial frame using the line's direction and the cutting frame's normal
            frame = Frame(edge.midpoint, edge.direction, cutting_frame.normal)

            if i != 0:
                # Determine the rotation direction: right and bottom are positive, top and left are negative
                # Apply the rotation based on the flank angle
                rotation = Rotation.from_axis_and_angle(-edge.direction, math.radians(self.flank_angle), frame.point)
                frame.transform(rotation)

            trimming_frames.append(frame)

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
        assert self.height is not None
        assert self.flank_angle is not None
        assert self.shape is not None
        assert self.shape_radius is not None
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

        # get the cutting planes for the dovetail tenon
        trimming_frames = self.dovetail_cutting_planes_from_params_and_beam(beam)

        # trim the box to create the dovetail volume
        for frame in trimming_frames:
            try:
                if self.orientation == OrientationType.START:
                    frame.xaxis = -frame.xaxis
                dovetail_volume.trim(frame)
            except Exception as e:
                raise FeatureApplicationError(
                    frame, dovetail_volume, "Failed to trim tenon volume with cutting plane: {}".format(str(e))
                )

        # rotate the dovetail volume based on the rotation value
        # if self.orientation == OrientationType.START:
        #     rot_axis = -cutting_frame.normal
        #     rot_angle = math.radians((90 - self.rotation) % 90)
        # else:
        #     rot_axis = cutting_frame.normal
        #     rot_angle = math.radians(self.rotation % 90)
        # rot_point = cutting_surface.point_at(self.start_y, start_depth)

        # rotation = Rotation.from_axis_and_angle(rot_axis, rot_angle, rot_point)
        # dovetail_volume.transform(rotation)

        return dovetail_volume


class DovetailMortiseParams(BTLxProcessParams):
    """A class to store the parameters of a Dovetail Mortise feature.

    Parameters
    ----------
    instance : :class:`~compas_timber._fabrication.DovetailMortise`
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

        result = super(DovetailMortiseParams, self).as_dict()
        result["StartX"] = "{:.{prec}f}".format(self._instance.start_x, prec=TOL.precision)
        result["StartY"] = "{:.{prec}f}".format(self._instance.start_y, prec=TOL.precision)
        result["StartDepth"] = "{:.{prec}f}".format(self._instance.start_depth, prec=TOL.precision)
        result["Angle"] = "{:.{prec}f}".format(self._instance.angle, prec=TOL.precision)
        result["Slope"] = "{:.{prec}f}".format(self._instance.slope, prec=TOL.precision)
        result["Inclination"] = "{:.{prec}f}".format(self._instance.inclination, prec=TOL.precision)
        result["LimitationTop"] = self._instance.limitation_top
        result["LengthLimitedBottom"] = "yes" if self._instance.length_limited_bottom else "no"
        result["Length"] = "{:.{prec}f}".format(self._instance.length, prec=TOL.precision)
        result["Width"] = "{:.{prec}f}".format(self._instance.width, prec=TOL.precision)
        result["Depth"] = "{:.{prec}f}".format(self._instance.depth, prec=TOL.precision)
        result["ConeAngle"] = "{:.{prec}f}".format(self._instance.cone_angle, prec=TOL.precision)
        result["UseFlankAngle"] = "yes" if self._instance.use_flank_angle else "no"
        result["FlankAngle"] = "{:.{prec}f}".format(self._instance.flank_angle, prec=TOL.precision)
        result["Shape"] = self._instance.shape
        result["ShapeRadius"] = "{:.{prec}f}".format(self._instance.shape_radius, prec=TOL.precision)
        return result
