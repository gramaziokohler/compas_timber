import math
from collections import OrderedDict

from compas.geometry import Frame
from compas.geometry import Line
from compas.geometry import Plane
from compas.geometry import Point
from compas.geometry import Rotation
from compas.geometry import Transformation
from compas.geometry import Vector
from compas.geometry import angle_vectors
from compas.geometry import dot_vectors
from compas.geometry import intersection_line_plane
from compas.geometry import intersection_plane_plane
from compas.tolerance import TOL

from compas_timber.errors import FeatureApplicationError
from compas_timber.utils import intersection_line_beam_param

from .btlx import BTLxProcessing
from .btlx import BTLxProcessingParams
from .btlx import OrientationType


class DoubleCut(BTLxProcessing):
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

    PROCESSING_NAME = "DoubleCut"  # type: ignore

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
        orientation = OrientationType.START,
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
    def params(self):
        return DoubleCutParams(self)

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

    @property
    def is_concave(self):
        return self.angle_1 < self.angle_2



    ########################################################################
    # Alternative constructors
    ########################################################################

    @classmethod
    def from_planes_and_beam(cls, planes, beam, ref_side_index=None):
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

        # get the intersection line of cutting planes, which is used to determine whether the planes cut a concave or convex shape
        ln = intersection_plane_plane(planes[0], planes[1])
        if not ln:
            raise ValueError("The two cutting planes are parallel consider using a JackRafterCut")

        line = Line(Point(*ln[0]), Point(*ln[1]))
        intersection_points, face_indices = intersection_line_beam_param(line, beam)
        if not intersection_points:
            raise ValueError("Planes do not intersect with beam.")
        if not ref_side_index:
            ref_side_index = face_indices[0]
            ref_side = beam.ref_sides[ref_side_index]
            point_start_xy = intersection_points[0]

        else:
            if ref_side_index not in face_indices:
                raise ValueError("Planes do not intersect with selected ref_side {}.".format(ref_side_index))
            else:
                ref_side = beam.ref_sides[ref_side_index]
                index = face_indices.index(ref_side_index)
                point_start_xy = intersection_points[index]

        planes = cls._reorder_planes(planes, line, ref_side)
        orientation = cls._calculate_orientation(beam, planes)
        start_x, start_y = cls._calculate_start_x_y(ref_side, point_start_xy)
        angle_1, angle_2 = cls._calculate_angle(ref_side, planes, orientation)
        inclination_1, inclination_2 = cls._calculate_inclination(ref_side, planes)

        # TODO: evaluate if the planes should be cached for use in geometry creation.
        return cls(orientation, start_x, start_y, angle_1, inclination_1, angle_2, inclination_2, ref_side_index=ref_side_index)


    @staticmethod
    def _reorder_planes(planes, intersection_line, ref_side):
        """this makes sure that plane[0] is the one that is closest to the ref_side yaxis"""
        lines = [Line.from_point_and_vector(plane.point, intersection_line.direction) for plane in planes]
        points = [Point(*intersection_line_plane(line, Plane.from_frame(ref_side))) for line in lines]
        dots = [dot_vectors(point, ref_side.yaxis) for point in points]
        if dots[0] > dots[1]:
            return [planes[1],planes[0]]
        else:
            return planes

    @classmethod
    def from_shapes_and_element(cls, plane_a, plane_b, element, **kwargs):
        """Construct a DoubleCut process from a two planes and an element.

        Parameters
        ----------
        plane_a : :class:`compas.geometry.Plane`
            The first cutting plane.
        plane_b : :class:`compas.geometry.Plane`
            The second cutting plane.
        element : :class:`compas_timber.elements.Element`
            The element to be cut.

        Returns
        -------
        :class:`compas_timber.fabrication.DoubleCut`
            The constructed double cut process.

        """
        return cls.from_planes_and_beam([plane_a, plane_b], element, **kwargs)

    @staticmethod
    def _calculate_orientation(beam, cutting_planes):
        # orientation is START if cutting plane normal points towards the start of the beam and END otherwise
        # essentially if the start is being cut or the end
        if dot_vectors(beam.centerline.direction, (cutting_planes[0].normal+cutting_planes[1].normal)) > 0:
            return OrientationType.START
        else:
            return OrientationType.END

    @staticmethod
    def _calculate_start_x_y(ref_side, point_start_xy):
        # calculate the start_x and start_y of the cut
        pt_xy = point_start_xy.transformed(Transformation.from_frame_to_frame(ref_side, Frame.worldXY()))
        return pt_xy.x, pt_xy.y

    @staticmethod
    def _calculate_angle(ref_side, planes, orientation):
        # calculate the angles of the planes in the horizontal direction. (normal: ref_side.zaxis)
        angles = []
        for plane in planes:
            angle_vector = Vector.cross(ref_side.zaxis, plane.normal)
            if dot_vectors(angle_vector, ref_side.yaxis)<0:
                angle_vector = -angle_vector    # make sure the angle vector is pointing in the same direction as the yaxis
            if orientation == OrientationType.START:
                angle = angle_vectors(ref_side.xaxis, angle_vector, deg=True)
            else:
                angle = angle_vectors(ref_side.xaxis, -angle_vector, deg=True)
            angles.append(angle)
        return angles

    @staticmethod
    def _calculate_inclination(ref_side, planes):
        # calculate the inclinations of the planes in the vertical direction. (normal: ref_side.yaxis)
        inclinations = []
        for plane in planes:
            inclination = angle_vectors(ref_side.normal, plane.normal, deg=True)
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
        :class:`~compas_timber.errors.FeatureApplicationError`
            If the cutting plane does not intersect with beam geometry.

        Returns
        -------
        :class:`~compas.geometry.Brep`
            The resulting geometry after processing

        """
        # type: (Brep, Beam) -> Brep
        # get cutting planes from params and beam

        try:
            cutting_planes = self.planes_from_params_and_beam(beam)
        except ValueError as e:
            raise FeatureApplicationError(
                None, geometry, "Failed to generate cutting planes from parameters and beam: {}".format(str(e))
            )
        if self.is_concave:
            trim_volume = geometry.copy()
            for cutting_plane in cutting_planes:
                trim_volume.trim(cutting_plane)
            return geometry - trim_volume
        else:
            for cutting_plane in cutting_planes:
                plane = Plane(cutting_plane.point, -cutting_plane.normal)
                geometry.trim(plane)
            return geometry


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


class DoubleCutParams(BTLxProcessingParams):
    """A class to store the parameters of a Double Cut feature.

    Parameters
    ----------
    instance : :class:`~compas_timber.fabrication.DoubleCut`
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
        result = OrderedDict()
        result["Orientation"] = self._instance.orientation
        result["StartX"] = "{:.{prec}f}".format(float(self._instance.start_x), prec=TOL.precision)
        result["StartY"] = "{:.{prec}f}".format(float(self._instance.start_y), prec=TOL.precision)
        result["Angle1"] = "{:.{prec}f}".format(float(self._instance.angle_1), prec=TOL.precision)
        result["Inclination1"] = "{:.{prec}f}".format(float(self._instance.inclination_1), prec=TOL.precision)
        result["Angle2"] = "{:.{prec}f}".format(float(self._instance.angle_2), prec=TOL.precision)
        result["Inclination2"] = "{:.{prec}f}".format(float(self._instance.inclination_2), prec=TOL.precision)
        return result
