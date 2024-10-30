import math

from compas.geometry import BrepTrimmingError
from compas.geometry import Frame
from compas.geometry import Line
from compas.geometry import Plane
from compas.geometry import Point
from compas.geometry import Rotation
from compas.geometry import Vector
from compas.geometry import angle_vectors_signed
from compas.geometry import distance_point_point
from compas.geometry import dot_vectors
from compas.geometry import intersection_line_plane
from compas.geometry import intersection_plane_plane_plane
from compas.geometry import is_point_behind_plane
from compas.tolerance import TOL

from compas_timber.elements import FeatureApplicationError

from .btlx_process import BTLxProcess
from .btlx_process import BTLxProcessParams
from .btlx_process import OrientationType


class DoubleCut(BTLxProcess):
    """Represents a Double Cut feature to be made on a beam.

    Parameters
    ----------
    orientation : int
        The orientation of the cut. Must be either OrientationType.START or OrientationType.END.
    start_x : float
        The start x-coordinate of the cut in parametric space of the reference side. -100000.0 < start_x < 100000.0.
    start_y : float
        The start y-coordinate of the cut in parametric space of the reference side. 0.0 < start_y < 50000.0.
    angle_1 : float
        The horizontal angle of the first cut. 0.1 < angle_1 < 179.9.
    inclination_1 : float
        The vertical angle of the first cut. 0.1 < inclination_1 < 179.9.
    angle_2 : float
        The horizontal angle of the second cut. 0.1 < angle_2 < 179.9.
    inclination_2 : float
        The vertical angle of the second cut. 0.1 < inclination_2 < 179.9.


    """

    PROCESS_NAME = "DoubleCut"  # type: ignore

    @property
    def __data__(self):
        data = super(DoubleCut, self).__data__
        data["orientation"] = self.orientation
        data["start_x"] = self.start_x
        data["start_y"] = self.start_y
        data["angle_1"] = self.angle_1
        data["inclination_1"] = self.inclination_1
        data["angle_2"] = self.angle_2
        data["inclination_2"] = self.inclination_2
        return data

    # fmt: off
    def __init__(
        self,
        orientation,
        start_x=0.0,
        start_y=50.0,
        angle_1=45.0,
        inclination_1=90.0,
        angle_2=90.0,
        inclination_2=90.0,
        **kwargs
    ):
        super(DoubleCut, self).__init__(**kwargs)
        self._orientation = None
        self._start_x = None
        self._start_y = None
        self._angle_1 = None
        self._inclination_1 = None
        self._angle_2 = None
        self._inclination_2 = None

        self.orientation = orientation
        self.start_x = start_x
        self.start_y = start_y
        self.angle_1 = angle_1
        self.inclination_1 = inclination_1
        self.angle_2 = angle_2
        self.inclination_2 = inclination_2

    ########################################################################
    # Properties
    ########################################################################

    @property
    def params_dict(self):
        return DoubleCutParams(self).as_dict()

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
    def angle_1(self):
        return self._angle_1

    @angle_1.setter
    def angle_1(self, angle_1):
        if angle_1 > 179.9 or angle_1 < 0.1:
            raise ValueError("Angle_1 must be between 0.1 and 179.9.")
        self._angle_1 = angle_1

    @property
    def inclination_1(self):
        return self._inclination_1

    @inclination_1.setter
    def inclination_1(self, inclination_1):
        if inclination_1 > 179.9 or inclination_1 < 0.1:
            raise ValueError("Inclination_1 must be between 0.1 and 179.9.")
        self._inclination_1 = inclination_1

    @property
    def angle_2(self):
        return self._angle_2

    @angle_2.setter
    def angle_2(self, angle_2):
        if angle_2 > 179.9 or angle_2 < 0.1:
            raise ValueError("Angle_2 must be between 0.1 and 179.9.")
        self._angle_2 = angle_2

    @property
    def inclination_2(self):
        return self._inclination_2

    @inclination_2.setter
    def inclination_2(self, inclination_2):
        if inclination_2 > 179.9 or inclination_2 < 0.1:
            raise ValueError("Inclination_2 must be between 0.1 and 179.9.")
        self._inclination_2 = inclination_2

    ########################################################################
    # Alternative constructors
    ########################################################################

    @classmethod
    def from_planes_and_beam(cls, planes, beam, ref_side_index=0):
        """Create a DoubleCut instance from two cutting planes and the beam they should cut.

        Parameters
        ----------
        planes : list of :class:`~compas.geometry.Plane` or :class:`~compas.geometry.Frame`
            The two cutting planes that define the double cut.
        beam : :class:`~compas_timber.elements.Beam`
            The beam that is cut by this instance.
        ref_side_index : int, optional
            The reference side index of the beam to be cut. Default is 0 (i.e. RS1).

        Returns
        -------
        :class:`~compas_timber.fabrication.DoubleCut`

        """
        # type: (list(Plane|Frame), Beam, int) -> DoubleCut
        if len(planes) != 2:
            raise ValueError("Exactly two cutting planes are required to create a DoubleCut instance.")

        # convert all frames to planes
        planes = [Plane.from_frame(plane) if isinstance(plane, Frame) else plane for plane in planes]

        # check if the normals are facing the same direction
        normals = [plane.normal for plane in planes]
        if dot_vectors(*normals) < 0:
            raise ValueError("The normals of the two planes are not aligned. Consider flipping one of them.")

        # define ref side and ref edge
        ref_side = beam.ref_sides[ref_side_index]
        ref_edge = Line.from_point_and_vector(ref_side.point, ref_side.xaxis)

        # calculate the average plane of the two planes
        point_start_xy = Point(*intersection_plane_plane_plane(planes[0], planes[1], Plane.from_frame(ref_side)))
        if point_start_xy is None:
            raise ValueError("Planes do not intersect with beam.")
        average_plane = Plane(point_start_xy, planes[0].normal + planes[1].normal)

        # calculate the orientation of the cut
        orientation = cls._calculate_orientation(ref_side, average_plane)

        # calculate the start_x and start_y of the cut
        start_x, start_y = cls._calculate_start_x_y(ref_edge, point_start_xy)

        # calculate the angles of the cuts
        angle_1, angle_2 = cls._calculate_angle(ref_side, planes, orientation)

        # calculate the inclinations of the cuts
        inclination_1, inclination_2 = cls._calculate_inclination(ref_side, planes)

        # flip the values if the first angle is larger than the second.
        if angle_1 > angle_2:
            angle_1, angle_2 = angle_2, angle_1
            inclination_1, inclination_2 = inclination_2, inclination_1

        return cls(
            orientation, start_x, start_y, angle_1, inclination_1, angle_2, inclination_2, ref_side_index=ref_side_index
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
    def _calculate_start_x_y(ref_edge, point_start_xy):
        # calculate the start_x and start_y of the cut
        intersection_plane = Plane(point_start_xy, ref_edge.direction)
        intersection_point = intersection_line_plane(ref_edge, intersection_plane)

        start_x = distance_point_point(intersection_point, ref_edge.start)
        start_y = distance_point_point(intersection_point, point_start_xy)
        if start_x is None or start_y is None:
            raise ValueError("Planes do not intersect with beam.")
        return start_x, start_y

    @staticmethod
    def _calculate_angle(ref_side, planes, orientation):
        # calculate the angles of the planes in the horizontal direction. (normal: ref_side.zaxis)
        if orientation == OrientationType.END:
            planes.reverse()

        angles = []
        for plane in planes:
            angle_vector = Vector.cross(ref_side.zaxis, plane.normal)
            angle = angle_vectors_signed(ref_side.xaxis, angle_vector, ref_side.zaxis, deg=True)
            angles.append(abs(angle))

        if sum(angle % 90 for angle in angles) > 180:
            raise ValueError(
                "The angles do not satisfy the required condition: one angle must be < 90 and another > 90."
            )
        return angles

    @staticmethod
    def _calculate_inclination(ref_side, planes):
        # calculate the inclinations of the planes in the vertical direction. (normal: ref_side.yaxis)
        inclinations = []
        for plane in planes:
            ref_vect = Vector.cross(ref_side.normal, plane.normal)
            inclination = angle_vectors_signed(ref_side.normal, plane.normal, ref_vect, deg=True)
            inclinations.append(inclination)
        return inclinations

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
        # get cutting planes from params and beam
        trim_volume = geometry.copy()
        try:
            cutting_planes = self.planes_from_params_and_beam(beam)
        except ValueError as e:
            raise FeatureApplicationError(
                None, geometry, "Failed to generate cutting planes from parameters and beam: {}".format(str(e))
            )

        for cutting_plane in cutting_planes:
            try:
                trim_volume.trim(cutting_plane)
            except Exception as e:
                raise BrepTrimmingError(
                    cutting_plane, geometry, "Failed to trim geometry with cutting planes: {}".format(str(e))
                )

        return geometry - trim_volume

    def planes_from_params_and_beam(self, beam):
        """Calculates the cutting planeS from the machining parameters in this instance and the given beam

        Parameters
        ----------
        beam : :class:`compas_timber.elements.Beam`
            The beam that is cut by this instance.

        Returns
        -------
        list of :class:`~compas.geometry.Plane`
            The cutting planes for this instance

        """
        # type: (Beam) -> list(Plane)
        assert self.angle_1 is not None
        assert self.inclination_1 is not None
        assert self.angle_2 is not None
        assert self.inclination_2 is not None

        # start with a plane aligned with the ref side but shifted to the start_x of the cut
        ref_side = beam.side_as_surface(self.ref_side_index)
        p_origin = ref_side.point_at(self.start_x, self.start_y)
        ref_frame = Frame(p_origin, ref_side.frame.xaxis, ref_side.frame.yaxis)

        if self.orientation == OrientationType.END:
            ref_frame.xaxis = -ref_frame.xaxis
            inclination_1 = 180-self.inclination_1
            inclination_2 = 180-self.inclination_2
        else:
            inclination_1 = self.inclination_1
            inclination_2 = self.inclination_2

        # normal pointing towards xaxis so just need the delta
        cutting_frame_1 = ref_frame.copy()
        rot_1_horiz = Rotation.from_axis_and_angle(ref_frame.zaxis, math.radians(self.angle_1), point=p_origin)
        rot_1_vert = Rotation.from_axis_and_angle(
            ref_frame.xaxis, math.radians(inclination_1), point=p_origin
        )
        cutting_frame_1.transform(rot_1_horiz * rot_1_vert)

        cutting_frame_2 = ref_frame.copy()
        rot_2_horiz = Rotation.from_axis_and_angle(ref_frame.zaxis, math.radians(self.angle_2), point=p_origin)
        rot_2_vert = Rotation.from_axis_and_angle(
            ref_frame.xaxis, math.radians(inclination_2), point=p_origin
        )
        cutting_frame_2.transform(rot_2_horiz * rot_2_vert)

        return [Plane.from_frame(cutting_frame) for cutting_frame in [cutting_frame_1, cutting_frame_2]]


class DoubleCutParams(BTLxProcessParams):
    """A class to store the parameters of a Double Cut feature.

    Parameters
    ----------
    instance : :class:`~compas_timber._fabrication.DoubleCut`
        The instance of the Double Cut feature.
    """

    def __init__(self, instance):
        # type: (DoubleCut) -> None
        super(DoubleCutParams, self).__init__(instance)

    def as_dict(self):
        """Returns the parameters of the Double Cut feature as a dictionary.

        Returns
        -------
        dict
            The parameters of the Double Cut feature as a dictionary.
        """
        # type: () -> OrderedDict
        result = super(DoubleCutParams, self).as_dict()
        result["Orientation"] = self._instance.orientation
        result["StartX"] = "{:.{prec}f}".format(self._instance.start_x, prec=TOL.precision)
        result["StartY"] = "{:.{prec}f}".format(self._instance.start_y, prec=TOL.precision)
        result["Angle1"] = "{:.{prec}f}".format(self._instance.angle_1, prec=TOL.precision)
        result["Inclination1"] = "{:.{prec}f}".format(self._instance.inclination_1, prec=TOL.precision)
        result["Angle2"] = "{:.{prec}f}".format(self._instance.angle_2, prec=TOL.precision)
        result["Inclination2"] = "{:.{prec}f}".format(self._instance.inclination_2, prec=TOL.precision)
        return result
