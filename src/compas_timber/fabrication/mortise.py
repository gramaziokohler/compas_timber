import math
from collections import OrderedDict

from compas.geometry import Box
from compas.geometry import Brep
from compas.geometry import Frame
from compas.geometry import Line
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
from .btlx import OrientationType
from .btlx import TenonShapeType


class Mortise(BTLxProcessing):
    """Represents a Mortise feature to be made on a beam.

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
    length_limited_top : bool
        Whether the top length of the cut is limited. True or False.
    length_limited_bottom : bool
        Whether the bottom length of the cut is limited. True or False.
    length : float
        The length of the cut. 0.0 < length < 5000.0.
    width : float
        The width of the cut. 0.0 < width < 1000.0.
    depth : float
        The depth of the mortise. 0.0 < depth < 1000.0.
    shape : str
        The shape of the cut. Must be either 'automatic', 'square', 'round', 'rounded', or 'radius'.
    shape_radius : float
        The radius of the shape of the cut. 0.0 < shape_radius < 1000.0.

    """

    PROCESSING_NAME = "Mortise"  # type: ignore

    @property
    def __data__(self):
        data = super(Mortise, self).__data__
        data["start_x"] = self.start_x
        data["start_y"] = self.start_y
        data["start_depth"] = self.start_depth
        data["angle"] = self.angle
        data["slope"] = self.slope
        data["inclination"] = self.inclination
        data["length_limited_top"] = self.length_limited_top
        data["length_limited_bottom"] = self.length_limited_bottom
        data["length"] = self.length
        data["width"] = self.width
        data["depth"] = self.depth
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
        length_limited_top=True,
        length_limited_bottom=True,
        length=80.0,
        width=40.0,
        depth=28.0,
        shape=TenonShapeType.AUTOMATIC,
        shape_radius=20.0,
        **kwargs
    ):
        super(Mortise, self).__init__(**kwargs)
        self._start_x = None
        self._start_y = None
        self._start_depth = None
        self._angle = None
        self._slope = None
        self._inclination = None
        self._length_limited_top = None
        self._length_limited_bottom = None
        self._length = None
        self._width = None
        self._depth = None
        self._shape = None
        self._shape_radius = None

        self.start_x = start_x
        self.start_y = start_y
        self.start_depth = start_depth
        self.angle = angle
        self.slope = slope
        self.inclination = inclination
        self.length_limited_top = length_limited_top
        self.length_limited_bottom = length_limited_bottom
        self.length = length
        self.width = width
        self.depth = depth
        self.shape = shape
        self.shape_radius = shape_radius

    ########################################################################
    # Properties
    ########################################################################

    @property
    def params(self):
        return MortiseParams(self)

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
        length=80.0,
        width=40.0,
        depth=28.0,
        shape=TenonShapeType.AUTOMATIC,
        shape_radius=20.0,
        ref_side_index=0,
    ):
        """Create a Mortise instance from a cutting frame and the beam it should cut. This could be the ref_side of the main beam of a Joint and the cross beam.

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
            The depth of the mortise. The equivalent value of the Tenon BTLxProcessing is the height.
        shape : str, optional
            The shape of the mortise in regards to it's edges. Default is 'automatic'.
        shape_radius : float, optional
            The radius of the shape of the mortise. Default is 20.0.
        ref_side_index : int, optional
            The reference side index of the beam to be cut. Default is 0 (i.e. RS1).

        Returns
        -------
        :class:`~compas_timber.fabrication.Mortise`

        """
        # type: (Frame|Plane, Beam, float, float, float, float, float, str, float, int) -> Mortise

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
        length_limited_top = True
        length_limited_bottom = True

        return cls(
            start_x,
            start_y,
            start_depth,
            angle,
            slope,
            inclination,
            length_limited_top,
            length_limited_bottom,
            length,
            width,
            depth,
            shape,
            shape_radius,
            ref_side_index=ref_side_index,
        )

    @staticmethod
    def _calculate_orientation(ref_side, cutting_frame):
        # calculate the orientation of the beam by comparing the xaxis's direction of the ref_side and the plane.
        # Orientation is not set as a param for the BTLxMortise processing but its essential for the definition of the rest of the params.
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

        # get mortise volume from params and beam
        try:
            mortise_volume = self.volume_from_params_and_beam(beam)
        except ValueError as e:
            raise FeatureApplicationError(
                None, geometry, "Failed to generate mortise mortise volume from parameters and beam: {}".format(str(e))
            )

        # fillet the edges of the mortise volume based on the shape
        if self.shape is not TenonShapeType.SQUARE:
            try:
                edges = mortise_volume.edges[:8]
                mortise_volume.fillet(self.shape_radius, edges)
            except Exception as e:
                raise FeatureApplicationError(
                    mortise_volume,
                    geometry,
                    "Failed to fillet the edges of the tenon volume based on the shape: {}".format(str(e)),
                )

        # remove tenon volume to geometry
        try:
            return geometry - mortise_volume
        except Exception as e:
            raise FeatureApplicationError(
                mortise_volume, geometry, "Failed to remove mortise volume from geometry: {}".format(str(e))
            )

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
        angle_rotation = Rotation.from_axis_and_angle(
            cutting_frame.normal, math.radians(self.angle + 90), cutting_frame.point
        )
        cutting_frame.transform(angle_rotation)
        return cutting_frame

    def volume_from_params_and_beam(self, beam):
        """Calculates the mortise volume from the machining parameters in this instance and the given beam.

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
        assert self.length is not None
        assert self.width is not None
        assert self.depth is not None

        cutting_frame = self.frame_from_params_and_beam(beam)
        # translate the cutting frame to the center of the mortise
        translation_vector = (-cutting_frame.normal * self.depth - cutting_frame.yaxis * self.length)
        cutting_frame.translate(translation_vector * 0.5)

        # get the tenon as a box
        tenon_box = Box(self.width, self.length, self.depth, cutting_frame)
        return Brep.from_box(tenon_box)


class MortiseParams(BTLxProcessingParams):
    """A class to store the parameters of a Mortise feature.

    Parameters
    ----------
    instance : :class:`~compas_timber.fabrication.Mortise`
        The instance of the Mortise feature.
    """

    def __init__(self, instance):
        # type: (Mortise) -> None
        super(MortiseParams, self).__init__(instance)

    def as_dict(self):
        """Returns the parameters of the Mortise feature as a dictionary.

        Returns
        -------
        dict
            The parameters of the Mortise as a dictionary.
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
        result["LengthLimitedTop"] = "yes" if self._instance.length_limited_top else "no"
        result["LengthLimitedBottom"] = "yes" if self._instance.length_limited_bottom else "no"
        result["Length"] = "{:.{prec}f}".format(float(self._instance.length), prec=TOL.precision)
        result["Width"] = "{:.{prec}f}".format(float(self._instance.width), prec=TOL.precision)
        result["Depth"] = "{:.{prec}f}".format(float(self._instance.depth), prec=TOL.precision)
        result["Shape"] = self._instance.shape
        result["ShapeRadius"] = "{:.{prec}f}".format(float(self._instance.shape_radius), prec=TOL.precision)
        return result
