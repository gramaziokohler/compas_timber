import math
from collections import OrderedDict

from compas.geometry import Box
from compas.geometry import Brep
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
from .btlx import StepShapeType


class StepJoint(BTLxProcessing):
    """Represents a Step Joint feature to be made on a beam.

    Parameters
    ----------
    orientation : int
        The orientation of the cut. Must be either OrientationType.START or OrientationType.END.
    start_x : float
        The start x-coordinate of the cut in parametric space of the reference side. -100000.0 < start_x < 100000.0.
    strut_inclination : float
        The inclination of the strut. 0.1 < strut_inclination < 179.9.
    step_depth : float
        The depth of the step. step_depth < 50000.0.
    heel_depth : float
        The depth of the heel. heel_depth < 50000.0.
    step_shape : str
        The shape of the step. Must be either 'double', 'step', 'heel', or 'taperedheel'.
    tenon : str
        The presence of a tenon. Must be either 'no' or 'yes'.
    tenon_width : float
        The width of the tenon. tenon_width < 1000.0.
    tenon_height : float
        The height of the tenon. tenon_height < 1000.0.

    """

    PROCESSING_NAME = "StepJoint"  # type: ignore

    @property
    def __data__(self):
        data = super(StepJoint, self).__data__
        data["orientation"] = self.orientation
        data["start_x"] = self.start_x
        data["strut_inclination"] = self.strut_inclination
        data["step_depth"] = self.step_depth
        data["heel_depth"] = self.heel_depth
        data["step_shape"] = self.step_shape
        data["tenon"] = self.tenon
        data["tenon_width"] = self.tenon_width
        data["tenon_height"] = self.tenon_height
        return data

    # fmt: off
    def __init__(
        self,
        orientation=OrientationType.START,
        start_x=0.0,
        strut_inclination=90.0,
        step_depth=20.0,
        heel_depth=20.0,
        step_shape=StepShapeType.DOUBLE,
        tenon=False,
        tenon_width=40.0,
        tenon_height=40.0,
        **kwargs
    ):
        super(StepJoint, self).__init__(**kwargs)
        self._orientation = None
        self._start_x = None
        self._strut_inclination = None
        self._step_depth = None
        self._heel_depth = None
        self._step_shape = None
        self._tenon = None
        self._tenon_width = None
        self._tenon_height = None

        self.orientation = orientation
        self.start_x = start_x
        self.strut_inclination = strut_inclination
        self.step_depth = step_depth
        self.heel_depth = heel_depth
        self.step_shape = step_shape
        self.tenon = tenon
        self.tenon_width = tenon_width
        self.tenon_height = tenon_height

    ########################################################################
    # Properties
    ########################################################################

    @property
    def params(self):
        return StepJointParams(self)

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
    def strut_inclination(self):
        return self._strut_inclination

    @strut_inclination.setter
    def strut_inclination(self, strut_inclination):
        if strut_inclination < 0.1 or strut_inclination > 179.9 or strut_inclination == 90.0:
            raise ValueError("StrutInclination must be between 0.1 and 89.9 or 90.1 and 179.9.")
        self._strut_inclination = strut_inclination

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
    def tenon(self):
        return self._tenon

    @tenon.setter
    def tenon(self, tenon):
        if not isinstance(tenon, bool):
            raise ValueError("tenon must be either True or False.")
        self._tenon = tenon

    @property
    def tenon_width(self):
        return self._tenon_width

    @tenon_width.setter
    def tenon_width(self, tenon_width):
        if tenon_width > 1000.0:
            raise ValueError("tenonWidth must be less than 1000.0.")
        self._tenon_width = tenon_width

    @property
    def tenon_height(self):
        return self._tenon_height

    @tenon_height.setter
    def tenon_height(self, tenon_height):
        if tenon_height > 1000.0:
            raise ValueError("tenonHeight must be less than 1000.0.")
        self._tenon_height = tenon_height

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
    def from_plane_and_beam(cls, plane, beam, step_depth=20.0, heel_depth=0.0, tapered_heel=False, ref_side_index=0):
        """Create a StepJoint instance from a cutting surface and the beam it should cut. This could be the ref_side of the cross beam of a Joint and the main beam.

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
        :class:`~compas_timber.fabrication.StepJoint`

        """
        # type: (Plane|Frame, Beam, float, float, bool, int) -> StepJoint

        if isinstance(plane, Frame):
            plane = Plane.from_frame(plane)
        plane.normal = plane.normal * -1  # flip the plane normal to point towards the beam
        # define ref_side & ref_edge
        ref_side = beam.ref_sides[ref_side_index]
        ref_edge = Line.from_point_and_vector(ref_side.point, ref_side.xaxis)

        # calculate orientation
        orientation = cls._calculate_orientation(ref_side, plane)

        # calculate start_x
        point_start_x = intersection_line_plane(ref_edge, plane)
        if point_start_x is None:
            raise ValueError("Plane does not intersect with beam.")
        start_x = distance_point_point(ref_side.point, point_start_x)

        # calculate strut_inclination
        strut_inclination = cls._calculate_strut_inclination(ref_side, plane)

        # define step_shape
        step_shape = cls._define_step_shape(step_depth, heel_depth, tapered_heel)

        return cls(
            orientation, start_x, strut_inclination, step_depth, heel_depth, step_shape, ref_side_index=ref_side_index
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
    def _calculate_strut_inclination(ref_side, plane):
        # vector rotation direction of the plane's normal in the vertical direction
        strut_inclination_vector = Vector.cross(ref_side.zaxis, plane.normal)
        strut_inclination = 180 - abs(
            angle_vectors_signed(ref_side.zaxis, plane.normal, strut_inclination_vector, deg=True)
        )
        return strut_inclination

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
    def _calculate_y_displacement_end(beam_height, strut_inclination):
        # Calculates the linear displacement along the y-axis of the ref_side from the origin point to the opposite end of the step.
        displacement_end = beam_height / math.sin(math.radians(strut_inclination))
        return displacement_end

    @staticmethod
    def _calculate_x_displacement_end(beam_height, strut_inclination, orientation):
        # Calculates the linear displacement along the x-axis of the ref_side from the origin point to the opposite end of the step.
        displacement_end = beam_height / math.tan(math.radians(strut_inclination))
        if orientation == OrientationType.END:
            displacement_end = -displacement_end
        return displacement_end

    @staticmethod
    def _calculate_x_displacement_heel(heel_depth, strut_inclination, orientation):
        # Calculates the linear displacement alond the x-axis of the ref_side from the origin point to the heel.
        displacement_heel = heel_depth / (math.sin(math.radians(strut_inclination)))
        if orientation == OrientationType.START:
            displacement_heel = -displacement_heel
        return displacement_heel

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

        # get cutting planes from params and beam
        try:
            cutting_planes = self.planes_from_params_and_beam(beam)
        except ValueError as e:
            raise FeatureApplicationError(
                None, geometry, "Failed to generate cutting planes from parameters and beam: {}".format(str(e))
            )

        if self.step_shape == StepShapeType.STEP:
            for cutting_plane in cutting_planes:
                cutting_plane.normal = cutting_plane.normal * -1
                try:
                    geometry.trim(cutting_plane)
                except Exception as e:
                    raise FeatureApplicationError(
                        cutting_plane, geometry, "Failed to trim geometry with cutting planes: {}".format(str(e))
                    )

        elif self.step_shape == StepShapeType.HEEL:
            trimmed_geometies = []
            for cutting_plane in cutting_planes:
                cutting_plane.normal = cutting_plane.normal * -1
                try:
                    trimmed_geometies.append(geometry.trimmed(cutting_plane))
                except Exception as e:
                    raise FeatureApplicationError(
                        cutting_plane, geometry, "Failed to trim geometry with cutting plane: {}".format(str(e))
                    )
            try:
                geometry = (
                    trimmed_geometies[0] + trimmed_geometies[1]
                )  # TODO: should be swed (.sew()) for a cleaner Brep
            except Exception as e:
                raise FeatureApplicationError(
                    trimmed_geometies, geometry, "Failed to union trimmed geometries: {}".format(str(e))
                )

        elif self.step_shape == StepShapeType.TAPERED_HEEL:
            try:
                cutting_plane = cutting_planes[0]
                cutting_plane.normal = cutting_plane.normal * -1
                geometry.trim(cutting_plane)
            except Exception as e:
                raise FeatureApplicationError(
                    cutting_planes, geometry, "Failed to trim geometry with cutting plane: {}".format(str(e))
                )

        elif self.step_shape == StepShapeType.DOUBLE:
            # trim geometry with last cutting plane
            cutting_planes[-1].normal = cutting_planes[-1].normal * -1
            try:
                geometry.trim(cutting_planes[-1])
            except Exception as e:
                raise FeatureApplicationError(
                    cutting_planes[-1], geometry, "Failed to trim geometry with cutting plane: {}".format(str(e))
                )
            # trim geometry with first two cutting planes
            trimmed_geometies = []
            for cutting_plane in cutting_planes[:2]:
                cutting_plane.normal = cutting_plane.normal * -1
                try:
                    trimmed_geometies.append(geometry.trimmed(cutting_plane))
                except Exception as e:
                    raise FeatureApplicationError(
                        cutting_plane, geometry, "Failed to trim geometry with cutting plane: {}".format(str(e))
                    )
            try:
                geometry = (
                    trimmed_geometies[0] + trimmed_geometies[1]
                )  # TODO: should be swed (.sew()) for a cleaner Brep
            except Exception as e:
                raise FeatureApplicationError(
                    trimmed_geometies, geometry, "Failed to union trimmed geometries: {}".format(str(e))
                )

        if self.tenon and self.step_shape != StepShapeType.DOUBLE:  # TODO: check if tenon applies only to step in BTLx
            # create tenon volume and subtract from brep
            tenon_volume = self.tenon_volume_from_params_and_beam(beam)
            cutting_planes[0].normal = cutting_planes[0].normal * -1
            if self.step_shape == StepShapeType.STEP:
                # trim tenon volume with cutting plane
                try:
                    tenon_volume.trim(cutting_planes[0])
                except Exception as e:
                    raise FeatureApplicationError(
                        cutting_planes[0],
                        tenon_volume,
                        "Failed to trim tenon volume with cutting plane: {}".format(str(e)),
                    )
                # trim tenon volume with second cutting plane if tenon height is greater than step depth
                if self.tenon_height > self.step_depth:
                    try:
                        tenon_volume.trim(cutting_planes[1])
                    except Exception as e:
                        raise FeatureApplicationError(
                            cutting_planes[1],
                            tenon_volume,
                            "Failed to trim tenon volume with second cutting plane: {}".format(str(e)),
                        )
            # add tenon volume to geometry
            try:
                geometry += tenon_volume
            except Exception as e:
                raise FeatureApplicationError(
                    tenon_volume, geometry, "Failed to add tenon volume to geometry: {}".format(str(e))
                )

        return geometry

    def add_tenon(self, tenon_width, tenon_height):
        """Add a tenon to the existing StepJointNotch instance.

        Parameters
        ----------
        tenon_width : float
            The width of the tenon. tenon_width < 1000.0.
        tenon_height : float
            The height of the tenon. tenon_height < 1000.0.
        """
        self.tenon = True
        self.tenon_width = tenon_width
        self.tenon_height = (
            self.step_depth if tenon_height < self.step_depth else tenon_height
        )  # TODO: should this be constrained?

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
        assert self.orientation is not None
        assert self.strut_inclination is not None
        assert self.step_shape is not None

        # Get the reference side as a PlanarSurface for the first cut
        ref_side = beam.side_as_surface(self.ref_side_index)
        # Get the opposite side as a PlanarSurface for the second cut and calculate the additional displacement along the xaxis
        opp_side = beam.side_as_surface((self.ref_side_index + 2) % 4)

        # Determine whether to use the beam's width or height based on the alignment of the reference side normal.
        # If the reference side normal and the frame normal are aligned, use the beam's height as the "width" for calculations.
        if abs(beam.ref_sides[self.ref_side_index].normal.dot(beam.frame.normal)) > 0.0:
            beam_width = beam.height
        else:
            beam_width = beam.width
        # Calculate the displacements for the cutting planes along the y-axis and x-axis
        y_displacement_end = self._calculate_y_displacement_end(beam_width, self.strut_inclination)
        x_displacement_end = self._calculate_x_displacement_end(beam_width, self.strut_inclination, self.orientation)
        x_displacement_heel = self._calculate_x_displacement_heel(
            self.heel_depth, self.strut_inclination, self.orientation
        )

        # Get the points at the start of the step, at the end and at the heel
        p_ref = ref_side.point_at(self.start_x, 0)
        p_opp = opp_side.point_at(self.start_x + x_displacement_end, beam.width)
        p_heel = ref_side.point_at(self.start_x + x_displacement_heel, 0)
        # Create cutting planes at the start of the step, at the end and at the heel
        cutting_plane_ref = Frame(p_ref, ref_side.frame.xaxis, ref_side.frame.yaxis)
        cutting_plane_opp = Frame(p_opp, ref_side.frame.xaxis, ref_side.frame.yaxis)
        cutting_plane_heel = Frame(p_heel, ref_side.frame.xaxis, ref_side.frame.yaxis)

        if self.orientation == OrientationType.START:
            rot_axis = cutting_plane_ref.yaxis
        else:
            rot_axis = -cutting_plane_ref.yaxis

        if self.step_shape == StepShapeType.STEP:
            return self._calculate_step_planes(cutting_plane_ref, cutting_plane_opp, y_displacement_end, rot_axis)
        elif self.step_shape == StepShapeType.HEEL:
            return self._calculate_heel_planes(cutting_plane_heel, cutting_plane_opp, rot_axis)
        elif self.step_shape == StepShapeType.TAPERED_HEEL:
            return self._calculate_heel_tapered_planes(cutting_plane_opp, y_displacement_end, rot_axis)
        elif self.step_shape == StepShapeType.DOUBLE:
            return self._calculate_double_planes(
                cutting_plane_heel, cutting_plane_opp, y_displacement_end, x_displacement_heel, rot_axis
            )

    def _calculate_step_planes(self, cutting_plane_ref, cutting_plane_opp, displacement_end, rot_axis):
        """Calculate cutting planes for a step."""
        # Rotate cutting plane at opp_side
        angle_opp = math.radians(self.strut_inclination / 2)
        rot_opp = Rotation.from_axis_and_angle(rot_axis, angle_opp, point=cutting_plane_opp.point)
        cutting_plane_opp.transform(rot_opp)

        # Rotate cutting plane at ref_side
        angle_ref = math.radians(self.strut_inclination) + math.atan(
            self.step_depth / (displacement_end - self.step_depth / math.tan(angle_opp))
        )
        rot_ref = Rotation.from_axis_and_angle(rot_axis, angle_ref, point=cutting_plane_ref.point)
        cutting_plane_ref.transform(rot_ref)

        return [Plane.from_frame(cutting_plane_ref), Plane.from_frame(cutting_plane_opp)]

    def _calculate_heel_planes(self, cutting_plane_heel, cutting_plane_opp, rot_axis):
        """Calculate cutting planes for a heel."""
        # Rotate cutting plane at displaced origin
        angle_heel = math.radians(90)
        rot_heel = Rotation.from_axis_and_angle(rot_axis, angle_heel, point=cutting_plane_heel.point)
        cutting_plane_heel.transform(rot_heel)

        # Rotate cutting plane at opp_side
        angle_opp = math.radians(self.strut_inclination)
        rot_opp = Rotation.from_axis_and_angle(rot_axis, angle_opp, point=cutting_plane_opp.point)
        cutting_plane_opp.transform(rot_opp)

        return [Plane.from_frame(cutting_plane_heel), Plane.from_frame(cutting_plane_opp)]

    def _calculate_heel_tapered_planes(self, cutting_plane_opp, displacement_end, rot_axis):
        """Calculate cutting planes for a tapered heel."""
        # Rotate cutting plane at opp_side
        angle_opp = math.radians(self.strut_inclination) - math.atan(
            self.heel_depth
            / (displacement_end - (self.heel_depth / abs(math.tan(math.radians(self.strut_inclination)))))
        )
        rot_opp = Rotation.from_axis_and_angle(rot_axis, angle_opp, point=cutting_plane_opp.point)
        cutting_plane_opp.transform(rot_opp)

        return [Plane.from_frame(cutting_plane_opp)]

    def _calculate_double_planes(
        self, cutting_plane_heel, cutting_plane_opp, displacement_end, displacement_heel, rot_axis
    ):
        """Calculate cutting planes for a double step."""
        # Rotate first cutting plane at displaced origin
        rot_origin = Rotation.from_axis_and_angle(rot_axis, math.radians(90), point=cutting_plane_heel.point)
        cutting_plane_heel.transform(rot_origin)

        # Rotate last cutting plane at opp_side
        rot_opp = Rotation.from_axis_and_angle(
            rot_axis, math.radians(self.strut_inclination / 2), point=cutting_plane_opp.point
        )
        cutting_plane_opp.transform(rot_opp)

        # Translate first cutting plane at heel
        trans_len = math.tan(math.radians(self.strut_inclination)) * displacement_heel
        trans_vect = cutting_plane_heel.xaxis
        cutting_plane_heel_mid = cutting_plane_heel.translated(trans_vect * trans_len)
        # Calculate rotation angle for middle cutting plane
        heel_hypotenus = math.sqrt(math.pow(trans_len, 2) + math.pow(displacement_heel, 2))
        angle_heel = (
            math.radians(self.strut_inclination)
            - math.radians(90)
            + math.atan(
                self.step_depth
                / (
                    displacement_end
                    - heel_hypotenus
                    - self.step_depth / math.tan(math.radians(self.strut_inclination / 2))
                )
            )
        )

        # Rotate middle cutting plane at heel
        rot_heel = Rotation.from_axis_and_angle(rot_axis, angle_heel, point=cutting_plane_heel_mid.point)
        cutting_plane_heel_mid.transform(rot_heel)

        return [
            Plane.from_frame(cutting_plane_heel),
            Plane.from_frame(cutting_plane_heel_mid),
            Plane.from_frame(cutting_plane_opp),
        ]

    def tenon_volume_from_params_and_beam(self, beam):
        """Calculates the tenon volume from the machining parameters in this instance and the given beam

        Parameters
        ----------
        beam : :class:`compas_timber.elements.Beam`
            The beam that is cut by this instance.

        Returns
        -------
        :class:`compas.geometry.Brep`
            The tenon volume.

        """
        # type: (Beam) -> Brep
        assert self.tenon_width is not None
        assert self.tenon_height is not None

        # start with a plane aligned with the ref side but shifted to the start of the first cut
        ref_side = beam.ref_sides[self.ref_side_index]
        ref_surface = beam.side_as_surface(self.ref_side_index)
        beam_height = beam.side_as_surface((self.ref_side_index+1)%4).ysize

        # calculate the dx and dy of the tenon volume
        dx = beam_height/math.sin(math.radians(self.strut_inclination))
        dy = self.tenon_width

        start_x = self.start_x
        start_y = ref_surface.ysize/2

        # create a box volume for the tenon
        box_origin = ref_surface.point_at(start_x, start_y)
        box_frame = Frame(box_origin, ref_side.xaxis, ref_side.yaxis)
        tenon_box = Box(dx, dy, self.tenon_height, box_frame)

        # translate the box to the correct position and rotate it to the strut inclination
        xaxis_vector = box_frame.xaxis * (dx/2)
        zaxis_vector = -box_frame.zaxis * (self.tenon_height/2)
        if self.orientation == OrientationType.END:
            inclination = math.radians(180-self.strut_inclination)
            zaxis_vector = -zaxis_vector
        else:
            inclination = math.radians(self.strut_inclination)
        tenon_box.translate(xaxis_vector + zaxis_vector)

        # rotate the tenon volume to the strut inclination
        rotation = Rotation.from_axis_and_angle(ref_side.yaxis, inclination, box_frame.point)
        tenon_box.transform(rotation)

        # convert to Brep and trim with ref_side
        tenon_brep = Brep.from_box(tenon_box)
        try:
            tenon_brep.trim(ref_side)
        except Exception as e:
            raise FeatureApplicationError(
                None, tenon_brep, "Failed to trim tenon volume with cutting planes: {}".format(str(e))
            )
        return tenon_brep


class StepJointParams(BTLxProcessingParams):
    """A class to store the parameters of a Step Joint feature.

    Parameters
    ----------
    instance : :class:`~compas_timber.fabrication.StepJoint`
        The instance of the Step Joint feature.
    """

    def __init__(self, instance):
        # type: (StepJoint) -> None
        super(StepJointParams, self).__init__(instance)

    def as_dict(self):
        """Returns the parameters of the Step Joint feature as a dictionary.

        Returns
        -------
        dict
            The parameters of the Step Joint as a dictionary.
        """
        # type: () -> OrderedDict
        result = OrderedDict()
        result["Orientation"] = self._instance.orientation
        result["StartX"] = "{:.{prec}f}".format(float(self._instance.start_x), prec=TOL.precision)
        result["StrutInclination"] = "{:.{prec}f}".format(float(self._instance.strut_inclination), prec=TOL.precision)
        result["StepDepth"] = "{:.{prec}f}".format(float(self._instance.step_depth), prec=TOL.precision)
        result["HeelDepth"] = "{:.{prec}f}".format(float(self._instance.heel_depth), prec=TOL.precision)
        result["StepShape"] = self._instance.step_shape
        result["Tenon"] = "yes" if self._instance.tenon else "no"
        result["TenonWidth"] = "{:.{prec}f}".format(float(self._instance.tenon_width), prec=TOL.precision)
        result["TenonHeight"] = "{:.{prec}f}".format(float(self._instance.tenon_height), prec=TOL.precision)
        return result
