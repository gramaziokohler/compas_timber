from collections import OrderedDict

from compas.geometry import Line
from compas.geometry import Plane
from compas.geometry import Point
from compas.geometry import angle_vectors
from compas.geometry import angle_vectors_signed
from compas.geometry import distance_point_point
from compas.geometry import intersection_segment_plane
from compas.tolerance import TOL

from .btlx import BTLxProcessing
from .btlx import BTLxProcessingParams
from .btlx import OrientationType


class Slot(BTLxProcessing):
    PROCESSING_NAME = "Slot"  # type: ignore

    # fmt: off
    def __init__(
        self,
        orientation=OrientationType.START,
        start_x=0.0,
        start_y=0.0,
        start_depth=0.0,
        angle=90.0,
        inclination=90.0,
        length=200.0,
        depth=10.0,
        thickness=10.0,
        angle_ref_point=90.0,
        angle_opp_point=90.0,
        add_angle_opp_point=0.0,
        machining_limits=None,
        **kwargs
    ):
        super(Slot, self).__init__(**kwargs)
        self._orientation = None
        self._start_x = None
        self._start_y = None
        self._start_depth = None
        self._angle = None
        self._inclination = None
        self._length = None
        self._depth = None
        self._thickness = None
        self._angle_ref_point = None
        self._angle_opp_point = None
        self._add_angle_opp_point = None
        self._machining_limits = None

        self.orientation = orientation
        self.start_x = start_x
        self.start_y = start_y
        self.start_depth = start_depth
        self.angle = angle
        self.inclination = inclination
        self.length = length
        self.depth = depth
        self.thickness = thickness
        self.angle_ref_point = angle_ref_point
        self.angle_opp_point = angle_opp_point
        self.add_angle_opp_point = add_angle_opp_point
        self.machining_limits = machining_limits

    ########################################################################
    # Properties
    ########################################################################

    @property
    def params(self):
        return SlotParams(self)

    @property
    def orientation(self):
        return self._orientation

    @orientation.setter
    def orientation(self, orientation):
        if orientation not in [OrientationType.START, OrientationType.END]:
            raise ValueError("Orientation must be either OrientationType.START or OrientationType.END. Got: {}".format(orientation))
        self._orientation = orientation

    @property
    def start_x(self):
        return self._start_x

    @start_x.setter
    def start_x(self, start_x):
        if start_x > 100000.0 or start_x < -100000.0:
            raise ValueError("Start X must be between -100000.0 and 100000. Got: {}".format(start_x))
        self._start_x = start_x

    @property
    def start_y(self):
        return self._start_y

    @start_y.setter
    def start_y(self, start_y):
        if start_y > 50000.0 or start_y < -50000.0:
            raise ValueError("Start Y must be between -50000.0 and 50000.0. Got: {}".format(start_y))
        self._start_y = start_y

    @property
    def start_depth(self):
        return self._start_depth

    @start_depth.setter
    def start_depth(self, start_depth):
        if start_depth > 50000.0 or start_depth < 0.0:
            raise ValueError("Start Depth must be less than 50000.0 and positive. Got: {}".format(start_depth))
        self._start_depth = start_depth

    @property
    def angle(self):
        return self._angle

    @angle.setter
    def angle(self, angle):
        if angle < -90.0 or angle > 90.0:
            raise ValueError("Angle must be between -90.0 and 90.0. Got: {}".format(angle))
        self._angle = angle

    @property
    def inclination(self):
        return self._inclination

    @inclination.setter
    def inclination(self, inclination):
        if inclination > 179.9 or inclination < 0.1:
            raise ValueError("Inclination must be between 0.1 and 179.9. Got: {}".format(inclination))
        self._inclination = inclination

    @property
    def length(self):
        return self._length

    @length.setter
    def length(self, length):
        if length < 0.0 or length > 100000.0:
            raise ValueError("Length must be between 0.0 and 100000.0. Got: {}".format(length))
        self._length = length

    @property
    def depth(self):
        return self._depth

    @depth.setter
    def depth(self, depth):
        if depth < 0.0 or depth > 50000.0:
            raise ValueError("Depth must be between 0.0 and 50000.0. Got: {}".format(depth))
        self._depth = depth

    @property
    def thickness(self):
        return self._thickness

    @thickness.setter
    def thickness(self, thickness):
        if thickness < 0.0 or thickness > 50000.0:
            raise ValueError("Thickness must be between 0.0 and 50000.0. Got: {}".format(thickness))
        self._thickness = thickness

    @property
    def angle_ref_point(self):
        return self._angle_ref_point

    @angle_ref_point.setter
    def angle_ref_point(self, angle_ref_point):
        if angle_ref_point < 0.1 or angle_ref_point > 179.9:
            raise ValueError("Angle Ref Point must be between 0.1 and 179.9. Got: {}".format(angle_ref_point))
        self._angle_ref_point = angle_ref_point

    @property
    def angle_opp_point(self):
        return self._angle_opp_point

    @angle_opp_point.setter
    def angle_opp_point(self, angle_opp_point):
        if angle_opp_point < 0.1 or angle_opp_point > 179.9:
            raise ValueError("Angle Opp Point must be between 0.1 and 179.9. Got: {}".format(angle_opp_point))
        self._angle_opp_point = angle_opp_point

    @property
    def add_angle_opp_point(self):
        return self._add_angle_opp_point

    @add_angle_opp_point.setter
    def add_angle_opp_point(self, add_angle_opp_point):
        if add_angle_opp_point < -179.9 or add_angle_opp_point > 179.9:
            raise ValueError("Add Angle Opp Point must be between -179.9 and 179.9. Got: {}".format(add_angle_opp_point))
        self._add_angle_opp_point = add_angle_opp_point

    @property
    def machining_limits(self):
        return self._machining_limits

    @machining_limits.setter
    def machining_limits(self, machining_limits):
        # TODO: figure this one out, a generic class?
        self._machining_limits = machining_limits

    ########################################################################
    # Alternative constructors
    ########################################################################

    @classmethod
    def from_plane_and_beam(cls, plane, beam, depth, thickness):
        """Makes a full horizontal or vertical slot accross one of the end faces of the beam.

        Therefore, the provided plane must cut the beam at one of its ends, and it must intersect with exactly two parallel small edges of the side face.
        The length of the slot is equal to the full length accross.

        Parameters
        ----------
        plane : :class:`~compas.geometry.Plane`
            The plane which specifies the orientation and depth of the Slot.
        beam : :class:`~compas_timber.elements.Beam`
            The beam that is cut by this instance.

        Returns
        -------
        :class:`~compas_timber.fabrication.Slot`
            The constructed Slot feature.

        """
        # this only really matters if `start_depth` != 0. which we're not dealing with quite yet
        orientation = OrientationType.START

        # angle of rotation is bound to between -90 and 90. the rotation point and axis is determined by start_x and start_y

        # 1. find out of the plane cuts horizontally or vertically
        #   check intersections with the small edges. There should be two intersections with parallel small edges
        #   start_x and start_y are depending on this classification
        # 2. find the angle

        # find relevant end surface
        distance_from_start = distance_point_point(plane.point, beam.centerline_start)
        distance_from_end = distance_point_point(plane.point, beam.centerline_end)
        if distance_from_start < distance_from_end:
            ref_side_index = 4
        else:
            ref_side_index = 5

        ref_side = beam.side_as_surface(ref_side_index)
        # find 2 points of intersection
        # TODO: shove this into some function. what are we? savages?
        small_edge_bottom = Line(ref_side.point_at(0, 0), ref_side.point_at(beam.width, 0))
        small_edge_top = Line(ref_side.point_at(0, beam.height), ref_side.point_at(beam.width, beam.height))
        small_edge_left = Line(ref_side.point_at(0, 0), ref_side.point_at(0, beam.height))
        small_edge_right = Line(ref_side.point_at(beam.width, 0), ref_side.point_at(beam.width, beam.height))

        slot_plane = Plane.from_frame(plane)
        intersection_bottom = intersection_segment_plane(small_edge_bottom, slot_plane)
        intersection_top = intersection_segment_plane(small_edge_top, slot_plane)
        intersection_left = intersection_segment_plane(small_edge_left, slot_plane)
        intersection_right = intersection_segment_plane(small_edge_right, slot_plane)

        # find inclination angle
        # look at the jack rafter cut. but idea might be to cross normal and one of the
        # axes of the ref frame to get the yaw angle between ref_side.xaxis and the horizontal direction of the plane
        yaw_vector = plane.normal.cross(ref_side.yaxis)
        inclination = angle_vectors_signed(yaw_vector, ref_side.xaxis, -ref_side.yaxis, deg=True)

        roll_vector = plane.normal.cross(ref_side.zaxis)
        angle = angle_vectors_signed(ref_side.xaxis, roll_vector, ref_side.zaxis, deg=True)
        print("calculated non-signed angle: {}".format(angle_vectors(ref_side.xaxis, roll_vector, deg=True)))
        print("calculated signed angle: {}".format(angle))

        # adjust 0-360 to -90 to 90
        if angle > 90:
            angle = (180 - angle) * -1
        elif angle < -90:
            angle = (180 + angle) * -1
        print("adjusted angle: {}".format(angle))

        ref_frame = ref_side.frame
        if intersection_bottom and intersection_top:
            length = distance_point_point(intersection_bottom, intersection_top)
            if angle < 0:
                slot_start_point = Point(*intersection_top)
            else:
                slot_start_point = Point(*intersection_bottom)
        elif intersection_left and intersection_right:
            length = distance_point_point(intersection_left, intersection_right)
            slot_start_point = Point(*intersection_left)
        else:
            raise ValueError("The slot plane must fully cross one of the beam's end faces")

        local_intersection = ref_frame.to_local_coordinates(Point(*slot_start_point))
        start_x = local_intersection.x
        start_y = local_intersection.y

        return cls(
            orientation,
            start_x=start_x,
            start_y=start_y,
            angle=angle,
            inclination=inclination,
            length=length,
            depth=depth,
            thickness=thickness,
            ref_side_index=ref_side_index,
        )

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
        return geometry.copy()


class SlotParams(BTLxProcessingParams):
    """A class to store the parameters of a Slot feature.

    Parameters
    ----------
    instance : :class:`~compas_timber.fabrication.Slot`
        The instance of the Slot feature.

    """

    def __init__(self, instance):
        # type: (Slot) -> None
        super(SlotParams, self).__init__(instance)

    def as_dict(self):
        """Returns the parameters of the Slot feature as a dictionary.

        Returns
        -------
        dict
            The parameters of the Slot feature as a dictionary.
        """
        # type: () -> OrderedDict
        result = OrderedDict()
        result["Orientation"] = self._instance.orientation
        result["StartX"] = "{:.{prec}f}".format(float(self._instance.start_x), prec=TOL.precision)
        result["StartY"] = "{:.{prec}f}".format(float(self._instance.start_y), prec=TOL.precision)
        result["StartDepth"] = "{:.{prec}f}".format(float(self._instance.start_depth), prec=TOL.precision)
        result["Angle"] = "{:.{prec}f}".format(float(self._instance.angle), prec=TOL.precision)
        result["Inclination"] = "{:.{prec}f}".format(float(self._instance.inclination), prec=TOL.precision)
        result["Length"] = "{:.{prec}f}".format(float(self._instance.length), prec=TOL.precision)
        result["Depth"] = "{:.{prec}f}".format(float(self._instance.depth), prec=TOL.precision)
        result["Thickness"] = "{:.{prec}f}".format(float(self._instance.thickness), prec=TOL.precision)
        result["AngleRefPoint"] = "{:.{prec}f}".format(float(self._instance.angle_ref_point), prec=TOL.precision)
        result["AngleOppPoint"] = "{:.{prec}f}".format(float(self._instance.angle_opp_point), prec=TOL.precision)
        result["AddAngleOppPoint"] = "{:.{prec}f}".format(float(self._instance.add_angle_opp_point), prec=TOL.precision)
        result["MachiningLimits"] = {"FaceLimitedStart": "no", "FaceLimitedEnd": "no"}
        return result
