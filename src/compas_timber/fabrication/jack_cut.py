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
from compas.geometry import is_point_behind_plane
from compas.tolerance import TOL

from compas_timber.errors import FeatureApplicationError

from .btlx import BTLxProcessing
from .btlx import BTLxProcessingParams
from .btlx import OrientationType


class JackRafterCut(BTLxProcessing):
    """Represents a Jack Rafter Cut feature to be made on a beam.

    Parameters
    ----------
    orientation : int
        The orientation of the cut. Must be either OrientationType.START or OrientationType.END.
    start_x : float
        The start x-coordinate of the cut in parametric space of the reference side. -100000.0 < start_x < 100000.0.
    start_y : float
        The start y-coordinate of the cut in parametric space of the reference side. 0.0 < start_y < 50000.0.
    start_depth : float
        The start depth of the cut. 0.0 < start_depth < 50000.0.
    angle : float
        The horizontal angle of the cut. 0.1 < angle < 179.9.
    inclination : float
        The vertical angle of the cut. 0.1 < inclination < 179.9.

    """

    PROCESSING_NAME = "JackRafterCut"  # type: ignore

    @property
    def __data__(self):
        data = super(JackRafterCut, self).__data__
        data["orientation"] = self.orientation
        data["start_x"] = self.start_x
        data["start_y"] = self.start_y
        data["start_depth"] = self.start_depth
        data["angle"] = self.angle
        data["inclination"] = self.inclination
        return data

    def __init__(self, orientation=OrientationType.START, start_x=0.0, start_y=0.0, start_depth=0.0, angle=90.0, inclination=90.0, **kwargs):
        super(JackRafterCut, self).__init__(**kwargs)
        self._orientation = orientation
        self._start_x = None
        self._start_y = None
        self._start_depth = None
        self._angle = None
        self._inclination = None

        self.orientation = orientation
        self.start_x = start_x
        self.start_y = start_y
        self.start_depth = start_depth
        self.angle = angle
        self.inclination = inclination

    ########################################################################
    # Properties
    ########################################################################

    @property
    def params(self):
        return JackRafterCutParams(self)

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
        if start_y > 50000.0:
            raise ValueError("Start Y must be less than 50000.0.")
        self._start_y = start_y

    @property
    def start_depth(self):
        return self._start_depth

    @start_depth.setter
    def start_depth(self, start_depth):
        if start_depth > 50000.0:
            raise ValueError("Start Depth must be less than 50000.0.")
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

    ########################################################################
    # Alternative constructors
    ########################################################################

    @classmethod
    def from_plane_and_beam(cls, plane, beam, ref_side_index=0):
        """Create a JackRafterCut instance from a cutting plane and the beam it should cut.

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
        :class:`~compas_timber.fabrication.JackRafterCut`

        """
        # type: (Plane | Frame, Beam, int) -> JackRafterCut
        if isinstance(plane, Frame):
            plane = Plane.from_frame(plane)
        start_y = 0.0
        start_depth = 0.0
        ref_side = beam.ref_sides[ref_side_index]  # TODO: is this arbitrary?
        ref_edge = Line.from_point_and_vector(ref_side.point, ref_side.xaxis)
        orientation = cls._calculate_orientation(ref_side, plane)
        point_start_x = intersection_line_plane(ref_edge, plane)
        if point_start_x is None:
            raise ValueError("Plane does not intersect with beam.")

        start_x = distance_point_point(ref_edge.point, point_start_x)
        angle = cls._calculate_angle(ref_side, plane, orientation)
        inclination = cls._calculate_inclination(ref_side, plane, orientation)
        return cls(orientation, start_x, start_y, start_depth, angle, inclination, ref_side_index=ref_side_index)

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

    @staticmethod
    def _calculate_orientation(ref_side, cutting_plane):
        # orientation is START if cutting plane normal points towards the start of the beam and END otherwise
        # essentially if the start is being cut or the end
        if is_point_behind_plane(ref_side.point, cutting_plane):
            return OrientationType.END
        else:
            return OrientationType.START

    @staticmethod
    def _calculate_angle(ref_side, plane, orientation):
        # vector rotation direction of the plane's normal in the vertical direction
        angle_vector = Vector.cross(ref_side.zaxis, plane.normal)
        angle = angle_vectors_signed(ref_side.xaxis, angle_vector, ref_side.zaxis, deg=True)
        return 180 - abs(angle)

    @staticmethod
    def _calculate_inclination(ref_side, plane, orientation):
        # vector rotation direction of the plane's normal in the horizontal direction
        inclination_vector = Vector.cross(ref_side.zaxis, plane.normal)
        inclination = angle_vectors_signed(ref_side.zaxis, plane.normal, inclination_vector, deg=True)
        return 180 - abs(inclination)

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


class JackRafterCutParams(BTLxProcessingParams):
    """A class to store the parameters of a Jack Rafter Cut feature.

    Parameters
    ----------
    instance : :class:`~compas_timber.fabrication.JackRafterCut`
        The instance of the Jack Rafter Cut feature.
    """

    def __init__(self, instance):
        # type: (JackRafterCut) -> None
        super(JackRafterCutParams, self).__init__(instance)

    def as_dict(self):
        """Returns the parameters of the Jack Rafter Cut feature as a dictionary.

        Returns
        -------
        dict
            The parameters of the Jack Rafter Cut feature as a dictionary.
        """
        # type: () -> OrderedDict
        result = OrderedDict()
        result["Orientation"] = self._instance.orientation
        result["StartX"] = "{:.{prec}f}".format(float(self._instance.start_x), prec=TOL.precision)
        result["StartY"] = "{:.{prec}f}".format(float(self._instance.start_y), prec=TOL.precision)
        result["StartDepth"] = "{:.{prec}f}".format(float(self._instance.start_depth), prec=TOL.precision)
        result["Angle"] = "{:.{prec}f}".format(float(self._instance.angle), prec=TOL.precision)
        result["Inclination"] = "{:.{prec}f}".format(float(self._instance.inclination), prec=TOL.precision)
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
