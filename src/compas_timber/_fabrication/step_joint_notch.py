import math

from compas.geometry import BrepTrimmingError
from compas.geometry import Frame
from compas.geometry import Line
from compas.geometry import Plane
from compas.geometry import Rotation
from compas.geometry import Vector
from compas.geometry import Surface
from compas.geometry import PlanarSurface
from compas.geometry import angle_vectors_signed
from compas.geometry import distance_point_point
from compas.geometry import intersection_line_plane
from compas.geometry import is_point_behind_plane
from compas.tolerance import TOL


from compas_timber.elements import FeatureApplicationError

from .btlx_process import BTLxProcess
from .btlx_process import BTLxProcessParams
from .btlx_process import OrientationType


class StepJointNotch(BTLxProcess):
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
        The shape of the step. Must be either 'double', 'step', 'heel', or 'taperedheel'.
    mortise : str
        The presence of a mortise. Must be either 'no' or 'yes'.
    mortise_width : float
        The width of the mortise. mortise_width < 1000.0.
    mortise_height : float
        The height of the mortise. mortise_height < 1000.0.

    """

    PROCESS_NAME = "StepJointNotch"  # type: ignore

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

    def __init__(self, orientation, start_x=0.0, start_y=0.0, strut_inclination=90.0, notch_limited="no", notch_width=20.0, step_depth=20.0, heel_depth=20.0, strut_height=20.0, step_shape="double", mortise="no", mortise_width=40.0, mortise_height=40.0, **kwargs):
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
    def params_dict(self):
        return StepJointNotchParams(self).as_dict()

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
        if strut_inclination < 0.1 or strut_inclination > 179.9:
            raise ValueError("StrutInclination must be between 0.1 and 179.9.")
        self._strut_inclination = strut_inclination

    @property
    def notch_limited(self):
        return self._notch_limited

    @notch_limited.setter
    def notch_limited(self, notch_limited):
        if notch_limited not in ["no", "yes"]:
            raise ValueError("NotchLimited must be either 'no' or 'yes'.")
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

    @step_shape.setter #TODO: should this be defined automatically depending on the other parameters? (ie. if heel_depth > 0 and step_depth > 0, then step_shape = "double")
    def step_shape(self, step_shape):
        if step_shape not in ["double", "step", "heel", "taperedheel"]:
            raise ValueError("StepShape must be either 'double', 'step', 'heel', or 'taperedheel'.")
        self._step_shape = step_shape

    @property
    def mortise(self):
        return self._mortise

    @mortise.setter
    def mortise(self, mortise):
        if mortise not in ["no", "yes"]:
            raise ValueError("Mortise must be either 'no' or 'yes'.")
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

    ########################################################################
    # Alternative constructors
    ########################################################################

    @classmethod
    def from_surface_and_beam(cls, surface, beam, notch_limited=False, step_depth=20.0, heel_depth=0.0, strut_height=20.0, tapered_heel=False, ref_side_index=0):
        """Create a StepJointNotch instance from a cutting surface and the beam it should cut. This could be the ref_side of the main beam of a Joint.

        Parameters
        ----------
        surface : :class:`~compas.geometry.PlanarSurface` or :class:`~compas.geometry.Surface`
            The cutting surface.
        beam : :class:`~compas_timber.elements.Beam`
            The beam that is cut by this instance.
        ref_side_index : int, optional
            The reference side index of the beam to be cut. Default is 0 (i.e. RS1).

        Returns
        -------
        :class:`~compas_timber.fabrication.StepJointNotch`

        """
        # type: (PlanarSurface|Surface, Beam, bool, float, float, float, bool, int) -> StepJointNotch
        #TODO: the stepjointnotch is always orthogonal, this means that the surface should be perpendicular to the beam's ref_side | should there be a check for that?
        #TODO: I am using a PlanarSurface instead of a Plane because otherwise there is no way to define the start_y of the Notch
        #TODO: The alternative in order to use a Plane instead would be to have start_y and notch_width as parameters of the class
        # define ref_side & ref_edge
        ref_side = beam.ref_sides[ref_side_index]  # TODO: is this arbitrary?
        ref_edge = Line.from_point_and_vector(ref_side.point, ref_side.xaxis)
        plane = surface.to_plane()
        intersection_line = Line(*ref_side.intersections_with_surface(surface)) #TODO NotImplementedError: Plane|Surface // COMPAS core issue

        # calculate orientation
        orientation = cls._calculate_orientation(ref_side, plane)

        # calculate start_x
        point_start_x = intersection_line_plane(ref_edge, plane)
        if point_start_x is None:
            raise ValueError("Surface does not intersect with beam.")
        start_x = distance_point_point(ref_side.point, point_start_x)

        # calculate start_y
        start_y = cls._calculate_start_y(orientation, intersection_line, point_start_x, ref_side)

        # calculate strut_inclination
        strut_inclination = cls._calculate_strut_inclination(ref_side, plane, orientation)

        # calculate notch_width
        if notch_limited == True:
            notch_width = intersection_line.length
            notch_limited = "yes"
        else:
            notch_width = beam.width
            notch_limited = "no"

        # restrain step_depth & heel_depth to beam's height # TODO: should it be restrained? should they be proportional to the beam's dimensions?
        step_depth = beam.height if step_depth > beam.height else step_depth
        heel_depth = beam.height if heel_depth > beam.height else heel_depth

        # define step_shape
        step_shape = cls._define_step_shape(step_depth, heel_depth, tapered_heel)

        return cls(orientation, start_x, start_y, strut_inclination, notch_limited, notch_width, step_depth, heel_depth, step_shape, strut_height, ref_side_index=ref_side_index)

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
        # if out then start_y = 0.0, otherwise it calculates the displacement
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
        if orientation == OrientationType.START:
            return abs(strut_inclination)
        else:
            return 180 - abs(strut_inclination) # get the other side of the angle

    @staticmethod
    def _define_step_shape(step_depth, heel_depth, tapered_heel):
        # step_shape based on step_depth and heel_depth and tapered_heel variables
        if step_depth > 0.0 and heel_depth == 0.0:
            step_shape = "step"
        elif step_depth == 0.0 and heel_depth > 0.0:
            if tapered_heel:
                step_shape = "heel_tapered"
            else:
                step_shape = "heel"
        elif step_depth > 0.0 and heel_depth > 0.0:
            step_shape = "double"
        else:
            raise ValueError("at least one of step_depth or heel_depth must be greater than 0.0.")
        return step_shape

    @classmethod
    def from_two_planes_and_beam(cls, plane_a, plane_b, beam, ref_side_index=0):
        """Create a StepJointNotch instance from two planes and the beam it should cut.

        Parameters
        ----------
        plane_a : :class:`~compas.geometry.Plane`
            The first cutting plane.
        plane_b : :class:`~compas.geometry.Plane`
            The second cutting plane.
        beam : :class:`~compas_timber.elements.Beam`
            The beam that is cut by this instance.
        ref_side_index : int, optional
            The reference side index of the beam to be cut. Default is 0 (i.e. RS1).

        Returns
        -------
        :class:`~compas_timber.fabrication.StepJointNotch`

        """
        # type: (Plane, Plane, Beam, int) -> StepJointNotch
        # define ref_side & ref_edge
        ref_side = beam.ref_sides[ref_side_index]
        pass

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
        cutting_planes = self.planes_from_params_and_beam(beam)
        try:
            return geometry.trimmed(cutting_plane)
        except BrepTrimmingError:
            raise FeatureApplicationError(
                cutting_plane,
                geometry,
                "The cutting plane does not intersect with beam geometry.",
            )

    def add_mortise(self, mortise_width, mortise_height):
        """Add a mortise to the existing StepJointNotch instance.

        Parameters
        ----------
        mortise_width : float
            The width of the mortise. mortise_width < 1000.0.
        mortise_height : float
            The height of the mortise. mortise_height < 1000.0.
        """
        self.mortise = "yes"
        self.mortise_width = mortise_width
        self.mortise_height = mortise_height
        # self.mortise_width = beam.width / 4  # TODO: should this be related to a beam? 1/3 or 1/4 of beam.width?
        # self.mortise_height = beam.height if mortise_height > beam.height else mortise_height #TODO: should this be constrained?

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
        # type: (Beam) -> Planes
        assert self.strut_inclination is not None
        assert self.step_shape is not None
        assert self.strut_height is not None

        # start with a plane aligned with the ref side but shifted to the start of the first cut
        ref_side = beam.side_as_surface(self.ref_side_index)


        if self.step_type == "step":
            start_displacement = self.strut_height / math.sin(math.radians(self.strut_inclination))
            rot_axis = ref_side.frame.yaxis
            if self.orientation==OrientationType.END:
                start_displacement = -start_displacement # negative displacement for the end cut
                rot_axis = -rot_axis # negative rotation axis for the end cut

            #move the frames to the start and end of the notch to create the cuts
            p_origin = ref_side.point_at(self.start_x, self.start_y)
            p_displaced = ref_side.point_at(self.start_x + start_displacement, self.start_y)
            cutting_plane_origin = Frame(p_origin, ref_side.frame.xaxis, ref_side.frame.yaxis)
            cutting_plane_displaced = Frame(p_displaced, ref_side.frame.xaxis, ref_side.frame.yaxis)

            if self.strut_inclination>90:
                # rotate first cutting plane at the start of the notch (large side of the step)
                angle_long_side = math.atan(self.step_depth / (start_displacement - self.step_depth/math.tan(math.radians(self.strut_inclination/2))))
                rot_long_side = Rotation.from_axis_and_angle(rot_axis, angle_long_side, point=p_origin)
                cutting_plane_origin.transform(rot_long_side)
                # rotate second cutting plane at the end of the notch (short side of the step)
                angle_short_side = math.radians(180-self.strut_inclination/2)
                rot_short_side = Rotation.from_axis_and_angle(rot_axis, angle_short_side, point=p_displaced)
                cutting_plane_displaced.transform(rot_short_side)
            else:
                # rotate first cutting plane at the start of the notch (short side of the step)
                angle_short_side = math.radians(90+self.strut_inclination/2) #math.radians(180-(180-self.strut_inclination)/2)
                rot_short_side = Rotation.from_axis_and_angle(rot_axis, angle_short_side, point=p_origin)
                cutting_plane_origin.transform(rot_short_side)
                # rotate second cutting plane at the end of the notch (large side of the step)
                angle_long_side = 180 - math.atan(self.step_depth / (start_displacement - self.step_depth/math.tan(math.radians(90-self.strut_inclination/2))))
                rot_long_side = Rotation.from_axis_and_angle(rot_axis, angle_long_side, point=p_displaced)
                cutting_plane_displaced.transform(rot_long_side)
            cutting_planes = [cutting_plane_origin, cutting_plane_displaced]

        elif self.step_type == "heel":
            if self.strut_inclination>90:
                start_displacement = abs(self.heel_depth / (math.sin(math.radians(self.strut_inclination))*math.cos(math.radians(self.strut_inclination)))) #abs() because cos(180-x)-->gives negative
                rot_axis = ref_side.frame.yaxis
                if self.orientation==OrientationType.END:
                    start_displacement = -start_displacement # negative displacement for the end cut
                    rot_axis = -rot_axis # negative rotation axis for the end cut

                #move the frames to the start and end of the notch to create the cuts
                p_origin = ref_side.point_at(self.start_x, self.start_y)
                p_displaced = ref_side.point_at(self.start_x + start_displacement, self.start_y)
                cutting_plane_origin = Frame(p_origin, ref_side.frame.xaxis, ref_side.frame.yaxis)
                cutting_plane_displaced = Frame(p_displaced, ref_side.frame.xaxis, ref_side.frame.yaxis)
                # rotate first cutting plane at the start of the notch (short side of the heel)
                angle_short_side = math.rad(180-self.strut_inclination)
                rot_short_side = Rotation.from_axis_and_angle(rot_axis, angle_short_side, point=p_origin)
                cutting_plane_origin.transform(rot_short_side)
                # rotate second cutting plane at the end of the notch (long side of the heel)
                angle_long_side = math.radians(270-self.strut_inclination)
                rot_long_side = Rotation.from_axis_and_angle(rot_axis, angle_long_side, point=p_displaced)
                cutting_plane_displaced.transform(rot_long_side)
            else:
                start_displacement_2 = self.heel_depth / (math.sin(math.radians(self.strut_inclination))*math.cos(math.radians(self.strut_inclination)))
                start_displacement_1 = start_displacement_2 - (self.strut_height / math.sin(math.radians(self.strut_inclination)))
                rot_axis = ref_side.frame.yaxis
                if self.orientation==OrientationType.END:
                    start_displacement_1, start_displacement_2 = -start_displacement_1, -start_displacement_2 # negative displacement for the start and end cut
                    rot_axis = -rot_axis # negative rotation axis for the end cut

                #move the frames to the start and end of the notch to create the cuts
                p_origin = ref_side.point_at(self.start_x+start_displacement_1, self.start_y)
                p_displaced = ref_side.point_at(self.start_x+start_displacement_2, self.start_y)
                cutting_plane_origin = Frame(p_origin, ref_side.frame.xaxis, ref_side.frame.yaxis)
                cutting_plane_displaced = Frame(p_displaced, ref_side.frame.xaxis, ref_side.frame.yaxis)
                # rotate first cutting plane at the translated start of the notch (long side of the heel)
                angle_long_side = math.radians(270+self.strut_inclination)
                rot_long_side = Rotation.from_axis_and_angle(rot_axis, angle_long_side, point=p_origin)
                cutting_plane_origin.transform(rot_long_side)
                # rotate second cutting plane at the end of the notch (short side of the heel)
                angle_short_side = math.radians(180+self.strut_inclination)
                rot_short_side = Rotation.from_axis_and_angle(rot_axis, angle_short_side, point=p_displaced)
                cutting_plane_displaced.transform(rot_short_side)
            cutting_planes = [cutting_plane_origin, cutting_plane_displaced]

        elif self.step_type == "heel_tapered":
            start_displacement = self.strut_height / math.sin(math.radians(self.strut_inclination))
            rot_axis = ref_side.frame.yaxis
            if self.orientation==OrientationType.END:
                start_displacement = -start_displacement # negative displacement for the end cut
                rot_axis = -rot_axis # negative rotation axis for the end cut

            #move the frames to the start and end of the notch to create the cuts
            p_origin = ref_side.point_at(self.start_x, self.start_y)
            p_displaced = ref_side.point_at(self.start_x + start_displacement, self.start_y)
            cutting_plane_origin = Frame(p_origin, ref_side.frame.xaxis, ref_side.frame.yaxis)
            cutting_plane_displaced = Frame(p_displaced, ref_side.frame.xaxis, ref_side.frame.yaxis)
            if self.strut_inclination>90:
                # rotate first cutting plane at the start of the notch (short side of the heel)
                angle_short_side = math.radians(180-self.strut_inclination)
                rot_short_side = Rotation.from_axis_and_angle(rot_axis, angle_short_side, point=p_origin)
                cutting_plane_origin.transform(rot_short_side)
                # rotate second cutting plane at the end of the notch (long side of the heel)
                angle_long_side = math.radians(180) - math.atan(self.heel_depth / (abs(start_displacement) - abs(self.heel_depth/math.tan(math.radians(self.strut_inclination)))))
                rot_long_side = Rotation.from_axis_and_angle(rot_axis, angle_long_side, point=p_displaced)
                cutting_plane_displaced.transform(rot_long_side)
            else:
                # rotate first cutting plane at the start of the notch (long side of the heel)
                angle_long_side = math.atan(self.heel_depth / (abs(start_displacement) - abs(self.heel_depth/math.tan(math.radians(self.strut_inclination)))))
                rot_long_side = Rotation.from_axis_and_angle(rot_axis, angle_long_side, point=p_origin)
                cutting_plane_origin.transform(rot_long_side)
                # rotate second cutting plane at the end of the notch (short side of the heel)
                angle_short_side = math.radians(180-self.strut_inclination)
                rot_short_side = Rotation.from_axis_and_angle(rot_axis, angle_short_side, point=p_displaced)
                cutting_plane_displaced.transform(rot_short_side)
            cutting_planes = [cutting_plane_origin, cutting_plane_displaced]

        elif self.step_type == "double":
            pass





        # # for simplicity, we always start with normal pointing towards xaxis.
        # # if start is cut, we need to flip the normal
        # if self.orientation == OrientationType.END:
        #     plane_normal = cutting_plane.xaxis
        # else:
        #     plane_normal = -cutting_plane.xaxis
        # return Plane(cutting_plane.point, plane_normal)
        return cutting_planes

class StepJointNotchParams(BTLxProcessParams):
    """A class to store the parameters of a Jack Rafter Cut feature.

    Parameters
    ----------
    instance : :class:`~compas_timber._fabrication.JackRafterCut`
        The instance of the Jack Rafter Cut feature.
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
        result = super(StepJointNotchParams, self).as_dict()
        result["Orientation"] = self._instance.orientation
        result["StartX"] = "{:.{prec}f}".format(self._instance.start_x, prec=TOL.precision)
        result["StartY"] = "{:.{prec}f}".format(self._instance.start_y, prec=TOL.precision)
        result["StrutInclination"] = "{:.{prec}f}".format(self._instance.strut_inclination, prec=TOL.precision)
        result["NotchLimited"] = self._instance.notch_limited
        result["NotchWidth"] = "{:.{prec}f}".format(self._instance.notch_width, prec=TOL.precision)
        result["StepDepth"] = "{:.{prec}f}".format(self._instance.step_depth, prec=TOL.precision)
        result["HeelDepth"] = "{:.{prec}f}".format(self._instance.heel_depth, prec=TOL.precision)
        result["StrutHeight"] = "{:.{prec}f}".format(self._instance.strut_height, prec=TOL.precision)
        result["StepShape"] = self._instance.step_shape
        result["Mortise"] = self._instance.mortise
        result["MortiseWidth"] = "{:.{prec}f}".format(self._instance.mortise_width, prec=TOL.precision)
        result["MortiseHeight"] = "{:.{prec}f}".format(self._instance.mortise_height, prec=TOL.precision)
        return result
