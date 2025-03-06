import math
from collections import OrderedDict

from compas.geometry import Box
from compas.geometry import Brep
from compas.geometry import Frame
from compas.geometry import Line
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


class Tenon(BTLxProcessing):
    """Represents a Tenon feature to be made on a beam.

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
    shape : str
        The shape of the cut. Must be either 'automatic', 'square', 'round', 'rounded', or 'radius'.
    shape_radius : float
        The radius of the shape of the cut. 0.0 < shape_radius < 1000.0.
    chamfer : bool
        Whether the edges of the tenon are chamfered. True or False.

    """

    PROCESSING_NAME = "Tenon"  # type: ignore

    @property
    def __data__(self):
        data = super(Tenon, self).__data__
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
        data["shape"] = self.shape
        data["shape_radius"] = self.shape_radius
        data["chamfer"] = self.chamfer
        return data

    # fmt: off
    def __init__(
        self,
        orientation=OrientationType.START,
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
        shape=TenonShapeType.AUTOMATIC,
        shape_radius=20.0,
        chamfer=False,
        **kwargs
    ):
        super(Tenon, self).__init__(**kwargs)
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
        self._shape = None
        self._shape_radius = None
        self._chamfer = None

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
        self.shape = shape
        self.shape_radius = shape_radius
        self.chamfer = chamfer

    ########################################################################
    # Properties
    ########################################################################

    @property
    def params(self):
        return TenonParams(self)

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

    @property
    def chamfer(self):
        return self._chamfer

    @chamfer.setter
    def chamfer(self, chamfer):
        if not isinstance(chamfer, bool):
            raise ValueError("Chamfer must be either True or False.")
        self._chamfer = chamfer

    ########################################################################
    # Alternative constructors
    ########################################################################

    @classmethod
    def from_plane_and_beam(
        cls,
        plane,
        beam,
        start_y=0.0,
        start_depth=0.0,
        rotation=0.0,
        length_limited_top=True,
        length_limited_bottom=True,
        length=80.0,
        width=40.0,
        height=40.0,
        shape=TenonShapeType.AUTOMATIC,
        shape_radius=20.0,
        chamfer=False,
        ref_side_index=0,
    ):
        """Create a Tenon instance from a cutting plane and the beam it should cut. This could be the ref_side of the cross beam of a Joint and the main beam.

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
        length_limited_top : bool, optional
            Whether the top length of the tenon is limited. Default is True.
        length_limited_bottom : bool, optional
            Whether the bottom length of the tenon is limited. Default is True.
        length : float, optional
            The length of the tenon. Default is 80.0.
        width : float, optional
            The width of the bottom edge of the tenon. Default is 40.0.
        height : float, optional
            The height of the tenon. Related to the dovetail tool and can be defined using the `DovetailTenon.define_dovetail_tool()` method. Default is 28.0.
        shape : str, optional
            The shape of the tenon. Default is 'automatic'.
        shape_radius : float, optional
            The radius of the shape of the tenon. Related to the dovetail tool and can be defined using the `DovetailTenon.define_dovetail_tool()` method. Default is 20.0.
        chamfer : bool, optional
            Whether the edges of the tenon are chamfered. Default is False.
        ref_side_index : int, optional
            The reference side index of the beam to be cut. Default is 0 (i.e. RS1).

        Returns
        -------
        :class:`~compas_timber.fabrication.Tenon`

        """
        # type: (Plane|Frame, Beam, float, float, float, bool, bool, float, float, float, str, float, bool, int) -> Tenon
        if isinstance(plane, Frame):
            plane = Plane.from_frame(plane)

        # get ref_side & ref_edge
        ref_side = beam.ref_sides[ref_side_index]
        ref_edge = Line.from_point_and_vector(ref_side.point, ref_side.xaxis)

        # calculate orientation
        orientation = cls._calculate_orientation(ref_side, plane)

        # calculate angle
        angle = cls._calculate_angle(ref_side, plane)

        # calculate inclination
        inclination = cls._calculate_inclination(ref_side, plane, orientation, angle)

        # calculate rotation
        rotation = cls._calculate_rotation(orientation, rotation) # TODO: calculate and include the rotation of the beam and the plane

        # calculate start_y
        start_y = cls._calculate_start_y(beam, orientation, start_y, ref_side_index)

        # calculate start_depth
        start_depth += cls._calculate_start_depth(beam, inclination, length, ref_side_index)

        # override start_depth and length if not limited
        if not length_limited_top:
            start_depth = 0.0
        if not length_limited_bottom:
            beam_height = beam.get_dimensions_relative_to_side(ref_side_index)[1]
            length = beam_height / math.sin(math.radians(inclination)) - start_depth

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

        # calculate radius based on shape
        if shape == TenonShapeType.ROUND:
            shape_radius = width / 2

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
            shape,
            shape_radius,
            chamfer,
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
    def _calculate_start_y(beam, orientation, start_y, ref_side_index):
        # calculate the start_y of the cut based on the beam, orientation, start_y and ref_side_index
        if orientation == OrientationType.END:
            start_y = -start_y
        beam_width= beam.get_dimensions_relative_to_side(ref_side_index)[0]
        return start_y + beam_width / 2

    @staticmethod
    def _calculate_start_depth(beam, inclination, length, ref_side_index):
        # calculate the start_depth of the tenon from height of the beam and the projected length of the tenon
        proj_length = (length * math.sin(math.radians(inclination)))
        beam_height = beam.get_dimensions_relative_to_side(ref_side_index)[1]
        return (beam_height  - proj_length)/2

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
    def _calculate_rotation(orientation, rotation):
        # calculate rotation. Constrain the input (additional) rotation value to be between -90 and 90.
        rotation = (rotation % 90) if rotation >= 0 else -(abs(rotation) % 90)
        if orientation == OrientationType.END:
            rotation = -rotation
        return rotation + 90

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
        # trim geometry with cutting plane
        try:
            geometry.trim(cutting_plane)
        except Exception as e:
            raise FeatureApplicationError(
                cutting_plane, geometry, "Failed to trim geometry with cutting plane: {}".format(str(e))
            )
        # get tenon volume from params and beam
        try:
            tenon_volume = self.volume_from_params_and_beam(beam)
        except ValueError as e:
            raise FeatureApplicationError(
                None, geometry, "Failed to generate tenon volume from parameters and beam: {}".format(str(e))
            )
        # fillet the edges of the volume based on the shape
        if self.shape is not TenonShapeType.SQUARE:
            try:
                edges = tenon_volume.edges[:8]
                tenon_volume.fillet(self.shape_radius, edges)
            except Exception as e:
                raise FeatureApplicationError(
                    tenon_volume,
                    geometry,
                    "Failed to fillet the edges of the tenon volume based on the shape: {}".format(str(e)),
                )
        # remove any parts of the volume that exceed the beam geometry. Fails silently.
        for frame in beam.ref_sides[:4]:
            try:
                tenon_volume = tenon_volume.trimmed(frame)
            except Exception:
                pass # Fail silently since it won't be possible to trim the tenon if it doesn't exceed the beam geometry.
        # add tenon volume to geometry
        try:
            geometry += tenon_volume
        except Exception as e:
            raise FeatureApplicationError(
                tenon_volume, geometry, "Failed to add tenon volume to geometry: {}".format(str(e))
            )
        return geometry

    def frame_from_params_and_beam(self, beam):
        """
        Calculates the cutting plane from the machining parameters in this instance and the given beam.

        Parameters
        ----------
        beam : :class:`compas_timber.elements.Beam`
            The beam that is cut by this instance.

        Returns
        -------
        :class:`compas.geometry.Frame`
            The cutting Frame.
        """
        # type: (Beam) -> Frame
        assert self.orientation is not None
        assert self.start_x is not None
        assert self.start_y is not None
        assert self.angle is not None
        assert self.inclination is not None
        assert self.rotation is not None
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

    def volume_from_params_and_beam(self, beam):
        """Calculates the tenon volume from the machining parameters in this instance and the given beam.

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
        assert self.length is not None
        assert self.width is not None
        assert self.height is not None

        cutting_frame = self.frame_from_params_and_beam(beam)
        # translate the cutting frame to the center of the tenon
        translation_vector = (cutting_frame.normal * self.height - cutting_frame.yaxis * self.length)
        cutting_frame.translate(translation_vector * 0.5)

        # get the tenon as a box
        tenon_box = Box(self.width, self.length, self.height, cutting_frame)
        return Brep.from_box(tenon_box)


class TenonParams(BTLxProcessingParams):
    """A class to store the parameters of a Tenon feature.

    Parameters
    ----------
    instance : :class:`~compas_timber.fabrication.Tenon`
        The instance of the Tenon feature.
    """

    def __init__(self, instance):
        # type: (Tenon) -> None
        super(TenonParams, self).__init__(instance)

    def as_dict(self):
        """Returns the parameters of the Tenon feature as a dictionary.

        Returns
        -------
        dict
            The parameters of the Tenon as a dictionary.
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
        result["Shape"] = self._instance.shape
        result["ShapeRadius"] = "{:.{prec}f}".format(float(self._instance.shape_radius), prec=TOL.precision)
        result["Chamfer"] = "yes" if self._instance.chamfer else "no"
        return result
