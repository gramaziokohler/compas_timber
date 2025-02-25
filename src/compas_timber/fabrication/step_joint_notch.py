import math
from collections import OrderedDict

from compas.geometry import Box
from compas.geometry import Brep
from compas.geometry import Frame
from compas.geometry import Line
from compas.geometry import Plane
from compas.geometry import Vector
from compas.geometry import angle_vectors_signed
from compas.geometry import distance_point_point
from compas.geometry import intersection_line_plane
from compas.geometry import intersection_plane_plane
from compas.geometry import is_point_behind_plane
from compas.tolerance import TOL

from compas_timber.errors import FeatureApplicationError

from .btlx import BTLxProcessing
from .btlx import BTLxProcessingParams
from .btlx import OrientationType
from .btlx import StepShapeType


class StepJointNotch(BTLxProcessing):
    """Represents a Step Joint Notch feature to be made on a beam.

    Parameters
    ----------
    orientation : int
        The orientation of the cut. Must be either OrientationType.START or OrientationType.END.
    start_x : float
        The start x-coordinate of the cut in parametric space of the reference side. -100000.0 < start_x < 100000.0.
    start_y : float
        The start y-coordinate of the notch in parametric space of the reference side. -50000.0 < start_y < 50000.0.
    strut_inclination : float
        The inclination of the strut. 0.1 < strut_inclination < 179.9.
    notch_limited : bool
        Whether the notch is limited. If True, the notch is limited by the start_y and notch_width values.
    notch_width : float
        The width of the notch. notch_width < 50000.0.
    step_depth : float
        The depth of the step. step_depth < 50000.0.
    heel_depth : float
        The depth of the heel. heel_depth < 50000.0.
    strut_height : float
        The height of the strut. It is the cross beam's height. strut_height < 50000.0.
    step_shape : str
        The shape of the step. Must be either StepShapeType.DOUBLE, StepShapeType.STEP, StepShapeType.HEEL or StepShapeType.TAPERED_HEEL.
    mortise : str
        The presence of a mortise. Must be either 'no' or 'yes'.
    mortise_width : float
        The width of the mortise. mortise_width < 1000.0.
    mortise_height : float
        The height of the mortise. mortise_height < 1000.0.

    """

    PROCESSING_NAME = "StepJointNotch"  # type: ignore

    @property
    def __data__(self):
        data = super(StepJointNotch, self).__data__
        data["orientation"] = self.orientation
        data["start_x"] = self.start_x
        data["start_y"] = self.start_y
        data["strut_inclination"] = self.strut_inclination
        data["notch_limited"] = self.notch_limited
        data["notch_width"] = self.notch_width
        data["step_depth"] = self.step_depth
        data["heel_depth"] = self.heel_depth
        data["strut_height"] = self.strut_height
        data["step_shape"] = self.step_shape
        data["mortise"] = self.mortise
        data["mortise_width"] = self.mortise_width
        data["mortise_height"] = self.mortise_height
        return data

    # fmt: off
    def __init__(
        self,
        orientation=OrientationType.START,
        start_x=0.0,
        start_y=0.0,
        strut_inclination=90.0,
        notch_limited=False,
        notch_width=20.0,
        step_depth=20.0,
        heel_depth=20.0,
        strut_height=20.0,
        step_shape=StepShapeType.DOUBLE,
        mortise=False,
        mortise_width=40.0,
        mortise_height=40.0,
        **kwargs
    ):
        super(StepJointNotch, self).__init__(**kwargs)
        self._orientation = None
        self._start_x = None
        self._start_y = None
        self._strut_inclination = None
        self._notch_limited = None
        self._notch_width = None
        self._step_depth = None
        self._heel_depth = None
        self._strut_height = None
        self._step_shape = None
        self._mortise = None
        self._mortise_width = None
        self._mortise_height = None

        self.orientation = orientation
        self.start_x = start_x
        self.start_y = start_y
        self.strut_inclination = strut_inclination
        self.notch_limited = notch_limited
        self.notch_width = notch_width
        self.step_depth = step_depth
        self.heel_depth = heel_depth
        self.strut_height = strut_height
        self.step_shape = step_shape
        self.mortise = mortise
        self.mortise_width = mortise_width
        self.mortise_height = mortise_height

    ########################################################################
    # Properties
    ########################################################################

    @property
    def params(self):
        return StepJointNotchParams(self)

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
            raise ValueError("StartX must be between -100000.0 and 100000.")
        self._start_x = start_x

    @property
    def start_y(self):
        return self._start_y

    @start_y.setter
    def start_y(self, start_y):
        if start_y > 50000.0 or start_y < -50000.0:
            raise ValueError("StartY must be between -50000.0 and 50000.")
        self._start_y = start_y

    @property
    def strut_inclination(self):
        return self._strut_inclination

    @strut_inclination.setter
    def strut_inclination(self, strut_inclination):
        if strut_inclination < 0.1 or strut_inclination > 179.9 or strut_inclination == 90.0:
            raise ValueError("StrutInclination must be between 0.1 and 89.9 or 90.1 and 179.9.")
        self._strut_inclination = strut_inclination

    @property
    def notch_limited(self):
        return self._notch_limited

    @notch_limited.setter
    def notch_limited(self, notch_limited):
        if not isinstance(notch_limited, bool):
            raise ValueError("NotchLimited must be either True or False.")
        self._notch_limited = notch_limited

    @property
    def notch_width(self):
        return self._notch_width

    @notch_width.setter
    def notch_width(self, notch_width):
        if notch_width > 50000.0:
            raise ValueError("NotchWidth must be less than 50000.0.")
        self._notch_width = notch_width

    @property
    def step_depth(self):
        return self._step_depth

    @step_depth.setter
    def step_depth(self, step_depth):
        if step_depth > 50000.0:
            raise ValueError("StepDepth must be less than 50000.0.")
        self._step_depth = step_depth

    @property
    def heel_depth(self):
        return self._heel_depth

    @heel_depth.setter
    def heel_depth(self, heel_depth):
        if heel_depth > 50000.0:
            raise ValueError("HeelDepth must be less than 50000.0.")
        self._heel_depth = heel_depth

    @property
    def strut_height(self):
        return self._strut_height

    @strut_height.setter
    def strut_height(self, strut_height):
        if strut_height > 50000.0:
            raise ValueError("StrutHeight must be less than 50000.0.")
        self._strut_height = strut_height

    @property
    def step_shape(self):
        return self._step_shape

    @step_shape.setter
    def step_shape(self, step_shape):
        if step_shape == StepShapeType.DOUBLE:
            if self.step_depth <= 0 or self.heel_depth <= 0:
                raise ValueError("For a 'double' step_shape, both step_depth and heel_depth must be greater than 0.")
        elif step_shape == StepShapeType.STEP:
            if self.step_depth <= 0 or self.heel_depth != 0:
                raise ValueError("For a 'step' step_shape, step_depth must be greater than 0 and heel_depth must be 0.")
        elif step_shape in [StepShapeType.HEEL, StepShapeType.TAPERED_HEEL]:
            if self.heel_depth <= 0 or self.step_depth != 0:
                raise ValueError(
                    "For 'heel' or 'tapered heel' step_shape, heel_depth must be greater than 0 and step_depth must be 0."
                )
        else:
            raise ValueError(
                "StepShapeType must be either StepShapeType.DOUBLE, StepShapeType.STEP, StepShapeType.HEEL, or StepShapeType.TAPERED_HEEL."
            )
        self._step_shape = step_shape

    @property
    def mortise(self):
        return self._mortise

    @mortise.setter
    def mortise(self, mortise):
        if not isinstance(mortise, bool):
            raise ValueError("Mortise must be either True or False.")
        self._mortise = mortise

    @property
    def mortise_width(self):
        return self._mortise_width

    @mortise_width.setter
    def mortise_width(self, mortise_width):
        if mortise_width > 1000.0:
            raise ValueError("MortiseWidth must be less than 1000.0.")
        self._mortise_width = mortise_width

    @property
    def mortise_height(self):
        return self._mortise_height

    @mortise_height.setter
    def mortise_height(self, mortise_height):
        if mortise_height > 1000.0:
            raise ValueError("MortiseHeight must be less than 1000.0.")
        self._mortise_height = mortise_height

    @property
    def displacement_end(self):
        return self._calculate_displacement_end(self.strut_height, self.strut_inclination, self.orientation)

    @property
    def displacement_heel(self):
        return self._calculate_displacement_heel(self.heel_depth, self.strut_inclination, self.orientation)

    ########################################################################
    # Alternative constructors
    ########################################################################

    @classmethod
    def from_plane_and_beam(
        cls,
        plane,
        beam,
        start_y=0.0,
        notch_limited=False,
        notch_width=20.0,
        step_depth=20.0,
        heel_depth=0.0,
        strut_height=20.0,
        tapered_heel=False,
        ref_side_index=0,
    ):
        """Create a StepJointNotch instance from a cutting surface and the beam it should cut. This could be the ref_side of the main beam of a Joint and the cross beam.

        Parameters
        ----------
        plane: :class:`~compas.geometry.Planae` or :class:`~compas.geometry.Frame`
            The cutting plane.
        beam : :class:`~compas_timber.elements.Beam`
            The beam that is cut by this instance.
        ref_side_index : int, optional
            The reference side index of the beam to be cut. Default is 0 (i.e. RS1).

        Returns
        -------
        :class:`~compas_timber.fabrication.StepJointNotch`

        """
        # type: (Plane|Frame, Beam, float, bool, float, float, float, float, bool, int) -> StepJointNotch

        if isinstance(plane, Frame):
            plane = Plane.from_frame(plane)
        # define ref_side & ref_edge
        ref_side = beam.ref_sides[ref_side_index]
        ref_edge = Line.from_point_and_vector(ref_side.point, ref_side.xaxis)

        # calculate orientation
        orientation = cls._calculate_orientation(ref_side, plane)

        # calculate start_x
        point_start_x = intersection_line_plane(ref_edge, plane)
        if point_start_x is None:
            raise ValueError("Surface does not intersect with beam.")
        start_x = distance_point_point(ref_side.point, point_start_x)

        # calculate strut_inclination
        strut_inclination = cls._calculate_strut_inclination(ref_side, plane, orientation)

        # calculate notch_width
        if notch_limited:
            notch_width = notch_width if notch_width < beam.width else beam.width
        else:
            notch_width = beam.width
            start_y = 0.0

        # define step_shape
        step_shape = cls._define_step_shape(step_depth, heel_depth, tapered_heel)

        return cls(
            orientation,
            start_x,
            start_y,
            strut_inclination,
            notch_limited,
            notch_width,
            step_depth,
            heel_depth,
            strut_height,
            step_shape,
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
    def _calculate_start_y(orientation, intersection_line, point_start_x, ref_side):
        # checks if the start of the intersection line is out of the beam's ref_side
        # if it's out then start_y = 0.0, otherwise it calculates the displacement
        if orientation == OrientationType.START:
            point_start_y = intersection_line.start
        else:
            point_start_y = intersection_line.end
        startxy_vect = Vector.from_start_end(point_start_x, point_start_y)
        dot_product = startxy_vect.dot(ref_side.yaxis)
        start_y = abs(dot_product) if dot_product > 0 else 0.0
        return start_y

    @staticmethod
    def _calculate_strut_inclination(ref_side, plane, orientation):
        # vector rotation direction of the plane's normal in the vertical direction
        strut_inclination_vector = Vector.cross(ref_side.zaxis, plane.normal)
        strut_inclination = angle_vectors_signed(ref_side.zaxis, plane.normal, strut_inclination_vector, deg=True)
        return abs(strut_inclination)

    @staticmethod
    def _define_step_shape(step_depth, heel_depth, tapered_heel):
        # step_shape based on step_depth and heel_depth and tapered_heel variables
        if step_depth > 0.0 and heel_depth == 0.0:
            return StepShapeType.STEP
        elif step_depth == 0.0 and heel_depth > 0.0:
            if tapered_heel:
                return StepShapeType.TAPERED_HEEL
            else:
                return StepShapeType.HEEL
        elif step_depth > 0.0 and heel_depth > 0.0:
            return StepShapeType.DOUBLE
        else:
            raise ValueError("At least one of step_depth or heel_depth must be greater than 0.0.")

    @staticmethod
    def _calculate_displacement_end(strut_height, strut_inclination, orientation):
        # Calculates the linear displacement from the origin point to the end of the notch based on the strut_height and strut_inclination.
        displacement_end = strut_height / math.sin(math.radians(strut_inclination))
        if orientation == OrientationType.END:
            displacement_end = -displacement_end  # negative displacement for the end cut
        return displacement_end

    @staticmethod
    def _calculate_displacement_heel(heel_depth, strut_inclination, orientation):
        # Calculates the linear displacement from the origin point to the heel of the notch based on the heel_depth and strut_inclination.
        displacement_heel = abs(
            heel_depth / (math.sin(math.radians(strut_inclination)) * math.cos(math.radians(strut_inclination)))
        )
        if orientation == OrientationType.END:
            displacement_heel = -displacement_heel
        return displacement_heel

    ########################################################################
    # Methods
    ########################################################################

    def apply(self, geometry, beam):
        """Apply the feature to the beam geometry.

        Parameters
        ----------
        geometry : :class:`~compas.geometry.Brep`
            The beam geometry to be processed.
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

        # get cutting planes from params
        try:
            cutting_planes = self.planes_from_params_and_beam(beam)
        except ValueError as e:
            raise FeatureApplicationError(
                None, geometry, "Failed to generate cutting planes from parameters and beam: {}".format(str(e))
            )

        # get notch volume
        subtraction_volume = geometry.copy()
        if self.step_shape == StepShapeType.DOUBLE:
            # trim geometry with first and last cutting plane
            try:
                for cutting_plane in [cutting_planes[1], cutting_planes[3]]:
                    cutting_plane.normal = cutting_plane.normal * -1
                    subtraction_volume.trim(cutting_plane)
            except Exception as e:
                raise FeatureApplicationError(
                    cutting_planes[-1],
                    subtraction_volume,
                    "Failed to trim geometry with cutting plane: {}".format(str(e)),
                )
            # trim geometry with two middle cutting planes
            trimmed_geometies = []
            for cutting_plane in [cutting_planes[0], cutting_planes[2]]:
                cutting_plane.normal = cutting_plane.normal * -1
                try:
                    trimmed_geometies.append(subtraction_volume.trimmed(cutting_plane))
                except Exception as e:
                    raise FeatureApplicationError(
                        cutting_plane,
                        subtraction_volume,
                        "Failed to trim geometry with cutting plane: {}".format(str(e)),
                    )
            subtraction_volume = trimmed_geometies

        else:
            for cutting_plane in cutting_planes:
                cutting_plane.normal = cutting_plane.normal * -1
                try:
                    subtraction_volume.trim(cutting_plane)
                except Exception as e:
                    raise FeatureApplicationError(
                        cutting_plane,
                        subtraction_volume,
                        "Failed to trim geometry with cutting planes: {}".format(str(e)),
                    )
        ## subtract volume from geometry
        if isinstance(subtraction_volume, list):
            for sub_vol in subtraction_volume:
                try:
                    geometry -= sub_vol
                except Exception as e:
                    raise FeatureApplicationError(
                        sub_vol, geometry, "Failed to subtract volume from geometry: {}".format(str(e))
                    )
        else:
            geometry -= subtraction_volume

        ## add mortise
        if self.mortise and self.step_shape != StepShapeType.DOUBLE: # TODO: check if mortise applies only to step in BTLx
            # create mortise box and convert to Brep
            mortise_box = self.mortise_volume_from_params_and_beam(beam)
            mortise_volume = Brep.from_box(mortise_box)
            # trim mortise volume at step
            origin = intersection_plane_plane(cutting_planes[0], cutting_planes[1])[0]
            normal = mortise_box.frame.xaxis
            if self.step_shape != StepShapeType.STEP:
                normal = -normal
            cuttin_plane_step = Plane(origin, normal)
            try:
                mortise_volume.trim(cuttin_plane_step)
            except Exception as e:
                raise FeatureApplicationError(
                    cuttin_plane_step,
                    mortise_volume,
                    "Failed to trim mortise volume with step cutting plane: {}".format(str(e)),
                )
            try:
                geometry -= mortise_volume
            except Exception as e:
                raise FeatureApplicationError(
                    mortise_volume,
                    subtraction_volume,
                    "Failed to subtract mortise volume from geometry: {}".format(str(e)),
                )
        return geometry

    def add_mortise(self, mortise_width, mortise_height, beam):
        """Add a mortise to the existing StepJointNotch instance.

        Parameters
        ----------
        mortise_width : float
            The width of the mortise. mortise_width < 1000.0.
        mortise_height : float
            The height of the mortise. mortise_height < 1000.0.
        """
        self.mortise = True
        self.mortise_width = mortise_width
        if mortise_height > beam.height:  # TODO: should this be constrained?
            self.mortise_height = beam.height
        elif mortise_height < self.step_depth:
            self.mortise_height = self.step_depth
        else:
            self.mortise_height = mortise_height

    def planes_from_params_and_beam(self, beam):
        """Calculates the cutting planes from the machining parameters in this instance and the given beam

        Parameters
        ----------
        beam : :class:`compas_timber.elements.Beam`
            The beam that is cut by this instance.

        Returns
        -------
        :class:`compas.geometry.Plane`
            The cutting planes.
        """
        assert self.strut_inclination is not None
        assert self.step_shape is not None
        assert self.strut_height is not None

        # Start with a plane aligned with the ref side but shifted to the start of the first cut
        ref_side = beam.side_as_surface(self.ref_side_index)

        if self.step_shape == StepShapeType.STEP:
            return self._calculate_step_planes(ref_side)
        elif self.step_shape == StepShapeType.HEEL:
            return self._calculate_heel_planes(ref_side)
        elif self.step_shape == StepShapeType.TAPERED_HEEL:
            return self._calculate_tapered_heel_planes(ref_side)
        elif self.step_shape == StepShapeType.DOUBLE:
            return self._calculate_double_planes(ref_side)

    def _calculate_step_planes(self, ref_side):
        """Calculate cutting planes for a step notch."""
        # Move the frames to the start and end of the notch to create the cuts
        if self.strut_inclination > 90:
            p_origin = ref_side.point_at(self.start_x, self.start_y)
            p_end = ref_side.point_at(self.start_x + self.displacement_end, self.start_y)
        else:
            p_origin = ref_side.point_at(self.start_x + self.displacement_end, self.start_y)
            p_end = ref_side.point_at(self.start_x, self.start_y)
        cutting_plane_origin = Frame(p_origin, ref_side.frame.xaxis, ref_side.frame.yaxis)
        cutting_plane_end = Frame(p_end, ref_side.frame.xaxis, ref_side.frame.yaxis)
        # Calculate step cutting planes angles
        angle_origin = math.atan(
                self.step_depth
                / (abs(self.displacement_end) - self.step_depth / math.tan(math.radians((self.strut_inclination) / 2)))
            )
        angle_end = math.radians(self.strut_inclination / 2)
        # Get the rotation axis
        rot_axis = ref_side.frame.yaxis
        if self.orientation == OrientationType.END:
            rot_axis = -rot_axis
        # Rotate the cutting planes
        cutting_plane_end.rotate(angle_end, -rot_axis, p_end)
        cutting_plane_origin.rotate(angle_origin, rot_axis, p_origin)
        return [Plane.from_frame(cutting_plane_origin), Plane.from_frame(cutting_plane_end)]

    def _calculate_heel_planes(self, ref_side):
        """Calculate cutting planes for a heel notch."""
        # Move the frames to the start and end of the notch to create the cuts
        p_origin = ref_side.point_at(self.start_x, self.start_y)
        p_heel = ref_side.point_at(self.start_x + self.displacement_heel, self.start_y)
        cutting_plane_end = Frame(p_origin, ref_side.frame.xaxis, -ref_side.frame.yaxis)
        cutting_plane_heel = Frame(p_heel, ref_side.frame.xaxis, -ref_side.frame.yaxis)
        # Calculate heel cutting planes angles
        rot_axis = ref_side.frame.yaxis
        if self.orientation == OrientationType.START:
            rot_axis = -rot_axis
        # Rotate the cutting planes
        cutting_plane_end.rotate(math.radians(self.strut_inclination), rot_axis, p_origin)
        cutting_plane_heel.rotate(math.radians(self.strut_inclination + 90), rot_axis, p_heel)
        return [Plane.from_frame(cutting_plane_heel), Plane.from_frame(cutting_plane_end)]

    def _calculate_tapered_heel_planes(self, ref_side):
        """Calculate cutting planes for a tapered heel notch."""
        # Move the frames to the start and end of the notch to create the cuts
        p_origin = ref_side.point_at(self.start_x, self.start_y)
        p_end = ref_side.point_at(self.start_x + self.displacement_end, self.start_y)
        cutting_plane_origin = Frame(p_origin, ref_side.frame.xaxis, -ref_side.frame.yaxis)
        cutting_plane_end = Frame(p_end, ref_side.frame.xaxis, ref_side.frame.yaxis)
        # Calculate heel cutting planes angles
        angle_origin = math.radians(self.strut_inclination)
        angle_end = math.atan(
            self.heel_depth
            / (abs(self.displacement_end) - abs(self.heel_depth / math.tan(math.radians(self.strut_inclination))))
        )
        rot_axis = ref_side.frame.yaxis
        if self.orientation == OrientationType.START:
            rot_axis = -rot_axis
        # Rotate the cutting planes
        cutting_plane_origin.rotate(angle_origin, rot_axis, p_origin)
        cutting_plane_end.rotate(angle_end, rot_axis, p_end)
        return [Plane.from_frame(cutting_plane_origin), Plane.from_frame(cutting_plane_end)]

    def _calculate_double_planes(self, ref_side):
        """Calculate cutting planes for a double notch."""
        # Move the frames to the start and end of the notch to create the cutsy
        p_heel = ref_side.point_at(self.start_x + self.displacement_heel, self.start_y)
        cutting_plane_heel_step = Frame(p_heel, ref_side.frame.xaxis, ref_side.frame.yaxis)
        # Calculate step cutting planes angles
        dx = self.step_depth / math.tan(math.radians(180 - self.strut_inclination / 2))
        if self.orientation == OrientationType.START:
            dx = -dx
        angle_long_side_step = math.atan(self.step_depth / (self.displacement_end - self.displacement_heel - dx))
        # Rotate the cutting planes
        cutting_plane_heel_step.rotate(angle_long_side_step, ref_side.frame.yaxis, p_heel)
        # Get the heel and step cutting planes
        heel_planes = self._calculate_heel_planes(ref_side)
        step_planes = self._calculate_step_planes(ref_side)
        step_planes[0] = Plane.from_frame(cutting_plane_heel_step) # replace the first step plane with the heel-step plane
        return heel_planes + step_planes

    def mortise_volume_from_params_and_beam(self, beam):
        """Calculates the mortise volume from the machining parameters in this instance and the given beam

        Parameters
        ----------
        beam : :class:`compas_timber.elements.Beam`
            The beam that is cut by this instance.

        Returns
        -------
        :class:`compas.geometry.Box`
            The mortise volume.

        """
        # type: (Beam) -> Box

        assert self.strut_inclination is not None
        assert self.step_shape is not None
        assert self.strut_height is not None
        assert self.notch_width is not None
        assert self.mortise_width is not None
        assert self.mortise_height is not None

        # start with a plane aligned with the ref side but shifted to the start of the first cut
        ref_side = beam.side_as_surface(self.ref_side_index)
        ref_side.point -= ref_side.zaxis * (self.mortise_height / 2)

        dx = self.strut_height / math.sin(math.radians(self.strut_inclination))
        dy = self.mortise_width

        start_x = self.start_x + dx/2 if self.orientation == OrientationType.START else self.start_x - dx/2
        start_y = ref_side.ysize / 2

        box_origin = ref_side.point_at(start_x, start_y)
        box_frame =  Frame(box_origin, ref_side.frame.xaxis, ref_side.frame.yaxis)
        if self.orientation == OrientationType.END:
            box_frame.xaxis = -box_frame.xaxis

        return Box(dx, dy, self.mortise_height, box_frame)


class StepJointNotchParams(BTLxProcessingParams):
    """A class to store the parameters of a Step Joint Notch feature.

    Parameters
    ----------
    instance : :class:`~compas_timber.fabrication.StepJointNotch`
        The instance of the Step Joint Notch feature.
    """

    def __init__(self, instance):
        # type: (StepJointNotch) -> None
        super(StepJointNotchParams, self).__init__(instance)

    def as_dict(self):
        """Returns the parameters of the Step Joint Notch feature as a dictionary.

        Returns
        -------
        dict
            The parameters of the Step Joint Notch as a dictionary.
        """
        # type: () -> OrderedDict
        result = OrderedDict()
        result["Orientation"] = self._instance.orientation
        result["StartX"] = "{:.{prec}f}".format(float(self._instance.start_x), prec=TOL.precision)
        result["StartY"] = "{:.{prec}f}".format(float(self._instance.start_y), prec=TOL.precision)
        result["StrutInclination"] = "{:.{prec}f}".format(float(self._instance.strut_inclination), prec=TOL.precision)
        result["NotchLimited"] = "yes" if self._instance.notch_limited else "no"
        result["NotchWidth"] = "{:.{prec}f}".format(float(self._instance.notch_width), prec=TOL.precision)
        result["StepDepth"] = "{:.{prec}f}".format(float(self._instance.step_depth), prec=TOL.precision)
        result["HeelDepth"] = "{:.{prec}f}".format(float(self._instance.heel_depth), prec=TOL.precision)
        result["StrutHeight"] = "{:.{prec}f}".format(float(self._instance.strut_height), prec=TOL.precision)
        result["StepShape"] = self._instance.step_shape
        result["Mortise"] = "yes" if self._instance.mortise else "no"
        result["MortiseWidth"] = "{:.{prec}f}".format(float(self._instance.mortise_width), prec=TOL.precision)
        result["MortiseHeight"] = "{:.{prec}f}".format(float(self._instance.mortise_height), prec=TOL.precision)
        return result
