from compas.geometry import Box
from compas.geometry import Brep
from compas.geometry import Frame
from compas.tolerance import TOL

from compas_timber.errors import FeatureApplicationError

from .btlx import BTLxProcessing
from .btlx import BTLxProcessingParams
from .btlx import TenonShapeType


class HouseMortise(BTLxProcessing):
    """Represents a House Mortise feature to be made on a beam.

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
    mortise: :class:`~compas_timber.fabrication.Mortise` or :class:`~compas_timber.fabrication.DovetailMortise`
        The mortise instance that is made in conjunction with this house mortise.

    """

    PROCESSING_NAME = "HouseMortise"  # type: ignore

    @property
    def __data__(self):
        data = super(HouseMortise, self).__data__
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
        data["mortise"] = self.mortise
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
        mortise=None,
        **kwargs
    ):
        super(HouseMortise, self).__init__(**kwargs)
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
        self._mortise = None

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
        self.mortise = mortise

    ########################################################################
    # Properties
    ########################################################################

    @property
    def params_dict(self):
        return HouseMortiseParams(self).as_dict()

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

    @property
    def mortise(self):
        return self._mortise

    @mortise.setter
    def mortise(self, mortise):
        if mortise.__class__.__name__ not in ["Mortise", "DovetailMortise"]:
            raise ValueError("Mortise must be an instance of Mortise or DovetailMortise.")
        self._mortise = mortise
        self.add_subprocessing(mortise)

    ########################################################################
    # Alternative constructors
    ########################################################################

    @classmethod
    def from_mortise(cls, mortise, length, width, depth):
        """Create a House instance from a Mortise or DovetailMortise instance.

        Parameters
        ----------
        mortise : :class:`~compas_timber.fabrication.Mortise` or :class:`~compas_timber.fabrication.DovetailMortise`
            The mortise feature that is made in conjunction with this HouseMortise feature.
        length : float
            The length of the house mortise.
        width : float
            The width of the house mortise.
        height : float
            The height of the house mortise.

        Returns
        -------
        :class:`~compas_timber.fabrication.HouseMortise`
        """
        # type: (Mortise, float, float, float) -> HouseMortise
        return cls(
            mortise.start_x,
            mortise.start_y,
            mortise.start_depth,
            mortise.angle,
            mortise.slope,
            mortise.inclination,
            mortise.length_limited_top,
            mortise.length_limited_bottom,
            length,
            width,
            depth,
            TenonShapeType.SQUARE,
            mortise.shape_radius,
            mortise=mortise,
            ref_side_index=mortise.ref_side_index,
        )


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

        # get house mortise volume from params and beam
        try:
            house_mortise_volume = self.volume_from_params_and_beam(beam)
        except ValueError as e:
            raise FeatureApplicationError(
                None, geometry, "Failed to generate house mortise volume from parameters and beam: {}".format(str(e))
            )

        # fillet the edges of the house mortise volume based on the shape
        if self.shape is not TenonShapeType.SQUARE:
            try:
                edges = house_mortise_volume.edges[:8]
                house_mortise_volume.fillet(self.shape_radius, edges)
            except Exception as e:
                raise FeatureApplicationError(
                    house_mortise_volume,
                    geometry,
                    "Failed to fillet the edges of the house_mortise volume based on the shape: {}".format(str(e)),
                )

        # get mortise volume from mortise instance
        try:
            mortise_volume = self.mortise.volume_from_params_and_beam(beam)
        except ValueError as e:
            raise FeatureApplicationError(
                None, geometry, "Failed to generate mortise volume from mortise instance: {}".format(str(e))
            )

        # fillet the edges of the mortise volume based on the shape
        if self.mortise.shape is not TenonShapeType.SQUARE:
            try:
                edges = mortise_volume.edges[:8]
                mortise_volume.fillet(self.mortise.shape_radius, edges)
            except Exception as e:
                raise FeatureApplicationError(
                    mortise_volume,
                    geometry,
                    "Failed to fillet the edges of the mortise volume based on the shape: {}".format(str(e)),
                )

        # add mortise volume to house mortise volume
        try:
            house_mortise_volume += mortise_volume
        except Exception as e:
            raise FeatureApplicationError(
                mortise_volume, geometry, "Failed to add mortise volume to house_mortise volume: {}".format(str(e))
            )

        # remove tenon volume to geometry
        try:
            return geometry - house_mortise_volume
        except Exception as e:
            raise FeatureApplicationError(
                mortise_volume, geometry, "Failed to remove house mortise volume from geometry: {}".format(str(e))
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
        return cutting_frame

    def volume_from_params_and_beam(self, beam):
        """Calculates the house mortise volume from the machining parameters in this instance and the given beam.

        Parameters
        ----------
        beam : :class:`compas_timber.elements.Beam`
            The beam that is cut by this instance.

        Returns
        -------
        :class:`compas.geometry.Brep`
            The house mortise volume.

        """
        # type: (Beam) -> Brep
        assert self.length is not None
        assert self.width is not None
        assert self.depth is not None

        cutting_frame = self.frame_from_params_and_beam(beam)

        translation_vector = (-cutting_frame.normal * self.depth - cutting_frame.xaxis * self.length)
        cutting_frame.translate(translation_vector * 0.5)

        # get the tenon as a box
        house_mortise_box = Box(self.width, self.length, self.depth, cutting_frame)
        return Brep.from_box(house_mortise_box)


class HouseMortiseParams(BTLxProcessingParams):
    """A class to store the parameters of a HouseMortise feature.

    Parameters
    ----------
    instance : :class:`~compas_timber.fabrication.HouseMortise`
        The instance of the HouseMortise feature.
    """

    def __init__(self, instance):
        # type: (HouseMortise) -> None
        super(HouseMortiseParams, self).__init__(instance)

    def as_dict(self):
        """Returns the parameters of the HouseMortise feature as a dictionary.

        Returns
        -------
        dict
            The parameters of the HouseMortise as a dictionary.
        """
        # type: () -> OrderedDict

        result = super(HouseMortiseParams, self).as_dict()
        result["StartX"] = "{:.{prec}f}".format(self._instance.start_x, prec=TOL.precision)
        result["StartY"] = "{:.{prec}f}".format(self._instance.start_y, prec=TOL.precision)
        result["StartDepth"] = "{:.{prec}f}".format(self._instance.start_depth, prec=TOL.precision)
        result["Angle"] = "{:.{prec}f}".format(self._instance.angle, prec=TOL.precision)
        result["Slope"] = "{:.{prec}f}".format(self._instance.slope, prec=TOL.precision)
        # result["Inclination"] = "{:.{prec}f}".format(self._instance.inclination, prec=TOL.precision)
        #! Inclination is a parameter according to the documentation but gives an error in BTL Viewer.
        result["LengthLimitedTop"] = "yes" if self._instance.length_limited_top else "no"
        result["LengthLimitedBottom"] = "yes" if self._instance.length_limited_bottom else "no"
        result["Length"] = "{:.{prec}f}".format(self._instance.length, prec=TOL.precision)
        result["Width"] = "{:.{prec}f}".format(self._instance.width, prec=TOL.precision)
        result["Depth"] = "{:.{prec}f}".format(self._instance.depth, prec=TOL.precision)
        result["Shape"] = self._instance.shape
        result["ShapeRadius"] = "{:.{prec}f}".format(self._instance.shape_radius, prec=TOL.precision)
        return result
