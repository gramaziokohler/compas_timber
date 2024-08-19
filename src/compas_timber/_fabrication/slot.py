from compas.tolerance import TOL

from .btlx_process import BTLxProcess
from .btlx_process import BTLxProcessParams
from .btlx_process import OrientationType


class Slot(BTLxProcess):

    PROCESS_NAME = "Slot"  # type: ignore

    def __init__(
        self,
        orientation,
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
    def params_dict(self):
        return SlotParams(self).as_dict()

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
        if start_y > 50000.0 or start_y < -50000.0:
            raise ValueError("Start Y must be between -50000.0 and 50000.0.")
        self._start_y = start_y

    @property
    def start_depth(self):
        return self._start_depth

    @start_depth.setter
    def start_depth(self, start_depth):
        if start_depth > 50000.0 or start_depth < 0.0:
            raise ValueError("Start Depth must be less than 50000.0 and positive.")
        self._start_depth = start_depth

    @property
    def angle(self):
        return self._angle

    @angle.setter
    def angle(self, angle):
        if angle < -90.0 or angle > 90.0:
            raise ValueError("Angle must be between -90.0 and 90.0.")
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
    def length(self):
        return self._length

    @length.setter
    def length(self, length):
        if length < 0.0 or length > 100000.0:
            raise ValueError("Length must be between 0.0 and 100000.0.")
        self._length = length

    @property
    def depth(self):
        return self._depth

    @depth.setter
    def depth(self, depth):
        if depth < 0.0 or depth > 50000.0:
            raise ValueError("Depth must be between 0.0 and 50000.0.")
        self._depth = depth

    @property
    def thickness(self):
        return self._thickness

    @thickness.setter
    def thickness(self, thickness):
        if thickness < 0.0 or thickness > 50000.0:
            raise ValueError("Thickness must be between 0.0 and 50000.0.")
        self._thickness = thickness

    @property
    def angle_ref_point(self):
        return self._angle_ref_point

    @angle_ref_point.setter
    def angle_ref_point(self, angle_ref_point):
        if angle_ref_point < 0.1 or angle_ref_point > 179.9:
            raise ValueError("Angle Ref Point must be between 0.1 and 179.9.")
        self._angle_ref_point = angle_ref_point

    @property
    def angle_opp_point(self):
        return self._angle_opp_point

    @angle_opp_point.setter
    def angle_opp_point(self, angle_opp_point):
        if angle_opp_point < 0.1 or angle_opp_point > 179.9:
            raise ValueError("Angle Opp Point must be between 0.1 and 179.9.")
        self._angle_opp_point = angle_opp_point

    @property
    def add_angle_opp_point(self):
        return self._add_angle_opp_point

    @add_angle_opp_point.setter
    def add_angle_opp_point(self, add_angle_opp_point):
        if add_angle_opp_point < -179.9 or add_angle_opp_point > 179.9:
            raise ValueError("Add Angle Opp Point must be between -179.9 and 179.9.")
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
    def from_box_and_beam(cls, box, beam, ref_side_index=0):
        """Construct a Slot feature from a box and a beam.

        Parameters
        ----------
        box : :class:`~compas.geometry.Box`
            The box to be cut.
        beam : :class:`~compas_timber.elements.Beam`
            The beam that is cut by this instance.

        Returns
        -------
        :class:`~compas_timber._fabrication.Slot`
            The constructed Slot feature.

        """
        # type: (Box, Beam) -> Slot
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
        return geometry.copy()


class SlotParams(BTLxProcessParams):
    """A class to store the parameters of a Jack Rafter Cut feature.

    Parameters
    ----------
    instance : :class:`~compas_timber._fabrication.JackRafterCut`
        The instance of the Jack Rafter Cut feature.

    """

    def __init__(self, instance):
        # type: (Slot) -> None
        super(SlotParams, self).__init__(instance)

    def as_dict(self):
        """Returns the parameters of the Jack Rafter Cut feature as a dictionary.

        Returns
        -------
        dict
            The parameters of the Jack Rafter Cut feature as a dictionary.
        """
        # type: () -> OrderedDict
        result = super(SlotParams, self).as_dict()
        result["Orientation"] = self._instance.orientation
        result["StartX"] = "{:.{prec}f}".format(self._instance.start_x, prec=TOL.precision)
        result["StartY"] = "{:.{prec}f}".format(self._instance.start_y, prec=TOL.precision)
        result["StartDepth"] = "{:.{prec}f}".format(self._instance.start_depth, prec=TOL.precision)
        result["Angle"] = "{:.{prec}f}".format(self._instance.angle, prec=TOL.precision)
        result["Inclination"] = "{:.{prec}f}".format(self._instance.inclination, prec=TOL.precision)
        result["Length"] = "{:.{prec}f}".format(self._instance.length, prec=TOL.precision)
        result["Depth"] = "{:.{prec}f}".format(self._instance.depth, prec=TOL.precision)
        result["Thickness"] = "{:.{prec}f}".format(self._instance.thickness, prec=TOL.precision)
        result["AngleRefPoint"] = "{:.{prec}f}".format(self._instance.angle_ref_point, prec=TOL.precision)
        result["AngleOppPoint"] = "{:.{prec}f}".format(self._instance.angle_opp_point, prec=TOL.precision)
        result["AddAngleOppPoint"] = "{:.{prec}f}".format(self._instance.add_angle_opp_point, prec=TOL.precision)
        result["MachiningLimits"] = {"FaceLimitedStart": "no", "FaceLimitedEnd": "no"}
        return result
