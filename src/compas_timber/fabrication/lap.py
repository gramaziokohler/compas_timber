import math

from compas.datastructures import Mesh
from compas.geometry import Brep
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
from compas.tolerance import Tolerance

from compas_timber.errors import FeatureApplicationError

from .btlx import BTLxProcessing
from .btlx import BTLxProcessingParams
from .btlx import MachiningLimits
from .btlx import OrientationType


class Lap(BTLxProcessing):
    """Represents a Lap feature to be made on a beam.

    Parameters
    ----------
    orientation : int
        The orientation of the cut. Must be either OrientationType.START or OrientationType.END.
    start_x : float
        The start x-coordinate of the cut in parametric space of the reference side. -100000.0 < start_x < 100000.0.
    start_y : float
        The start y-coordinate of the cut in parametric space of the reference side. -50000.0 < start_y < 50000.0.
    angle : float
        The horizontal angle of the cut. 0.1 < angle < 179.9.
    inclination : float
        The vertical angle of the cut. 0.1 < inclination < 179.9.
    slope : float
        The slope of the cut. -89.9 < slope < 89.9.
    length : float
        The length of the cut. 0.0 < length < 100000.0.
    width : float
        The width of the cut. 0.0 < width < 50000.0.
    depth : float
        The depth of the cut. -50000.0 < depth < 50000.0.
    lead_angle_parallel : bool
        The lead angle is parallel to the beam axis.
    lead_angle : float
        The lead angle of the cut. 0.1 < lead_angle < 179.9.
    lead_inclination_parallel : bool
        The lead inclination is parallel to the beam axis.
    lead_inclination : float
        The lead inclination of the cut. 0.1 < lead_inclination < 179.9.
    machining_limits : dict, optional
        The machining limits for the cut. Default is None

    """

    PROCESSING_NAME = "Lap"  # type: ignore

    @property
    def __data__(self):
        data = super(Lap, self).__data__
        data["orientation"] = self.orientation
        data["start_x"] = self.start_x
        data["start_y"] = self.start_y
        data["angle"] = self.angle
        data["inclination"] = self.inclination
        data["slope"] = self.slope
        data["length"] = self.length
        data["width"] = self.width
        data["depth"] = self.depth
        data["lead_angle_parallel"] = self.lead_angle_parallel
        data["lead_angle"] = self.lead_angle
        data["lead_inclination_parallel"] = self.lead_inclination_parallel
        data["lead_inclination"] = self.lead_inclination
        data["machining_limits"] = self.machining_limits
        return data

    # fmt: off
    def __init__(
        self,
        orientation,
        start_x=0.0,
        start_y=0.0,
        angle=90.0,
        inclination=90.0,
        slope=0.0,
        length=200.0,
        width=50.0,
        depth=40.0,
        lead_angle_parallel=True,
        lead_angle=90.0,
        lead_inclination_parallel=True,
        lead_inclination=90.0,
        machining_limits=None,
        **kwargs
    ):
        super(Lap, self).__init__(**kwargs)
        self._orientation = None
        self._start_x = None
        self._start_y = None
        self._angle = None
        self._inclination = None
        self._slope = None
        self._length = None
        self._width = None
        self._depth = None
        self._lead_angle_parallel = None
        self._lead_angle = None
        self._lead_inclination_parallel = None
        self._lead_inclination = None
        self._machining_limits = None

        self.orientation = orientation
        self.start_x = start_x
        self.start_y = start_y
        self.angle = angle
        self.inclination = inclination
        self.slope = slope
        self.length = length
        self.width = width
        self.depth = depth
        self.lead_angle_parallel = lead_angle_parallel
        self.lead_angle = lead_angle
        self.lead_inclination_parallel = lead_inclination_parallel
        self.lead_inclination = lead_inclination
        self.machining_limits = machining_limits

    ########################################################################
    # Properties
    ########################################################################

    @property
    def params_dict(self):
        return LapParams(self).as_dict()

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
        if -50000.0 > start_y > 50000.0:
            raise ValueError("Start Y must be between -50000.0 and 50000.")
        self._start_y = start_y

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
    def slope(self):
        return self._slope

    @slope.setter
    def slope(self, slope):
        if slope > 89.9 or slope < -89.9:
            raise ValueError("Slope must be between -89.9 and 89.9.")
        self._slope = slope

    @property
    def length(self):
        return self._length

    @length.setter
    def length(self, length):
        if not 0.0 < length < 100000.0:
            raise ValueError("Length must be between 0.0 and 100000.0")
        self._length = length

    @property
    def width(self):
        return self._width

    @width.setter
    def width(self, width):
        if width > 50000.0 or width < 0.0:
            raise ValueError("Width must be between 0.0 and 50000.")
        self._width = width

    @property
    def depth(self):
        return self._depth

    @depth.setter
    def depth(self, depth):
        if depth > 50000.0 or depth < -50000.0:
            raise ValueError("Depth must be between -50000 and 50000.")
        self._depth = depth

    @property
    def lead_angle_parallel(self):
        return self._lead_angle_parallel

    @lead_angle_parallel.setter
    def lead_angle_parallel(self, lead_angle_parallel):
        if not isinstance(lead_angle_parallel, bool):
            raise ValueError("Lead angle parallel must be a boolean.")
        self._lead_angle_parallel = lead_angle_parallel

    @property
    def lead_angle(self):
        return self._lead_angle

    @lead_angle.setter
    def lead_angle(self, lead_angle):
        if lead_angle > 179.9 or lead_angle < 0.1:
            raise ValueError("Lead angle must be between 0.1 and 179.9.")
        self._lead_angle = lead_angle

    @property
    def lead_inclination_parallel(self):
        return self._lead_inclination_parallel

    @lead_inclination_parallel.setter
    def lead_inclination_parallel(self, lead_inclination_parallel):
        if not isinstance(lead_inclination_parallel, bool):
            raise ValueError("Lead inclination parallel must be a boolean.")
        self._lead_inclination_parallel = lead_inclination_parallel

    @property
    def lead_inclination(self):
        return self._lead_inclination

    @lead_inclination.setter
    def lead_inclination(self, lead_inclination):
        if lead_inclination > 179.9 or lead_inclination < 0.1:
            raise ValueError("Lead inclination must be between 0.1 and 179.9.")
        self._lead_inclination = lead_inclination

    @property
    def machining_limits(self):
        return self._machining_limits

    @machining_limits.setter
    def machining_limits(self, machining_limits):
        if not isinstance(machining_limits, dict):
            raise ValueError("Machining limits must be a dictionary.")
        for key, value in machining_limits.items():
            if key not in MachiningLimits.EXPECTED_KEYS:
                raise ValueError("The key must be one of the following: ", {self.EXPECTED_KEYS})
            if not isinstance(value, bool):
                raise ValueError("The values must be a boolean.")
        self._machining_limits = machining_limits


    ########################################################################
    # Alternative constructors
    ########################################################################

    @classmethod
    def from_plane_and_beam(cls, plane, beam, length, depth, is_pocket=False, ref_side_index=0):
        """Create a Lap instance from a plane and a beam. The lap is defined by the plane given and a plane parallel to that at a distance defined by the length and a given depth.
        This method is used to create pocket cuts.

        Parameters
        ----------
        plane : :class:`~compas.geometry.Plane`
            The plane that defines the lap.
        beam : :class:`~compas_timber.elements.Beam`
            The beam that the Lap instance is applied to.
        length : float
            The length of the lap.
        depth : float
            The depth of the lap.
        is_pocket : bool, optional
            If True, the lap is a pocket cut. Default is False
        ref_side_index : int, optional
            The reference side index of the main_beam to be cut. Default is 0 (i.e. RS1).

        Returns
        -------
        :class:`~compas_timber.fabrication.Lap`

        """
        # type: (Plane, Beam, float, float, int) -> Lap
        if isinstance(plane, Frame):
            plane = Plane.from_frame(plane)

        # create an offset plane at the depth of the lap
        offset_plane = Plane(plane.point - plane.normal * length, -plane.normal)
        planes = [plane, offset_plane]

        # get ref_side, and ref_edge from the beam
        ref_side = beam.ref_sides[ref_side_index]
        ref_side_surface = beam.side_as_surface(ref_side_index)
        ref_edge = Line.from_point_and_vector(ref_side.point, ref_side.xaxis)

        # sort the planes based on the angle between their normals and the reference side's normal
        planes.sort(key=lambda plane: abs(angle_vectors_signed(ref_side.normal, plane.normal, ref_side.yaxis, deg=True)))

        # calculate the orientation of the lap
        orientation = cls._calculate_orientation(ref_side, planes[0])

        # calculate the start_x of the lap
        start_x = cls._calculate_start_x(ref_side, ref_edge, planes, orientation, depth, is_pocket)

        # calculate the angle of the lap
        angle = cls._calculate_angle(ref_side, planes[0])

        # calculate the inclination of the lap
        inclination = cls._calculate_inclination(ref_side, planes[0], is_pocket)

        # calculate the slope of the lap
        slope = 0.0 # TODO: implement slope calculation

        # calculate length
        length = cls._calculate_length(planes, ref_side, ref_edge, depth, angle)

        # define the width of the lap
        width = ref_side_surface.ysize

        # define machining limits
        machining_limits = MachiningLimits()
        machining_limits.face_limited_top = False
        machining_limits.face_limited_back = False
        machining_limits.face_limited_front = False

        return cls(orientation=orientation,
                   start_x=start_x,
                   angle=angle,
                   inclination=inclination,
                   slope=slope,
                   length=length,
                   width=width,
                   depth=depth,
                   machining_limits=machining_limits.limits,
                   ref_side_index=ref_side_index)

    @staticmethod
    def _calculate_orientation(ref_side, plane):
        # orientation is START if cutting plane normal points towards the start of the beam and END otherwise
        if is_point_behind_plane(ref_side.point, plane):
            return OrientationType.END
        else:
            return OrientationType.START

    @staticmethod
    def _calculate_start_x(ref_side, ref_edge, planes, orientation, depth, is_pocket):
        # calculate the start x distance based on intersections of planes with reference edges.
        # if the lap is meant for a pocket one must consider the offseted reference edge
        if is_pocket:
            offseted_ref_edge = ref_edge.translated(-ref_side.normal * depth)
            ref_edges = [offseted_ref_edge, ref_edge]
        else:
            ref_edges = [ref_edge]
        x_distances = []
        for edge, plane in zip(ref_edges, planes):
            if intersection_line_plane(edge, plane) is None:
                raise ValueError("One of the planes does not intersect with the beam.")
            intersection_point = Point(*intersection_line_plane(edge, plane))
            distance_vector = (Vector.from_start_end(edge.start, intersection_point))
            x_distances.append(dot_vectors(distance_vector, edge.direction))
        return max(x_distances) if orientation == OrientationType.END else min(x_distances)

    @staticmethod
    def _calculate_angle(ref_side, plane):
        # vector rotation direction of the plane's normal in the vertical direction
        angle_vector = Vector.cross(ref_side.normal, plane.normal)
        return abs(angle_vectors_signed(ref_side.xaxis, angle_vector, ref_side.normal, deg=True))

    @staticmethod
    def _calculate_inclination(ref_side, plane, is_pocket):
        # vector rotation direction of the plane's normal in the vertical direction
        if is_pocket:
            return 90.0
        else:
            return abs(angle_vectors_signed(ref_side.normal, plane.normal, ref_side.normal, deg=True))

    @staticmethod
    def _calculate_length(planes, ref_side, ref_edge, depth, angle):
        # calculate the length of the lap based on the intersection points of the planes with the reference edge
        # the length is the perpendicular distance between the two planes
        vect = ref_side.yaxis.cross(planes[0].normal)
        intersection_pts = [Point(*intersection_line_plane(ref_edge, plane)) for plane in planes]
        dist = distance_point_point(*intersection_pts)
        # calculate the compansation distance based on the angle of intersection
        compensation_angle = angle_vectors_signed(vect, ref_side.xaxis, ref_side.normal)
        dist += depth / abs(math.tan(compensation_angle))
        # calculate the perpendicular distance between the two planes
        length = math.sin(math.radians(angle))*dist
        return length


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
        lap_volume = self.volume_from_params_and_beam(beam)

        # convert mesh to brep
        try:
            lap_volume = Brep.from_mesh(lap_volume)
        except Exception:
            raise FeatureApplicationError(
                lap_volume,
                geometry,
                "Could not convert the lap volume to a Brep.",
            )

        # subtract the lap volume from the beam geometry
        try:
            return geometry - lap_volume
        except IndexError:
            raise FeatureApplicationError(
                lap_volume,
                geometry,
                "The lap volume does not intersect with the beam geometry.",
            )

    def planes_from_params_and_beam(self, beam):
        """Calculates the planes that create the lap from the machining parameters in this instance and the given beam

        Parameters
        ----------
        beam : :class:`compas_timber.elements.Beam`
            The beam that is cut by this instance.

        Returns
        -------
        list of :class:`compas.geometry.Plane`
            The planes of the cut as a list.

        """
        # type: (Beam) -> List[Plane]
        assert self.orientation is not None
        assert self.start_x is not None
        assert self.start_y is not None
        assert self.angle is not None
        assert self.inclination is not None
        assert self.slope is not None
        assert self.length is not None
        assert self.width is not None
        assert self.depth is not None
        assert self.machining_limits is not None

        ref_surface = beam.side_as_surface(self.ref_side_index)
        p_origin = ref_surface.point_at(self.start_x, self.start_y)
        start_frame = Frame(p_origin, ref_surface.frame.xaxis, ref_surface.frame.yaxis)

        # define angle rotation matrix
        angle_angle = self.angle if self.orientation == OrientationType.END else 180-self.angle
        angle_rot = Rotation.from_axis_and_angle(start_frame.zaxis, math.radians(angle_angle), point=p_origin)
        # define inclination rotation matrix
        inclination_axis = start_frame.xaxis if self.orientation == OrientationType.END else -start_frame.xaxis
        inclination_rot = Rotation.from_axis_and_angle(inclination_axis, math.radians(self.inclination), point=p_origin)
        # define slope rotation matrix
        slope_axis = -start_frame.zaxis
        slope_rot = Rotation.from_axis_and_angle(slope_axis, math.radians(self.slope), point=p_origin)

        # get start_face and opp_face (two sides of the cut)
        start_frame.transform(angle_rot*inclination_rot*slope_rot)
        end_frame = start_frame.translated(-start_frame.zaxis * self.length)
        end_frame.yaxis = -end_frame.yaxis

        # get top_face and bottom_face
        lead_inclination_axis = -start_frame.xaxis if self.orientation == OrientationType.END else start_frame.xaxis
        lead_inclination_rot = Rotation.from_axis_and_angle(lead_inclination_axis, math.radians(self.lead_inclination), point=p_origin)
        top_frame = start_frame.transformed(lead_inclination_rot)
        bottom_frame = top_frame.translated(-top_frame.zaxis * self.depth)
        bottom_frame.xaxis = -bottom_frame.xaxis

        # get front_face and back_face #TODO: is this correct?
        front_frame = start_frame.rotated(math.radians(self.lead_angle), start_frame.xaxis, point=start_frame.point)
        back_frame = front_frame.translated(-front_frame.zaxis * self.width)
        back_frame.xaxis = -back_frame.xaxis

        frames = [start_frame, end_frame, top_frame, bottom_frame, front_frame, back_frame]

        # replace frames according to machining limits
        frames = self._update_frames_based_on_machining_limits(frames, beam)

        return [Plane.from_frame(frame) for frame in frames]

    def volume_from_params_and_beam(self, beam):
        """
        Calculates the trimming volume from the machining parameters in this instance and the given beam,
        ensuring correct face orientation.

        Parameters
        ----------
        beam : :class:`compas_timber.elements.Beam`
            The beam that is cut by this instance.

        Returns
        -------
        :class:`compas.geometry.Mesh`
            The correctly oriented trimming volume of the cut.
        """
        # Get cutting frames

        start_plane, end_plane, top_plane, bottom_plane, front_plane, back_plane = self.planes_from_params_and_beam(beam)

        # Calculate vertices using plane-plane-plane intersection
        vertices = [
            Point(*intersection_plane_plane_plane(start_plane, bottom_plane, front_plane)),     # v0
            Point(*intersection_plane_plane_plane(start_plane, bottom_plane, back_plane)),      # v1
            Point(*intersection_plane_plane_plane(end_plane, bottom_plane, back_plane)),        # v2
            Point(*intersection_plane_plane_plane(end_plane, bottom_plane, front_plane)),       # v3
            Point(*intersection_plane_plane_plane(start_plane, top_plane, front_plane)),        # v4
            Point(*intersection_plane_plane_plane(start_plane, top_plane, back_plane)),         # v5
            Point(*intersection_plane_plane_plane(end_plane, top_plane, back_plane)),           # v6
            Point(*intersection_plane_plane_plane(end_plane, top_plane, front_plane)),          # v7
        ]
        # define faces of the trimming volume
        # ensure vertices are defined in counter-clockwise order when viewed from the outside
        faces = [
            [3, 2, 1, 0],  # Bottom face
            [7, 6, 5, 4],  # Top face
            [0, 1, 5, 4],  # Side face 1
            [1, 2, 6, 5],  # Side face 2
            [2, 3, 7, 6],  # Side face 3
            [3, 0, 4, 7],  # Side face 4
        ]
        # ensure proper vertex order based on orientation
        if self.orientation == OrientationType.END:
            faces = [face[::-1] for face in faces]

        return Mesh.from_vertices_and_faces(vertices, faces)

    def _update_frames_based_on_machining_limits(self, frames, beam):
        """Updates the frames based on the machining limits.

        Parameters
        ----------
        frames : list of :class:`compas.geometry.Frame`
            The frames of the cut.
        beam : :class:`compas_timber.elements.Beam`
            The beam that is cut by this instance.

        Returns
        -------
        list of :class:`compas.geometry.Frame`
            The updated frames of the cut.
        """
        tol = Tolerance()
        tol.absolute=1e-3

        if not self.machining_limits["FaceLimitedStart"]:
            frames[0] = beam.ref_sides[4]
        if not self.machining_limits["FaceLimitedEnd"]:
            frames[1] = beam.ref_sides[5]
        if not self.machining_limits["FaceLimitedTop"]:
            frames[2] = beam.ref_sides[self.ref_side_index]
            frames[2].translate(frames[2].zaxis * tol.absolute) # offset the top frame to avoid tolerance issues
        if not self.machining_limits["FaceLimitedBottom"]:
            opp_ref_side_index = beam.opposing_side_index(self.ref_side_index)
            frames[3] = beam.ref_sides[opp_ref_side_index]
            frames[3].translate(frames[3].zaxis * tol.absolute) # offset the bottom frame to avoid tolerance issues
        if not self.machining_limits["FaceLimitedFront"]:
            frames[4] = beam.ref_sides[(self.ref_side_index-1)%4]
            frames[4].translate(frames[4].zaxis * tol.absolute) # offset the front frame to avoid tolerance issues
        if not self.machining_limits["FaceLimitedBack"]:
            frames[5] = beam.ref_sides[(self.ref_side_index+1)%4]
            frames[5].translate(frames[5].zaxis * tol.absolute) # offset the back frame to avoid tolerance issues

        return frames


class LapParams(BTLxProcessingParams):
    """A class to store the parameters of a Lap feature.

    Parameters
    ----------
    instance : :class:`~compas_timber.fabrication.Lap`
        The instance of the Lap feature.
    """

    def __init__(self, instance):
        # type: (Lap) -> None
        super(LapParams, self).__init__(instance)

    def as_dict(self):
        """Returns the parameters of the Lap feature as a dictionary.

        Returns
        -------
        dict
            The parameters of the Lap feature as a dictionary.
        """
        # type: () -> OrderedDict
        result = super(LapParams, self).as_dict()
        result["Orientation"] = self._instance.orientation
        result["StartX"] = "{:.{prec}f}".format(float(self._instance.start_x), prec=TOL.precision)
        result["StartY"] = "{:.{prec}f}".format(float(self._instance.start_y), prec=TOL.precision)
        result["Angle"] = "{:.{prec}f}".format(float(self._instance.angle), prec=TOL.precision)
        result["Inclination"] = "{:.{prec}f}".format(float(self._instance.inclination), prec=TOL.precision)
        result["Slope"] = "{:.{prec}f}".format(float(self._instance.slope), prec=TOL.precision)
        result["Length"] = "{:.{prec}f}".format(float(self._instance.length), prec=TOL.precision)
        result["Width"] = "{:.{prec}f}".format(float(self._instance.width), prec=TOL.precision)
        result["Depth"] = "{:.{prec}f}".format(float(self._instance.depth), prec=TOL.precision)
        result["LeadAngleParallel"] = "yes" if self._instance.lead_angle_parallel else "no"
        result["LeadAngle"] = "{:.{prec}f}".format(float(self._instance.lead_angle), prec=TOL.precision)
        result["LeadInclinationParallel"] = "yes" if self._instance.lead_inclination_parallel else "no"
        result["LeadInclination"] = "{:.{prec}f}".format(float(self._instance.lead_inclination), prec=TOL.precision)
        result["MachiningLimits"] = {key: "yes" if value else "no" for key, value in self._instance.machining_limits.items()}
        return result
