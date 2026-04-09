import math

from compas.geometry import Brep
from compas.geometry import Frame
from compas.geometry import Line
from compas.geometry import Plane
from compas.geometry import Point
from compas.geometry import Vector
from compas.geometry import angle_vectors
from compas.geometry import angle_vectors_projected
from compas.geometry import dot_vectors
from compas.geometry import intersection_plane_plane_plane
from compas.tolerance import TOL

from compas_timber.elements import Beam
from compas_timber.errors import FeatureApplicationError
from compas_timber.utils import planar_surface_point_at

from .btlx import AttributeSpec
from .btlx import BTLxProcessing
from .btlx import OrientationType


class BirdsMouth(BTLxProcessing):
    """Represents a Birds Mouth feature to be made on a beam.

    Parameters
    ----------
    orientation : str
        The orientation of the cut. Must be either ``OrientationType.START`` or ``OrientationType.END``.
    start_x : float
        The start x-coordinate of the cut in parametric space of the reference side. -100000.0 < start_x < 100000.0.
    start_y : float
        The start y-coordinate of the cut in parametric space of the reference side. -50000.0 < start_y < 50000.0.
    start_depth : float
        The start depth of the cut. 0.0 < start_depth < 50000.0.
    angle : float
        The angle of the cut in degrees. 0.1 < angle < 179.9.
    inclination1 : float
        The first inclination angle of the cut in degrees. 0.0 < inclination1 < 180.0.
    inclination2 : float
        The second inclination angle of the cut in degrees. 0.0 < inclination2 < 180.0.
    depth : float
        The depth of the cut. 0.0 < depth < 50000.0.
    width : float
        The width of the cut. 0.0 < width < 50000.0.
    width_counter_part_limited : bool
        Whether the width of the counter part is limited.
    width_counter_part : float
        The width of the counter part. 0.0 < width_counter_part < 50000.0.
    height_counter_part_limited : bool
        Whether the height of the counter part is limited.
    height_counter_part : float
        The height of the counter part. 0.0 < height_counter_part < 50000.0.
    face_limited_front : bool
        Whether the front face is limited.
    face_limited_back : bool
        Whether the back face is limited.
    lead_angle_parallel : bool
        Whether the lead angle is parallel to the reference side.
    lead_angle : float
        The lead angle in degrees. 0.1 < lead_angle < 179.9.
    lead_inclination_parallel : bool
        Whether the lead inclination is parallel to the reference side.
    lead_inclination : float
        The lead inclination angle in degrees. 0.1 < lead_inclination < 179.9.
    rafter_nail_hole : bool
        Whether a rafter nail hole is added.

    """

    PROCESSING_NAME = "BirdsMouth"  # type: ignore
    ATTRIBUTE_MAP = {
        "Orientation": AttributeSpec("orientation", str),
        "StartX": AttributeSpec("start_x", float),
        "StartY": AttributeSpec("start_y", float),
        "StartDepth": AttributeSpec("start_depth", float),
        "Angle": AttributeSpec("angle", float),
        "Inclination1": AttributeSpec("inclination1", float),
        "Inclination2": AttributeSpec("inclination2", float),
        "Depth": AttributeSpec("depth", float),
        "Width": AttributeSpec("width", float),
        "WidthCounterPartLimited": AttributeSpec("width_counter_part_limited", bool),
        "WidthCounterPart": AttributeSpec("width_counter_part", float),
        "HeightCounterPartLimited": AttributeSpec("height_counter_part_limited", bool),
        "HeightCounterPart": AttributeSpec("height_counter_part", float),
        "FaceLimitedFront": AttributeSpec("face_limited_front", bool),
        "FaceLimitedBack": AttributeSpec("face_limited_back", bool),
        "LeadAngleParallel": AttributeSpec("lead_angle_parallel", bool),
        "LeadAngle": AttributeSpec("lead_angle", float),
        "LeadInclinationParallel": AttributeSpec("lead_inclination_parallel", bool),
        "LeadInclination": AttributeSpec("lead_inclination", float),
        "RafterNailHole": AttributeSpec("rafter_nail_hole", bool),
    }

    @property
    def __data__(self):
        data = super(BirdsMouth, self).__data__
        data["orientation"] = self.orientation
        data["start_x"] = self.start_x
        data["start_y"] = self.start_y
        data["start_depth"] = self.start_depth
        data["angle"] = self.angle
        data["inclination1"] = self.inclination1
        data["inclination2"] = self.inclination2
        data["depth"] = self.depth
        data["width"] = self.width
        data["width_counter_part_limited"] = self.width_counter_part_limited
        data["width_counter_part"] = self.width_counter_part
        data["height_counter_part_limited"] = self.height_counter_part_limited
        data["height_counter_part"] = self.height_counter_part
        data["face_limited_front"] = self.face_limited_front
        data["face_limited_back"] = self.face_limited_back
        data["lead_angle_parallel"] = self.lead_angle_parallel
        data["lead_angle"] = self.lead_angle
        data["lead_inclination_parallel"] = self.lead_inclination_parallel
        data["lead_inclination"] = self.lead_inclination
        data["rafter_nail_hole"] = self.rafter_nail_hole
        return data

    # fmt: off
    def __init__(
        self,
        orientation: OrientationType = OrientationType.START,
        start_x: float = 0.0,
        start_y: float = 0.0,
        start_depth: float = 20.0,
        angle: float = 90.0,
        inclination1: float = 45.0,
        inclination2: float = 135.0,
        depth: float = 20.0,
        width: float = 0.0,
        width_counter_part_limited: bool = False,
        width_counter_part: float = 120.0,
        height_counter_part_limited: bool = False,
        height_counter_part: float = 120.0,
        face_limited_front: bool = False,
        face_limited_back: bool = False,
        lead_angle_parallel: bool = True,
        lead_angle: float = 90.0,
        lead_inclination_parallel: bool = True,
        lead_inclination: float = 90.0,
        rafter_nail_hole: bool = False,
        **kwargs
    ):
        super(BirdsMouth, self).__init__(**kwargs)
        self._orientation = None
        self._start_x = None
        self._start_y = None
        self._start_depth = None
        self._angle = None
        self._inclination1 = None
        self._inclination2 = None
        self._depth = None
        self._width = None
        self._width_counter_part_limited = None
        self._width_counter_part = None
        self._height_counter_part_limited = None
        self._height_counter_part = None
        self._face_limited_front = None
        self._face_limited_back = None
        self._lead_angle_parallel = None
        self._lead_angle = None
        self._lead_inclination_parallel = None
        self._lead_inclination = None
        self._rafter_nail_hole = None

        self.orientation = orientation
        self.start_x = start_x
        self.start_y = start_y
        self.start_depth = start_depth
        self.angle = angle
        self.inclination1 = inclination1
        self.inclination2 = inclination2
        self.depth = depth
        self.width = width
        self.width_counter_part_limited = width_counter_part_limited
        self.width_counter_part = width_counter_part
        self.height_counter_part_limited = height_counter_part_limited
        self.height_counter_part = height_counter_part
        self.face_limited_front = face_limited_front
        self.face_limited_back = face_limited_back
        self.lead_angle_parallel = lead_angle_parallel
        self.lead_angle = lead_angle
        self.lead_inclination_parallel = lead_inclination_parallel
        self.lead_inclination = lead_inclination
        self.rafter_nail_hole = rafter_nail_hole

    ########################################################################
    # Properties
    ########################################################################

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
        if start_y > 50000.0 or start_y < -50000.0:
            raise ValueError("StartY must be between -50000.0 and 50000.0.")
        self._start_y = start_y

    @property
    def start_depth(self):
        return self._start_depth

    @start_depth.setter
    def start_depth(self, start_depth):
        if start_depth > 50000.0 or start_depth < 0.0:
            raise ValueError("StartDepth must be between 0.0 and 50000.0.")
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
    def inclination1(self):
        return self._inclination1

    @inclination1.setter
    def inclination1(self, inclination1):
        if inclination1 > 180.0 or inclination1 < 0.0:
            raise ValueError("Inclination1 must be between 0.0 and 180.0.")
        self._inclination1 = inclination1

    @property
    def inclination2(self):
        return self._inclination2

    @inclination2.setter
    def inclination2(self, inclination2):
        if inclination2 > 180.0 or inclination2 < 0.0:
            raise ValueError("Inclination2 must be between 0.0 and 180.0.")
        self._inclination2 = inclination2

    @property
    def depth(self):
        return self._depth

    @depth.setter
    def depth(self, depth):
        if depth > 50000.0 or depth < 0.0:
            raise ValueError("Depth must be between 0.0 and 50000.0.")
        self._depth = depth

    @property
    def width(self):
        return self._width

    @width.setter
    def width(self, width):
        if width > 50000.0 or width < 0.0:
            raise ValueError("Width must be between 0.0 and 50000.0.")
        self._width = width

    @property
    def width_counter_part_limited(self):
        return self._width_counter_part_limited

    @width_counter_part_limited.setter
    def width_counter_part_limited(self, width_counter_part_limited):
        if not isinstance(width_counter_part_limited, bool):
            raise ValueError("WidthCounterPartLimited must be a boolean.")
        self._width_counter_part_limited = width_counter_part_limited

    @property
    def width_counter_part(self):
        return self._width_counter_part

    @width_counter_part.setter
    def width_counter_part(self, width_counter_part):
        if width_counter_part > 50000.0 or width_counter_part < 0.0:
            raise ValueError("WidthCounterPart must be between 0.0 and 50000.0.")
        self._width_counter_part = width_counter_part

    @property
    def height_counter_part_limited(self):
        return self._height_counter_part_limited

    @height_counter_part_limited.setter
    def height_counter_part_limited(self, height_counter_part_limited):
        if not isinstance(height_counter_part_limited, bool):
            raise ValueError("HeightCounterPartLimited must be a boolean.")
        self._height_counter_part_limited = height_counter_part_limited

    @property
    def height_counter_part(self):
        return self._height_counter_part

    @height_counter_part.setter
    def height_counter_part(self, height_counter_part):
        if height_counter_part > 50000.0 or height_counter_part < 0.0:
            raise ValueError("HeightCounterPart must be between 0.0 and 50000.0.")
        self._height_counter_part = height_counter_part

    @property
    def face_limited_front(self):
        return self._face_limited_front

    @face_limited_front.setter
    def face_limited_front(self, face_limited_front):
        if not isinstance(face_limited_front, bool):
            raise ValueError("FaceLimitedFront must be a boolean.")
        self._face_limited_front = face_limited_front

    @property
    def face_limited_back(self):
        return self._face_limited_back

    @face_limited_back.setter
    def face_limited_back(self, face_limited_back):
        if not isinstance(face_limited_back, bool):
            raise ValueError("FaceLimitedBack must be a boolean.")
        self._face_limited_back = face_limited_back

    @property
    def lead_angle_parallel(self):
        return self._lead_angle_parallel

    @lead_angle_parallel.setter
    def lead_angle_parallel(self, lead_angle_parallel):
        if not isinstance(lead_angle_parallel, bool):
            raise ValueError("LeadAngleParallel must be a boolean.")
        self._lead_angle_parallel = lead_angle_parallel

    @property
    def lead_angle(self):
        return self._lead_angle

    @lead_angle.setter
    def lead_angle(self, lead_angle):
        if lead_angle > 179.9 or lead_angle < 0.1:
            raise ValueError("LeadAngle must be between 0.1 and 179.9.")
        self._lead_angle = lead_angle

    @property
    def lead_inclination_parallel(self):
        return self._lead_inclination_parallel

    @lead_inclination_parallel.setter
    def lead_inclination_parallel(self, lead_inclination_parallel):
        if not isinstance(lead_inclination_parallel, bool):
            raise ValueError("LeadInclinationParallel must be a boolean.")
        self._lead_inclination_parallel = lead_inclination_parallel

    @property
    def lead_inclination(self):
        return self._lead_inclination

    @lead_inclination.setter
    def lead_inclination(self, lead_inclination):
        if lead_inclination > 179.9 or lead_inclination < 0.1:
            raise ValueError("LeadInclination must be between 0.1 and 179.9.")
        self._lead_inclination = lead_inclination

    @property
    def rafter_nail_hole(self):
        return self._rafter_nail_hole

    @rafter_nail_hole.setter
    def rafter_nail_hole(self, rafter_nail_hole):
        if not isinstance(rafter_nail_hole, bool):
            raise ValueError("RafterNailHole must be a boolean.")
        self._rafter_nail_hole = rafter_nail_hole

    ########################################################################
    # Alternative constructors
    ########################################################################

    @classmethod
    def from_planes_and_beam(cls, planes:list[Plane], beam:Beam, start_y:float=0.0, width:float=None, ref_side_index:int=None, **kwargs) -> "BirdsMouth":
        """Create a BirdsMouth instance from two cutting planes and the beam they notch.

        The intersection line of the two planes defines the ridge of the birds mouth notch.
        The individual planes define the two angled faces of the notch.

        Parameters
        ----------
        planes : list of :class:`~compas.geometry.Plane` or :class:`~compas.geometry.Frame`
            The two cutting planes that define the birds mouth notch.
        beam : :class:`~compas_timber.elements.Beam`
            The beam that is notched by this instance.
        start_y : float, optional
            The start y-coordinate of the cut in parametric space of the reference side. Default is 0.0.
        width : float, optional
            The width of the notch in mm. Default is the full width of the beam minus start_y.
        ref_side_index : int, optional
            The reference side index of the beam to be notched. Default is determined from the planes.

        Returns
        -------
        :class:`~compas_timber.fabrication.BirdsMouth`

        """
        if len(planes) != 2:
            raise ValueError("Exactly two cutting planes are required to create a BirdsMouth instance.")

        # normalise to Plane
        planes = [Plane.from_frame(p) if isinstance(p, Frame) else p for p in planes]

        # determine ref_side_index
        if ref_side_index is None:
            ref_side_index = cls._get_default_ref_side_index(planes, beam)
        ref_side = beam.ref_sides[ref_side_index]
        beam_width = beam.get_dimensions_relative_to_side(ref_side_index)[0]

        if width is None:
            width = beam_width - start_y

        # determine face limits based on start_y and width
        face_limited_front = TOL.is_positive(start_y)
        face_limited_back = beam_width > start_y + width

        # compute notch apex and rear point by intersecting the planes with the front and back side planes of the beam
        front_side_plane = Plane.from_frame(beam.front_side(ref_side_index))
        back_side_plane = Plane.from_frame(beam.back_side(ref_side_index))

        if face_limited_front:
            front_side_plane.translate(ref_side.yaxis * start_y)
        if face_limited_back:
            back_side_plane.translate(ref_side.yaxis * (beam_width - start_y - width))

        apex = Point(*intersection_plane_plane_plane(planes[0], planes[1], front_side_plane))
        rear = Point(*intersection_plane_plane_plane(planes[0], planes[1], back_side_plane))
        ridge_line = Line(apex, rear)

        # orientation — which end of the beam the notch faces
        orientation = cls._calculate_orientation(beam, planes)

        # start_x and start_depth from apex projected onto ref_side local coords
        start_x, start_depth = cls._calculate_start_x_and_depth(ref_side, apex)

        # depth — distance from ref_side plane to rear point along -ref_side.zaxis
        depth = cls._calculate_depth(ref_side, rear)

        # angle — horizontal angle of the ridge line relative to -ref_side.xaxis (START) or ref_side.xaxis (END)
        angle = cls._calculate_angle(ref_side, ridge_line, orientation)

        # inclination1 and inclination2 — each plane's tilt relative to ref_side normal
        inclination1, inclination2 = cls._calculate_inclinations(ref_side, planes, ridge_line)


        return cls(
            orientation=orientation,
            start_x=start_x,
            start_y=start_y,
            start_depth=start_depth,
            angle=angle,
            inclination1=inclination1,
            inclination2=inclination2,
            depth=depth,
            width=width,
            face_limited_front=face_limited_front,
            face_limited_back=face_limited_back,
            ref_side_index=ref_side_index,
            **kwargs
        )

    @classmethod
    def from_shapes_and_element(cls, plane_a, plane_b, element, **kwargs):
        """Construct a BirdsMouth process from two planes and a beam.

        Parameters
        ----------
        plane_a : :class:`~compas.geometry.Plane` or :class:`~compas.geometry.Frame`
            The first cutting plane.
        plane_b : :class:`~compas.geometry.Plane` or :class:`~compas.geometry.Frame`
            The second cutting plane.
        element : :class:`~compas_timber.elements.Beam`
            The beam to be notched.

        Returns
        -------
        :class:`~compas_timber.fabrication.BirdsMouth`

        """
        return cls.from_planes_and_beam([plane_a, plane_b], element, **kwargs)

    ########################################################################
    # Private helpers
    ########################################################################

    @staticmethod
    def _get_default_ref_side_index(planes, beam):
        """Return the ref_side whose normal is most aligned with the average of the two plane normals."""
        avg_normal = planes[0].normal + planes[1].normal
        best_index = 0
        best_dot = -1.0
        for i, ref_side in enumerate(beam.ref_sides[:4]):
            d = abs(dot_vectors(ref_side.zaxis, avg_normal))
            if d > best_dot:
                best_dot = d
                best_index = i
        return best_index

    @staticmethod
    def _calculate_orientation(beam, planes):
        """Orientation is START when the combined plane normals point toward the beam start."""
        combined = planes[0].normal + planes[1].normal
        if dot_vectors(beam.centerline.direction, combined) > 0:
            return OrientationType.END
        return OrientationType.START

    @staticmethod
    def _calculate_start_x_and_depth(ref_side, apex):
        """Project the apex onto the ref_side to get start_x and start_depth."""
        v = Vector.from_start_end(ref_side.point, apex)
        start_x = dot_vectors(v, ref_side.xaxis)
        start_depth = dot_vectors(v, -ref_side.zaxis)
        return start_x, start_depth

    @staticmethod
    def _calculate_depth(ref_side, rear):
        """Depth is distance from ref_side plane to rear point along -ref_side.zaxis."""
        depth = dot_vectors(Vector.from_start_end(ref_side.point, rear), -ref_side.zaxis)
        return depth

    @staticmethod
    def _calculate_angle(ref_side, ridge_line, orientation):
        """Horizontal angle of the ridge line projected onto the ref_side plane."""
        # project ridge onto the ref_side plane
        projected_ridge = ridge_line.direction - ref_side.zaxis * dot_vectors(ridge_line.direction, ref_side.zaxis)
        if TOL.is_zero(projected_ridge.length):
            # if the ridge is parallel to the ref_side normal, define the angle as 0
            return 0.0
        angle = angle_vectors(ref_side.xaxis, projected_ridge, deg=True)
        if orientation == OrientationType.START:
            return 180.0 - angle
        return angle

    @staticmethod
    def _calculate_inclinations(ref_side, planes, ridge_line):
        """Inclination of each cutting plane relative to the ref_side normal. Returned in ascending order as inclination1 and inclination2."""
        inclinations = []
        for plane in planes:
            inclination = angle_vectors_projected(plane.normal, ref_side.normal, -ridge_line.direction, deg=True)
            inclinations.append(abs(inclination))
        inclinations[0] = 180.0 - inclinations[0]
        return sorted(inclinations)  # return in ascending order as inclination1 and inclination2

    ########################################################################
    # Methods
    ########################################################################

    def planes_from_params_and_beam(self, beam:Beam) -> list[Plane]:
        """Calculates the two cutting planes from the machining parameters in this instance and the given beam.

        Parameters
        ----------
        beam : :class:`compas_timber.elements.Beam`
            The beam that is notched by this instance.

        Returns
        -------
        list of :class:`~compas.geometry.Plane`
            The two cutting planes for this instance.

        """
        assert self.inclination1 is not None
        assert self.inclination2 is not None

        ref_frame = beam.ref_sides[self.ref_side_index]
        ridge_line = self._get_ridge_line_from_params_and_beam(beam)

        # # For START the stored angle is measured from -xaxis; flip xaxis for reconstruction.
        # # Inclinations are adjusted accordingly, mirroring DoubleCut's END handling.
        inclination_1 = self.inclination1
        inclination_2 = self.inclination2
        if self.orientation == OrientationType.END:
            inclination_1 = 180.0 - inclination_1
            inclination_2 = 180.0 - inclination_2

        plane_1 = Plane(ridge_line.start, ref_frame.xaxis)
        plane_1.rotate(math.radians(inclination_1), -ridge_line.direction, point=ridge_line.start)

        plane_2 = Plane(ridge_line.end, ref_frame.xaxis)
        plane_2.rotate(math.radians(inclination_2), -ridge_line.direction, point=ridge_line.end)

        return [plane_1, plane_2]

    def _get_ridge_line_from_params_and_beam(self, beam:Beam) -> Line:
        """Calculate the ridge line created by the intersection of the two cutting planes of the BirdsMouth notch from the machining parameters and the given beam."""
        assert self.orientation is not None
        assert self.start_x is not None
        assert self.start_y is not None
        assert self.start_depth is not None
        assert self.angle is not None
        assert self.depth is not None
        assert self.width is not None
        assert self.ref_side_index is not None

        ref_side = beam.side_as_surface(self.ref_side_index)
        # Reconstruct apex: on ref_side surface at (start_x, start_y), shifted inward by start_depth
        p_apex = planar_surface_point_at(ref_side, self.start_x, self.start_y)
        p_apex -= ref_side.zaxis * self.start_depth

        angle = self.angle
        if self.orientation == OrientationType.END:
            angle = 180.0 - angle
        dx = self.width / math.tan(math.radians(angle))
        p_rear = planar_surface_point_at(ref_side, self.start_x + dx , self.start_y + self.width)
        p_rear -= ref_side.zaxis * (self.depth)
        return Line(p_apex, p_rear)

    def apply(self, geometry: Brep, beam: Beam) -> Brep:
        """Apply the feature to the beam geometry.

        Parameters
        ----------
        geometry : :class:`~compas.geometry.Brep`
            The beam geometry to be notched.
        beam : :class:`compas_timber.elements.Beam`
            The beam that is notched by this instance.

        Raises
        ------
        :class:`~compas_timber.errors.FeatureApplicationError`
            If the cutting planes do not intersect with beam geometry.

        Returns
        -------
        :class:`~compas.geometry.Brep`
            The resulting geometry after processing.

        """
        try:
            cutting_planes = self.planes_from_params_and_beam(beam)
        except ValueError as e:
            raise FeatureApplicationError(
                None, geometry, "Failed to generate cutting planes from parameters and beam: {}".format(str(e))
            )
        # convert to the local coordinates of the beam
        cutting_planes = [plane.transformed(beam.transformation_to_local()) for plane in cutting_planes]

        # birds mouth is always a concave (v-notch) cut
        trim_volume = geometry.copy()
        try:
            for cutting_plane in cutting_planes:
                flipped_plane = Plane(cutting_plane.point, -cutting_plane.normal)
                trim_volume.trim(flipped_plane)
        except Exception as e:
            raise FeatureApplicationError(cutting_planes, beam, "Failed to trim notch geometry with cutting planes: {}".format(str(e)))

        try:
            return geometry - trim_volume
        except Exception as e:
            raise FeatureApplicationError(trim_volume, beam, "Failed to compute final geometry difference for birds mouth notch: {}".format(str(e)))

    def scale(self, factor: float) -> None:
        """Scale the parameters of the processing by the given factor.

        Notes
        -----
        Only distances are scaled, angles remain unchanged.

        Parameters
        ----------
        factor : float
            The scaling factor. A value of 1.0 means no scaling, while a value of 2.0 means doubling the size.

        """
        # type: (float) -> None
        assert self.start_x is not None
        assert self.start_y is not None
        assert self.start_depth is not None
        assert self.depth is not None
        assert self.width is not None
        self._start_x *= factor
        self._start_y *= factor
        self._start_depth *= factor
        self._depth *= factor
        self._width *= factor
